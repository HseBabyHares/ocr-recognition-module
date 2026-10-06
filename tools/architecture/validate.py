#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import fnmatch
import json
import pathlib
import subprocess

CATEGORIES = [
    "spoofing",
    "tampering",
    "repudiation",
    "information-disclosure",
    "denial-of-service",
    "elevation-of-privilege",
]


def load(root, rel, errors):
    artifact_path = root / rel
    if not artifact_path.exists():
        errors.append({"rule": "missing-artifact", "path": rel})
        return None
    try:
        return json.loads(artifact_path.read_text())
    except Exception as error:
        errors.append(
            {"rule": "invalid-json", "path": rel, "message": str(error)}
        )
        return None


def match(path, patterns):
    return any(
        fnmatch.fnmatch(path, pattern)
        or fnmatch.fnmatch(path, "**/" + pattern)
        for pattern in patterns
    )


def git(root, args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--policy", default="architecture/policy.json")
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument(
        "--mode", choices=["advisory", "strict"], default="strict"
    )
    parser.add_argument("--out")
    return parser.parse_args()


def _policy_unavailable_output(mode, errors, warnings):
    return {
        "schemaVersion": "1.0",
        "status": "blocked" if mode == "strict" else "not-configured",
        "errors": errors,
        "warnings": warnings,
    }


def _inactive_policy_output(policy, mode, warnings):
    return {
        "schemaVersion": "1.0",
        "status": "blocked" if mode == "strict" else "not-configured",
        "profile": policy.get("profile"),
        "changedFiles": [],
        "errors": [
            {
                "rule": "architecture-policy-unconfigured",
                "status": policy.get("status"),
            }
        ],
        "warnings": warnings,
        "counts": {
            "components": 0,
            "views": 0,
            "dfdElements": 0,
            "flows": 0,
            "threats": 0,
        },
    }


def _validate_required_files(root, policy, errors):
    for relative_path in policy.get("requiredFiles", []):
        if not (root / relative_path).exists():
            errors.append(
                {"rule": "missing-required-artifact", "path": relative_path}
            )


def _load_architecture_artifacts(root, errors):
    registry = load(root, "architecture/component-registry.json", errors) or {
        "components": []
    }
    views = load(root, "architecture/views.json", errors) or {"views": []}
    dfd = load(root, "security/threat-model/dfd.json", errors) or {}
    coverage = (
        load(root, "security/threat-model/stride-coverage.json", errors) or {}
    )
    threats = load(root, "security/threat-model/threats.json", errors) or {
        "threats": []
    }
    return registry, views, dfd, coverage, threats


def _index_components(registry, errors):
    components = {}
    for component in registry.get("components", []):
        component_id = component.get("id")
        if component_id in components:
            errors.append({"rule": "duplicate-component", "id": component_id})
        components[component_id] = component
    return components


def _validate_required_views(views, policy, errors):
    view_ids = {view.get("id") for view in views.get("views", [])}
    for required_view_id in policy.get("requiredViews", []):
        if required_view_id not in view_ids:
            errors.append({"rule": "missing-view", "id": required_view_id})
    return view_ids


def _index_dfd_elements(dfd, components, errors):
    elements = {}
    for element in dfd.get("elements", []):
        element_id = element.get("id")
        if element_id in elements:
            errors.append({"rule": "duplicate-dfd-element", "id": element_id})
        elements[element_id] = element
        if (
            element.get("componentId")
            and element["componentId"] not in components
        ):
            errors.append(
                {
                    "rule": "unknown-component-reference",
                    "subject": element_id,
                    "componentId": element.get("componentId"),
                }
            )
    return elements


def _index_and_validate_flows(dfd, elements, boundaries, errors):
    flows = {}
    for flow in dfd.get("flows", []):
        flow_id = flow.get("id")
        flows[flow_id] = flow
        if (
            flow.get("source") not in elements
            or flow.get("target") not in elements
        ):
            errors.append({"rule": "invalid-flow-endpoint", "id": flow_id})
        else:
            source_zone = elements[flow["source"]].get("trustZone")
            target_zone = elements[flow["target"]].get("trustZone")
            if (
                source_zone != target_zone
                and flow.get("trustBoundary") not in boundaries
            ):
                errors.append(
                    {
                        "rule": "missing-trust-boundary",
                        "id": flow_id,
                        "from": source_zone,
                        "to": target_zone,
                    }
                )
    return flows


def _validate_stride_coverage(subjects, threat_map, flows, elements, errors):
    expected_subjects = [("flow", flow_id) for flow_id in flows] + [
        (element.get("type"), element_id)
        for element_id, element in elements.items()
        if element.get("type") in {"process", "data-store", "external-entity"}
    ]
    for subject_key in expected_subjects:
        subject = subjects.get(subject_key)
        if not subject:
            errors.append(
                {
                    "rule": "missing-stride-subject",
                    "type": subject_key[0],
                    "id": subject_key[1],
                }
            )
            continue
        coverage = subject.get("coverage", {})
        for category in CATEGORIES:
            record = coverage.get(category)
            if not record:
                errors.append(
                    {
                        "rule": "missing-stride-category",
                        "subject": subject_key,
                        "category": category,
                    }
                )
                continue
            disposition = record.get("disposition")
            if disposition not in {"threat", "mitigated", "not-applicable"}:
                errors.append(
                    {
                        "rule": "invalid-stride-disposition",
                        "subject": subject_key,
                        "category": category,
                    }
                )
            if disposition in {"threat", "mitigated"} and not record.get(
                "refs"
            ):
                errors.append(
                    {
                        "rule": "missing-threat-reference",
                        "subject": subject_key,
                        "category": category,
                    }
                )
            if (
                disposition == "not-applicable"
                and not str(record.get("rationale") or "").strip()
            ):
                errors.append(
                    {
                        "rule": "missing-na-rationale",
                        "subject": subject_key,
                        "category": category,
                    }
                )
            for reference in record.get("refs", []):
                if reference not in threat_map:
                    errors.append(
                        {
                            "rule": "unknown-threat-reference",
                            "subject": subject_key,
                            "category": category,
                            "ref": reference,
                        }
                    )


def _validate_threats(threat_map, errors):
    now = datetime.datetime.now(datetime.timezone.utc)
    for threat in threat_map.values():
        for field in [
            "id",
            "subject",
            "stride",
            "scenario",
            "response",
            "owner",
            "status",
        ]:
            if not threat.get(field):
                errors.append(
                    {
                        "rule": "incomplete-threat",
                        "id": threat.get("id"),
                        "field": field,
                    }
                )
        if threat.get("response") not in {
            "mitigate",
            "eliminate",
            "transfer",
            "accept",
        }:
            errors.append(
                {"rule": "invalid-risk-response", "id": threat.get("id")}
            )
        if threat.get("response") in {"mitigate", "eliminate"} and (
            not threat.get("controls") or not threat.get("verification")
        ):
            errors.append(
                {"rule": "unverifiable-mitigation", "id": threat.get("id")}
            )
        if threat.get("response") in {"accept", "transfer"}:
            _validate_human_risk_decision(threat, now, errors)


def _validate_human_risk_decision(threat, now, errors):
    for field in ["approvedBy", "approvedAt", "expiresAt", "trackingIssue"]:
        if not threat.get(field):
            errors.append(
                {
                    "rule": "missing-human-risk-decision",
                    "id": threat.get("id"),
                    "field": field,
                }
            )
    try:
        expiry = datetime.datetime.fromisoformat(
            threat.get("expiresAt", "").replace("Z", "+00:00")
        )
        if expiry <= now:
            errors.append(
                {"rule": "expired-risk-decision", "id": threat.get("id")}
            )
    except Exception:
        errors.append({"rule": "invalid-risk-expiry", "id": threat.get("id")})


def _validate_change_evidence(root, policy, components, base, head, errors):
    changed_files = []
    if base:
        raw_changed_files = (
            git(root, ["diff", "--name-only", f"{base}...{head}"]) or ""
        )
        changed_files = [
            changed_file
            for changed_file in raw_changed_files.splitlines()
            if changed_file
        ]
        impacted_components = [
            component["id"]
            for component in components.values()
            if any(
                match(changed_file, component.get("paths", []))
                for changed_file in changed_files
            )
        ]
        architecture_changed = any(
            match(changed_file, policy.get("architectureArtifactGlobs", []))
            for changed_file in changed_files
        )
        if impacted_components and not architecture_changed:
            assessment = (
                root / "architecture/change-assessments" / f"{head}.json"
            )
            if not assessment.exists():
                errors.append(
                    {
                        "rule": "stale-architecture-evidence",
                        "components": impacted_components,
                        "message": "implementation changed without architecture/threat artifact or exact change assessment",
                    }
                )
    return changed_files


def _validate_conditional_views(policy, changed_files, view_ids, errors):
    for rule in policy.get("conditionalViews", []):
        if changed_files and any(
            match(changed_file, rule.get("when", []))
            for changed_file in changed_files
        ):
            for required_view_id in rule.get("require", []):
                if required_view_id not in view_ids:
                    errors.append(
                        {
                            "rule": "missing-triggered-view",
                            "id": required_view_id,
                        }
                    )


def _build_result(
    policy,
    changed_files,
    errors,
    warnings,
    components,
    view_ids,
    elements,
    flows,
    threat_map,
):
    return {
        "schemaVersion": "1.0",
        "status": "fail" if errors else "pass",
        "profile": policy.get("profile"),
        "changedFiles": changed_files,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "components": len(components),
            "views": len(view_ids),
            "dfdElements": len(elements),
            "flows": len(flows),
            "threats": len(threat_map),
        },
    }


def main():
    arguments = _parse_arguments()
    root = pathlib.Path(arguments.repo).resolve()
    errors = []
    warnings = []
    policy = load(root, arguments.policy, errors)
    if not policy:
        output = _policy_unavailable_output(arguments.mode, errors, warnings)
        return finish(
            output,
            arguments.out,
            2 if arguments.mode == "strict" else 0,
        )
    if policy.get("status") != "active":
        output = _inactive_policy_output(policy, arguments.mode, warnings)
        return finish(
            output,
            arguments.out,
            2 if arguments.mode == "strict" else 0,
        )

    _validate_required_files(root, policy, errors)
    registry, views, dfd, coverage, threats = _load_architecture_artifacts(
        root, errors
    )
    components = _index_components(registry, errors)
    view_ids = _validate_required_views(views, policy, errors)
    elements = _index_dfd_elements(dfd, components, errors)
    boundaries = {
        boundary.get("id"): boundary
        for boundary in dfd.get("trustBoundaries", [])
    }
    flows = _index_and_validate_flows(dfd, elements, boundaries, errors)
    subjects = {
        (subject.get("type"), subject.get("id")): subject
        for subject in coverage.get("subjects", [])
    }
    threat_map = {
        threat.get("id"): threat for threat in threats.get("threats", [])
    }
    _validate_stride_coverage(subjects, threat_map, flows, elements, errors)
    _validate_threats(threat_map, errors)
    changed_files = _validate_change_evidence(
        root,
        policy,
        components,
        arguments.base,
        arguments.head,
        errors,
    )
    _validate_conditional_views(policy, changed_files, view_ids, errors)
    output = _build_result(
        policy,
        changed_files,
        errors,
        warnings,
        components,
        view_ids,
        elements,
        flows,
        threat_map,
    )
    return finish(output, arguments.out, 1 if errors else 0)


def finish(out, path, code):
    text = json.dumps(out, indent=2) + "\n"
    print(text, end="")
    if path:
        pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(path).write_text(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

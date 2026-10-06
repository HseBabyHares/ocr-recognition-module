# Python quality profile

Ruff owns fast lint/format; `wemake-python-styleguide` owns complexity/design; mypy owns types; Import Linter owns architecture import contracts; pytest/coverage/diff-cover own behavior and ratchets; mutmut is scheduled or scoped to critical changed modules.

`policy.example.json` is intentionally `template-unconfigured`. Copy it to `quality/python-policy.json`, set real paths and thresholds, then approve it as a protected control. Existing projects should baseline pre-existing debt and block only new violations; greenfield and harness/policy code can use strict whole-repository gates.

Agents may not raise thresholds, add `noqa`, expand ignores, modify the baseline, weaken tests, or disable a check without exact human authority.

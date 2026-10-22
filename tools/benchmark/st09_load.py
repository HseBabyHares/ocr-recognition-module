"""Frozen 5,000-document arrival profile and load generator for ST-09/PR-1.

The profile is fixed by seeds and by a committed lock. The document pool is
rendered by tools/corpus/render_snils_forms.py: the three MVP layouts, photo
and scan, supported documents only. The arrival file gives each of the 5,000
arrivals an offset in a 24-hour window and one distinct pool document. The
replay sends due arrivals to the Task API (at most 100 files per request, one
Idempotency-Key per request), polls every accepted task to a terminal state,
reconciles accepted IDs with terminal results, and samples the RabbitMQ
backlog and resource use. The report records host hardware and versions.

Run from the repository root:
  uv run python tools/benchmark/st09_load.py freeze
  uv run python tools/benchmark/st09_load.py prepare
  uv run python tools/benchmark/st09_load.py run --report PATH
  uv run python tools/benchmark/st09_load.py run --limit 20 --speed 2000 \\
      --report PATH        # compressed smoke run, not a PR-1 verdict
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import time
import uuid
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name("st09-profile.lock.json")
ARRIVALS = Path(__file__).with_name("st09-arrivals.v1.csv")
POOL = ROOT / "artifacts" / "benchmark" / "st09"
RENDERER = ROOT / "tools" / "corpus" / "render_snils_forms.py"
API = "http://localhost:18080/api/v1/processing"

# Seeds differ from the development (0, 3) and PR-2 (1250, 1260) corpora.
ACQUISITIONS = {"photo": (2090, False), "scan": (2091, True)}
PROFILE_SEED = 2092
COUNT_PER_LAYOUT = 834  # 3 layouts x 2 acquisitions x 834 = 5,004 >= 5,000
DOCUMENTS = 5000
WINDOW_SECONDS = 86400
# Working-day peak (local time of the operator): a night trough, a morning
# ramp, peaks at 10-12 and 15-16, a lunch dip. Peak hour ~504 documents,
# about 2.4 times the mean of ~208 per hour.
HOURLY_WEIGHTS = (
    1, 1, 1, 1, 1, 2, 4, 8, 14, 20, 24, 24,
    18, 16, 22, 24, 20, 14, 8, 5, 4, 3, 2, 1,
)  # fmt: skip
MAX_FILES = 100  # consumer-api.yaml maxItems for the files part
TERMINAL = frozenset(("RECOGNIZED", "ERROR"))
CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg"}

Arrival = tuple[int, float, str]  # sequence, offset seconds, pool key


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hourly_counts(total: int, weights: tuple[int, ...]) -> list[int]:
    """Split total over hours by weight; largest remainder keeps the sum."""
    exact = [total * weight / sum(weights) for weight in weights]
    counts = [math.floor(value) for value in exact]
    order = sorted(
        range(len(weights)), key=lambda hour: counts[hour] - exact[hour]
    )
    for hour in order[: total - sum(counts)]:
        counts[hour] += 1
    return counts


def build_arrivals(pool_keys: list[str], seed: int) -> list[Arrival]:
    """Seeded arrivals: per-hour counts, uniform times inside each hour.

    Uniform order statistics inside an hour are a Poisson process with the
    hour's rate, conditioned on the frozen count.
    """
    rng = random.Random(seed)
    hour_seconds = WINDOW_SECONDS // len(HOURLY_WEIGHTS)
    offsets_ms = sorted(
        hour * hour_seconds * 1000 + rng.randrange(hour_seconds * 1000)
        for hour, count in enumerate(hourly_counts(DOCUMENTS, HOURLY_WEIGHTS))
        for _ in range(count)
    )
    keys = sorted(pool_keys)
    rng.shuffle(keys)
    return [
        (sequence, offset / 1000, key)
        for sequence, (offset, key) in enumerate(
            zip(offsets_ms, keys[:DOCUMENTS], strict=True)
        )
    ]


def arrivals_text(arrivals: list[Arrival]) -> str:
    rows = [f"{seq},{round(at * 1000)},{key}" for seq, at, key in arrivals]
    return "\n".join(["sequence,offset_ms,document", *rows]) + "\n"


def read_arrivals(text: str) -> list[Arrival]:
    rows = [line.split(",") for line in text.splitlines()[1:]]
    return [(int(seq), int(ms) / 1000, key) for seq, ms, key in rows]


def _render(out: Path) -> dict[str, str]:
    """Render the pool and return one digest per acquisition."""
    jobs = {}
    for acquisition, (seed, clean) in ACQUISITIONS.items():
        command = ["uv", "run", "-q", str(RENDERER)]
        command += ["--out", str(out / acquisition), "--seed", str(seed)]
        command += ["--count", str(COUNT_PER_LAYOUT)]
        command += ["--clean"] if clean else []
        jobs[acquisition] = subprocess.Popen(
            command, stdout=subprocess.DEVNULL
        )
    if any(job.wait() for job in jobs.values()):
        raise SystemExit("pool render failed")
    return pool_digests(out)


def pool_files(out: Path) -> list[str]:
    """Pool keys in the order of the renderer manifests."""
    return [
        f"{acquisition}/{json.loads(row)['file']}"
        for acquisition in ACQUISITIONS
        for row in (out / acquisition / "manifest.jsonl")
        .read_text()
        .splitlines()
    ]


def pool_digests(out: Path) -> dict[str, str]:
    """Write a sha256sum manifest of the pool; return a digest per mode."""
    lines: dict[str, list[str]] = {name: [] for name in ACQUISITIONS}
    for key in sorted([*pool_files(out), *_manifests()]):
        acquisition = key.split("/", 1)[0]
        digest = _sha256((out / key).read_bytes())
        lines[acquisition].append(f"{digest}  {key}\n")
    (out / "pool.sha256").write_text(
        "".join(line for rows in lines.values() for line in rows)
    )
    return {
        name: _sha256("".join(rows).encode()) for name, rows in lines.items()
    }


def _manifests() -> list[str]:
    return [f"{acquisition}/manifest.jsonl" for acquisition in ACQUISITIONS]


def _lock_body(digests: dict[str, str], arrivals: str) -> dict:
    return {
        "version": 1,
        "documents": DOCUMENTS,
        "window_seconds": WINDOW_SECONDS,
        "profile_seed": PROFILE_SEED,
        "render_seeds": {
            name: seed for name, (seed, _) in ACQUISITIONS.items()
        },
        "count_per_layout": COUNT_PER_LAYOUT,
        "hourly_weights": list(HOURLY_WEIGHTS),
        "hourly_counts": hourly_counts(DOCUMENTS, HOURLY_WEIGHTS),
        "arrivals_file": ARRIVALS.name,
        "arrivals_sha256": _sha256(arrivals.encode()),
        "pool_sha256": digests,
    }


def freeze() -> int:
    digests = _render(POOL)
    text = arrivals_text(build_arrivals(pool_files(POOL), PROFILE_SEED))
    ARRIVALS.write_text(text)
    LOCK.write_text(json.dumps(_lock_body(digests, text), indent=2) + "\n")
    print(json.dumps(_lock_body(digests, text)["pool_sha256"]))
    return 0


def check(render: bool) -> int:
    """Refuse drift of the arrival file or the pool from the lock."""
    lock = json.loads(LOCK.read_text())
    if _sha256(ARRIVALS.read_bytes()) != lock["arrivals_sha256"]:
        print("arrival drift: the arrival file does not match the lock")
        return 2
    if not render and not (POOL / "pool.sha256").exists():
        print("no pool: run the prepare command first")
        return 2
    digests = _render(POOL) if render else pool_digests(POOL)
    if digests != lock["pool_sha256"]:
        # Pillow and font files change pixels; re-freeze on a new host.
        print("pool drift: rendered files do not match the lock")
        return 2
    return 0


# ---------------------------------------------------------------- replay


class TaskApi:
    """Task API client with client-credential tokens refreshed on expiry."""

    def __init__(self, api: str, token: Callable[[], str]) -> None:
        import httpx

        self._token_source = token
        self._token, self._expires = "", 0.0
        self._http = httpx.Client(base_url=api, timeout=300)

    def _headers(self) -> dict[str, str]:
        if time.time() > self._expires - 60:
            self._token = self._token_source()
            payload = self._token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            self._expires = float(claims["exp"])
        return {"Authorization": f"Bearer {self._token}"}

    def create(self, files: list[tuple[str, bytes, str]]) -> tuple[int, dict]:
        parts = [("files", file) for file in files]
        headers = self._headers() | {"Idempotency-Key": str(uuid.uuid4())}
        response = self._http.post("/tasks", files=parts, headers=headers)
        return response.status_code, response.json()

    def statuses(self, ids: list[int]) -> list[dict]:
        response = self._http.get(
            "/tasks/statuses",
            params={"task_ids": ",".join(map(str, ids))},
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()["statuses"]


class Replay:
    """Replay arrivals; the clock and sleep are injected for tests."""

    def __init__(
        self,
        api,
        load: Callable[[str], bytes],
        sample: Callable[[], dict],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api, self.load, self.sample = api, load, sample
        self.clock, self.sleep = clock, sleep
        self.items: dict[int, dict] = {}
        self.tasks: dict[int, dict] = {}
        self.requests: list[dict] = []
        self.samples: list[dict] = []
        self.start = 0.0

    def now(self) -> float:
        return self.clock() - self.start

    def submit(self, batch: list[Arrival]) -> None:
        files = []
        for seq, _, key in batch:
            name = f"st09-{seq:05d}-{key.replace('/', '_')}"
            content_type = CONTENT_TYPES[key.rsplit(".", 1)[1]]
            files.append((name, self.load(key), content_type))
            self.items[seq] = {"document": key, "file": name}
        sent = self.now()
        status, body, error = None, {}, ""
        try:
            status, body = self.api.create(files)
        except Exception as exc:  # noqa: BLE001 - recorded, run goes on
            error = repr(exc)
        self.requests.append(
            {
                "first_sequence": batch[0][0],
                "files": len(batch),
                "http": status,
                "sent_at": round(sent, 3),
                "seconds": round(self.now() - sent, 3),
                **({"error": error} if error else {}),
            }
        )
        by_name = {row.get("filename"): row for row in body.get("results", [])}
        for seq, _, _ in batch:
            item = self.items[seq]
            row = by_name.get(item["file"], {})
            task_id = (row.get("task") or {}).get("task_id")
            item |= {"submitted_at": round(sent, 3), "http": status}
            item |= {"outcome": row.get("outcome"), "task_id": task_id}
            if row.get("problem"):
                item["problem"] = row["problem"]
            if task_id is not None:
                task = self.tasks.setdefault(task_id, {"sequences": []})
                task["sequences"].append(seq)
                task.setdefault("accepted_at", round(sent, 3))

    def pending(self) -> list[int]:
        return [
            task_id
            for task_id, task in self.tasks.items()
            if task.get("state") not in TERMINAL
        ]

    def poll(self, ids: list[int]) -> None:
        for chunk in (
            ids[i : i + MAX_FILES] for i in range(0, len(ids), MAX_FILES)
        ):
            try:
                entries = self.api.statuses(chunk)
            except Exception:  # noqa: BLE001 - the next poll retries
                continue
            for entry in entries:
                task = self.tasks.get(entry.get("task_id"))
                if task is None or task.get("state") in TERMINAL:
                    continue
                task["state"] = entry.get("state")
                task["outcome"] = entry.get("task_outcome")
                task["updated_at"] = entry.get("updated_at")
                if entry.get("state") in TERMINAL:
                    task["terminal_at"] = round(self.now(), 3)

    def take_sample(self) -> None:
        self.samples.append({"t": round(self.now(), 3), **self.sample()})

    def run(
        self,
        arrivals: list[Arrival],
        speed: float,
        poll_every: float,
        sample_every: float,
        drain_timeout: float,
    ) -> None:
        self.start = self.clock()
        due_at = [offset / speed for _, offset, _ in arrivals]
        index, next_poll, next_sample = 0, 0.0, 0.0
        while True:
            now = self.now()
            end = index
            while end < len(arrivals) and due_at[end] <= now:
                end += 1
            if end > index:
                for first in range(index, end, MAX_FILES):
                    self.submit(arrivals[first : min(end, first + MAX_FILES)])
                index = end
                continue
            if now >= next_sample:
                self.take_sample()
                next_sample = now + sample_every
            pending = self.pending()
            if pending and now >= next_poll:
                self.poll(pending)
                next_poll = now + poll_every
                pending = self.pending()
            if index == len(arrivals):
                last = self.requests[-1]["sent_at"] if self.requests else 0
                if not pending or now - last >= drain_timeout:
                    break
            wakes = [next_sample]
            if index < len(arrivals):
                wakes.append(due_at[index])
            if pending:
                wakes.append(next_poll)
            self.sleep(max(0.0, min(wakes) - self.now()))
        self.take_sample()

    def recheck(self) -> int:
        """Re-read terminal tasks; count those whose result changed."""
        before = {
            task_id: (task.get("state"), task.get("updated_at"))
            for task_id, task in self.tasks.items()
            if task.get("state") in TERMINAL
        }
        changed = 0
        ids = list(before)
        for chunk in (
            ids[i : i + MAX_FILES] for i in range(0, len(ids), MAX_FILES)
        ):
            for entry in self.api.statuses(chunk):
                again = (entry.get("state"), entry.get("updated_at"))
                changed += before.get(entry.get("task_id")) != again
        return changed


def percentile(values: list[float], rank: float) -> float | None:
    """Nearest-rank percentile; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(rank * len(ordered)) - 1)]


def reconcile(replay: Replay, planned: int, speed: float) -> dict:
    """Accepted IDs against terminal results, backlog and throughput."""
    items, tasks = replay.items.values(), replay.tasks
    terminal = [
        task for task in tasks.values() if task.get("state") in TERMINAL
    ]
    latencies = [
        task["terminal_at"] - task["accepted_at"] for task in terminal
    ]
    first = min((item["submitted_at"] for item in items), default=0.0)
    last_submit = max((item["submitted_at"] for item in items), default=0.0)
    last_terminal = max((task["terminal_at"] for task in terminal), default=0)
    busy = max(last_terminal - first, 1e-9)
    hours = Counter(
        int(task["terminal_at"] * speed // 3600) for task in terminal
    )
    backlog = Counter()
    for sample in replay.samples:
        for queue in sample.get("queues", []):
            name, depth = queue["name"], queue.get("messages", 0)
            backlog[name] = max(backlog[name], depth)
    counts = {
        "planned": planned,
        "submitted": len(replay.items),
        "accepted": sum(item["task_id"] is not None for item in items),
        "rejected": sum(item.get("outcome") == "REJECTED" for item in items),
        "request_failed": sum(
            item["http"] is None or item["http"] >= 400 for item in items
        ),
        "duplicate_task_ids": sum(
            len(task["sequences"]) > 1 for task in tasks.values()
        ),
        "terminal": len(terminal),
        "lost": len(tasks) - len(terminal),
        "by_state": Counter(task.get("state") for task in tasks.values()),
        "by_outcome": Counter(task.get("outcome") for task in terminal),
    }
    window = WINDOW_SECONDS / speed
    full = planned == DOCUMENTS and speed == 1
    within = bool(terminal) and last_terminal - first <= window
    pr1 = all(
        (
            full,
            within,
            counts["accepted"] == planned,
            counts["lost"] == 0,
            counts["duplicate_task_ids"] == 0,
            counts["by_outcome"].get("FAILED", 0) == 0,
        )
    )
    return {
        "counts": counts,
        "latency_seconds": {
            name: percentile(latencies, rank)
            for name, rank in (("p50", 0.5), ("p95", 0.95), ("p99", 0.99))
        },
        "throughput": {
            "terminal_per_hour_wall": round(len(terminal) / busy * 3600, 1),
            "terminal_per_profile_hour": dict(sorted(hours.items())),
            "first_submit_s": first,
            "last_submit_s": last_submit,
            "last_terminal_s": last_terminal,
            "drain_after_last_submit_s": round(last_terminal - last_submit, 3),
        },
        "backlog_max_messages": dict(backlog),
        "window_seconds_scaled": window,
        "completed_within_window": within,
        "full_profile": full,
        "pr1_passed": pr1,
    }


# ------------------------------------------------------------- cluster


def _run(command: list[str]) -> tuple[int, str]:
    try:
        done = subprocess.run(
            command, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, repr(error)
    return done.returncode, (done.stdout or done.stderr).strip()


def kind_name(context: str) -> str:
    return context.removeprefix("kind-")


def cluster_sampler(context: str, namespace: str, vhost: str):
    """Read-only probes: RabbitMQ queue depth and pod or node resource use."""
    kubectl = ["kubectl", "--context", context, "-n", namespace]
    queues = [*kubectl, "exec", "deploy/rabbitmq", "--", "rabbitmqctl"]
    queues += ["list_queues", "-q", "-p", vhost, "--formatter", "json"]
    queues += ["name", "messages", "messages_ready", "messages_unacknowledged"]
    nodes = ["docker", "ps", "--format", "{{.Names}}", "--filter"]
    nodes.append(f"label=io.x-k8s.kind.cluster={kind_name(context)}")

    def sample() -> dict:
        code, text = _run(queues)
        out: dict = {"queues": json.loads(text) if code == 0 else []}
        if code:
            out["queues_error"] = text[-300:]
        code, text = _run([*kubectl, "top", "pods", "--no-headers"])
        if code == 0:
            out["pods"] = [line.split() for line in text.splitlines()]
            return out
        # metrics-server is absent on the kind cluster: use the node
        # containers, which hold every pod of the cluster.
        names = _run(nodes)[1].split()
        stats = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]
        code, text = _run([*stats, *names]) if names else (1, "no nodes")
        out["nodes"] = (
            [json.loads(line) for line in text.splitlines()]
            if code == 0
            else []
        )
        return out

    return sample


def environment(context: str, namespace: str) -> dict:
    """Host hardware and software versions, recorded before the run."""
    meminfo = Path("/proc/meminfo")
    cpuinfo = Path("/proc/cpuinfo")
    kubectl = ["kubectl", "--context", context]
    images = "{range .items[*]}{.metadata.name}={.spec.template.spec"
    images += ".containers[*].image}{'\\n'}{end}"
    nodes = "{range .items[*]}{.metadata.name} {.status.capacity.cpu} "
    nodes += "{.status.capacity.memory} {.status.nodeInfo.kubeletVersion} "
    nodes += "{.status.nodeInfo.osImage}{'\\n'}{end}"
    return {
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {
            "uname": " ".join(platform.uname()),
            "cpu_count": os.cpu_count(),
            "cpu_model": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in cpuinfo.read_text().splitlines()
                    if line.startswith("model name")
                ),
                None,
            )
            if cpuinfo.exists()
            else None,
            "mem_total": meminfo.read_text().splitlines()[0]
            if meminfo.exists()
            else None,
        },
        "python": sys.version.split()[0],
        "repository_commit": _run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"]
        )[1],
        "kubectl": _run([*kubectl, "version", "-o", "json"])[1][-600:],
        "nodes": _run([*kubectl, "get", "nodes", "-o", f"jsonpath={nodes}"])[
            1
        ].splitlines(),
        "images": _run(
            [
                *kubectl,
                "-n",
                namespace,
                "get",
                "deploy",
                "-o",
                "jsonpath=" + images,
            ]
        )[1].splitlines(),
    }


def token_source(context: str, namespace: str, keycloak: str, secret: str):
    """Client credentials read from the cluster secret; never printed."""
    import httpx

    def field(key: str) -> str:
        command = ["kubectl", "--context", context, "-n", namespace, "get"]
        command += ["secret", secret, "-o", f"jsonpath={{.data.{key}}}"]
        return base64.b64decode(subprocess.check_output(command)).decode()

    def token() -> str:
        response = httpx.post(
            f"{keycloak}/realms/sird/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": field("client_id"),
                "client_secret": field("client_secret"),
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]

    return token


def select(arrivals: list[Arrival], limit: int | None) -> list[Arrival]:
    """Every n-th arrival, so a short run keeps the shape of the day."""
    if not limit or limit >= len(arrivals):
        return arrivals
    step = len(arrivals) / limit
    return [arrivals[math.floor(index * step)] for index in range(limit)]


def summary(report: dict) -> str:
    counts, result = report["counts"], report
    lines = [
        f"ST-09 {'full' if result['full_profile'] else 'compressed'} run, "
        f"speed x{report['run']['speed']}, {counts['planned']} planned",
        f"accepted {counts['accepted']}, rejected {counts['rejected']}, "
        f"request failures {counts['request_failed']}, "
        f"duplicate IDs {counts['duplicate_task_ids']}",
        f"terminal {counts['terminal']}, lost {counts['lost']}, "
        f"by outcome {dict(counts['by_outcome'])}, "
        f"changed after terminal {report['changed_after_terminal']}",
        f"latency s {report['latency_seconds']}",
        f"drain after last submit "
        f"{report['throughput']['drain_after_last_submit_s']} s, "
        f"max backlog {report['backlog_max_messages']}",
        f"PR-1 passed: {report['pr1_passed']}",
    ]
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    if check(render=False):
        return 2
    arrivals = select(read_arrivals(ARRIVALS.read_text()), args.limit)
    env = environment(args.context, args.namespace)
    api = TaskApi(
        args.api,
        token_source(args.context, args.namespace, args.keycloak, args.secret),
    )
    replay = Replay(
        api,
        lambda key: (POOL / key).read_bytes(),
        cluster_sampler(args.context, args.namespace, args.vhost),
    )
    replay.run(
        arrivals,
        args.speed,
        args.poll_every,
        args.sample_every,
        args.drain_timeout,
    )
    report = {
        "run": {
            "speed": args.speed,
            "limit": args.limit,
            "lock_sha256": _sha256(LOCK.read_bytes()),
            "api": args.api,
        },
        "environment": env,
        **reconcile(replay, len(arrivals), args.speed),
        "changed_after_terminal": replay.recheck(),
        "requests": replay.requests,
        "tasks": {str(key): task for key, task in replay.tasks.items()},
        "items": replay.items,
        "samples": replay.samples,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n"
    )
    text = summary(report)
    args.report.with_suffix(".txt").write_text(text)
    print(text, end="")
    return 0 if report["pr1_passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="ST-09 frozen load profile")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze")
    commands.add_parser("prepare")
    replay = commands.add_parser("run")
    replay.add_argument("--report", type=Path, required=True)
    replay.add_argument("--limit", type=int)
    replay.add_argument("--speed", type=float, default=1.0)
    replay.add_argument("--poll-every", type=float, default=5.0)
    replay.add_argument("--sample-every", type=float, default=30.0)
    replay.add_argument("--drain-timeout", type=float, default=7200.0)
    replay.add_argument("--api", default=API)
    replay.add_argument("--keycloak", default="http://localhost:18081")
    replay.add_argument("--context", default="kind-sird-dev")
    replay.add_argument("--namespace", default="sird")
    replay.add_argument("--vhost", default="/sird")
    replay.add_argument("--secret", default="hse-example-app")
    args = parser.parse_args()
    if args.command == "freeze":
        return freeze()
    if args.command == "prepare":
        return check(render=True)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

# Isolated SPIFFE/SPIRE profile

The project does not use SPIFFE/SPIRE. The owner dropped it on 2026-10-13.
Workload identity uses mTLS client certificates (`sird_workflow.mtls`).

This folder keeps the old local SPIRE profile for reference only. It is not
supported, not tested in CI, and not part of the delivery scope.

- `compose.yml` and `start.sh` start a local SPIRE server, agent and probe.
- `sird_workflow.spiffe` keeps the SPIFFE ID and policy checks. The
  `sird_workflow` root API does not export it.

Nothing else in the repository imports this profile or this package.

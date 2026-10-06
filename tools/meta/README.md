# CI meta-lint

The harness checks itself with actionlint, ShellCheck, check-jsonschema, and zizmor. This prevents an agent from producing valid product code while silently breaking or weakening the workflow that should verify it. CI runs check mode only; automated fixes to protected workflow, policy, schema, and threshold files are not permitted.

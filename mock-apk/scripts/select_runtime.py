#!/usr/bin/env python3
"""Choose which Node runtime to package for a pull-request CI run.

This avoids GitHub's requirement that manual workflow_dispatch workflows
already exist on the default branch. The selector is a tracked PR file;
switch it to run-artifacts only after a successful Node build run.
"""
import json
import sys
from pathlib import Path


def validate(data):
    if not isinstance(data, dict) or set(data) != {"source", "runtime_run_id"}:
        raise ValueError("Expected only source and runtime_run_id fields")
    source, run_id = data["source"], data["runtime_run_id"]
    if source == "reference":
        if run_id is not None:
            raise ValueError("reference mode requires runtime_run_id: null")
        return "reference", ""
    if source != "run-artifacts":
        raise ValueError(f"Unrecognized runtime source: {source!r}")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("run-artifacts requires a positive integer runtime_run_id")
    return "run-artifacts", str(run_id)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: select_runtime.py mock-apk/runtime-selection.json")
    try:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        source, run_id = validate(data)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"Invalid mock runtime selection: {error}") from error
    # Format for append to GITHUB_ENV; no other output.
    print(f"RUNTIME_SOURCE={source}")
    print(f"RUNTIME_RUN_ID={run_id}")


if __name__ == "__main__":
    main()

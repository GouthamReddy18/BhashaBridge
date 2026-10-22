"""Validate a versioned linguistic resource manifest; never execute rules."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.linguistic_resources import ResourceError, load_resource, resource_readiness  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="UTF-8 JSON resource manifest")
    args = parser.parse_args(argv)
    try:
        resource = load_resource(args.manifest)
    except ResourceError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    blockers = resource_readiness(resource)
    print(f"Resource: {resource.resource_id}@{resource.resource_version}")
    print(f"Rules: {len(resource.rules)}")
    print(f"Readiness: {'READY' if not blockers else 'BLOCKED'}")
    for blocker in blockers:
        print(f"BLOCKER {blocker}")
    print("Review metadata and evidence are declarations and are not independently authenticated.")
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())

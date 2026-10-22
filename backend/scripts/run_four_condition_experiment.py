"""Run the approved four-condition experiment and save a versioned JSONL artifact."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.four_condition import FourConditionConfiguration  # noqa: E402
from app.services.four_condition_execution import FourConditionDatasetError, run_four_condition_dataset  # noqa: E402
from app.services.four_condition_experiment import load_condition_resource  # noqa: E402
from app.services.google_translation import configured_google_translation_provider  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--dataset-label", required=True)
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--output", required=True, help="new JSONL artifact path; existing files are never overwritten")
    parser.add_argument("--normalizer-resource")
    parser.add_argument("--transliterator-resource")
    parser.add_argument("--contextual-resource")
    parser.add_argument("--allow-provider-calls", action="store_true", help="explicitly permit configured external translation requests")
    parser.add_argument("--allow-test-fixtures", action="store_true", help="permit test-only resources and ineligible synthetic datasets; output is permanently marked test-only")
    args = parser.parse_args(argv)
    try:
        resources = {}
        for kind, path in (
            ("normalizer", args.normalizer_resource),
            ("transliterator", args.transliterator_resource),
            ("contextual_transformer", args.contextual_resource),
        ):
            if path:
                binding = load_condition_resource(path)
                if binding.kind != kind:
                    raise FourConditionDatasetError(f"{kind} resource file declares a different kind")
                resources[kind] = binding
        provider = configured_google_translation_provider()
        configuration = FourConditionConfiguration(
            dataset_label=args.dataset_label,
            split=args.split,
            requested_model=getattr(provider, "requested_model", None),
            resources=resources,
        )
        output = run_four_condition_dataset(
            args.annotations, args.output,
            configuration=configuration,
            provider=provider,
            allow_provider_calls=args.allow_provider_calls,
            allow_test_fixtures=args.allow_test_fixtures,
        )
    except (FourConditionDatasetError, ValueError) as exc:
        print(f"Four-condition experiment blocked: {exc}", file=sys.stderr)
        return 2
    print(f"Four-condition artifact written: {output}")
    print("Condition definitions remain stable in direct_v1, normalized_v1, transliterated_v1, ambiguity_aware_v1 order.")
    print("Inspect per-condition status; an artifact may contain blocked conditions or failed/unavailable provider outcomes.")
    print("Exit code 0 means every condition succeeded; exit code 1 means an artifact was written with incomplete outcomes.")
    import json
    payload = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
    complete = all(
        item["result"]["conditions"][index]["status"] == "completed"
        and item["result"]["conditions"][index]["translation"]
        and item["result"]["conditions"][index]["translation"]["status"] == "success"
        and item["result"]["conditions"][index]["research_eligible"]
        for item in payload for index in range(4)
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Execute paired translations for an eligible dataset split.

Provider calls require both explicit CLI opt-in and enabled provider configuration.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.experiment import ExperimentConfiguration  # noqa: E402
from app.services.experiment_execution import ExperimentExecutionError, run_dataset_experiment  # noqa: E402
from app.services.google_translation import configured_google_translation_provider  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--split", required=True, choices=("train", "validation", "test"))
    parser.add_argument("--output", required=True, help="new JSONL path; existing artifacts are never overwritten")
    parser.add_argument("--execution-order", choices=("direct_first", "assisted_first"), default="direct_first")
    parser.add_argument("--allow-provider-calls", action="store_true", help="explicitly permit external provider calls; may incur cost and transmit text")
    args = parser.parse_args(argv)
    provider = configured_google_translation_provider()
    if provider is None:
        print("Translation provider is not configured.", file=sys.stderr)
        return 2
    if not args.allow_provider_calls:
        print("Provider calls require --allow-provider-calls; no request was sent.", file=sys.stderr)
        return 2
    try:
        output = run_dataset_experiment(
            args.annotations, args.output, split=args.split,
            provider=provider,
            configuration=ExperimentConfiguration(
                execution_order=args.execution_order, requested_model=provider.requested_model,
            ),
            allow_provider_calls=True,
        )
    except ExperimentExecutionError as exc:
        print(f"Experiment blocked: {exc}", file=sys.stderr)
        return 1
    print(f"Experiment artifact: {output}")
    print("Artifact contains provider outcomes; it is not a quality or research conclusion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

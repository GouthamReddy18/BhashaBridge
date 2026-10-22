"""Prepare pending human semantic-rating tasks and aggregate completed ratings."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.human_rating_workflow import (  # noqa: E402
    RatingWorkflowError, aggregate_human_ratings, create_rating_tasks,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-tasks")
    create.add_argument("--annotations", required=True)
    create.add_argument("--paired-results", required=True)
    create.add_argument("--split", required=True, choices=("train", "validation", "test"))
    create.add_argument("--dataset-label", required=True)
    create.add_argument("--tasks-output", required=True)
    create.add_argument("--ratings-output", required=True)
    create.add_argument("--blinded", action="store_true")
    create.add_argument("--mapping-output")
    aggregate = commands.add_parser("aggregate")
    aggregate.add_argument("--tasks", required=True)
    aggregate.add_argument("--ratings", required=True)
    aggregate.add_argument("--mapping")
    aggregate.add_argument("--min-reviewers", type=int, default=1)
    aggregate.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "create-tasks":
            paths = create_rating_tasks(
                args.annotations, args.paired_results, split=args.split,
                dataset_label=args.dataset_label,
                tasks_output=args.tasks_output, ratings_output=args.ratings_output,
                blinded=args.blinded, mapping_output=args.mapping_output,
            )
            print(f"Task sheet: {paths[0]}")
            print(f"Pending ratings: {paths[1]}")
            if paths[2]:
                print(f"Blind key (keep separate from raters): {paths[2]}")
            print("All ratings remain pending until a human completes them.")
            return 0
        report = aggregate_human_ratings(
            args.tasks, args.ratings, mapping_path=args.mapping,
            min_reviewers=args.min_reviewers,
        )
        destination = Path(args.output)
        if not destination.parent.is_dir():
            raise RatingWorkflowError("output directory does not exist")
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except FileExistsError:
        print("rating output already exists", file=sys.stderr)
        return 1
    except OSError:
        print("rating report could not be written safely", file=sys.stderr)
        return 1
    except RatingWorkflowError as exc:
        print(f"Rating workflow error: {exc}", file=sys.stderr)
        return 1
    print(f"Human rating report: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import sys
import argparse
import logging
from ingestion.pipeline import run_pipeline, IngestionStats
from ingestion.client import ENDPOINT_CONFIG

logger = logging.getLogger(__name__)


def _print_summary(all_stats: dict[str, IngestionStats]) -> None:
    """Print a summary table of ingestion results."""
    print(f"\n{'Endpoint':<12} {'Total':>6} {'OK':>6} {'Failed':>6} {'Skipped':>6}")
    print("-" * 42)
    grand_total = grand_ok = grand_failed = grand_skipped = 0
    for ep, stats in all_stats.items():
        print(f"{ep:<12} {stats.total:>6} {stats.succeeded:>6} {stats.failed:>6} {stats.skipped:>6}")
        grand_total += stats.total
        grand_ok += stats.succeeded
        grand_failed += stats.failed
        grand_skipped += stats.skipped
    print("-" * 42)
    print(f"{'TOTAL':<12} {grand_total:>6} {grand_ok:>6} {grand_failed:>6} {grand_skipped:>6}")
    # Show last few errors if any
    all_errors = []
    for stats in all_stats.values():
        all_errors.extend(stats.errors)
    if all_errors:
        print(f"\nLast errors ({min(3, len(all_errors))}/{len(all_errors)}):")
        for err in all_errors[-3:]:
            print(f"  - {err.get('url', 'unknown')}: {err.get('error', 'unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Ingest ReliefWeb content into ChromaDB")
    parser.add_argument("--limit", type=int, default=100, help="Max documents per endpoint")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion (clear collection first)")
    parser.add_argument(
        "--endpoints",
        nargs="+",
        default=["reports"],
        choices=list(ENDPOINT_CONFIG.keys()),
        help="Endpoints to ingest from (default: reports)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    all_stats = run_pipeline(limit=args.limit, force=args.force, endpoints=args.endpoints)
    _print_summary(all_stats)
    total_failed = sum(s.failed for s in all_stats.values())
    total_succeeded = sum(s.succeeded for s in all_stats.values())
    if total_failed > 0 and total_succeeded > 0:
        sys.exit(1)
    elif total_failed > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()
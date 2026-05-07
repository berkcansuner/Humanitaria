import argparse
import logging
from ingestion.pipeline import run_pipeline
from ingestion.client import ENDPOINT_CONFIG

logger = logging.getLogger(__name__)


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
    run_pipeline(limit=args.limit, force=args.force, endpoints=args.endpoints)


if __name__ == "__main__":
    main()
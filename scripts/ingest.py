import argparse
import logging
from ingestion.pipeline import run_pipeline

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Ingest ReliefWeb reports into ChromaDB")
    parser.add_argument("--limit", type=int, default=100, help="Max reports to ingest")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    run_pipeline(limit=args.limit, force=args.force)

if __name__ == "__main__":
    main()

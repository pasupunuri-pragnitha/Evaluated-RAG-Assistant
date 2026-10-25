import argparse
import sys
from pathlib import Path
from ingest.pipeline import IngestionPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Evaluated RAG Assistant - Document Ingestion Pipeline"
    )
    parser.add_argument(
        "--docs",
        type=str,
        default="data/docs",
        help="Path to documentation directory containing markdown files (default: data/docs)",
    )
    args = parser.parse_args()

    docs_path = Path(args.docs)
    if not docs_path.exists():
        print(f"Error: Directory '{args.docs}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Starting ingestion from: {docs_path.resolve()}")
    pipeline = IngestionPipeline()
    summary = pipeline.run(docs_path)

    print("\n--- Ingestion Summary ---")
    print(f"Documents processed: {summary.documents_processed}")
    print(f"Chunks created:      {summary.chunks_created}")
    print(f"Skipped (unchanged): {summary.skipped}")
    print(f"Total documents:     {summary.total_documents}")
    print(f"Total chunks:        {summary.total_chunks}")
    print(f"Min token count:     {summary.min_token_count}")
    print(f"Max token count:     {summary.max_token_count}")
    print(f"Avg token count:     {summary.avg_token_count:.1f}")
    print(f"Time taken:          {summary.time_taken_seconds:.2f}s")
    print("-------------------------\n")


if __name__ == "__main__":
    main()

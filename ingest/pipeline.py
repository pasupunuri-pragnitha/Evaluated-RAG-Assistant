import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from db.connection import get_db_connection
from ingest.chunker import MarkdownHeadingChunker
from ingest.embedder import Embedder
from ingest.loader import DocumentFile, load_markdown_documents


@dataclass
class IngestionSummary:
    documents_processed: int
    chunks_created: int
    skipped: int
    time_taken_seconds: float


class IngestionPipeline:
    """
    Idempotent document ingestion pipeline:
    - Loads markdown documents
    - Checks content hash against database
    - Chunks by markdown headings with token bounds
    - Batch embeds chunks
    - Upserts document and replaces chunks within a single transaction
    """

    def __init__(self, embedder: Embedder | None = None):
        self.embedder = embedder or Embedder()
        self.chunker = MarkdownHeadingChunker(tokenizer=self.embedder.tokenizer)

    def run(self, docs_dir: str | Path) -> IngestionSummary:
        start_time = time.perf_counter()
        documents = load_markdown_documents(docs_dir)

        processed = 0
        chunks_created = 0
        skipped = 0

        with get_db_connection() as conn:
            for doc in documents:
                with conn.cursor() as cur:
                    # Check if document already exists and has identical content hash
                    cur.execute(
                        "SELECT id, content_hash FROM documents WHERE source_path = %s",
                        (doc.source_path,),
                    )
                    existing = cur.fetchone()

                    if existing and existing["content_hash"] == doc.content_hash:
                        skipped += 1
                        continue

                    # Generate chunks for the document
                    chunks = self.chunker.chunk_document(
                        markdown_content=doc.content, default_title=doc.title
                    )

                    # Compute batch embeddings for all chunks
                    chunk_texts = [c.content for c in chunks]
                    embeddings = self.embedder.embed_documents(
                        chunk_texts, batch_size=32
                    )

                    # Execute atomic transaction: upsert doc, delete old chunks, insert new chunks
                    cur.execute(
                        """
                        INSERT INTO documents (source_path, title, content_hash, version)
                        VALUES (%s, %s, %s, 1)
                        ON CONFLICT (source_path) DO UPDATE SET
                            title = EXCLUDED.title,
                            content_hash = EXCLUDED.content_hash,
                            version = documents.version + 1,
                            updated_at = CURRENT_TIMESTAMP
                        RETURNING id;
                        """,
                        (doc.source_path, doc.title, doc.content_hash),
                    )
                    doc_id = cur.fetchone()["id"]

                    # Delete previous chunks to prevent stale entries
                    cur.execute(
                        "DELETE FROM chunks WHERE document_id = %s;", (doc_id,)
                    )

                    # Insert new chunks
                    if chunks:
                        insert_rows = [
                            (
                                doc_id,
                                chunk.chunk_index,
                                chunk.heading_path,
                                chunk.content,
                                chunk.token_count,
                                embedding,
                            )
                            for chunk, embedding in zip(chunks, embeddings)
                        ]
                        cur.executemany(
                            """
                            INSERT INTO chunks (
                                document_id, chunk_index, heading_path, content, token_count, embedding
                            ) VALUES (%s, %s, %s, %s, %s, %s);
                            """,
                            insert_rows,
                        )

                    conn.commit()
                    processed += 1
                    chunks_created += len(chunks)

        elapsed = time.perf_counter() - start_time
        return IngestionSummary(
            documents_processed=processed,
            chunks_created=chunks_created,
            skipped=skipped,
            time_taken_seconds=elapsed,
        )

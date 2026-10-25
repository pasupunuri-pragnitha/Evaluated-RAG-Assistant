import hashlib
import os
import re
from pathlib import Path
from typing import List, NamedTuple


class DocumentFile(NamedTuple):
    source_path: str
    title: str
    content: str
    content_hash: str


def extract_title(content: str, fallback_filename: str) -> str:
    """Extract first H1 heading from markdown or fall back to file stem."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return Path(fallback_filename).stem.replace("-", " ").replace("_", " ").title()


def load_markdown_documents(docs_dir: str | Path) -> List[DocumentFile]:
    """Recursively load all markdown documents from docs_dir."""
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")

    documents: List[DocumentFile] = []
    # Collect all .md files recursively
    for file_path in sorted(docs_path.rglob("*.md")):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Normalize relative source path with forward slashes
        try:
            rel_path = file_path.relative_to(docs_path.parent).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        title = extract_title(content, file_path.name)

        documents.append(
            DocumentFile(
                source_path=rel_path,
                title=title,
                content=content,
                content_hash=content_hash,
            )
        )

    return documents

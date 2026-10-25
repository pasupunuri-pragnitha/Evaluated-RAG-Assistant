import hashlib
import os
import re
from pathlib import Path
from typing import List, NamedTuple
from app.config import settings


class DocumentFile(NamedTuple):
    source_path: str
    title: str
    content: str
    content_hash: str


def strip_fastapi_includes(content: str) -> str:
    """
    FastAPI docs include code from other files with lines like {* ../../docs_src/... *}.
    Strip those include directives while preserving surrounding text and code blocks.
    """
    # Remove standalone include lines
    cleaned = re.sub(r"^\s*\{[*].*?[*]\}\s*$", "", content, flags=re.MULTILINE)
    # Remove any inline include tags
    cleaned = re.sub(r"\{[*].*?[*]\}", "", cleaned)
    return cleaned


def extract_title(content: str, fallback_filename: str) -> str:
    """Extract first H1 heading from markdown or fall back to file stem."""
    match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if match:
        title = match.group(1).strip()
        # Clean markdown header attribute IDs like {#first-steps} or { #first-steps }
        title = re.sub(r"\{[^{}]*\}", "", title).strip()
        if title:
            return title
    return Path(fallback_filename).stem.replace("-", " ").replace("_", " ").title()


def load_markdown_documents(docs_dir: str | Path) -> List[DocumentFile]:
    """
    Recursively load all markdown documents from docs_dir.
    Skips non-content files (images, css, js, anything not ending in .md).
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")

    documents: List[DocumentFile] = []
    # Collect exclusively .md files recursively (case-insensitive)
    for file_path in sorted(docs_path.rglob("*")):
        if file_path.is_dir() or file_path.suffix.lower() not in [".md", ".markdown"]:
            continue

        # Skip excluded documents (changelogs, contributor rosters, reference docs, etc.)
        if any(
            file_path.name.lower() == ex.lower()
            or ex.lower() in file_path.as_posix().lower()
            or ex.lower().rstrip("/") in file_path.as_posix().lower()
            for ex in settings.exclude_docs
        ):
            continue

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            # Skip any binary or non-utf8 files
            continue

        # Strip FastAPI code include tags
        clean_content = strip_fastapi_includes(raw_content)

        # Normalize relative source path with forward slashes
        try:
            rel_path = file_path.relative_to(docs_path.parent).as_posix()
        except ValueError:
            rel_path = file_path.as_posix()

        content_hash = hashlib.sha256(clean_content.encode("utf-8")).hexdigest()
        title = extract_title(clean_content, file_path.name)

        documents.append(
            DocumentFile(
                source_path=rel_path,
                title=title,
                content=clean_content,
                content_hash=content_hash,
            )
        )

    return documents

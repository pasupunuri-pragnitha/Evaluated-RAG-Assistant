import hashlib
import logging
import os
import re
from pathlib import Path
from typing import List, NamedTuple
from app.config import settings

logger = logging.getLogger(__name__)

DOCS_SRC_DIR = Path("data/docs_src")


class DocumentFile(NamedTuple):
    source_path: str
    title: str
    content: str
    content_hash: str


def resolve_code_include(match: re.Match) -> str:
    """
    Resolves directives like {* ../../docs_src/path/to/file.py ln[1:20] hl[5] *}.
    Reads the file from data/docs_src, applies line range annotations if present,
    ignores hl[...] highlights, and returns code formatted in a python code fence.
    If the file cannot be found, logs a warning and returns an empty string.
    """
    full_directive = match.group(0)
    inner = match.group(1).strip()
    parts = inner.split()
    if not parts:
        return ""

    file_spec = parts[0]
    # Normalize path to relative path under docs_src
    if "docs_src/" in file_spec:
        rel_path = file_spec.split("docs_src/", 1)[1]
    else:
        rel_path = file_spec.lstrip("./")

    src_file = DOCS_SRC_DIR / rel_path
    if not src_file.exists():
        logger.warning("Code file missing for directive: %s (path: %s)", full_directive, src_file)
        return ""

    try:
        with open(src_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logger.warning("Failed to read code file %s: %s", src_file, e)
        return ""

    # Parse line range annotation: ln[start:end] or ln[start]
    line_range_match = re.search(r"ln\[(\d+)(?::(\d+))?\]", inner)
    if line_range_match:
        start_line = int(line_range_match.group(1))
        end_line = int(line_range_match.group(2)) if line_range_match.group(2) else start_line
        # Convert 1-indexed range to 0-indexed slice
        selected_lines = lines[start_line - 1 : end_line]
    else:
        selected_lines = lines

    code_text = "".join(selected_lines).rstrip()
    if not code_text:
        return ""

    return f"\n\n```python\n{code_text}\n```\n\n"


def resolve_fastapi_includes(content: str) -> str:
    """
    Replaces FastAPI code inclusion directives with actual inlined code blocks.
    """
    return re.sub(r"\{[*]\s*(.*?)\s*[*]\}\n?", resolve_code_include, content)


def strip_html_noise(content: str) -> str:
    """
    Strips raw HTML tags (<div>, <u>, <dfn>, <details>, <summary>, <a>, <span>, <font>, etc.)
    and style/class attributes, while preserving visible text.
    """
    # Remove standalone void elements like img
    text = re.sub(r"<img[^>]*>", "", content)
    # Remove button elements and contents (e.g. tabs in opinions)
    text = re.sub(r"<button[^>]*>.*?</button>", "", text, flags=re.DOTALL)
    # Remove HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Strip opening and closing HTML tags, keeping inner text
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
    return text


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
    Recursively loads all markdown documents from docs_dir.
    Resolves code includes from data/docs_src, strips HTML noise,
    and skips excluded documents.
    """
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")

    documents: List[DocumentFile] = []
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
            continue

        # 1. Resolve {* ../../docs_src/... *} directives into fenced python blocks
        with_code = resolve_fastapi_includes(raw_content)

        # 2. Strip HTML tags and attributes while keeping visible text
        clean_content = strip_html_noise(with_code)

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

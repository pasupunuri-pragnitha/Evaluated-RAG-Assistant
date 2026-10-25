import pytest
from transformers import AutoTokenizer
from ingest.chunker import MarkdownHeadingChunker


@pytest.fixture(scope="module")
def tokenizer():
    return AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")


@pytest.fixture
def chunker(tokenizer):
    return MarkdownHeadingChunker(
        tokenizer=tokenizer,
        target_tokens=100,
        overlap_tokens=20,
        max_tokens=150,
        min_tokens=30,
    )


def test_headings_inside_code_fences_ignored(chunker):
    markdown = """# Main Title

Intro text for the document.

```python
# This is a python comment
def compute():
    # Another comment inside fence
    return 42
```

~~~bash
# Bash comment inside tilde fence
echo "hello world"
~~~

## Sub Section

Real subsection content goes here with plenty of words to verify heading hierarchy and structure.
FastAPI provides automatic docs, data validation, and dependency injection right out of the box.
Building production services requires robust validation, comprehensive testing, and clear architecture.
"""
    chunks = chunker.chunk_document(markdown, default_title="Main Title")
    
    # Verify no heading path contains the code comments
    for chunk in chunks:
        assert "# This is a python comment" not in chunk.heading_path
        assert "Another comment inside fence" not in chunk.heading_path
        assert "Bash comment inside tilde fence" not in chunk.heading_path

    # Heading paths should strictly be from actual markdown headings
    heading_paths = [c.heading_path for c in chunks]
    assert any("Main Title" in p for p in heading_paths)
    assert any("Sub Section" in p for p in heading_paths)


def test_chunks_never_exceed_max_token_limit(chunker):
    # Create very long content under a heading
    long_paragraph = "FastAPI is a modern, fast web framework for building APIs with Python. " * 50
    markdown = f"""# Performance Test

{long_paragraph}
"""
    chunks = chunker.chunk_document(markdown, default_title="Performance Test")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= chunker.max_tokens


def test_tiny_chunks_are_merged(chunker):
    markdown = """# First Section

Tiny note.

## Second Section

Here is substantial content for the second section that exceeds the minimum token threshold.
We add plenty of sentences explaining how dependencies and background tasks operate in FastAPI.
"""
    chunks = chunker.chunk_document(markdown, default_title="Overview")
    # Tiny "Tiny note." should be merged rather than remaining a standalone tiny chunk
    for chunk in chunks:
        assert chunk.token_count >= chunker.min_tokens

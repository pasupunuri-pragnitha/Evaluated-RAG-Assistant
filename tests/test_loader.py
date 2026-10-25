import logging
import pytest
from pathlib import Path
from ingest.loader import (
    resolve_fastapi_includes,
    strip_html_noise,
)
import ingest.loader as loader_mod


def test_code_directive_inlined_with_line_range_and_hl_ignored(tmp_path, monkeypatch):
    # Setup mock docs_src dir
    docs_src = tmp_path / "docs_src"
    docs_src.mkdir(parents=True)
    sample_file = docs_src / "sample.py"
    sample_file.write_text(
        "line 1\nline 2: important logic\nline 3: extra detail\nline 4: final step\nline 5\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(loader_mod, "DOCS_SRC_DIR", docs_src)

    # Directive with range ln[2:4] and highlight hl[3]
    content = """Here is an example:
{* ../../docs_src/sample.py ln[2:4] hl[3] *}
And more text follows."""

    resolved = resolve_fastapi_includes(content)

    assert "```python" in resolved
    assert "line 2: important logic" in resolved
    assert "line 3: extra detail" in resolved
    assert "line 4: final step" in resolved
    # Lines outside 2..4 should not be inlined
    assert "line 1" not in resolved
    assert "line 5" not in resolved


def test_missing_file_logs_warning_and_drops_line(tmp_path, monkeypatch, caplog):
    docs_src = tmp_path / "docs_src"
    docs_src.mkdir(parents=True)
    monkeypatch.setattr(loader_mod, "DOCS_SRC_DIR", docs_src)

    content = """Before directive.
{* ../../docs_src/non_existent.py ln[1:5] *}
After directive."""

    with caplog.at_level(logging.WARNING):
        resolved = resolve_fastapi_includes(content)

    # Directive line was dropped
    assert "non_existent.py" not in resolved
    assert "```python" not in resolved
    assert "Before directive." in resolved
    assert "After directive." in resolved
    assert any("Code file missing for directive" in record.message for record in caplog.records)


def test_strip_html_noise():
    raw_markdown = """Here is <dfn class="term">Dependency Injection</dfn> explanation.
<div class="admonition note">
<p class="admonition-title">Note</p>
<p>Keep this text content!</p>
</div>
<button class="tab-button">Ignore button</button>
<!-- HTML comment to drop -->
<u>Underlined text</u>
<img src="chart.png" alt="chart">
"""
    cleaned = strip_html_noise(raw_markdown)

    assert "<dfn" not in cleaned
    assert "</dfn>" not in cleaned
    assert "Dependency Injection" in cleaned
    assert "<div" not in cleaned
    assert "<p" not in cleaned
    assert "Keep this text content!" in cleaned
    assert "Ignore button" not in cleaned
    assert "HTML comment to drop" not in cleaned
    assert "<img" not in cleaned
    assert "Underlined text" in cleaned

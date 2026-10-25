import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

FASTAPI_REPO_URL = "https://github.com/fastapi/fastapi.git"
TARGET_DOCS_DIR = Path("data/docs/fastapi")


def download_fastapi_docs():
    """
    Shallow-clones fastapi repository into a temporary directory
    and copies docs/en/docs into data/docs/fastapi.
    """
    TARGET_DOCS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Shallow cloning {FASTAPI_REPO_URL} into temporary directory...")
        cmd = ["git", "clone", "--depth", "1", FASTAPI_REPO_URL, temp_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Git clone failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(result.returncode)

        source_en_docs = Path(temp_dir) / "docs" / "en" / "docs"
        if not source_en_docs.exists():
            print(
                f"Error: Could not locate 'docs/en/docs' in cloned repository: {source_en_docs}",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"Copying documentation from {source_en_docs} to {TARGET_DOCS_DIR}...")
        shutil.copytree(source_en_docs, TARGET_DOCS_DIR, dirs_exist_ok=True)

    print(f"Successfully downloaded and populated FastAPI docs into {TARGET_DOCS_DIR.resolve()}")


if __name__ == "__main__":
    download_fastapi_docs()

import logging
import re
from typing import List, Set, Tuple
import httpx
from app.config import REFUSAL_MESSAGE, settings
from app.schemas import SourceItem
from retrieval.vector import SearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are an expert technical documentation assistant.
Answer the user's question using ONLY the facts and code provided in the numbered context passages below.

Strict instructions:
1. Answer ONLY from the provided context passages. Do NOT extrapolate, speculate, or introduce outside knowledge.
2. Cite the context passages you use with brackets, such as [1], [2], etc.
3. If the provided context does not contain enough information to answer the question, you must reply strictly with: "{REFUSAL_MESSAGE}"
4. Be direct, factual, and concise."""


class LLMClient:
    """
    Client for OpenAI-compatible LLM endpoints (e.g. Ollama v1 at http://localhost:11434/v1).
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.endpoint = f"{self.base_url}/chat/completions"

    def check_reachability(self, timeout: float = 3.0) -> bool:
        """Verify the LLM server is up and responding."""
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.get(f"{self.base_url}/models")
                return res.status_code == 200
        except Exception:
            return False

    def generate_answer(self, query: str, chunks: List[SearchResult]) -> str:
        """
        Formats retrieved passages into the grounded prompt, calls the OpenAI-compatible endpoint,
        and returns the raw generated answer.
        """
        if not chunks:
            return REFUSAL_MESSAGE

        context_blocks = []
        for i, chunk in enumerate(chunks, 1):
            context_blocks.append(
                f"[{i}] Document: {chunk.source_path} | Section: {chunk.heading_path}\n{chunk.content}"
            )
        formatted_context = "\n\n".join(context_blocks)

        user_content = f"Context Passages:\n{formatted_context}\n\nQuestion: {query}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        }

        try:
            with httpx.Client(timeout=float(settings.llm_timeout_seconds)) as client:
                response = client.post(self.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError as e:
            logger.error("LLM server connection error at %s: %s", self.endpoint, e)
            raise ConnectionError(f"LLM server not reachable at {self.base_url}") from e
        except Exception as e:
            logger.error("LLM generation request failed: %s", e)
            raise


def process_answer_and_citations(
    answer: str,
    k: int,
    sources_retrieved: List[SourceItem],
) -> Tuple[str, bool, List[SourceItem], List[str]]:
    """
    Validates citations, detects refusal, strips invalid brackets, and filters cited sources.
    Returns: (cleaned_answer, refused, sources_cited, warnings)
    """
    warnings: List[str] = []

    # Check if model refused
    if answer.strip().lower().startswith("i don't know") or answer.strip() == REFUSAL_MESSAGE:
        return REFUSAL_MESSAGE, True, [], []

    found_citation_indices: Set[int] = set()

    def citation_replacer(match: re.Match) -> str:
        num = int(match.group(1))
        if 1 <= num <= k:
            found_citation_indices.add(num)
            return match.group(0)
        else:
            warnings.append(f"citation [{num}] outside 1..{k} removed")
            return ""

    # Validate and filter [n] citations
    cleaned_answer = re.sub(r"\[(\d+)\]", citation_replacer, answer)
    # Collapse double spaces created by removed citations
    cleaned_answer = re.sub(r"  +", " ", cleaned_answer).strip()

    # Filter sources_cited to only those present in the answer
    sources_cited = [s for s in sources_retrieved if s.index in found_citation_indices]

    if not found_citation_indices:
        warnings.append("no citations in answer")

    return cleaned_answer, False, sources_cited, warnings

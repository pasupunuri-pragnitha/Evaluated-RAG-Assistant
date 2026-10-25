import logging
from typing import List, Tuple
import httpx
from app.config import settings
from retrieval.vector import SearchResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical documentation assistant.
Answer the user's question using ONLY the facts and code provided in the numbered context passages below.

Strict instructions:
1. Answer ONLY from the provided context passages. Do NOT extrapolate, speculate, or introduce outside knowledge.
2. Cite the context passages you use with brackets, such as [1], [2], etc.
3. If the provided context does not contain enough information to answer the question, reply strictly with: "I don't know."
4. Be direct, factual, and concise."""


class LLMClient:
    """
    Client for OpenAI-compatible LLM endpoints (e.g. Ollama v1 at http://localhost:11434/v1).
    """

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.endpoint = f"{self.base_url}/chat/completions"

    def generate_answer(
        self, query: str, chunks: List[SearchResult]
    ) -> Tuple[str, List[SearchResult]]:
        """
        Formats retrieved passages into the grounded prompt, calls the LLM,
        and returns the generated answer and associated citations.
        """
        if not chunks:
            return "I don't know.", []

        # Format context passages with 1-based indexing for citations
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
                answer = data["choices"][0]["message"]["content"].strip()
                return answer, chunks
        except Exception as e:
            logger.error("LLM generation request failed: %s", e)
            raise RuntimeError(f"LLM generation failed: {e}") from e

from typing import List
from sentence_transformers import SentenceTransformer
from app.config import settings


class Embedder:
    """
    Embedding service wrapping sentence-transformers for BAAI/bge-small-en-v1.5.
    Embeds documents normalized, without the query prefix.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model_name
        self.model = SentenceTransformer(self.model_name)

    @property
    def tokenizer(self):
        """Provide underlying HuggingFace tokenizer for accurate token counts."""
        return self.model.tokenizer

    def embed_documents(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """
        Embed list of document texts in batches with L2 normalization
        and without query instruction prefix.
        """
        if not texts:
            return []

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

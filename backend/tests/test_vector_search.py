from unittest.mock import patch

from app.services.embeddings import BaseEmbedder, GeminiEmbedder, LocalSentenceTransformerEmbedder, get_embedder

class DummyEmbedder(BaseEmbedder):
    def embed_text(self, text):
        return [0.1, 0.2, 0.3]
    def embed_batch(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

def test_embedder_factory():
    with patch("app.core.config.settings.gemini_api_key", "test_key"):
        embedder = get_embedder()
        assert isinstance(embedder, GeminiEmbedder)
        
    with patch("app.core.config.settings.gemini_api_key", None):
        embedder = get_embedder()
        assert isinstance(embedder, LocalSentenceTransformerEmbedder)

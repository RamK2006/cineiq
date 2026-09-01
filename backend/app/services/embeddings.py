import abc
from typing import List
import structlog
from app.core.config import settings

logger = structlog.get_logger(__name__)

class BaseEmbedder(abc.ABC):
    """Abstract Base Class for Vector Embeddings Generation."""
    
    @abc.abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate an embedding for a single string."""
        pass
        
    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of strings."""
        pass

class GeminiEmbedder(BaseEmbedder):
    """
    Implementation using Google Gemini Embedding API.
    Provides highly dimensional dense semantic vectors (e.g., text-embedding-004).
    """
    def __init__(self, model_name: str = "models/text-embedding-004"):
        self.model_name = model_name
        self._initialize_client()
        
    def _initialize_client(self):
        if not settings.gemini_api_key:
            logger.warning("gemini_api_key_missing", msg="GeminiEmbedder initialized without an API key")
            return
            
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        
    def embed_text(self, text: str) -> List[float]:
        if not text.strip():
            return []
            
        import google.generativeai as genai
        try:
            result = genai.embed_content(
                model=self.model_name,
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error("gemini_embedding_failed", error=str(e), text_sample=text[:20])
            return []
            
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        import google.generativeai as genai
        embeddings = []
        try:
            # Note: Gemini embed_content supports lists
            result = genai.embed_content(
                model=self.model_name,
                content=texts,
                task_type="retrieval_document"
            )
            # Depending on SDK version, result might be a dict with 'embedding' as a list of lists
            emb = result.get('embedding', [])
            if emb and not isinstance(emb[0], list):
                # single result returned
                return [emb]
            return emb
        except Exception as e:
            logger.error("gemini_batch_embedding_failed", error=str(e))
            # Fallback to serial processing
            for t in texts:
                embeddings.append(self.embed_text(t))
            return embeddings

class LocalSentenceTransformerEmbedder(BaseEmbedder):
    """
    Local offline embedding generation using HuggingFace sentence-transformers.
    Defaults to all-MiniLM-L6-v2 which maps sentences to a 384 dimensional dense vector.
    """
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()
        
    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info("sentence_transformer_loaded", model=self.model_name)
        except ImportError:
            logger.warning("sentence_transformers_not_installed", msg="pip install sentence-transformers")
        except Exception as e:
            logger.error("sentence_transformers_load_failed", error=str(e))
            
    def embed_text(self, text: str) -> List[float]:
        if not self.model or not text.strip():
            return []
        vectors = self.model.encode([text])
        return vectors[0].tolist()
        
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.model or not texts:
            return []
        vectors = self.model.encode(texts)
        return vectors.tolist()

def get_embedder() -> BaseEmbedder:
    """Factory method to return the most appropriate configured embedder."""
    if settings.gemini_api_key:
        return GeminiEmbedder()
    else:
        return LocalSentenceTransformerEmbedder()

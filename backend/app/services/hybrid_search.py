import re
import math
import time
import structlog
from typing import List, Dict, Tuple, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Movie
from app.core.config import settings

logger = structlog.get_logger()

def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase words."""
    return re.findall(r'\w+', (text or '').lower())

class BM25Scorer:
    def __init__(self, movies: List[Movie], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.movies = movies
        self.num_docs = len(movies)
        
        self.doc_lengths = []
        self.doc_term_freqs: List[Dict[str, int]] = []
        self.doc_ids = []
        self.df: Dict[str, int] = {}
        
        for m in movies:
            content = f"{m.title} {m.title} {m.overview}" # Weigh title higher
            tokens = tokenize(content)
            self.doc_lengths.append(len(tokens))
            self.doc_ids.append(m.id)
            
            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs.append(tf)
            
            for t in tf.keys():
                self.df[t] = self.df.get(t, 0) + 1
                
        self.avg_doc_len = sum(self.doc_lengths) / max(self.num_docs, 1)

    def get_idf(self, term: str) -> float:
        df_t = self.df.get(term, 0)
        return math.log((self.num_docs - df_t + 0.5) / (df_t + 0.5) + 1.0)

    def score(self, query: str) -> List[Tuple[str, float]]:
        query_terms = tokenize(query)
        scores = []
        
        for idx, doc_id in enumerate(self.doc_ids):
            doc_score = 0.0
            doc_len = self.doc_lengths[idx]
            tf_dict = self.doc_term_freqs[idx]
            
            for term in query_terms:
                tf = tf_dict.get(term, 0)
                if tf == 0:
                    continue
                idf = self.get_idf(term)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / max(self.avg_doc_len, 1)))
                doc_score += idf * (numerator / denominator)
                
            if doc_score > 0:
                scores.append((doc_id, doc_score))
                
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

_model_cache = None

def get_sentence_transformer():
    global _model_cache
    if _model_cache is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model_cache = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            logger.warning("failed_to_load_sentence_transformer", error=str(e))
    return _model_cache

class HybridSearchEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, limit: int = 10) -> List[Tuple[Movie, float]]:
        """Perform hybrid search using BM25 and Semantic Embeddings combined via RRF."""
        start_time = time.time()
        
        stmt = select(Movie)
        result = await self.db.execute(stmt)
        movies = list(result.scalars().all())
        
        if not movies:
            return []

        # 1. Calculate BM25 ranks
        bm25_scorer = BM25Scorer(movies)
        bm25_scores = bm25_scorer.score(query)
        bm25_ranks: Dict[str, int] = {movie_id: rank + 1 for rank, (movie_id, _) in enumerate(bm25_scores)}

        # 2. Calculate Semantic ranks
        semantic_scores: List[Tuple[str, float]] = []
        qdrant_success = False
        
        if settings.qdrant_url and query:
            try:
                from qdrant_client import QdrantClient
                model = get_sentence_transformer()
                if model:
                    query_vector = model.encode(query).tolist()
                    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
                    if client.collection_exists("movies"):
                        qdrant_results = client.search(
                            collection_name="movies",
                            query_vector=query_vector,
                            limit=len(movies)
                        )
                        if qdrant_results:
                            semantic_scores = [(str(hit.payload.get("movie_id", hit.id)), float(hit.score)) for hit in qdrant_results]
                            qdrant_success = True
            except Exception as e:
                logger.warning("qdrant_semantic_search_failed", error=str(e))

        if not qdrant_success and query:
            try:
                model = get_sentence_transformer()
                if model:
                    doc_texts = [f"{m.title} {m.overview}" for m in movies]
                    embeddings = model.encode(doc_texts)
                    query_emb = model.encode(query)
                    
                    import numpy as np
                    dot_products = np.dot(embeddings, query_emb)
                    norms_doc = np.linalg.norm(embeddings, axis=1)
                    norm_query = np.linalg.norm(query_emb)
                    
                    similarities = dot_products / (norms_doc * norm_query + 1e-8)
                    for idx, m in enumerate(movies):
                        semantic_scores.append((m.id, float(similarities[idx])))
            except Exception as e:
                logger.warning("in_memory_semantic_search_failed", error=str(e))
                # Overlap score fallback
                for m in movies:
                    q_words = set(tokenize(query))
                    m_words = set(tokenize(f"{m.title} {m.overview}"))
                    overlap = len(q_words & m_words) / max(len(q_words), 1)
                    semantic_scores.append((m.id, overlap))

        semantic_scores.sort(key=lambda x: x[1], reverse=True)
        semantic_ranks: Dict[str, int] = {movie_id: rank + 1 for rank, (movie_id, _) in enumerate(semantic_scores)}

        # 3. Combine ranks using Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        for m in movies:
            m_id = m.id
            r_bm25 = bm25_ranks.get(m_id, 100000)
            r_sem = semantic_ranks.get(m_id, 100000)
            
            rrf_score = (1.0 / (60.0 + r_bm25)) + (1.0 / (60.0 + r_sem))
            rrf_scores[m_id] = rrf_score

        movies_map = {m.id: m for m in movies}
        sorted_movie_ids = sorted(rrf_scores.keys(), key=lambda mid: rrf_scores[mid], reverse=True)
        
        results = []
        for mid in sorted_movie_ids[:limit]:
            movie = movies_map[mid]
            score = rrf_scores[mid]
            results.append((movie, score))

        latency = (time.time() - start_time) * 1000
        logger.info("hybrid_search_completed", query=query, latency_ms=latency, results=len(results))
        return results

import math
from typing import List, Dict, Any, Tuple
from collections import Counter
import structlog

from app.services.ml_engine.matrix_factorization import ImplicitFeedbackMF
from app.services.ml_engine.nlp_sentiment import SimpleTFIDFAnalyzer

logger = structlog.get_logger(__name__)

class RadarItem:
    def __init__(self, subject: str, A: int, fullMark: int = 100):
        self.subject = subject
        self.A = A
        self.fullMark = fullMark

class TasteAnalyticsEngine:
    """
    A highly-engineered analytics engine that fuses Matrix Factorization, 
    TF-IDF NLP Sentiment Analysis, and Explicit Rules to dynamically generate
    accurate User Taste Profiles and Radar charts.
    """
    
    def __init__(self):
        self.mf_model = ImplicitFeedbackMF(num_factors=10, epochs=25)
        self.nlp_analyzer = SimpleTFIDFAnalyzer()
        
    def _extract_base_weight(self, interaction_type: str, rating: float = None) -> float:
        interaction = str(interaction_type).upper()
        base = 1.0
        if interaction in ["LIKE", "FAVORITE", "FAVOURITE"]:
            base = 2.0
        elif interaction == "WATCHLIST":
            base = 1.5
        elif interaction == "DISLIKE":
            base = -1.0
            
        if rating is not None:
            r = float(rating)
            base *= (r if r >= 4 else (r * 0.5))
            
        return base

    def compute_taste_radar(
        self, 
        user_id: str,
        interactions: List[Dict[str, Any]], 
        reviews: List[Dict[str, str]]
    ) -> Tuple[List[RadarItem], str, List[Dict[str, Any]]]:
        """
        Takes raw interactions and textual reviews, processes them through the ML pipeline,
        and spits out a normalized radar chart.
        """
        
        # 1. Prepare ML Pipelines
        mf_tuples = []
        for ix in interactions:
            u_id = ix.get("user_id", user_id)
            m_id = str(ix.get("movie_id"))
            weight = self._extract_base_weight(ix.get("interaction", "NONE"), ix.get("rating"))
            mf_tuples.append((u_id, m_id, weight))
            
        # Fit models
        self.mf_model.fit(mf_tuples)
        self.nlp_analyzer.fit([r.get("text", "") for r in reviews if r.get("text")])
        
        # 2. Score Genres
        genre_scores: Dict[str, float] = {}
        
        # Map textual sentiment to genres
        for review in reviews:
            m_id = str(review.get("movie_id"))
            text = review.get("text", "")
            sentiment = self.nlp_analyzer.analyze_sentiment_weight(text)
            
            # Find the movie's genres from interactions (assuming joined data)
            movie_genres = next((ix.get("genres", []) for ix in interactions if str(ix.get("movie_id")) == m_id), [])
            for g in movie_genres:
                clean_g = str(g).strip()
                # Apply sentiment modifier to genre
                genre_scores[clean_g] = genre_scores.get(clean_g, 0.0) + (sentiment * 1.5)
                
        # Combine with Matrix Factorization implicit predictions
        for ix in interactions:
            m_id = str(ix.get("movie_id"))
            implicit_score = self.mf_model.predict(user_id, m_id)
            explicit_score = self._extract_base_weight(ix.get("interaction", "NONE"), ix.get("rating"))
            
            fused_score = (implicit_score * 0.4) + (explicit_score * 0.6)
            
            for g in ix.get("genres", []):
                clean_g = str(g).strip()
                genre_scores[clean_g] = genre_scores.get(clean_g, 0.0) + fused_score
                
        # 3. Normalize to 0-100 scale (Top 6)
        filtered_genres = {k: max(v, 0.0) for k, v in genre_scores.items()}
        if not filtered_genres or max(filtered_genres.values(), default=0) == 0:
            return [], "Insufficient interaction history to compile your taste profile.", []
            
        sorted_genres = sorted(filtered_genres.items(), key=lambda x: x[1], reverse=True)[:6]
        max_score = sorted_genres[0][1] if sorted_genres else 1.0
        if max_score == 0: max_score = 1.0
        
        radar_data = []
        genre_prefs = []
        for genre, score in sorted_genres:
            normalized = int(math.ceil((score / max_score) * 100))
            normalized = min(max(normalized, 0), 100)
            
            radar_data.append(RadarItem(subject=genre, A=normalized))
            genre_prefs.append({"genre": genre, "score": normalized})
            
        # 4. Generate Contextual Message
        primary_genre = sorted_genres[0][0] if len(sorted_genres) > 0 else "N/A"
        secondary_genre = sorted_genres[1][0] if len(sorted_genres) > 1 else "N/A"
        primary_val = next((r.A for r in radar_data if r.subject == primary_genre), 0)
        secondary_val = next((r.A for r in radar_data if r.subject == secondary_genre), 0)

        if len(sorted_genres) > 1:
            msg = f"Your taste profile leans heavily toward {primary_genre} ({primary_val}%) and {secondary_genre} ({secondary_val}%)."
        else:
            msg = f"Your taste profile leans heavily toward {primary_genre} ({primary_val}%)."

        return radar_data, msg, genre_prefs

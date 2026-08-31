import json
import structlog
from typing import List, Dict, Tuple
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Interaction, Review, Movie
from app.db.session import get_redis

logger = structlog.get_logger()

class CollaborativeRecommender:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = get_redis()

    async def train_and_cache_all(self) -> None:
        """Fetch ratings data, compute personalized recommendations, and cache them in Redis."""
        logger.info("recommender_training_start")
        try:
            # 1. Fetch ratings from reviews
            reviews_result = await self.db.execute(
                select(Review.user_id, Review.movie_id, Review.rating)
            )
            reviews = reviews_result.all()

            # 2. Fetch ratings from interactions
            interactions_result = await self.db.execute(
                select(Interaction.user_id, Interaction.movie_id, Interaction.interaction_type)
            )
            interactions = interactions_result.all()

            # Construct ratings dictionary: user_id -> movie_id -> rating
            user_item_ratings: Dict[str, Dict[str, float]] = {}

            # Map interaction types to numeric scores
            interaction_scores = {
                "like": 5.0,
                "watchlist": 4.0,
                "view": 3.0,
                "dislike": 1.0
            }

            for user_id, movie_id, rating in reviews:
                if user_id not in user_item_ratings:
                    user_item_ratings[user_id] = {}
                user_item_ratings[user_id][movie_id] = float(rating)

            for user_id, movie_id, itype in interactions:
                score = interaction_scores.get(itype, 3.0)
                if user_id not in user_item_ratings:
                    user_item_ratings[user_id] = {}
                if movie_id not in user_item_ratings[user_id]:
                    user_item_ratings[user_id][movie_id] = score
                else:
                    user_item_ratings[user_id][movie_id] = max(user_item_ratings[user_id][movie_id], score)

            # Get all movies for mapping/candidate generation
            movies_result = await self.db.execute(select(Movie))
            all_movies = {m.id: m for m in movies_result.scalars().all()}

            if not user_item_ratings or not all_movies:
                logger.info("recommender_training_skipped_empty_data")
                return

            # Compute recommendations for each user
            for target_user_id in user_item_ratings.keys():
                recs = self._get_recommendations_for_user(target_user_id, user_item_ratings, all_movies)
                if recs and self.redis:
                    key = f"rec:user:{target_user_id}"
                    cached_data = []
                    for movie, match_score in recs[:20]:
                        cached_data.append({
                            "id": movie.id,
                            "title": movie.title,
                            "poster_path": movie.poster_path,
                            "vote_average": movie.vote_average,
                            "genres": movie.genres or ["Movie"],
                            "match_score": round(match_score, 2)
                        })
                    self.redis.setex(key, 21600, json.dumps(cached_data)) # TTL 6 hours
                    logger.info("recommender_cached_user_recs", user_id=target_user_id, count=len(cached_data))

            logger.info("recommender_training_completed")
        except Exception as e:
            logger.error("recommender_training_failed", error=str(e))

    def _get_recommendations_for_user(
        self,
        target_user_id: str,
        user_item_ratings: Dict[str, Dict[str, float]],
        all_movies: Dict[str, Movie]
    ) -> List[Tuple[Movie, float]]:
        """Compute user-based collaborative filtering predictions using Cosine Similarity."""
        target_ratings = user_item_ratings.get(target_user_id, {})
        if not target_ratings:
            return []

        similarities: List[Tuple[str, float]] = []
        for other_user_id, other_ratings in user_item_ratings.items():
            if other_user_id == target_user_id:
                continue
            
            common_movies = set(target_ratings.keys()) & set(other_ratings.keys())
            if not common_movies:
                continue

            dot_product = sum(target_ratings[m] * other_ratings[m] for m in common_movies)
            norm_target = sum(target_ratings[m] ** 2 for m in target_ratings.keys()) ** 0.5
            norm_other = sum(other_ratings[m] ** 2 for m in other_ratings.keys()) ** 0.5

            if norm_target > 0 and norm_other > 0:
                similarity = dot_product / (norm_target * norm_other)
                similarities.append((other_user_id, similarity))

        similarities.sort(key=lambda x: x[1], reverse=True)

        predictions: Dict[str, float] = {}
        similarity_sums: Dict[str, float] = {}

        for other_user_id, sim in similarities[:10]:
            if sim <= 0:
                continue
            for movie_id, rating in user_item_ratings[other_user_id].items():
                if movie_id in target_ratings:
                    continue
                
                if movie_id not in predictions:
                    predictions[movie_id] = 0.0
                    similarity_sums[movie_id] = 0.0
                
                predictions[movie_id] += rating * sim
                similarity_sums[movie_id] += sim

        final_recs = []
        for movie_id, weighted_sum in predictions.items():
            if similarity_sums[movie_id] > 0:
                predicted_rating = weighted_sum / similarity_sums[movie_id]
                match_score = predicted_rating / 5.0
                movie = all_movies.get(movie_id)
                if movie:
                    final_recs.append((movie, match_score))

        final_recs.sort(key=lambda x: x[1], reverse=True)
        return final_recs

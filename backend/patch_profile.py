import re

with open('app/api/v1/profile.py', 'r') as f:
    content = f.read()

# Add imports
imports = """
from app.services.ml_engine.taste_profile import TasteAnalyticsEngine
from app.db.models import Review
"""

content = content.replace("from app.db.models import Interaction, Movie", "from app.db.models import Interaction, Movie, Review")
content = imports + content

# Replace the router logic to query reviews and use the engine
new_router_logic = """
    # Instantiate ML Engine
    engine = TasteAnalyticsEngine()
    
    # Fetch Interactions
    interaction_result = await db.execute(
        select(Interaction, Movie)
        .join(Movie, Interaction.movie_id == Movie.id)
        .where(Interaction.user_id == user_id)
        .order_by(Interaction.timestamp.desc())
    )
    interaction_rows = interaction_result.all()
    
    # Fetch Reviews for NLP
    review_result = await db.execute(
        select(Review)
        .where(Review.user_id == user_id)
    )
    review_rows = review_result.scalars().all()
    
    reviews_list = [
        {"movie_id": r.movie_id, "text": r.text}
        for r in review_rows
    ]

    watched_movie_ids = set()
    history_items = []
    
    for interaction, movie in interaction_rows:
        interaction_type = (interaction.interaction_type or "").upper()
        if interaction_type in {"VIEW", "WATCH", "WATCHED"}:
            watched_movie_ids.add(interaction.movie_id)
            
        movie_genres = [str(g).strip() for g in (movie.genres or []) if str(g).strip()]
        history_items.append({
            "user_id": user_id,
            "movie_id": interaction.movie_id,
            "genres": movie_genres,
            "rating": interaction.rating,
            "interaction": interaction_type
        })
        
    active_history = history_items if history_items else MOCK_WATCH_HISTORY
    
    # Compute using the highly engineered ML engine
    radar_data, summary_msg, genre_prefs = engine.compute_taste_radar(user_id, active_history, reviews_list)
    
    from app.api.v1.profile import RadarItem, GenrePreference
    
    # We map back to the Pydantic models
    formatted_radar = [RadarItem(subject=r.subject, A=r.A, fullMark=r.fullMark) for r in radar_data]
    formatted_prefs = [GenrePreference(genre=p["genre"], score=p["score"]) for p in genre_prefs]

    return ProfileStatsResponse(
        movies_watched=len(watched_movie_ids) if history_items else 12,
        reviews=len(review_rows) if review_rows else 5,
        genre_preferences=formatted_prefs,
        radarData=formatted_radar,
        summaryMessage=summary_msg,
    )
"""

content = re.sub(r'result = await db\.execute\([\s\S]*return ProfileStatsResponse\([\s\S]*?\)\n', new_router_logic, content)

with open('app/api/v1/profile.py', 'w') as f:
    f.write(content)

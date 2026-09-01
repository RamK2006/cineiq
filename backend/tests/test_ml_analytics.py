from app.services.ml_engine.matrix_factorization import ImplicitFeedbackMF
from app.services.ml_engine.nlp_sentiment import SimpleTFIDFAnalyzer
from app.services.ml_engine.taste_profile import TasteAnalyticsEngine

def test_implicit_feedback_mf():
    mf = ImplicitFeedbackMF(num_factors=5, epochs=10)
    interactions = [
        ("user1", "movie1", 2.0),
        ("user1", "movie2", -1.0),
        ("user2", "movie1", 1.5)
    ]
    mf.fit(interactions)
    
    pred1 = mf.predict("user1", "movie1")
    pred2 = mf.predict("user1", "movie2")
    
    # movie1 should have a higher prediction than movie2 for user1
    assert pred1 > pred2

def test_nlp_sentiment_analyzer():
    analyzer = SimpleTFIDFAnalyzer()
    corpus = [
        "This movie was a stunning masterpiece.",
        "Terrible and boring, I hate it.",
        "A good action flick."
    ]
    analyzer.fit(corpus)
    
    # Positive sentiment
    score_pos = analyzer.analyze_sentiment_weight("What a masterpiece, I loved it.")
    assert score_pos > 0.0
    
    # Negative sentiment
    score_neg = analyzer.analyze_sentiment_weight("It was terrible and dull.")
    assert score_neg < 0.0
    
def test_taste_analytics_engine():
    engine = TasteAnalyticsEngine()
    user_id = "user123"
    
    interactions = [
        {"movie_id": "m1", "interaction": "LIKE", "genres": ["Sci-Fi", "Action"]},
        {"movie_id": "m2", "interaction": "DISLIKE", "genres": ["Comedy"]},
        {"movie_id": "m3", "rating": 5.0, "genres": ["Sci-Fi", "Thriller"]},
    ]
    
    reviews = [
        {"movie_id": "m1", "text": "This was an amazing masterpiece!"},
        {"movie_id": "m2", "text": "Terrible movie, absolutely awful."}
    ]
    
    radar_data, summary, genre_prefs = engine.compute_taste_radar(user_id, interactions, reviews)
    
    assert len(radar_data) > 0
    assert len(genre_prefs) > 0
    
    # Sci-Fi should be the top genre
    assert radar_data[0].subject == "Sci-Fi"
    assert radar_data[0].A == 100 # Normalized to 100
    
    # Summary message should correctly format the output
    assert "Your taste profile leans heavily toward Sci-Fi" in summary
    assert "Thriller" in summary

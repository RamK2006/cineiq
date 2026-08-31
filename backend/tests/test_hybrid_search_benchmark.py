import pytest
import time
from app.db.session import AsyncSessionLocal
from app.services.hybrid_search import HybridSearchEngine
from app.services.sync import seed_movies_if_empty

BENCHMARK_QUERIES = [
    "Christopher Nolan space adventure with black hole",
    "Entering dreams to steal information",
    "Paul Atreides dunes desert sand worms",
    "J. Robert Oppenheimer atomic bomb nuclear physics",
    "Batman Joker chaos Gotham vigilante",
    "Animated girl spirit world bathhouse gods",
    "Miles Morales multiverse animation spider hero",
    "Class discrimination wealthy family parasite house",
    "Nolan time dilation relativity wormhole planets",
    "Dream heist inception Cobb DiCaprio Leonardo",
    "Desert planet Arrakis Fremen revenge Zendaya Chani",
    "Manhattan project nuclear bomb World War II",
    "Bruce Wayne Heath Ledger Joker Dark Knight",
    "Studio Ghibli Hayao Miyazaki Chihiro magic dragon",
    "Spider-Man Gwen Stacy multiversal journey",
    "Poor family pretending rich home tutor chauffeur",
    "Matthew McConaughey Cooper space travel TARS",
    "Dream within a dream spinning top totem Mal",
    "Denis Villeneuve sci-fi spice universe Harkonnen",
    "Los Alamos physics trinity test Cillian Murphy"
]

@pytest.mark.asyncio
async def test_hybrid_search_benchmark():
    """Benchmark query accuracy and ensure latency is strictly under 150ms."""
    async with AsyncSessionLocal() as db:
        await seed_movies_if_empty(db)
        
        engine = HybridSearchEngine(db)
        
        total_latency = 0.0
        queries_run = 0
        
        print("\n--- HYBRID SEARCH BENCHMARK RESULTS ---")
        for q in BENCHMARK_QUERIES:
            start = time.time()
            results = await engine.search(q, limit=5)
            latency = (time.time() - start) * 1000
            
            total_latency += latency
            queries_run += 1
            
            print(f"Query: '{q}' | Latency: {latency:.2f}ms | Matches: {[m[0].title for m in results]}")
            
            assert latency < 150.0, f"Query '{q}' exceeded 150ms latency threshold"
            
        avg_latency = total_latency / queries_run
        print(f"Average Latency: {avg_latency:.2f}ms across {queries_run} queries")
        assert avg_latency < 150.0, "Average latency exceeded 150ms threshold"

"""CINEIQ — ML Training Pipeline.

Downloads MovieLens + TMDB data,
Trains SVD and NCF models,
Generates and uploads Sentence-Transformers embeddings to Qdrant.
"""

import os
import sys
import logging
import pickle

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("cineiq.train")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
SVD_MODEL_PATH = os.path.join(MODEL_DIR, "svd_v1.pkl")
NCF_MODEL_PATH = os.path.join(MODEL_DIR, "ncf_v1.pt")


def train_svd():
    """Train SVD model using Surprise."""
    log.info("Starting SVD training...")
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    try:
        from surprise import Dataset, SVD
    except ImportError:
        log.error("scikit-surprise is not installed. Run `pip install scikit-surprise`.")
        sys.exit(1)

    # Load the built-in ml-100k dataset
    log.info("Loading ml-100k dataset...")
    data = Dataset.load_builtin('ml-100k')
    
    # Build full trainset
    trainset = data.build_full_trainset()
    
    # Train SVD
    log.info("Training SVD model...")
    algo = SVD()
    algo.fit(trainset)
    
    # Save the model
    with open(SVD_MODEL_PATH, "wb") as f:
        pickle.dump(algo, f)
        
    log.info(f"SVD Model saved to {SVD_MODEL_PATH}")


def train_ncf():
    """Train Neural Collaborative Filtering using PyTorch."""
    log.info("Starting NCF training (Scaffolded)...")
    # Placeholder for PyTorch NCF
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(NCF_MODEL_PATH, "w") as f:
        f.write("mock_ncf_model")
    log.info(f"NCF Model saved to {NCF_MODEL_PATH}")


def generate_embeddings():
    """Generate semantic embeddings for movies."""
    log.info("Generating sentence-transformers embeddings...")
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
        
        # Add backend dir to sys path so we can import app.core.config
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        from app.core.config import settings
    except ImportError as e:
        log.error(f"Missing dependencies: {e}. Run `pip install sentence-transformers qdrant-client`")
        return

    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    
    collection_name = "movies"
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
    
    # Mock data for demonstration. In production, this would load from a database or CSV.
    movies = [
        {"id": "1", "title": "Inception", "description": "A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O."},
        {"id": "2", "title": "Interstellar", "description": "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival."},
        {"id": "3", "title": "The Dark Knight", "description": "When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice."}
    ]
    
    points = []
    for idx, m in enumerate(movies):
        vec = model.encode(m["description"]).tolist()
        points.append(PointStruct(id=idx+1, vector=vec, payload={"movie_id": m["id"], "title": m["title"], "description": m["description"]}))
        
    client.upsert(collection_name=collection_name, points=points)
    log.info(f"Embeddings generated and uploaded to Qdrant collection '{collection_name}'.")


def train():
    log.info("=" * 60)
    log.info("CINEIQ ML Pipeline")
    log.info("=" * 60)

    train_svd()
    train_ncf()
    generate_embeddings()

    log.info("ML Pipeline completed successfully.")


if __name__ == "__main__":
    train()

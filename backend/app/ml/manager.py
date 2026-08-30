import os
import pickle
from typing import Optional

import structlog

logger = structlog.get_logger()

DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")


class ModelLoadError(Exception):
    """Raised when an ML model cannot be loaded."""


class ModelManager:
    """Lightweight manager for recommendation model loading and caching.

    Wraps the SVD model loading logic into a reusable class.
    """

    def __init__(self, model_dir: Optional[str] = None) -> None:
        self._model_dir = model_dir or DEFAULT_MODEL_DIR
        self._svd_model: Optional[object] = None

    def get_svd_model(self) -> Optional[object]:
        """Return the cached SVD model, loading it on first access.

        Returns:
            Loaded SVD model instance, or None if loading failed or
            the model file does not exist.
        """
        if self._svd_model is not None:
            return self._svd_model

        model_path = os.path.join(
            self._model_dir,
            "svd_v1.pkl",
        )

        if not os.path.exists(model_path):
            logger.warning(
                "svd_model_missing",
                path=model_path,
            )
            return None

        try:
            with open(model_path, "rb") as file:
                self._svd_model = pickle.load(file)

            logger.info(
                "svd_model_loaded",
                path=model_path,
            )

            return self._svd_model

        except Exception as error:
            logger.error(
                "svd_model_load_failed",
                path=model_path,
                error=str(error),
            )
            return None

    def invalidate_svd(self) -> None:
        """Clear the cached SVD model for reload on next access."""
        self._svd_model = None


model_manager = ModelManager()

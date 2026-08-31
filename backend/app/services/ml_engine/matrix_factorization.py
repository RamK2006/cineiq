import random
import math
from typing import List, Dict, Tuple
import structlog

logger = structlog.get_logger(__name__)

class ImplicitFeedbackMF:
    """
    Stochastic Gradient Descent (SGD) based Matrix Factorization from scratch.
    Designed to compute implicit interaction weights for the User Taste Radar.
    """
    
    def __init__(self, num_factors: int = 10, learning_rate: float = 0.01, regularization: float = 0.1, epochs: int = 20):
        self.num_factors = num_factors
        self.learning_rate = learning_rate
        self.regularization = regularization
        self.epochs = epochs
        
        self.user_factors: Dict[str, List[float]] = {}
        self.item_factors: Dict[str, List[float]] = {}
        self.user_biases: Dict[str, float] = {}
        self.item_biases: Dict[str, float] = {}
        self.global_bias: float = 0.0
        
    def _init_factors(self, user_id: str, item_id: str):
        if user_id not in self.user_factors:
            self.user_factors[user_id] = [random.uniform(-0.1, 0.1) for _ in range(self.num_factors)]
            self.user_biases[user_id] = 0.0
        if item_id not in self.item_factors:
            self.item_factors[item_id] = [random.uniform(-0.1, 0.1) for _ in range(self.num_factors)]
            self.item_biases[item_id] = 0.0

    def fit(self, interactions: List[Tuple[str, str, float]]):
        """
        Interactions is a list of tuples: (user_id, item_id, interaction_weight)
        """
        if not interactions:
            return

        self.global_bias = sum(w for _, _, w in interactions) / len(interactions)

        for user_id, item_id, _ in interactions:
            self._init_factors(user_id, item_id)

        for epoch in range(self.epochs):
            total_error = 0.0
            for user_id, item_id, weight in interactions:
                # Predict
                u_f = self.user_factors[user_id]
                i_f = self.item_factors[item_id]
                
                dot_product = sum(u * i for u, i in zip(u_f, i_f))
                prediction = self.global_bias + self.user_biases[user_id] + self.item_biases[item_id] + dot_product
                
                error = weight - prediction
                total_error += error ** 2
                
                # Update Biases
                self.user_biases[user_id] += self.learning_rate * (error - self.regularization * self.user_biases[user_id])
                self.item_biases[item_id] += self.learning_rate * (error - self.regularization * self.item_biases[item_id])
                
                # Update Factors
                for k in range(self.num_factors):
                    u_fk = u_f[k]
                    i_fk = i_f[k]
                    u_f[k] += self.learning_rate * (error * i_fk - self.regularization * u_fk)
                    i_f[k] += self.learning_rate * (error * u_fk - self.regularization * i_fk)
                    
            logger.debug("mf_epoch_completed", epoch=epoch, rmse=math.sqrt(total_error / len(interactions)))

    def predict(self, user_id: str, item_id: str) -> float:
        if user_id not in self.user_factors or item_id not in self.item_factors:
            return self.global_bias
            
        u_f = self.user_factors[user_id]
        i_f = self.item_factors[item_id]
        dot_product = sum(u * i for u, i in zip(u_f, i_f))
        
        return self.global_bias + self.user_biases[user_id] + self.item_biases[item_id] + dot_product

    def get_user_affinity_vector(self, user_id: str) -> List[float]:
        if user_id not in self.user_factors:
            return [0.0] * self.num_factors
        return self.user_factors[user_id]

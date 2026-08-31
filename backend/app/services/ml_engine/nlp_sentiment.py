import math
from typing import List, Dict
import re
import structlog

logger = structlog.get_logger(__name__)

class SimpleTFIDFAnalyzer:
    """
    A lightweight, from-scratch TF-IDF (Term Frequency-Inverse Document Frequency)
    Analyzer to extract implicit semantic meaning and sentiment from user reviews.
    """
    
    # Very basic static dictionary for positive/negative polarity weighting
    SENTIMENT_LEXICON = {
        "masterpiece": 2.0, "amazing": 1.5, "great": 1.0, "good": 0.5, "love": 1.0, "loved": 1.0,
        "terrible": -2.0, "awful": -1.5, "bad": -1.0, "boring": -1.0, "hate": -1.5, "worst": -2.0,
        "predictable": -0.5, "brilliant": 1.5, "stunning": 1.2, "dull": -1.2
    }

    def __init__(self):
        self.document_frequencies: Dict[str, int] = {}
        self.num_docs: int = 0
        
    def _tokenize(self, text: str) -> List[str]:
        # Lowercase and strip non-alphanumeric
        clean = re.sub(r"[^a-zA-Z0-9\s]", "", text.lower())
        return [w for w in clean.split() if w]

    def fit(self, corpus: List[str]):
        """Learns document frequencies from a corpus of movie overviews or reviews."""
        self.num_docs = len(corpus)
        for doc in corpus:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                self.document_frequencies[token] = self.document_frequencies.get(token, 0) + 1
                
        logger.debug("tfidf_fitted", num_docs=self.num_docs, vocab_size=len(self.document_frequencies))

    def analyze_sentiment_weight(self, text: str) -> float:
        """
        Calculates a semantic weight for a piece of text (e.g. a user's review)
        by combining TF-IDF rarity with the sentiment lexicon.
        Returns a float where > 0 is positive interaction, < 0 is negative.
        """
        if not text:
            return 0.0
            
        tokens = self._tokenize(text)
        if not tokens:
            return 0.0
            
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
            
        total_score = 0.0
        for token, count in tf.items():
            # Term Frequency
            term_freq = count / len(tokens)
            
            # Inverse Document Frequency (smooth)
            df = self.document_frequencies.get(token, 0)
            idf = math.log((self.num_docs + 1) / (df + 1)) + 1
            
            tfidf_score = term_freq * idf
            
            # Multiply by sentiment polarity if exists
            polarity = self.SENTIMENT_LEXICON.get(token, 0.0)
            
            total_score += (tfidf_score * polarity)
            
        # Normalize somewhat to prevent astronomical numbers
        # Typically maps between -3.0 and +3.0
        return max(-3.0, min(3.0, total_score))

import numpy as np
from typing import List, Optional
import os

# Force offline mode for transformers
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'

# Lazy-load model only when first needed to avoid slow imports
_MODEL: Optional[any] = None


def _get_model():
    """Lazy load the sentence transformer model from local Backend/Models folder."""
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        from pathlib import Path
        
        # Import BASE_DIR from config
        try:
            from ..config import BASE_DIR
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
            from config import BASE_DIR
        
        MODEL_PATH = str(BASE_DIR / "Models" / "all-MiniLM-L6-v2")
        print(f"Loading model from local path: {MODEL_PATH}")
        _MODEL = SentenceTransformer(MODEL_PATH, device='cpu')
        print("✓ Model loaded successfully from local files")
    return _MODEL


def encode(text: str) -> List[float]:
    """
    Encode a text string into a vector embedding.
    
    Args:
        text: Input text string to encode
        
    Returns:
        List of floats representing the embedding vector
    """
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Args:
        v1: First vector as list of floats
        v2: Second vector as list of floats
        
    Returns:
        Cosine similarity score between 0 and 1
    """
    vec1 = np.array(v1)
    vec2 = np.array(v2)
    
    # Compute cosine similarity: dot product / (norm1 * norm2)
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    
    # Ensure result is between 0 and 1
    return float(max(0.0, min(1.0, similarity)))


if __name__ == "__main__":
    # Simple test
    print("Testing embedding tool...")
    
    text1 = "Arsenal scored a brilliant goal"
    text2 = "The Gunners found the back of the net with a fantastic strike"
    text3 = "The weather is nice today"
    
    print(f"\nText 1: {text1}")
    print(f"Text 2: {text2}")
    print(f"Text 3: {text3}")
    
    # Encode texts
    embedding1 = encode(text1)
    embedding2 = encode(text2)
    embedding3 = encode(text3)
    
    print(f"\nEmbedding dimension: {len(embedding1)}")
    
    # Compute similarities
    similarity_1_2 = cosine_similarity(embedding1, embedding2)
    similarity_1_3 = cosine_similarity(embedding1, embedding3)
    similarity_2_3 = cosine_similarity(embedding2, embedding3)
    
    print(f"\nSimilarity between Text 1 and Text 2 (similar): {similarity_1_2:.4f}")
    print(f"Similarity between Text 1 and Text 3 (different): {similarity_1_3:.4f}")
    print(f"Similarity between Text 2 and Text 3 (different): {similarity_2_3:.4f}")

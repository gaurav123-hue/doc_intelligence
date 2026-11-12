
"""Generate text embeddings using a local Sentence Transformers model."""

from sentence_transformers import SentenceTransformer

# Use a lightweight general-purpose model for our first semantic-search experiment.
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Load the model once so repeated embedding requests can reuse it.
model = SentenceTransformer(MODEL_NAME, local_files_only=True)

def generate_embedding(text: str) -> list[float]:
    """Convert non-empty text into a list of floating-point embedding values."""

    # Reject empty input so we don't generate meaningless embeddings.
    if not text.strip():
        raise ValueError("Text must not be empty")

    # Normalize the result to a standard Python list for easier integration.
    embedding = model.encode(text, normalize_embeddings=True)

    return embedding.tolist()

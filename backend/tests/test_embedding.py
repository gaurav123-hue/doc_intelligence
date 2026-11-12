
"""Verify that the local embedding model generates valid vectors."""

from backend.services.embedding import generate_embedding

# Use a sample sentence to test the embedding service.
sample_text = "The court examined the investigation."

# Convert the sentence into a numerical embedding.
embedding = generate_embedding(sample_text)

# Print basic details without dumping all 384 numbers.
print("Embedding generated successfully!")
print(f"Vector dimensions: {len(embedding)}")
print(f"First five values: {embedding[:5]}")
print(f"All values are floats: {all(isinstance(value, float) for value in embedding)}")


"""Service for communicating with the Groq hosted language model."""

import os

from dotenv import load_dotenv
from groq import Groq

# Load environment variables from the project's .env file.
load_dotenv()

# Read the Groq API key without exposing it in the source code.
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Keep the model configurable so it can be changed without modifying code.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Fail early with a clear message if the API key is missing.
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not configured in .env")

# Initialize the Groq client once and reuse it for API requests.
client = Groq(api_key=GROQ_API_KEY)


def generate_response(prompt: str) -> str:
    """Send a prompt to Groq and return the generated text response."""

    # Reject empty prompts before making an external API request.
    if not prompt.strip():
        raise ValueError("Prompt must not be empty")

    # Request a response from the configured Groq chat model.
    completion = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.2,
    )

    # Extract the generated text from the first response choice.
    response = completion.choices[0].message.content

    # Guard against an empty response from the model.
    if not response:
        raise RuntimeError("Groq returned an empty response")

    return response.strip()

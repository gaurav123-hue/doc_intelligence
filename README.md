# AI Document Intelligence Platform

An AI-powered document question-answering platform that allows users to upload documents, extract and process their content, and ask natural-language questions using Retrieval-Augmented Generation (RAG).

The platform combines semantic search, vector embeddings, and a Large Language Model (LLM) to generate context-aware answers grounded in uploaded documents.

## Project Overview

AI Document Intelligence is designed to make information stored in documents easier to access and understand.

Users can create a session, upload documents, and ask questions about their content. The application retrieves relevant document passages and uses them as context for generating answers. Responses include source references to help users trace the information back to the original documents.

The current implementation focuses on the backend API, document processing, session management, and RAG-based question answering.

## Key Features

### Document Management
- Upload PDF, DOCX, and TXT documents.
- Maximum upload size of 10 MB per document.
- Support for up to 3 documents per session.
- SHA-256-based duplicate document detection within a session.
- Extract and store document text.
- Track document processing status.
- Store uploaded files in session-specific directories.

### Document Processing
- Extract selectable text from PDF files.
- Extract paragraphs and tables from DOCX files.
- Read text files using UTF-8 encoding.
- Split extracted content into overlapping text chunks.
- Generate vector embeddings for document chunks.
- Store document content, chunks, and embeddings in PostgreSQL.

### Retrieval-Augmented Generation (RAG)
- Convert user questions into vector embeddings.
- Retrieve semantically relevant document chunks.
- Restrict retrieval to documents belonging to the authenticated session.
- Use retrieved content as context for LLM responses.
- Generate answers grounded in the available document content.
- Validate that generated citations reference retrieved chunks.
- Return source information alongside generated answers.

### Session Management
- Create secure, token-based user sessions.
- Authenticate API requests using Bearer tokens.
- Maintain isolated documents and conversations for each session.
- Automatically expire sessions after 60 minutes of inactivity.
- Run a background cleanup worker to identify and remove expired sessions.
- Support explicit session termination.
- Delete associated database records and uploaded files when a session ends.

### Conversation History
- Persist user questions and generated answers in PostgreSQL.
- Store source information and citation metadata.
- Retrieve conversation history for the authenticated session.
- Preserve conversation history across API requests and application refreshes.

## Technology Stack

| Component | Technology |
|---|---|
| Backend framework | FastAPI |
| Programming language | Python 3.11 |
| Database | PostgreSQL 17 |
| Vector database extension | pgvector |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |
| Embedding dimensions | 384 |
| LLM provider | Groq |
| Configured LLM | openai/gpt-oss-120b |
| PDF extraction | pypdf |
| DOCX extraction | python-docx |
| API testing | pytest and FastAPI TestClient |
| API documentation | Swagger UI |

## System Architecture

The current application follows a modular backend architecture.

```text
                    Client
                      |
                      v
                 FastAPI API
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      Documents    Questions   Sessions
       Router       Router      Router
          |           |           |
          v           v           v
    Document       RAG Service  Session
    Processing                  Management
          |           |           |
          v           v           v
    Text Extraction  Semantic   Authentication
    Text Chunking    Retrieval  and Cleanup
          |           |
          v           v
       Embeddings   Groq LLM
          |           |
          +-----+-----+
                |
                v
          PostgreSQL
           + pgvector
```

### Document Processing Flow

1. A user uploads a supported document.
2. The API validates the file format and size.
3. The application calculates the document's SHA-256 hash.
4. The document is stored in the authenticated session's storage directory.
5. Text is extracted from the document.
6. Extracted text is stored in PostgreSQL.
7. The text is divided into overlapping chunks.
8. Chunks are stored in PostgreSQL.
9. Embeddings are generated and associated with the chunks.
10. The document processing status is updated.

### Question Answering Flow

1. The user submits a question through the authenticated API.
2. The question is converted into a vector embedding.
3. PostgreSQL and pgvector retrieve semantically relevant chunks.
4. Retrieval is restricted to documents belonging to the current session.
5. Retrieved passages are supplied to the Groq LLM as context.
6. The LLM generates an answer using the supplied document content.
7. Citation references are validated against the retrieved chunks.
8. The answer, sources, and citation metadata are stored in conversation history.
9. The API returns the answer and its supporting source information.

## Project Structure

```text
ai-document-intelligence/
│
├── backend/
│   ├── main.py
│   ├── database.py
│   │
│   ├── migrations/
│   │   └── 001_create_sessions.sql
│   │
│   ├── routers/
│   │   ├── documents.py
│   │   ├── questions.py
│   │   └── sessions.py
│   │
│   ├── services/
│   │   ├── document_processing.py
│   │   ├── text_extraction.py
│   │   ├── text_chunking.py
│   │   ├── embeddings.py
│   │   ├── llm.py
│   │   ├── rag.py
│   │   ├── sessions.py
│   │   └── session_cleanup.py
│   │
│   └── tests/
│
├── storage/
│   └── documents/
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

## Installation and Setup

### Prerequisites

- Python 3.11
- PostgreSQL 17
- pgvector PostgreSQL extension
- Groq API key
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/gaurav123-hue/doc_intelligence.git

cd doc_intelligence
```

### 2. Create a Virtual Environment

```bash
python3.11 -m venv .venv

source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
DATABASE_URL=postgresql://username:password@localhost:5432/ai_document_intelligence

GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=openai/gpt-oss-120b
```

Replace the database credentials and API key with your own values.

**Important:** Never commit `.env` or expose API keys and database credentials in source control.

### 5. Configure PostgreSQL

Create the application database and ensure the pgvector extension is installed and enabled.

The database schema must include the application's document, content, chunk, session, and conversation-history tables.

Apply the session migration:

```bash
psql "$DATABASE_URL" -f backend/migrations/001_create_sessions.sql
```

Ensure the database role has the required permissions.

### 6. Start the Backend Server

Run the following command from the project root:

```bash
./.venv/bin/python -m uvicorn backend.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

### 7. Access API Documentation

FastAPI provides interactive API documentation through Swagger UI.

```text
http://127.0.0.1:8000/docs
```

Use Swagger UI to explore and test the available API endpoints.

## Testing

The project uses pytest for automated testing.

Run the complete test suite:

```bash
./.venv/bin/python -m pytest -q
```

The tests cover areas including:

- Document upload and validation.
- Duplicate document detection.
- Document processing.
- Text extraction and chunking.
- Database operations.
- Embedding and retrieval functionality.
- RAG citation validation.
- Question-answering endpoints.
- Session authentication and isolation.
- Conversation history.
- Manual and automatic session cleanup.

## Security and Data Isolation

The application uses session-based authentication to isolate user data.

- Session tokens are generated using secure random token generation.
- Only token hashes are stored in the database.
- Authenticated API requests require a valid Bearer token.
- Document retrieval is restricted to the active session.
- Conversation history is session-specific.
- Session termination removes associated database records and uploaded files.
- Automatic expiration prevents inactive sessions from remaining indefinitely.

## Current Limitations

The current implementation primarily supports text-based document intelligence.

The following capabilities are not yet implemented:

- OCR for scanned PDFs and images.
- Extraction of embedded images from PDF documents.
- Understanding charts, diagrams, and flowcharts.
- Page-level source references.
- Multimodal document retrieval and question answering.
- A frontend user interface.
- Production deployment and monitoring.

## Future Development

Planned enhancements include:

1. OCR and scanned document processing.
2. PDF image extraction and visual content analysis.
3. Chart, diagram, and flowchart understanding.
4. Page-aware document extraction and citations.
5. Multimodal Retrieval-Augmented Generation.
6. Frontend development with document upload, library, chat, and source previews.
7. Full frontend and backend integration.
8. Production deployment, security hardening, and performance optimization.

## Project Goal

The long-term goal is to build a complete AI-powered document intelligence platform that can understand, retrieve, and answer questions from both textual and visual information contained in documents.

The platform aims to make large collections of documents easier to explore through natural-language interaction while maintaining reliable, traceable, and context-grounded answers.

---

**Project:** AI Document Intelligence Platform

**Repository:** https://github.com/gaurav123-hue/doc_intelligence.git

**Status:** Backend foundation and core RAG functionality implemented; frontend and advanced document intelligence capabilities are planned.

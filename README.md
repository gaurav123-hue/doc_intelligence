# AI Document Intelligence

**An intelligent platform for understanding, searching, and interacting with documents using Artificial Intelligence.**

AI Document Intelligence transforms static documents into interactive knowledge sources. Upload documents, extract information from text and visual content, and ask questions in natural language to receive accurate, context-aware answers backed by source citations.

Built using modern AI technologies, Retrieval-Augmented Generation (RAG), multimodal document processing, and vector search, the platform makes complex document analysis faster, easier, and more accessible.

---

## Overview

AI Document Intelligence is an end-to-end document intelligence platform that enables users to interact with their documents through an intelligent conversational interface.

The platform supports traditional text-based documents as well as scanned documents, images, diagrams, charts, and other visual content.

Instead of manually navigating lengthy documents, users can upload their files, ask questions, explore relevant information, and receive AI-generated answers with references to the original document pages and content.

## Features

### 1. Intelligent Document Management
- Upload and manage multiple documents.
- Support for PDF, DOCX, TXT, and image-based documents.
- Document validation and duplicate detection.
- Secure document storage and processing.
- Document processing status and metadata management.
- Session-based document organization.
- Automatic document cleanup when sessions expire or end.

### 2. Advanced Document Processing
- Extract text from digital PDF documents.
- Extract text from Word and text documents.
- Extract images and visual elements from PDFs.
- OCR processing for scanned PDFs and images.
- Understand diagrams, charts, tables, and flowcharts.
- Preserve page numbers and document references.
- Combine extracted text and visual information into searchable content.

### 3. Multimodal Retrieval-Augmented Generation
- Convert document content into vector embeddings.
- Perform semantic search using PostgreSQL and pgvector.
- Retrieve relevant passages and visual descriptions.
- Combine textual and visual context.
- Generate answers grounded in uploaded documents.
- Provide source references and page-level citations.
- Validate generated citations against retrieved sources.

### 4. AI-Powered Question Answering
- Ask questions using natural language.
- Receive context-aware answers based on uploaded documents.
- Search across multiple documents within a workspace.
- Retrieve relevant supporting information.
- Generate answers using large language models.
- Maintain conversational context through stored conversation history.
- Avoid relying on unsupported information outside retrieved document context.

### 5. Session Management and Security
- Secure session creation and authentication.
- Cryptographically generated session tokens.
- Hashed session-token storage.
- Isolated document workspaces.
- Session-based resource authorization.
- Automatic session expiration after 60 minutes of inactivity.
- Explicit session termination.
- Background cleanup of expired sessions.
- Removal of associated database records and uploaded files.

### 6. Conversation History
- Persistent conversation history.
- Store user questions and AI-generated answers.
- Preserve source references and citation metadata.
- Retrieve previous conversations.
- Maintain session-level conversation isolation.

### 7. User Interface
- Document upload interface.
- Document library and processing status.
- Interactive AI chat interface.
- Source and citation previews.
- Document page navigation.
- Conversation history.
- Session lifecycle management.
- Responsive user experience.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, FastAPI |
| Frontend | Modern web application framework |
| Database | PostgreSQL |
| Vector Database | PostgreSQL with pgvector |
| Embeddings | Sentence Transformers |
| Language Models | Groq-hosted LLMs |
| Document Processing | PyMuPDF and document extraction libraries |
| OCR | OCR processing engines |
| Visual Understanding | Vision-capable AI models |
| Authentication | Secure token-based sessions |
| Testing | Pytest |
| API Documentation | FastAPI Swagger UI |
| Version Control | Git and GitHub |

## System Architecture

The platform follows a modular architecture that separates the frontend, backend services, document-processing pipeline, AI services, and data-storage layer.

```text
                  USER
                    |
                    v
              FRONTEND
                    |
                    v
              FASTAPI API
                    |
       +------------+------------+
       |            |            |
       v            v            v
    SESSION      DOCUMENT     QUESTION
   MANAGEMENT   MANAGEMENT   ANSWERING
                    |
                    v
           DOCUMENT PROCESSING
                    |
          +---------+---------+
          |                   |
          v                   v
      TEXT EXTRACTION      IMAGE EXTRACTION
          |                   |
          v                   v
         OCR            VISUAL ANALYSIS
          |                   |
          +---------+---------+
                    |
                    v
          UNIFIED DOCUMENT CONTENT
                    |
                    v
             TEXT CHUNKING
                    |
                    v
              EMBEDDINGS
                    |
                    v
           POSTGRESQL + PGVECTOR
                    |
                    v
             SEMANTIC SEARCH
                    |
                    v
            CONTEXT RETRIEVAL
                    |
                    v
                GROQ LLM
                    |
                    v
          ANSWER + CITATIONS
                    |
                    v
                FRONTEND
```

## How It Works

### Document Intelligence Pipeline

1. The user uploads one or more documents.
2. The backend validates the files and stores document metadata.
3. Text, tables, and images are extracted from the documents.
4. OCR processes scanned pages and image-based content.
5. Vision models interpret relevant visual elements, including diagrams and charts.
6. Extracted information is organized into searchable content with page references.
7. Content is divided into manageable chunks.
8. Embeddings are generated and stored in PostgreSQL using pgvector.

### Question Answering Pipeline

1. The user submits a natural-language question.
2. The question is converted into a vector embedding.
3. Semantic search retrieves relevant document content.
4. Relevant text passages and visual descriptions are assembled into context.
5. The retrieved context is supplied to the language model.
6. The model generates an answer grounded in the available document information.
7. Citations are validated against retrieved sources.
8. The answer, citations, and conversation metadata are stored.
9. The frontend displays the answer with supporting document references.

---

## Project Structure

```text
ai-document-intelligence/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── main.py
│   ├── database.py
│   │
│   ├── routers/
│   │   ├── documents.py
│   │   ├── questions.py
│   │   └── sessions.py
│   │
│   ├── services/
│   │   ├── document_processing.py
│   │   ├── embedding.py
│   │   ├── llm.py
│   │   ├── rag.py
│   │   ├── sessions.py
│   │   └── session_cleanup.py
│   │
│   ├── migrations/
│   └── tests/
│
├── storage/
│   └── documents/
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Installation and Setup

### Prerequisites

- Python 3.11 or later
- Node.js and npm
- PostgreSQL
- pgvector extension
- Git
- Groq API credentials
- Required OCR and vision-model dependencies

### 1. Clone the Repository

```bash
git clone https://github.com/gaurav123-hue/doc_intelligence.git

cd doc_intelligence
```

### 2. Backend Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Frontend Setup

Install frontend dependencies:

```bash
cd frontend

npm install
```

Start the frontend development server using the project's configured npm script.

### 4. Environment Configuration

Create a `.env` file in the backend project root or the location expected by the application.

Configure the required environment variables:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_configured_model

DATABASE_URL=your_postgresql_connection_string
```

Configure any additional OCR, vision-model, and storage settings required by the deployment.

**Security:** Never commit `.env` files, API keys, database passwords, or other sensitive credentials.

### 5. Database Setup

Create the PostgreSQL database and enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Apply the application's database migrations and initialize the required tables and indexes.

### 6. Start the Backend

From the project root:

```bash
python -m uvicorn backend.main:app --reload
```

Backend URL:

```text
http://127.0.0.1:8000
```

### 7. API Documentation

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative documentation:

```text
http://127.0.0.1:8000/redoc
```

---

## API Overview

| Endpoint | Method | Description |
|---|---|---|
| `/sessions/start` | POST | Create a new session |
| `/sessions/end` | POST | Terminate a session |
| `/documents/upload` | POST | Upload a document |
| `/documents` | GET | List session documents |
| `/questions/preview` | POST | Preview retrieved context |
| `/questions/ask` | POST | Ask a document-related question |
| `/questions/history` | GET | Retrieve conversation history |
| `/health` | GET | Check API health |

Authenticated requests use Bearer token authentication.

```http
Authorization: Bearer YOUR_SESSION_TOKEN
```

Refer to the interactive API documentation for complete request and response schemas.

---

## Database Architecture

PostgreSQL serves as the primary relational database, while pgvector provides efficient vector similarity search.

The database manages:

- User session information.
- Document metadata and ownership.
- Extracted document content.
- Document chunks.
- Vector embeddings.
- Conversation history.
- Citation metadata.

Session-based relationships and database constraints maintain data isolation and support reliable cleanup.

## Security and Reliability

The platform incorporates:

- Secure random session-token generation.
- SHA-256 hashing of session tokens.
- Session-based authorization.
- Resource ownership validation.
- Database transaction management.
- Foreign-key cascade deletion.
- Safe filesystem path validation.
- Automatic inactivity expiration.
- Background cleanup processing.
- Automated application tests.
- Structured application logging.

## Testing

The backend uses Pytest for automated testing.

Run the test suite:

```bash
python -m pytest -q
```

Tests cover document processing, database operations, API endpoints, semantic retrieval, citation validation, session authentication, conversation history, and cleanup operations.

## License

This project is distributed under the license specified in the repository.

---

## Author

**AI Document Intelligence**

GitHub: [gaurav123-hue](https://github.com/gaurav123-hue)

Repository: [doc_intelligence](https://github.com/gaurav123-hue/doc_intelligence)

---

*Transforming documents into intelligent, searchable, and conversational knowledge.*

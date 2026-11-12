
-- Migration 001: Introduce session-based document workspaces.
-- This migration must run once, against the clean database.

BEGIN;

-- 1. Store active workspace sessions.
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,

    -- Store only the SHA-256 hash of the secret session token.
    token_hash VARCHAR(64) NOT NULL UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Validate that the token hash is a 64-character SHA-256 hex digest.
    CONSTRAINT sessions_token_hash_format
        CHECK (token_hash ~ '^[a-f0-9]{64}$')
);

-- 2. Associate every uploaded document with its owning session.
ALTER TABLE documents
ADD COLUMN session_id BIGINT NOT NULL
REFERENCES sessions(id) ON DELETE CASCADE;

-- 3. Replace global duplicate detection with session-specific detection.
DROP INDEX documents_content_hash_unique;

CREATE UNIQUE INDEX documents_session_content_hash_unique
ON documents (session_id, content_hash)
WHERE content_hash IS NOT NULL;

-- 4. Store each question and its generated answer as one conversation turn.
CREATE TABLE conversation_turns (
    id BIGSERIAL PRIMARY KEY,

    session_id BIGINT NOT NULL
        REFERENCES sessions(id) ON DELETE CASCADE,

    question TEXT NOT NULL,
    answer TEXT NOT NULL,

    -- Preserve retrieved passages and their metadata.
    sources JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Preserve only the passages actually cited in the answer.
    cited_source_details JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Preserve citation validation results.
    citation_validation JSONB NOT NULL DEFAULT '{}'::jsonb,

    result_count INTEGER NOT NULL DEFAULT 0
        CHECK (result_count >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT conversation_question_not_empty
        CHECK (LENGTH(TRIM(question)) > 0),

    CONSTRAINT conversation_answer_not_empty
        CHECK (LENGTH(TRIM(answer)) > 0)
);

-- 5. Add indexes to make session-specific queries efficient.
CREATE INDEX documents_session_id_idx
ON documents(session_id);

CREATE INDEX conversation_turns_session_created_idx
ON conversation_turns(session_id, created_at, id);

COMMIT;

# CallItADay

CallItADay is a diary and chat application built around model-agnostic agents, structured diary storage, hybrid retrieval, and visible tool traces.

The application lets a user write diary entries, search them through dense and sparse retrieval, and chat with an assistant that can call explicit skills for chat history, diary memory, and soul document management.

## Current Capabilities

- Diary writing with PostgreSQL as the structured source of truth.
- Semantic splitting for diary chunks before indexing.
- Milvus vector storage for dense embedding recall.
- Elasticsearch sparse index for BM25, metadata, and time filtering.
- Hybrid retrieval with RRF fusion and CrossEncoder reranking.
- LangGraph-based chat workflow with a first-layer intent/tool loop and second-layer response generation.
- Three model configurations managed from the UI and persisted to DB:
  - `intent_recognition`
  - `tool_enrichment`
  - `response_generation`
- Runtime chat settings managed from the UI, including first-layer max iterations.
- Tool trace visualization in the frontend.
- Soul documents persisted in DB with changelog support:
  - `diary-soul.md`
  - `user-soul.md`
  - `soul_system_prompt.md`

## Architecture

```text
React + Vite frontend
        |
        v
FastAPI backend
        |
        +-- LangGraph chat workflow
        |      |
        |      +-- chat-manager skill
        |      +-- diary-manager skill
        |      +-- soul-manager skill
        |
        +-- Model client
        |      |
        |      +-- OpenAI-compatible HTTP endpoint
        |      +-- User-configured provider/model/base URL/API key
        |
        +-- PostgreSQL
        |      |
        |      +-- chat messages
        |      +-- diary records
        |      +-- diary chunk mapping
        |      +-- model/runtime configs
        |      +-- soul docs and changelogs
        |      +-- local tool trace events
        |
        +-- Milvus
        |      |
        |      +-- dense diary chunk embeddings
        |
        +-- Elasticsearch
               |
               +-- BM25 text
               +-- metadata
               +-- time filters
```

The backend is provider agnostic at the application layer. It expects a chat model endpoint compatible with the OpenAI chat API shape, but that endpoint can be backed by any provider or gateway that implements the protocol.

## Diary Ingestion

Diary ingestion uses this order:

```text
raw diary
  -> semantic splitting
  -> document + chunk metadata extraction
  -> local embedding
  -> PostgreSQL diary/chunk rows
  -> Milvus dense vectors
  -> Elasticsearch sparse/metadata docs
```

Semantic splitting happens before metadata extraction so the metadata model can produce both document-level fields and chunk-level fields. This makes sparse retrieval and metadata filtering more precise than assigning one coarse metadata object to every chunk.

The semantic splitter uses LangChain's `SemanticChunker` when available, with a recursive character splitter fallback for local resilience.

## Retrieval

Diary search uses a staged retrieval pipeline:

```text
query
  -> query understanding
  -> Milvus dense recall
  -> Elasticsearch BM25 sparse recall
  -> RRF fusion
  -> optional LambdaMART stage
  -> optional ColBERT stage
  -> CrossEncoder rerank
```

LambdaMART and ColBERT are pluggable stages. CrossEncoder reranking is the first concrete reranker enabled by default.

## Chat Workflow

The chat workflow is implemented with LangGraph.

Layer 1 performs intent recognition and information enrichment. It receives:

- the layer-1 prompt
- length-bounded chat history
- `diary-soul.md`
- skill schemas
- current iteration and max iteration count

Layer 1 can call:

- `chat-manager`
  - `query_chat_messages`
  - `count_chat_messages`
- `diary-manager`
  - `search_diaries`
  - `add_diary`
- `soul-manager`
  - `read_soul_docs`
  - `apply_soul_change`

If the user request only modifies soul documents and the modification is handled, the workflow can end after layer 1. Otherwise layer 2 generates the final user-facing response.

## Model And Runtime Configuration

The UI exposes model configuration for:

- intent recognition
- tool enrichment
- response generation

Configurations are stored in PostgreSQL and loaded into an in-memory registry at backend startup. Updates through the API write to DB and immediately refresh the in-memory registry, so each chat request does not need to reload config from DB.

The runtime config includes chat settings such as:

- `layer1_max_iterations`
- `history_max_chars`
- `message_max_chars`
- `tool_trace_enabled`

## Tool Trace

Tool trace is stored locally in PostgreSQL and shown in the frontend after each chat response.

Trace events include:

- graph node
- layer
- event type
- tool name
- input JSON
- output JSON
- latency

LangSmith can also be enabled through environment variables for deeper LangGraph/LangChain tracing.

## Tech Stack

| Area | Technology |
| --- | --- |
| Frontend | React, Vite, TypeScript |
| Backend | FastAPI, SQLAlchemy |
| Agent workflow | LangGraph |
| Structured DB | PostgreSQL |
| Vector DB | Milvus |
| Sparse search | Elasticsearch |
| Embedding/rerank | sentence-transformers |
| Model protocol | OpenAI-compatible chat API |
| Local trace | PostgreSQL |
| Optional trace | LangSmith |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A model endpoint compatible with the OpenAI chat API shape

### Configure

Create or edit `.env`:

```bash
MODEL_BASE_URL=https://your-model-gateway.example.com/v1
MODEL_API_KEY=your-api-key
DEFAULT_LLM_MODEL=your-default-chat-model

EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5
CROSS_ENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L6-v2

LANGSMITH_TRACING=false
LANGSMITH_PROJECT=call-it-a-day
LANGSMITH_API_KEY=
```

You can also change the three chat model configs from the application UI after startup.

### Start

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- API docs: http://localhost:8080/docs

## Local Development

### Debug startup (VS Code + debugpy)

#### Option A: debug the backend in Docker

If you want to debug the backend in Docker, start the stack with the debug override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

Then in VS Code, open the Run and Debug view and choose `Python Attach: backend debugpy` to attach to port `5678`.

After the backend is attached, open:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- Debugger endpoint: http://localhost:5678

#### Option B: debug the backend locally (no Docker)

If you prefer to run the backend directly on your machine and still debug it in VS Code:

```bash
cd backend
conda run -n callItADay python -m pip install -r requirements.txt
cd ..
docker compose up -d postgres milvus elasticsearch
```

Then open the Run and Debug panel and choose `Python Launch: FastAPI (local)`. This launches the backend with `uvicorn --reload` directly from the workspace, so you can set breakpoints without starting the Docker backend container.

After the local backend starts, open:
- Backend API: http://localhost:8080/docs
- Frontend: http://localhost:5173 (started separately with `cd frontend && npm run dev`)

### Backend

```bash
cd backend
conda run -n callItADay python -m pip install -r requirements.txt
conda run -n callItADay uvicorn main:app --reload --port 8080
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Verification:

```bash
conda run -n callItADay python -m compileall backend
cd frontend && npm run build
```

## Important Notes

- The application no longer assumes a specific cloud provider.
- The model client uses OpenAI-compatible request semantics as a transport protocol.
- Milvus and Elasticsearch are started locally by Docker Compose.
- The generated local folders such as `frontend/node_modules`, `frontend/dist`, and Python `__pycache__` may be kept to speed up repeated local runs.

## License

MIT

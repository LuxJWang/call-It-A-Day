# Backend service

This service exposes the FastAPI API used by the frontend.

The backend is organized into explicit tool, skill, and agent layers. Tools implement atomic data operations, skills group related tool behavior, and a LangGraph workflow orchestrates chat reasoning and tool execution.

## Prerequisites

- Python 3.11
- Conda environment named `callItADay`
- Docker Desktop / Docker Compose for the local supporting services
- A model endpoint compatible with the OpenAI chat API shape (optional but required for real chat responses)

## Local run

1. Start the supporting infrastructure services:

   ```bash
   cd ..
   docker compose up -d postgres milvus elasticsearch
   ```

   This gives the backend access to:
   - PostgreSQL on `localhost:5432`
   - Milvus on `localhost:19530`
   - Elasticsearch on `localhost:9200`

2. Create or update the backend environment file if you want to override defaults:

   ```bash
   cd backend
   cp .env.example .env 2>/dev/null || true
   ```

   Recommended values for local host-based development:

   ```env
   DATABASE_URL=postgresql://callitaday:callitaday@localhost:5432/callitaday
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   ELASTICSEARCH_URL=http://localhost:9200
   MODEL_BASE_URL=https://your-model-gateway.example.com/v1
   MODEL_API_KEY=your-api-key
   DEFAULT_LLM_MODEL=your-default-chat-model
   LANGSMITH_TRACING=false
   LANGSMITH_PROJECT=call-it-a-day
   LANGSMITH_API_KEY=
   LANGFUSE_ENABLED=false
   LANGFUSE_PUBLIC_KEY=
   LANGFUSE_SECRET_KEY=
   LANGFUSE_HOST=https://api.langfuse.com  # or use LANGFUSE_BASE_URL for self-hosted Langfuse
   ```

   If you want to use the local LangFuse Docker stack, set:

   ```env
   LANGFUSE_ENABLED=true
   LANGFUSE_HOST=http://langfuse-web:3000
   LANGFUSE_PUBLIC_KEY=local
   LANGFUSE_SECRET_KEY=localsecret
   ```

   The local LangFuse stack in `docker-compose.full.yml` includes all repo services, local LangFuse, and observability. It also avoids port conflicts by publishing the LangFuse UI on `3002` while Grafana uses `3001`.

   ```bash
   conda run -n callItADay python -m pip install -r requirements.txt
   ```

4. Start the API:

   ```bash
   conda run -n callItADay uvicorn main:app --reload --port 8080
   ```

5. Open the backend:
   - API docs: http://localhost:8080/docs
   - Health check: http://localhost:8080/api/health

## Debug startup

### Option A: debug in Docker

If you want to debug the backend inside the Docker stack, start the debug override file from the repository root:

```bash
cd ..
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

Then in VS Code, choose `Python Attach: backend debugpy` in the Run and Debug panel to attach to port `5678`.

### Option B: debug locally without Docker

If you prefer to run the backend directly on your machine and debug it in VS Code:

```bash
cd backend
conda run -n callItADay python -m pip install -r requirements.txt
cd ..
docker compose up -d postgres milvus elasticsearch
```

Then start the `Python Launch: FastAPI (local)` configuration from the Run and Debug panel. It launches the backend with `uvicorn --reload` directly from the workspace.

For local AI tracing, set `LANGSMITH_TRACING=true` or `LANGFUSE_ENABLED=true` and provide the respective keys. If LangChain callback tracing is available, `LANGCHAIN_VERBOSE=true` will print model trace events to stdout.

## How it connects to the frontend

- In local development, the frontend calls the backend through the relative `/api` path and Vite proxies those requests to `http://localhost:8080`.
- The backend must be running before you start the local frontend UI.
- If you run the whole stack with Docker Compose, the frontend container will proxy `/api/*` to the backend container automatically on http://localhost:3000.

## Optional: run the full stack with Docker Compose

From the repository root:

```bash
docker compose up --build
```

With observability enabled:

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8080
- API docs: http://localhost:8080/docs
- Metrics: http://localhost:8080/metrics
- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090
- Jaeger: http://localhost:16686

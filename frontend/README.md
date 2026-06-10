# Frontend service

This Vite + React app talks to the FastAPI backend and renders the diary, chat, and configuration views.

## Prerequisites

- Node.js 20+
- npm
- The backend service running on `http://localhost:8080` for local development

## Local development

1. Start the backend first so the UI can call the API:

   ```bash
   cd backend
   conda run -n callItADay uvicorn main:app --reload --port 8080
   ```

   If you need the backing services as well, start them with:

   ```bash
   cd ..
   docker compose up -d postgres milvus elasticsearch
   ```

2. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   ```

3. Start the Vite dev server:

   ```bash
   npm run dev
   ```

   The app will be available at:
   - http://localhost:5173

## Debug startup

### Option A: debug the backend in Docker

If you want to debug the backend while the whole stack is running locally, use the debug override file from the repository root:

```bash
cd ..
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

Then in VS Code, start the `Python Attach: backend debugpy` configuration from the Run and Debug panel. It will connect to `localhost:5678` and allow breakpoints in the backend container.

You can still open the frontend at:
- http://localhost:3000

### Option B: debug the backend locally without Docker

If you want to keep the frontend on Vite and debug the backend directly on your machine instead of in Docker:

```bash
cd backend
conda run -n callItADay python -m pip install -r requirements.txt
cd ..
docker compose up -d postgres milvus elasticsearch
cd frontend
npm install
npm run dev
```

Then start `Python Launch: FastAPI (local)` in the VS Code Run and Debug panel. The frontend will still run at http://localhost:5173, while the backend is launched locally with `uvicorn --reload` for breakpoints.

### Frontend breakpoints in VS Code

To hit breakpoints in the React code itself, start the Vite dev server first:

```bash
cd frontend
npm install
npm run dev
```

Then open the Run and Debug panel and choose `Chrome: Vite Frontend`. VS Code will launch Chrome at `http://localhost:5173`, and breakpoints set in `frontend/src/**/*.tsx` or `frontend/src/**/*.ts` can be hit there.

## How it connects to the backend

- The frontend uses `http://localhost:8080` as its API base in development.
- That means the backend must be running before the frontend is opened in the browser.
- The API paths used by the UI are under `/api/`, for example:
  - `/api/chat`
  - `/api/diaries`
  - `/api/model-configs`

## Docker Compose mode

If you prefer to run the whole stack in containers instead of local dev mode:

```bash
cd ..
docker compose up --build
```

Then open:
- Frontend: http://localhost:3000
- Backend: http://localhost:8080

In this mode, the frontend container uses the nginx proxy in `frontend/nginx.conf` to forward `/api/*` requests to the backend container automatically.

## Verify the build

```bash
npm run build
```

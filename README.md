# AI Product Workspace

AI Product Workspace is a cloud/server-runnable PoC for a LangGraph-based multi-agent product workflow. It turns a rough product idea into aligned artefacts for product, UX, engineering, and QA review:

`idea -> clarification -> PRD -> UX flow -> interactive HTML prototype -> consistency review -> QA criteria -> Jira story drafts`

The built-in demo case is **Smart Notification Summary**, a phone system software feature for grouping low-priority notifications in Notification shade with Settings controls.

## Architecture

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS.
- **Backend:** FastAPI, Python, LangGraph.
- **Storage:** SQLite metadata plus generated local files under `data/projects/<project_id>/`.
- **LLM layer:** OpenAI-compatible environment variables are supported, but the current PoC has deterministic mock outputs so the demo runs without an API key.
- **Context pack:** Lightweight PM/UX/QA/Jira guidance lives in `context/` and is loaded by the workflow.

Generated artefacts are versioned together, for example `prd_v1.0.md`, `prototype_v1.0.html`, `qa_criteria_v1.0.md`, and `jira_stories_v1.0.json`.

## API

- `GET /api/health`
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/demo`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/runs`
- `GET /api/projects/{project_id}/artefacts`
- `GET /api/projects/{project_id}/artefacts/{artefact_id}`
- `GET /api/projects/{project_id}/prototype/{version}`

## Local Setup

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://127.0.0.1:3000`.

## Linux Server Startup

On a Linux server, bind both services to `0.0.0.0` and set the frontend API URL to the server address:

```bash
# Terminal 1
cd /path/to/MVP_for_AI-based_PoC/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. API_HOST=0.0.0.0 API_PORT=8000 uvicorn app.main:app --host 0.0.0.0 --port 8000
```

```bash
# Terminal 2
cd /path/to/MVP_for_AI-based_PoC/frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://<server-ip>:8000 npm run dev
```

From another computer on the same LAN or through a reachable public IP, open:

```text
http://<server-ip>:3000
```

Make sure firewall/security-group rules allow inbound TCP `3000` and `8000`.

For a production-like Next.js start:

```bash
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://<server-ip>:8000 npm run build
PORT=3000 npm run start
```

## Docker Compose

Set the public API URL, then start both services:

```bash
export NEXT_PUBLIC_API_BASE_URL=http://<server-ip>:8000
docker compose up --build
```

Open `http://<server-ip>:3000` from another computer.

## Demo Flow

1. Open the web app.
2. The demo project `Smart Notification Summary` is created automatically if missing.
3. Click **Run workflow** with the default Chinese prompt, or enter a new product idea.
4. Review PRD, UX Flow, Consistency, QA Criteria, and Jira Stories from the left navigation.
5. Inspect the generated prototype in the right iframe and use the focus selector to jump to feature states.

You can also seed demo artefacts from the backend environment:

```bash
cd backend
PYTHONPATH=. python ../scripts/seed_demo.py
```

## Environment

Copy `.env.example` if you want a local env file. Optional OpenAI-compatible variables:

```bash
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

Without an API key, deterministic mock generation is used.

## Tests and Checks

Backend:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest
```

Frontend:

```bash
cd frontend
npm run build
```

## Known Limits

- No production authentication or multi-user collaboration.
- Jira and Figma integrations are mocked by structured local artefacts.
- The LLM abstraction exists, but deterministic workflow generation is preferred for demo stability.
- Human approval gates are represented in UI copy and workflow structure, not enforced yet.
- Mermaid flow is generated as Markdown; the frontend displays it as text rather than rendering a diagram.

## Next Steps

- Add approval checkpoints before prototype generation and Jira export.
- Render Mermaid diagrams directly in the frontend.
- Add real Jira/Figma connectors behind explicit human approval.
- Expand prototype generation from deterministic templates to model-assisted variants.

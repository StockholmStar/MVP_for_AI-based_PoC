# AI Product Workspace

AI Product Workspace is a cloud/server-runnable foundation for a LangGraph-backed multi-agent product workflow platform. It turns one product input into a canonical product workspace state, then renders aligned artefacts for product, UX, engineering, and QA pre-review:

`brief -> input readiness -> PRD -> gated revision -> UX flow -> prototype -> gated alignment -> QA -> final alignment -> versioned artefacts`

The built-in demo case is **Smart Notification Summary**, a phone system software feature for grouping low-priority notifications in Notification shade with Settings controls.

## Architecture

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS.
- **Backend:** FastAPI, Python, LangGraph.
- **Storage:** SQLite metadata plus canonical state versions, gate results, agent run history, approvals, and generated local files under `data/projects/<project_id>/`.
- **LLM layer:** OpenAI-compatible environment variables are supported. When an API key is configured, agents call the configured model. Without a key, deterministic fallback keeps tests and demos runnable.
- **Context pack:** Lightweight PM/UX/QA/Jira guidance lives in `context/` and is loaded by the workflow.

The single source of truth is `ProductWorkspaceState`: project metadata, source brief, assumptions, questions, goals, non-goals, surfaces, device states, requirements, UX states, prototype screens, QA criteria, risks, owner boundaries, trace links, gate results, approvals, and agent run history. PRD, User Flow, Prototype HTML, QA Criteria, and Traceability are rendered views from that state and versioned together.

If one OpenAI-compatible model is configured, the app labels this honestly as a **single-model multi-agent workflow**. It does not claim separate model fleets or external Jira/Figma integrations.

## Agents and Gates

The backend exposes agent definitions through `GET /api/platform`. The current agents are:

- Coordinator Agent
- Input Checker Agent
- PRD Agent
- UX Flow Agent
- Prototype Agent
- QA Agent
- Traceability Agent
- Output Checker / Gate Agent
- Human Approval Agent

Each definition includes id/name, role, input and output contracts, prompt, deterministic fallback policy, model config reference, and quality checklist.

LangGraph gates use conditional routing:

- Input Readiness Gate: pass to PRD or route to approval/missing input status.
- PRD Quality Gate: pass to UX or revise PRD, with max attempts before approval.
- UX / Prototype Alignment Gate: pass to QA or revise UX/prototype.
- QA Coverage Gate: pass to traceability or revise QA.
- Final Alignment Gate: publish or route to human approval.

Gate results include status (`pass`, `fail`, `needs_human`, `skipped`), score, severity, failed checks, feedback, revision target, attempt count, and timestamp. The frontend shows PM-friendly status such as Passed, Revised automatically, Needs approval, or Failed with reason.

## API

- `GET /api/health`
- `GET /api/platform`
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
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

Open `http://127.0.0.1:3000`.

## Linux Server / Tunnel Startup

On a Linux server, bind both services to `0.0.0.0` and let Next.js proxy same-origin `/api` requests to the backend. This works for direct server access and HTTPS tunnels such as Cloudflare Tunnel because the browser only calls the frontend origin.

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
API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

From another computer on the same LAN or through a reachable public IP, open:

```text
http://<server-ip>:3000
```

Make sure firewall/security-group rules allow inbound TCP `3000`. Port `8000` can stay private when the frontend proxy can reach it locally.

For Cloudflare Tunnel, point the tunnel at the frontend service, for example `http://127.0.0.1:3000`. Keep the backend running on the server and set `API_PROXY_TARGET=http://127.0.0.1:8000` for the frontend process.

For a production-like Next.js start:

```bash
cd frontend
API_PROXY_TARGET=http://127.0.0.1:8000 npm run build
PORT=3000 npm run start
```

## Docker Compose

Start both services. The frontend container proxies same-origin `/api` requests to the backend container:

```bash
docker compose up --build
```

Open `http://<server-ip>:3000` from another computer.

## Demo Flow

1. Open the web app.
2. The demo project `Smart Notification Summary` is created automatically if missing.
3. Click **Run workflow** with the default Chinese prompt, or enter a new product idea.
4. Review Product Overview, PRD, User Flow, Prototype, QA Criteria, and Traceability status.
5. Inspect the Agents & Gates section for runtime mode, canonical version status, gate outcomes, and agent definitions.
6. Inspect the generated prototype in the right iframe and use the focus selector to jump to feature states.

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
- No production external Jira, Figma, proxy, or delivery-tool integration.
- Optional LLM execution uses one configured OpenAI-compatible model unless you extend model routing.
- Human approval is enforced for risky adjustments and gate `needs_human` routes; approving publishes a new canonical state version and cancelling preserves the previous version.
- Deterministic fallbacks are intentionally conservative so tests can run without credentials.

## Next Steps

- Add authentication and multi-user project boundaries.
- Expand model-assisted structured patch validation.
- Add explicit connector contracts for real external tools behind approval.
- Broaden product domains beyond the built-in phone system workflow.

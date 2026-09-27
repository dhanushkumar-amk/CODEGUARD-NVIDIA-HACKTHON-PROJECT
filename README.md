# CodeGuard 🛡️

CodeGuard is an autonomous AI agent that proactively scans codebases for digital accessibility (a11y) violations, generates WCAG-compliant fixes using NVIDIA Nemotron models via Nebius Token Factory, and validates each remediation inside isolated Nebius sandboxes using axe-core and the project's existing test suite before proposing pull requests.

---

## 🏗️ Repository Architecture

```text
codeguard/
├── backend/                 # Python FastAPI service (agent logic & orchestration)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI entrypoint & CORS configuration
│   │   ├── config.py         # Settings & environment configuration
│   │   ├── routers/          # API route handlers
│   │   ├── services/         # Agent workflows, scanner, & LLM clients
│   │   └── models/           # Pydantic data schemas
│   ├── tests/                # Pytest suite
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Environment variables template
│   └── Dockerfile            # Container definition
├── frontend/                 # React 18 + TypeScript + Vite web dashboard
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # View pages
│   │   ├── api/              # Backend API client integration
│   │   ├── App.tsx           # Application shell & health checker
│   │   └── main.tsx          # React application root
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── sandbox-scripts/          # Execution scripts for Nebius sandboxes (axe-core test runners)
├── docs/
│   ├── architecture.md       # Detailed technical design & agent flow
│   └── README.md             # Documentation overview
├── .gitignore
├── LICENSE                   # MIT License
└── README.md
```

---

## 🚀 Quickstart & Local Setup

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm** / **pnpm**
- (Optional) Docker & Git

---

### 1. Backend Setup (FastAPI)

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local `.env` configuration:
   ```bash
   # Windows (PowerShell)
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

5. Start the backend development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Verify backend health:
   - Visit [http://localhost:8000/health](http://localhost:8000/health) or [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI).
   - Expected output: `{"status": "ok"}`

---

### 2. Frontend Setup (React + Vite + TypeScript)

1. In a new terminal, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open your browser:
   - Visit [http://localhost:5173](http://localhost:5173)
   - CodeGuard will automatically ping the backend `/health` endpoint to verify live connectivity.

---

## ⚡ Built with Nebius Token Factory & NVIDIA Nemotron

CodeGuard leverages cutting-edge enterprise AI inference and secure execution infrastructure:

- **NVIDIA Nemotron Models**:
  - `nvidia/nemotron-4-340b-instruct` / Ultra models for multi-step reasoning, WCAG guideline analysis, and code synthesis.
  - `nvidia/nemotron-mini-4b-instruct` / Nano models for fast token-efficient pre-filtering and diff validation.
- **Nebius Token Factory**:
  - High-throughput, low-latency OpenAI-compatible API endpoints powering the Nemotron family of models.
- **Nebius Isolated Sandboxes**:
  - Ephemeral, secure microVM environments executing axe-core accessibility scanners, headless browser runs, and localized regression test suites to guarantee zero regression before submitting patches.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

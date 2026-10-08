# Contributing to CodeGuard

Thank you for your interest in contributing to **CodeGuard**! We welcome bug reports, feature enhancements, documentation improvements, and WCAG accessibility rule extensions.

---

## 🛠️ Development Setup

CodeGuard consists of two primary services:

1. **Backend (Python 3.11+ / FastAPI)**:
   ```bash
   cd backend
   python -m venv .venv
   # Windows:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   cp .env.example .env
   uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend (React 18 / TypeScript / Vite)**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 🧪 Running Tests

Ensure all tests pass before opening a pull request:

```bash
# Backend pytest suite
cd backend
pytest -v

# Frontend test suite
cd frontend
npm test
```

---

## 🤝 Contribution Guidelines

1. **Fork & Branch**: Create a feature branch off `master` (e.g. `feature/aria-modal-rule` or `fix/remediation-diff`).
2. **Commit Messages**: Write clear, descriptive commit messages summarizing the rationale and impact.
3. **Accessibility First**: If adding UI components, ensure they meet WCAG 2.2 AA standards (semantic elements, keyboard accessibility, contrast ratios).
4. **Issue First**: For significant architectural changes, please open an issue first to discuss the design before submitting code.

---

## 📄 License

By contributing to CodeGuard, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

# Campus Customs AI Storefront

Campus Customs is a React + Vite + TypeScript storefront with a FastAPI and PydanticAI shopping assistant. It supports product browsing, product detail pages, account login, database-grounded price and inventory answers, dynamic chat search results, customer chat memory, and an append-only audit trail.

## Project layout

- `frontend/` contains the Vite React application.
- `backend/` contains the FastAPI app, PydanticAI agent, tools, models, and system prompt.
- `output/` contains the harness, design and usability notes, app-check report, screenshots, and audit trail.
- `AI_prompts.md` records the prompts used for each problem.

## Local data

The course data pack is intentionally not committed. Place it in the project as:

```text
data/
  campus_customs.db
  products/
```

Alternatively, set `CAMPUS_DATA_DIR` to the directory containing the database and `products/` folder.

## Backend

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

Copy `.env.example` to `.env` and set a real provider key only in the local file if you want the PydanticAI model path. Without a model key, the app provides a narrow, database-backed fallback for current-product price/stock checks and category searches.

## Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Run `npm run build` for a production build check.

## App check

Open `output/app_check.html` directly to view the required screenshots and test captions.

## Security notes

Do not commit `.env`, `data/`, the SQLite database, product images, `.venv/`, `node_modules/`, or `dist/`. `.env.example` contains placeholders only.

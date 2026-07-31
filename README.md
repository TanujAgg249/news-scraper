# EnergyPulse

An institutional-grade energy market intelligence platform. EnergyPulse aggregates global news, classifies oil market sentiment using OpenAI `gpt-4o-mini`, maps articles geographically and by relationship clusters in 3D, and utilizes a Retrieval-Augmented Generation (RAG) vector pipeline via Supabase PostgreSQL (`pgvector`) to answer complex analyst queries.

---

## Key Features

- **Interactive 3D Graph (React Force Graph)**: Visualize relationships and clusters of geopolitical events affecting crude prices.
- **Geographic Map View (React Simple Maps)**: Track real-time events and their oil market sentiment color-coded across the globe.
- **EnergyPulseAI (RAG Search)**: Ask natural language queries (e.g., *"What is the latest on Russian oil sanctions?"*). The system embeds the query via OpenAI, searches the database using cosine similarity (`pgvector`), and streams a cited, factual answer.
- **OpenAI-Powered Sentiment Analysis**: Automatically classifies articles as Bullish, Bearish, or Neutral with detailed causal analyst reasoning.
- **Live Brent Crude Ticker**: Displays live pricing, daily percentage change, and status indicators.
- **Automatic Scraper Loop**: Runs continuously using a background scheduler to crawl news feeds, extract entities, calculate coordinates, and embed articles.
- **Automated Retention Pruning**: Articles older than 48 hours are automatically pruned to keep dashboards responsive and data focused.

---

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy ORM, PostgreSQL with `pgvector` (Supabase), OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`), Trafilatura, Pydantic, Uvicorn
- **Frontend**: React 18, Vite, React Force Graph 3D, React Simple Maps / D3-geo, Vanilla CSS
- **Infrastructure & Deployment**: Docker, Render (Backend Docker Service), Vercel (Frontend CI/CD)

---

## Repository Structure

```
EnergyPulse/
├── backend/                   # FastAPI Web Server & Data Pipelines
│   ├── app/
│   │   ├── api/               # REST Endpoints (articles, graph, chat, topics)
│   │   ├── analysis/          # AI Classifier & Vector Embedding generators
│   │   ├── scraper/           # RSS & Google News Crawlers
│   │   ├── services/          # Background schedulers & tickers
│   │   ├── config.py          # App settings (Pydantic)
│   │   └── models.py          # SQLAlchemy tables (pgvector Vector columns)
│   └── Dockerfile             # Container configuration for Render
├── frontend/                  # React Single-Page Application (Vite)
│   ├── src/
│   │   ├── components/        # UI (3D Graph, World Map, Chat, Topic Manager)
│   │   ├── hooks/             # Custom state & fetch hooks
│   │   ├── api/               # API clients
│   │   └── App.jsx            # Main app shell & layout
│   └── package.json           # Frontend dependencies
├── render.yaml                # Infrastructure-as-code configuration
└── pyproject.toml             # Python package and environment settings
```

---

## Local Development Setup

### Prerequisites

- **Python 3.11+** (using `uv` is recommended)
- **Node.js 18+**

### Step 1: Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a `.env` file in the root of the project with your API credentials:
   ```env
   OPENAI_API_KEY=sk-proj-YOUR_OPENAI_KEY
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.supabase.co:5432/postgres
   ```

3. Sync dependencies and start the local FastAPI server:
   ```bash
   uv sync
   source .venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Step 2: Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Access the web application at **http://localhost:5173**.

---

## Production Deployments

- **Frontend**: Deployed on Vercel (automatically triggered via git pushes to `main`).
- **Backend**: Deployed on Render as a Docker service.

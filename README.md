# PaperTrail - Research Paper Catalog with GraphRAG

A comprehensive research paper catalog system with continuous autonomous ingestion, GraphRAG-based search, and specialized views for discovering, analyzing, and exploring AI/ML papers.

## Features

### Core Functionality
- **Manual Paper Ingestion**: Import papers from arXiv URLs with automatic metadata and PDF extraction
- **Continuous Import**: Run multiple parallel import tasks 24/7 with configurable filters
- **Vector Similarity Search**: Semantic search across papers using embeddings
- **Theory Mode**: RAG-based analysis to find evidence for/against hypotheses
- **GraphRAG**: Knowledge graph showing paper relationships (authors, citations, topics)

### Four Specialized Views
1. **Dashboard**: Statistics, activity timeline, and collection overview
2. **Paper List**: Filterable/sortable table with search and status management
3. **Paper Detail**: Full metadata, AI summary, similar papers, and relationship graph
4. **Theory Mode**: Pro/contra argument extraction for hypothesis testing

### Resilience & Fallbacks
- **Embedding Fallback**: Auto-switches from litellm to sentence-transformers if needed
- **LLM Graceful Degradation**: Stores papers with placeholders when LLM unavailable
- **Background Backfill**: Automatically fills missing fields when LLM becomes available
- **Service Status Monitoring**: Clear UI indicators for service availability

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- uv package manager

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/AndreRatzenberger/cursor-research-scraper.git
cd cursor-research-scraper
```

2. **Set up environment variables**
```bash
cp .env.template .env
# Edit .env with your API keys
```

Required environment variables:
- `DEFAULT_MODEL`: LLM model (e.g., "gpt-3.5-turbo")
- `DEFAULT_EMBEDDING_MODEL`: Embedding model (e.g., "text-embedding-3-small")
- `OPENAI_API_KEY`: Your OpenAI API key (or other provider keys)

3. **Install backend dependencies**
```bash
uv sync
```

4. **Install frontend dependencies**
```bash
cd frontend
npm install
```

### Running the Application

1. **Start the backend**
```bash
# From project root
uv run python backend/api/main.py
```

The backend will start on `http://localhost:8000`

2. **Start the frontend** (in a new terminal)
```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:5173`

3. **Access the application**

Open your browser to `http://localhost:5173`

## Usage Guide

### Importing Papers

**Manual Import:**
1. Navigate to "Import" tab
2. Enter an arXiv URL (e.g., `https://arxiv.org/abs/2103.00020`)
3. Click "Import Paper"
4. Watch real-time progress in the activity feed

**Continuous Import:**
1. Navigate to "Import" tab
2. Click "+ New Task"
3. Configure filters:
   - **Category**: arXiv category (e.g., "cs.AI")
   - **Text Query**: Search terms for title/abstract
   - **Check Interval**: Seconds between checks
4. Click "Create Task"
5. The task will run continuously, checking for new papers

### Searching Papers

**Browse & Filter:**
- Use the "Papers" tab to view all papers
- Filter by status: New, Read, Starred
- Search by title, authors, or abstract

**Semantic Search:**
- Enter a natural language query
- System uses vector embeddings to find semantically similar papers
- Works even when LLM is unavailable (falls back to sentence-transformers)

### Theory Mode

1. Navigate to "Theory Mode" tab
2. Enter your hypothesis (e.g., "Transformer models are more efficient than RNNs for long sequences")
3. Click "Analyze"
4. View supporting and contradicting evidence in two columns
5. Each result shows:
   - Paper title and authors
   - Relevance score
   - Argument summary
   - Key quotes

**Note**: Theory mode requires LLM service. If unavailable, a clear message will be shown.

### Paper Details

Click any paper to view:
- Full metadata and abstract
- AI-generated summary (key contributions, methodology, results, future research)
- Similar papers (based on vector similarity)
- Relationship graph (connected papers through citations, authors, topics)
- Personal notes section

### Dashboard

Monitor your collection:
- Total paper count
- Papers by category (bar chart)
- Active import tasks
- Service status (LLM and embeddings)
- Recent activity timeline

## Architecture

### Backend (Python + FastAPI)

```
backend/
├── api/
│   └── main.py           # FastAPI application & endpoints
├── models/
│   ├── database.py       # TinyDB data layer
│   └── schemas.py        # Pydantic models
├── services/
│   ├── arxiv_service.py  # ArXiv API integration
│   ├── embedding_service.py  # Embeddings with fallback
│   ├── llm_service.py    # LLM with placeholders
│   └── graph_service.py  # GraphRAG layer
└── workers/
    ├── continuous_import.py  # Background import worker
    └── backfill_worker.py    # LLM backfill worker
```

### Frontend (React + Vite)

```
frontend/
├── src/
│   ├── App.jsx          # Main application & routing
│   ├── App.css          # Styling
│   └── main.jsx         # Entry point
└── index.html
```

### Data Storage

- **Database**: TinyDB (JSON-based, file: `data/papertrail.json`)
- **Tables**: papers, embeddings, import_tasks, relationships

## API Endpoints

### Papers
- `POST /api/papers/ingest` - Ingest paper from arXiv URL
- `GET /api/papers` - List all papers
- `GET /api/papers/{arxiv_id}` - Get paper details
- `PATCH /api/papers/{arxiv_id}` - Update paper
- `GET /api/papers/{arxiv_id}/similar` - Find similar papers
- `GET /api/papers/{arxiv_id}/relationships` - Get relationship graph

### Search
- `POST /api/search` - Vector similarity search

### Theory Mode
- `POST /api/theory` - Analyze hypothesis for pro/contra arguments

### Import Tasks
- `POST /api/tasks` - Create continuous import task
- `GET /api/tasks` - List all tasks
- `POST /api/tasks/{task_id}/start` - Start task
- `POST /api/tasks/{task_id}/stop` - Stop task
- `DELETE /api/tasks/{task_id}` - Delete task

### Dashboard
- `GET /api/dashboard/stats` - Get collection statistics
- `GET /health` - Health check & service status

### WebSocket
- `WS /ws` - Real-time updates for paper ingestion and imports

## Logging

### Backend Logging
The backend uses Python's logging module with structured logs:
- **INFO**: Normal operations, API calls, paper ingestion
- **DEBUG**: Detailed operation steps
- **WARNING**: Fallback activations, LLM unavailability
- **ERROR**: Exceptions and failures

View logs in the terminal where the backend is running.

### Frontend Logging
The frontend logs to browser console:
- API calls and responses
- WebSocket events
- User actions
- State changes
- Service availability changes

Open browser DevTools Console to view logs.

## Fallback Scenarios

### LLM Unavailable
- Papers are ingested with placeholder fields (`<summary>`, `<keywords>`, etc.)
- `needs_backfill` flag is set to `true`
- Background worker automatically fills placeholders when LLM becomes available
- Theory mode is disabled with clear UI message

### Embedding Service Unavailable
- System automatically falls back to sentence-transformers
- Embeddings always work (sentence-transformers runs locally)
- Search functionality remains available

## Testing

### Backend Tests
```bash
uv run pytest backend/tests/
```

### Manual Testing with Playwright
1. Ensure backend and frontend are running
2. Use Playwright MCP for browser automation testing
3. Test all views, interactions, and fallback scenarios

## Development

### Project Structure
- Managed by `uv` - Use only `uv run` and `uv add` commands
- Backend: Python 3.11+, FastAPI, litellm, sentence-transformers, tinydb, networkx
- Frontend: React, Vite, react-router-dom, recharts

### Adding Dependencies

**Backend:**
```bash
uv add package-name
```

**Frontend:**
```bash
cd frontend
npm install package-name
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (needs 3.11+)
- Verify .env file exists and has required keys
- Check port 8000 is not in use

### Frontend won't start
- Check Node.js version: `node --version` (needs 18+)
- Run `npm install` in frontend directory
- Check port 5173 is not in use

### LLM service unavailable
- Verify API keys in .env
- Check litellm configuration
- Papers will be ingested with placeholders and backfilled later

### No embeddings generated
- System should automatically fall back to sentence-transformers
- Check backend logs for fallback messages
- Sentence-transformers model downloads on first use

### WebSocket connection fails
- Ensure backend is running
- Check browser console for errors
- Real-time updates may not work, but app functionality remains

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

For issues or questions, please open a GitHub issue.

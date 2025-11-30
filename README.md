# GitHub RAG Agent

A full-stack RAG (Retrieval-Augmented Generation) system for answering questions about python public GitHub repositories using:

- **Vector Search**: Semantic code retrieval with OpenAI embeddings + ChromaDB
- **Graph Database**: Structural code relationships in Neo4j
- **LangChain Agents**: Orchestrated reasoning with GPT-4
- **React Frontend**: Chat interface
- **Chrome exension**: Chrome extension to use it directly on GitHub
- **Docker**: Fully containerized deployment

![Architecture](https://img.shields.io/badge/FastAPI-Backend-009688)
![React](https://img.shields.io/badge/React-Frontend-61DAFB)
![Neo4j](https://img.shields.io/badge/Neo4j-Graph-008CC1)
![LangChain](https://img.shields.io/badge/LangChain-Agents-121212)
![LangGraph](https://img.shields.io/badge/LangGraph-Agents-121212)

---

## Chrome Extension

You can use the GitHub RAG Agent directly on GitHub repository pages!

### Features
- **Auto-Detection**: Automatically detects when you're on a GitHub repo page
- **One-Click Loading**: Load repositories into the RAG system with a single click
- **Inline Chat**: Chat with the AI without leaving GitHub

### Installation

1. **Start the backend**:
   ```bash
   cd github-rag-agent && ./start.sh
   ```

2. **Load the extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` folder

3. **Use on GitHub**:
   - Navigate to any GitHub repository
   - Click the extension icon
   - Click "Load Repository"
   - Start chatting

See [chrome-extension/README.md](chrome-extension/README.md) for detailed instructions.

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenAI API Key
- Git

### 1. Clone & Configure

```bash
cd /Users/Leon_Jouet/Documents/perso/python-projects/github-agent/github-rag-agent
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Start the Stack

```bash
cd github-rag-agent && ./start.sh
```

This will start:
- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **Neo4j Browser**: http://localhost:7474

### 3. Bootstrap the System

In a new terminal:

```bash
docker exec -it github-rag-backend python backend/ingestion/bootstrap.py
```

### 4. Start Asking Questions!

Open http://localhost:3000 and ask questions like:
- "What are the main classes in FastAPI?"
- "What dependencies does LangChain use?"

---

## Repository structure

```
github-rag-agent/
├── backend/
│   ├── api/
│   │   ├── main.py              # FastAPI app
│   │   └── routes/              # API endpoints
│   │       ├── health.py
│   │       ├── repos.py         # Repository listing & ingestion
│   │       ├── query.py         # Q&A endpoint
│   │       └── graph.py         # Graph queries
│   ├── core/
│   │   ├── agent.py             # LangChain agent
│   │   ├── retriever.py         # Vector search
│   │   ├── neo4j_client.py      # Neo4j connection
│   │   ├── graph_loader.py      # Load repos to graph
│   │   └── git_tools.py         # Git utilities
│   ├── ingestion/
│   │   └── ingest.py            # Repo cloning & parsing
│   │   └── bootstrap.py         # Repo loading, vector db set up, neo4j db creation
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.js               # Main React component
│   │   ├── index.js
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── chrome-extension/            # Chrome extension
│   ├── manifest.json            # Extension config
│   ├── popup.html               # Extension UI
│   ├── popup.js                 # Extension logic
│   ├── popup.css                # GitHub-styled CSS
│   ├── content.js               # GitHub page integration
│   ├── icons/                   # Extension icons
│   ├── README.md
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Development

### Local Development (without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate 

# Install dependencies
pip install -r requirements.txt

# Start Neo4j separately
docker run -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/test \
  neo4j:5.10

# Run backend
uvicorn api.main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm start
```


## API Endpoints

### Health Check
```bash
GET /health
```
### List Repositories
```bash
GET /repos
```
### Get Repository Details
```bash
GET /repos/{repo_name}
```
### Ingest Repository (NEW)
```bash
POST /repos/ingest
Content-Type: application/json

{
  "repo_url": "https://github.com/owner/repo"
}
```

### Query Agent
```bash
POST /query
Content-Type: application/json

{
  "question": "How does authentication work?",
  "repo": "flask",  // optional
  "chat_history": []  // optional
}
```

### Graph Schema
```bash
GET /graph/schema
```

### Graph Statistics
```bash
GET /graph/stats
```

### Execute Cypher Query
```bash
POST /graph/query
Content-Type: application/json

{
  "query": "MATCH (r:Repository) RETURN r.name LIMIT 5"
}
```

---

## TODOs

- [ ] Support for more languages (JavaScript, Java)
- [ ] Chat history
- [ ] Authentication & multi-user support

---



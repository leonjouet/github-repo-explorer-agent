# GitHub RAG Agent

An AI-powered system for exploring and asking questions about Python GitHub repositories. Ask natural language questions and get answers based on the repository's code, structure, and relationships.

## Features

- **Semantic Code Search**: Find relevant code snippets using vector embeddings
- **Code Relationships**: Understand how classes, functions, and modules relate to each other with a knowledge graph database
- **Chat Interface**: Ask questions in natural language and get contextual answers
- **Chrome Extension**: Use it directly while browsing GitHub repositories
- **Docker Support**: One-command deployment

## Repository Structure

```
github-rag-agent/
├── backend/                     # FastAPI backend
│   ├── api/
│   │   ├── main.py             # FastAPI app
│   │   └── routes/             # API endpoints
│   ├── core/
│   │   ├── agent.py            # LangChain agent
│   │   ├── retriever.py        # Vector search
│   │   ├── neo4j_client.py     # Graph database
│   │   └── graph_loader.py     # Load repos to graph
│   ├── ingestion/
│   │   ├── ingest.py           # Repo parsing
│   │   └── bootstrap.py        # Repo loading & setup
│   └── requirements.txt
├── frontend/                    # React web interface
│   ├── src/
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── chrome-extension/            # Chrome extension
│   ├── manifest.json
│   ├── popup.js
│   └── content.js
├── docker-compose.yml
└── .env.example
```

## Installation

### Prerequisites
- Docker & Docker Compose
- OpenAI API Key

### Chrome Extension (Recommended)

1. **Start the backend**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ./start.sh
   ```

2. **Load the extension in Chrome**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select the `chrome-extension/` folder

3. **Use it on GitHub**:
   - Navigate to any GitHub repository
   - Click the extension icon
   - The extension automatically loads the repo
   - Start asking questions directly on the GitHub page

See [chrome-extension/README.md](chrome-extension/README.md) for detailed instructions.

### Web Interface (Alternative)

1. **Start the stack**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ./start.sh
   ```
   This starts:
   - Backend API: http://localhost:8000
   - Frontend: http://localhost:3000
   - Neo4j: http://localhost:7474

2. **Manually load repositories** (optional):
   ```bash
   docker exec -it [backend_container_ID] python ingestion/bootstrap.py https://github.com/karpathy/nanochat
   ```

3. **Open http://localhost:3000 and ask questions**

## TODOs

- [ ] Chat memory: Maintain context across multiple questions
- [ ] Dynamic content loading: Automatically load page content when navigating so questions can be asked without specifying file names
- [ ] Support for more languages (JavaScript, Java)
- [ ] Chat history persistence
- [ ] Authentication & multi-user support
---



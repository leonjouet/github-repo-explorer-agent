# GREA - GitHub Repository Explorer Agent

An AI-powered system for exploring and asking questions about GitHub repositories. Ask natural language questions and get answers based on the repository's code, structure, and relationships.

## Features

- **Semantic Code Search**: Find relevant code snippets using vector embeddings
- **Code Relationships**: Understand how classes, functions, and modules relate to each other with a knowledge graph database
- **Dynamic Context Retrieval**: Automatically detects which file you're viewing on GitHub, code you select and uses it as context for your questions
- **Code Selection Context**: Select any code snippet on GitHub and add it to the conversation context with one click
- **Chat Interface**: Ask questions in natural language and get contextual answers with ChatGPT-style markdown formatting
- **Chrome Extension**: Use it directly while browsing GitHub repositories - floating panel or toolbar popup
- **Docker Support**: One-command deployment

## Repository Structure

```
github-rag-agent/
├── backend/                    # FastAPI backend
│   ├── api/
│   │   ├── main.py             # FastAPI app
│   │   └── routes/             # API endpoints
│   │       ├── context.py      # Context management
│   │       ├── query.py        # Agent queries
│   │       ├── repos.py        # Repository ingestion
│   │       ├── graph.py        # Graph queries
│   │       └── health.py       # Health check
│   ├── core/
│   │   ├── agent.py            # LangChain agent
│   │   ├── file_explorer.py    # File navigation tool
│   │   ├── retriever.py        # Vector search
│   │   ├── graph_query_tool.py # Graph query tool
│   │   ├── neo4j_client.py     # Graph database client
│   │   ├── graph_loader.py     # Load repos to graph
│   │   └── logging_config.py   # Logging setup
│   ├── ingestion/
│   │   ├── ingest.py           # Repo parsing
│   │   └── bootstrap.py        # Repo loading & setup
│   ├── data/                   # Vector store
│   ├── logs/                   # Application logs
│   └── requirements.txt
├── chrome-extension/           # Chrome extension
│   ├── manifest.json           # Extension config
│   ├── content.js              # Floating panel (injected)
│   ├── content.css             # Panel styles
│   └── icons/                  # Extension icons
├── data/                       # Sample repositories
│   ├── repos/                  # Cloned repos
│   └── metadata/               # Repo metadata
├── neo4j/                      # Neo4j data directory
├── docker-compose.yml
├── start.sh                    # Quick start script
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
   - Click the extension icon or use the floating panel on the page
   - The extension automatically detects and loads the repo
   - **Context is automatically added**: The current file you're viewing is used as context
   - **Select code to add context**: Highlight any code and click "Add to Context"
   - Start asking questions with full context awareness
   - Responses are formatted with markdown (headers, code blocks, lists, etc.)

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
   - Neo4j: http://localhost:7474

2. **Manually load repositories** (optional):
   ```bash
   docker exec -it [backend_container_ID] python ingestion/bootstrap.py https://github.com/karpathy/nanochat
   ```

### Todos
- [ ] Chat memory: Maintain context across multiple questions
- [ ] Support for more languages in the knowledge graph (JavaScript, Java, Typescript)
---

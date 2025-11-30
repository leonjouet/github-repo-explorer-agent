# GitHub RAG Agent - Chrome Extension

A Chrome extension that brings AI-powered code assistance directly to GitHub repository pages.

## Features

- **Automatic Detection**: Automatically detects when you're viewing a GitHub repository
- **One-Click Loading**: Load any GitHub repository into the RAG system with a single click
- **Chat Interface**: Ask questions about the codebase directly from GitHub
- **GitHub-Styled UI**: Seamless integration with GitHub's dark theme

## Installation

### Prerequisites

1. Make sure your GitHub RAG Agent backend is running:
   ```bash
   cd github-rag-agent
   ./start.sh
   ```

2. The backend API should be accessible at `http://localhost:8000`

### Loading the Extension

1. Open Chrome and navigate to `chrome://extensions/`

2. Enable "Developer mode" (toggle in the top right)

3. Click "Load unpacked"

4. Navigate to and select the `chrome-extension` folder in your project:
   ```
   github-rag-agent/chrome-extension/
   ```

5. The extension should now appear in your Chrome toolbar

## Usage

### Loading a Repository

1. Navigate to any GitHub repository page (e.g., `https://github.com/karpathy/nanochat`)

2. Click on the GitHub RAG Agent extension icon in your toolbar

3. The extension will detect the current repository and show a "Load Repository" button

4. Click the button to ingest the repository into your RAG system
   - This may take a few minutes depending on repository size
   - The extension will show a loading indicator

5. Once loaded, the chat interface will appear

### Chatting with the Agent
Type your question in the chat input box and the agent will analyze the repository and provide answers based on:
   - Code structure and dependencies
   - Function and class definitions
   - Documentation and comments
   - File relationships

### Example Questions
- "What does the main function do?"
- "How is the database connection handled?"
- "Explain the architecture of this project"
- "Where is the authentication logic implemented?"

## Configuration
The extension communicates with the backend API at `http://localhost:8000` by default.
To change the API URL, edit `popup.js`:

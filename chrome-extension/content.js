// Content script for GitHub pages - Injects floating panel
console.log('GitHub RAG Agent: Content script loaded');

const API_BASE_URL = 'http://localhost:8000';

// State
let currentRepoUrl = null;
let currentRepoName = null;
let isLoaded = false;
let isPanelVisible = false;

// Create floating button and panel
function createFloatingUI() {
  // Create floating button
  const floatBtn = document.createElement('button');
  floatBtn.id = 'github-rag-float-btn';
  floatBtn.innerHTML = '🤖';
  floatBtn.title = 'GitHub RAG Agent';
  floatBtn.addEventListener('click', togglePanel);
  
  // Create panel with inline HTML
  const panel = document.createElement('div');
  panel.id = 'github-rag-panel';
  panel.innerHTML = `
    <div class="rag-header">
      <h1>GitHub RAG Agent</h1>
      <div id="repo-info" class="repo-info hidden">
        <span id="repo-name"></span>
      </div>
    </div>

    <div id="status-section" class="status-section">
      <div id="not-github" class="message hidden">
        <p>Please navigate to a GitHub repository page to use this extension.</p>
      </div>
      
      <div id="load-section" class="load-section hidden">
        <p class="repo-url">Ready to load: <span id="detected-repo"></span></p>
        <button id="load-repo-btn" class="btn-primary">Load Repository</button>
        <div id="loading-indicator" class="loading hidden">
          <div class="spinner"></div>
          <p>Loading repository... This may take a few minutes.</p>
        </div>
        <div id="load-error" class="error hidden"></div>
      </div>

      <div id="loaded-section" class="loaded-section hidden">
        <p class="success">✓ Repository loaded successfully!</p>
      </div>
    </div>

    <div id="chat-section" class="chat-section hidden">
      <div class="chat-messages" id="chat-messages">
        <div class="welcome-message">
          <p>👋 Hi! I'm your GitHub RAG Agent. Ask me anything about this repository!</p>
        </div>
      </div>
      
      <div class="chat-input-container">
        <textarea 
          id="chat-input" 
          class="chat-input" 
          placeholder="Ask a question about the code..."
          rows="3"
        ></textarea>
        <button id="send-btn" class="btn-send">Send</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(floatBtn);
  document.body.appendChild(panel);
  
  // Initialize after panel is added
  initializePanel();
}

function togglePanel() {
  isPanelVisible = !isPanelVisible;
  const panel = document.getElementById('github-rag-panel');
  
  if (isPanelVisible) {
    panel.classList.add('visible');
    if (!isLoaded) {
      detectGitHubRepo();
    }
  } else {
    panel.classList.remove('visible');
  }
}

// Detect the current repository
function detectRepository() {
  const match = window.location.href.match(/https:\/\/github\.com\/([^\/]+)\/([^\/]+)/);
  
  if (match) {
    const [, owner, repo] = match;
    currentRepoUrl = `https://github.com/${owner}/${repo}`;
    currentRepoName = repo.replace(/\.git$/, '');
    
    return { url: currentRepoUrl, owner, name: currentRepoName };
  }
  
  return null;
}

async function detectGitHubRepo() {
  const repo = detectRepository();
  
  if (!repo) {
    showNotGitHub();
    return;
  }

  currentRepoUrl = repo.url;
  currentRepoName = repo.name;
  
  // Check if repo is already loaded
  const loaded = await checkIfRepoLoaded(currentRepoName);
  
  if (loaded) {
    showChatInterface();
  } else {
    showLoadSection();
  }
}

async function checkIfRepoLoaded(repoName) {
  try {
    const response = await fetch(`${API_BASE_URL}/repos/${repoName}`);
    return response.ok;
  } catch (error) {
    console.error('Error checking repo status:', error);
    return false;
  }
}

function initializePanel() {
  // Get all DOM elements
  const loadRepoBtn = document.getElementById('load-repo-btn');
  const sendBtn = document.getElementById('send-btn');
  const chatInput = document.getElementById('chat-input');
  
  // Setup event listeners
  loadRepoBtn?.addEventListener('click', loadRepository);
  sendBtn?.addEventListener('click', sendMessage);
  
  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  
  // Initial detection
  detectGitHubRepo();
}

function showNotGitHub() {
  const notGithub = document.getElementById('not-github');
  const loadSection = document.getElementById('load-section');
  const loadedSection = document.getElementById('loaded-section');
  const chatSection = document.getElementById('chat-section');
  
  notGithub?.classList.remove('hidden');
  loadSection?.classList.add('hidden');
  loadedSection?.classList.add('hidden');
  chatSection?.classList.add('hidden');
}

function showLoadSection() {
  const detectedRepoSpan = document.getElementById('detected-repo');
  const notGithub = document.getElementById('not-github');
  const loadSection = document.getElementById('load-section');
  const loadedSection = document.getElementById('loaded-section');
  const chatSection = document.getElementById('chat-section');
  
  if (detectedRepoSpan) detectedRepoSpan.textContent = currentRepoUrl;
  
  notGithub?.classList.add('hidden');
  loadSection?.classList.remove('hidden');
  loadedSection?.classList.add('hidden');
  chatSection?.classList.add('hidden');
}

function showChatInterface() {
  isLoaded = true;
  const repoNameSpan = document.getElementById('repo-name');
  const repoInfo = document.getElementById('repo-info');
  const notGithub = document.getElementById('not-github');
  const loadSection = document.getElementById('load-section');
  const loadedSection = document.getElementById('loaded-section');
  const chatSection = document.getElementById('chat-section');
  
  if (repoNameSpan) repoNameSpan.textContent = currentRepoName;
  repoInfo?.classList.remove('hidden');
  
  notGithub?.classList.add('hidden');
  loadSection?.classList.add('hidden');
  loadedSection?.classList.add('hidden');
  chatSection?.classList.remove('hidden');
}

async function loadRepository() {
  if (!currentRepoUrl) return;
  
  const loadRepoBtn = document.getElementById('load-repo-btn');
  const loadingIndicator = document.getElementById('loading-indicator');
  const loadError = document.getElementById('load-error');
  
  loadRepoBtn.disabled = true;
  loadingIndicator?.classList.remove('hidden');
  loadError?.classList.add('hidden');
  
  try {
    const response = await fetch(`${API_BASE_URL}/repos/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        repo_url: currentRepoUrl
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to load repository');
    }
    
    const result = await response.json();
    console.log('Repository loaded:', result);
    
    const loadedSection = document.getElementById('loaded-section');
    loadedSection?.classList.remove('hidden');
    loadingIndicator?.classList.add('hidden');
    
    setTimeout(() => {
      showChatInterface();
    }, 1500);
    
  } catch (error) {
    console.error('Error loading repository:', error);
    if (loadError) {
      loadError.textContent = `Error: ${error.message}`;
      loadError.classList.remove('hidden');
    }
    loadingIndicator?.classList.add('hidden');
    loadRepoBtn.disabled = false;
  }
}

async function sendMessage() {
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const message = chatInput?.value.trim();
  
  if (!message || !isLoaded) return;
  
  addMessageToChat(message, 'user');
  chatInput.value = '';
  
  sendBtn.disabled = true;
  chatInput.disabled = true;
  
  const loadingId = addLoadingMessage();
  
  try {
    const response = await fetch(`${API_BASE_URL}/query/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: message,
        repo: currentRepoName
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to get response from agent');
    }
    
    const result = await response.json();
    
    removeLoadingMessage(loadingId);
    addMessageToChat(result.answer || result.response || 'No response received', 'assistant');
    
  } catch (error) {
    console.error('Error querying agent:', error);
    removeLoadingMessage(loadingId);
    addMessageToChat(`Error: ${error.message}`, 'assistant');
  } finally {
    sendBtn.disabled = false;
    chatInput.disabled = false;
    chatInput.focus();
  }
}

function addMessageToChat(text, role) {
  const chatMessages = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message-${role}`;
  messageDiv.textContent = text;
  chatMessages?.appendChild(messageDiv);
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

function addLoadingMessage() {
  const chatMessages = document.getElementById('chat-messages');
  const loadingDiv = document.createElement('div');
  const id = `loading-${Date.now()}`;
  loadingDiv.id = id;
  loadingDiv.className = 'message-assistant';
  loadingDiv.innerHTML = '💭 Thinking...';
  chatMessages?.appendChild(loadingDiv);
  if (chatMessages) {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
  return id;
}

function removeLoadingMessage(id) {
  const element = document.getElementById(id);
  if (element) {
    element.remove();
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', createFloatingUI);
} else {
  createFloatingUI();
}

// Listen for URL changes (GitHub is a single-page app)
let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    const repo = detectRepository();
    if (repo && isPanelVisible) {
      detectGitHubRepo();
    }
  }
}).observe(document, { subtree: true, childList: true });

// Content script for GitHub pages - Injects floating panel
console.log('GitHub RAG Agent: Content script loaded');

const API_BASE_URL = 'http://localhost:8000';

// State
let currentRepoUrl = null;
let currentRepoName = null;
let currentFilePath = null;
let selectedCode = null;
let isLoaded = false;
let isPanelVisible = false;

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getSelection') {
    // Capture current selection at the moment requested
    const selection = window.getSelection().toString().trim();
    sendResponse({ 
      selectedCode: selection && selection.length > 0 ? selection : null,
      currentFile: currentFilePath
    });
  }
});

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

    <!-- Context Section -->
    <div class="context-section">
      <div class="context-display">
        <div id="context-status" class="context-status">
          <span id="current-file-display" class="hidden">📄 <span id="current-file-name"></span></span>
          <span id="selected-code-display" class="hidden">✂️ <span id="selected-code-preview"></span></span>
        </div>
        <div class="context-actions">
          <button id="add-to-context-btn" class="btn-context">Add</button>
          <button id="clear-context-btn" class="btn-context">Clear</button>
        </div>
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

// Detect the current file path from GitHub URL
function detectCurrentFile() {
  // Match: github.com/owner/repo/blob/branch/path/to/file.py
  const match = window.location.href.match(/\/blob\/[^\/]+\/(.+?)(?:\?|#|$)/);
  
  if (match) {
    currentFilePath = match[1];
    updateFileDisplay();
    syncContextWithBackend();
    return currentFilePath;
  }
  
  currentFilePath = null;
  hideFileDisplay();
  return null;
}

function updateFileDisplay() {
  const fileDisplay = document.getElementById('current-file-display');
  const fileName = document.getElementById('current-file-name');
  const contextInfo = document.getElementById('context-info');
  
  if (currentFilePath) {
    fileName.textContent = currentFilePath;
    fileDisplay?.classList.remove('hidden');
    contextInfo?.classList.remove('hidden');
  } else {
    hideFileDisplay();
  }
}

function hideFileDisplay() {
  const fileDisplay = document.getElementById('current-file-display');
  fileDisplay?.classList.add('hidden');
}

// Listen for text selection and capture code
function setupSelectionListener() {
  document.addEventListener('mouseup', () => {
    const selection = window.getSelection().toString().trim();
    
    if (selection && selection.length > 0) {
      selectedCode = selection;
      updateSelectionDisplay();
      syncContextWithBackend();
      // Save to storage so popup can access it
      chrome.storage.session.set({ selectedCode: selection });
    }
  });
}

function updateSelectionDisplay() {
  const selectionDisplay = document.getElementById('selected-code-display');
  const contextInfo = document.getElementById('context-info');
  
  if (selectedCode) {
    selectionDisplay?.classList.remove('hidden');
    contextInfo?.classList.remove('hidden');
  }
}

function hideSelectionDisplay() {
  const selectionDisplay = document.getElementById('selected-code-display');
  selectionDisplay?.classList.add('hidden');
}

// Sync current context to backend
async function syncContextWithBackend() {
  if (!currentRepoName || (!currentFilePath && !selectedCode)) {
    return;
  }
  
  try {
    await fetch(`${API_BASE_URL}/context/set`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo: currentRepoName,
        context: {
          current_file: currentFilePath,
          selected_code: selectedCode,
          selected_code_file: currentFilePath
        }
      })
    });
  } catch (error) {
    console.error('Error syncing context:', error);
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
  
  // Detect current file if viewing code
  detectCurrentFile();
  
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
  const addToContextBtn = document.getElementById('add-to-context-btn');
  const clearContextBtn = document.getElementById('clear-context-btn');
  
  // Setup event listeners
  loadRepoBtn?.addEventListener('click', loadRepository);
  sendBtn?.addEventListener('click', sendMessage);
  addToContextBtn?.addEventListener('click', addToContext);
  clearContextBtn?.addEventListener('click', clearContext);
  
  chatInput?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  
  // Setup selection listener
  setupSelectionListener();
  
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

// Parse markdown to HTML
function parseMarkdown(text) {
  if (!text) return '';
  
  // Use marked library if available
  if (typeof marked !== 'undefined') {
    try {
      marked.setOptions({
        breaks: true,
        gfm: true
      });
      return marked.parse(text);
    } catch (e) {
      console.error('Error parsing markdown with marked:', e);
      return fallbackMarkdownParser(text);
    }
  }
  
  return fallbackMarkdownParser(text);
}

// Fallback markdown parser
function fallbackMarkdownParser(text) {
  let html = text;
  
  // Ensure proper line breaks before headers if missing
  html = html.replace(/([^\n])(#{1,3} )/g, '$1\n$2');
  
  // Headers (must be before other replacements)
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  
  // Code blocks (triple backticks)
  html = html.replace(/```[\w]*\n?([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
  
  // Inline code (single backticks)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Links (before bold/italic)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
  
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic (avoid matching already processed bold)
  html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
  
  // Unordered lists (- or *) - must be on own line
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  
  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  
  // Group consecutive <li> into <ul>
  html = html.replace(/(<li>.*<\/li>\n?)+/g, function(match) {
    return '<ul>' + match + '</ul>';
  });
  
  // Paragraph wrapping (avoid wrapping block elements)
  html = html.split('\n').map(line => {
    line = line.trim();
    if (line && !line.match(/^<(h[1-6]|pre|ul|ol|li|code|\/)/)) {
      return '<p>' + line + '</p>';
    }
    return line;
  }).join('\n');
  
  // Clean up - remove empty paragraphs and fix nesting
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<[ou]l>)/g, '$1');
  html = html.replace(/(<\/[ou]l>)<\/p>/g, '$1');
  html = html.replace(/<p>(<li>)/g, '$1');
  html = html.replace(/(<\/li>)<\/p>/g, '$1');
  
  return html;
}

function addMessageToChat(text, role) {
  const chatMessages = document.getElementById('chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.className = `message-${role}`;
  
  if (role === 'assistant') {
    // Parse markdown for assistant messages
    const html = parseMarkdown(text);
    messageDiv.innerHTML = html;
  } else {
    // Keep user messages as plain text
    messageDiv.textContent = text;
  }
  
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

// Add selected code to context
function addToContext() {
  const selection = window.getSelection().toString().trim();
  
  if (selection) {
    selectedCode = selection;
    updateContextDisplay();
    showButtonFeedback('add-to-context-btn', 'Added!');
  } else {
    showButtonFeedback('add-to-context-btn', 'No selection');
  }
}

// Clear context (only clears selected code, not current file)
function clearContext() {
  selectedCode = null;
  updateContextDisplay();
  showButtonFeedback('clear-context-btn', 'Cleared!');
}

// Update context display
function updateContextDisplay() {
  const selectedCodeDisplay = document.getElementById('selected-code-display');
  const currentFileDisplay = document.getElementById('current-file-display');
  const previewElement = document.getElementById('selected-code-preview');
  
  // Update file display
  if (currentFilePath) {
    document.getElementById('current-file-name').textContent = currentFilePath;
    currentFileDisplay?.classList.remove('hidden');
  } else {
    currentFileDisplay?.classList.add('hidden');
  }
  
  // Update selection display
  if (selectedCode) {
    const preview = selectedCode.substring(0, 40) + (selectedCode.length > 40 ? '...' : '');
    if (previewElement) previewElement.textContent = preview;
    selectedCodeDisplay?.classList.remove('hidden');
  } else {
    selectedCodeDisplay?.classList.add('hidden');
  }
}

// Show button feedback
function showButtonFeedback(buttonId, message, duration = 1500) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  
  const originalText = btn.textContent;
  btn.textContent = message;
  setTimeout(() => btn.textContent = originalText, duration);
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
    // Re-detect repo and file on navigation
    detectGitHubRepo();
    // Detect current file if viewing code page
    detectCurrentFile();
  }
}).observe(document, { subtree: true, childList: true });

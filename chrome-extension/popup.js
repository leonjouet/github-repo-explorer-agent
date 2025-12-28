// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
let loadRepoBtn, sendBtn, chatInput, chatMessages;
let notGithubSection, loadSection, loadedSection, chatSection;
let detectedRepoSpan, repoNameSpan, loadingIndicator, loadError;
let currentFileDisplay, selectedCodeDisplay, addToContextBtn, clearContextBtn;

// State
let currentRepoUrl = null;
let currentRepoName = null;
let currentFilePath = null;
let selectedCode = null;
let isLoaded = false;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  initializeElements();
  await detectGitHubRepo();
  await capturePageSelectionOnOpen();
  setupEventListeners();
  startContextPolling();
});

function initializeElements() {
  loadRepoBtn = document.getElementById('load-repo-btn');
  sendBtn = document.getElementById('send-btn');
  addToContextBtn = document.getElementById('add-to-context-btn');
  clearContextBtn = document.getElementById('clear-context-btn');
  chatInput = document.getElementById('chat-input');
  chatMessages = document.getElementById('chat-messages');
  notGithubSection = document.getElementById('not-github');
  loadSection = document.getElementById('load-section');
  loadedSection = document.getElementById('loaded-section');
  chatSection = document.getElementById('chat-section');
  detectedRepoSpan = document.getElementById('detected-repo');
  repoNameSpan = document.getElementById('repo-name');
  loadingIndicator = document.getElementById('loading-indicator');
  loadError = document.getElementById('load-error');
  currentFileDisplay = document.getElementById('current-file-display');
  selectedCodeDisplay = document.getElementById('selected-code-display');
}

async function detectGitHubRepo() {
  try {
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    if (!tab || !tab.url) {
      showNotGitHub();
      return;
    }

    // Parse GitHub URL
    const match = tab.url.match(/https:\/\/github\.com\/([^\/]+)\/([^\/]+)/);
    
    if (!match) {
      showNotGitHub();
      return;
    }

    const [, owner, repo] = match;
    currentRepoUrl = `https://github.com/${owner}/${repo}`;
    currentRepoName = repo.replace(/\.git$/, '');
    
    // Detect current file if viewing code
    detectCurrentFile(tab.url);
    
    // Check if repo is already loaded
    const loaded = await checkIfRepoLoaded(currentRepoName);
    
    if (loaded) {
      showChatInterface();
    } else {
      showLoadSection();
    }
    
  } catch (error) {
    console.error('Error detecting GitHub repo:', error);
    showNotGitHub();
  }
}

function detectCurrentFile(url) {
  const match = url.match(/\/blob\/[^\/]+\/(.+?)(?:\?|#|$)/);
  currentFilePath = match ? match[1] : null;
  updateContextDisplay();
  return currentFilePath;
}

function updateContextDisplay() {
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
    document.getElementById('selected-code-preview').textContent = preview;
    selectedCodeDisplay?.classList.remove('hidden');
  } else {
    selectedCodeDisplay?.classList.add('hidden');
  }
}

async function capturePageSelectionOnOpen() {
  try {
    const result = await chrome.storage.session.get(['selectedCode']);
    if (result?.selectedCode) {
      selectedCode = result.selectedCode;
      updateContextDisplay();
    }
  } catch (error) {
    console.error('Error reading from storage:', error);
  }
}

async function syncContextWithBackend() {
  if (!currentRepoName) return;
  
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

function startContextPolling() {
  setInterval(async () => {
    if (!currentRepoName) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/context/${currentRepoName}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.context) {
          currentFilePath = data.context.current_file || null;
          selectedCode = data.context.selected_code || null;
          updateContextDisplay();
        }
      }
    } catch (error) {
      // Silent fail on polling
    }
  }, 1000);
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

function showNotGitHub() {
  notGithubSection.classList.remove('hidden');
  loadSection.classList.add('hidden');
  loadedSection.classList.add('hidden');
  chatSection.classList.add('hidden');
}

function showLoadSection() {
  detectedRepoSpan.textContent = currentRepoUrl;
  notGithubSection.classList.add('hidden');
  loadSection.classList.remove('hidden');
  loadedSection.classList.add('hidden');
  chatSection.classList.add('hidden');
}

function showChatInterface() {
  isLoaded = true;
  repoNameSpan.textContent = currentRepoName;
  document.getElementById('repo-info').classList.remove('hidden');
  notGithubSection.classList.add('hidden');
  loadSection.classList.add('hidden');
  loadedSection.classList.add('hidden');
  chatSection.classList.remove('hidden');
}

function setupEventListeners() {
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
}

async function loadRepository() {
  if (!currentRepoUrl) return;
  
  // Disable button and show loading
  loadRepoBtn.disabled = true;
  loadingIndicator.classList.remove('hidden');
  loadError.classList.add('hidden');
  
  try {
    // Call the backend API to ingest the repository
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
    
    // Show success and switch to chat
    loadedSection.classList.remove('hidden');
    loadingIndicator.classList.add('hidden');
    
    // Wait a moment then show chat interface
    setTimeout(() => {
      showChatInterface();
    }, 1500);
    
  } catch (error) {
    console.error('Error loading repository:', error);
    loadError.textContent = `Error: ${error.message}`;
    loadError.classList.remove('hidden');
    loadingIndicator.classList.add('hidden');
    loadRepoBtn.disabled = false;
  }
}

async function sendMessage() {
  const message = chatInput.value.trim();
  
  if (!message || !isLoaded) return;
  
  // Add user message to chat
  addMessageToChat(message, 'user');
  chatInput.value = '';
  
  // Disable input while processing
  sendBtn.disabled = true;
  chatInput.disabled = true;
  
  // Add loading message
  const loadingId = addLoadingMessage();
  
  try {
    // Call the query API
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
    
    // Remove loading message
    removeLoadingMessage(loadingId);
    
    // Add assistant response
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

// Add selected code to context
async function addToContext() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.id) return;
    
    chrome.tabs.sendMessage(tab.id, { action: 'getSelection' }, (response) => {
      if (chrome.runtime.lastError || !response?.selectedCode?.trim()) {
        showButtonFeedback('add-to-context-btn', 'No selection');
        return;
      }
      
      selectedCode = response.selectedCode.trim();
      updateContextDisplay();
      syncContextWithBackend();
      chrome.storage.session.set({ selectedCode });
      showButtonFeedback('add-to-context-btn', 'Added!');
    });
  } catch (error) {
    console.error('Error adding to context:', error);
  }
}

// Clear context (only clears selected code, not current file)
function clearContext() {
  selectedCode = null;
  updateContextDisplay();
  syncContextWithBackend();
  chrome.storage.session.set({ selectedCode: null });
  showButtonFeedback('clear-context-btn', 'Cleared!');
}

// Helper to show temporary button feedback
function showButtonFeedback(buttonId, message, duration = 1500) {
  const btn = document.getElementById(buttonId);
  if (!btn) return;
  
  const originalText = btn.textContent;
  btn.textContent = message;
  setTimeout(() => btn.textContent = originalText, duration);
}

// Parse markdown to HTML
function parseMarkdown(text) {
  if (!text) return '';
  
  // Use marked library if available
  if (typeof marked !== 'undefined') {
    try {
      // Configure marked to break on line breaks
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
  
  // Group consecutive <li> into <ul> or based on context
  html = html.replace(/(<li>.*<\/li>\n?)+/g, function(match) {
    // Check if it's part of numbered list context
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
  
  chatMessages.appendChild(messageDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addLoadingMessage() {
  const loadingDiv = document.createElement('div');
  const id = `loading-${Date.now()}`;
  loadingDiv.id = id;
  loadingDiv.className = 'message-assistant';
  loadingDiv.innerHTML = '<div style="display: flex; gap: 4px;"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>';
  chatMessages.appendChild(loadingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return id;
}

function removeLoadingMessage(id) {
  const element = document.getElementById(id);
  if (element) {
    element.remove();
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

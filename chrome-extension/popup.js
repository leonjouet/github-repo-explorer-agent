// Configuration
const API_BASE_URL = 'http://localhost:8000';

// DOM Elements
let loadRepoBtn, sendBtn, chatInput, chatMessages;
let notGithubSection, loadSection, loadedSection, chatSection;
let detectedRepoSpan, repoNameSpan, loadingIndicator, loadError;

// State
let currentRepoUrl = null;
let currentRepoName = null;
let isLoaded = false;

// Initialize popup
document.addEventListener('DOMContentLoaded', async () => {
  initializeElements();
  await detectGitHubRepo();
  setupEventListeners();
});

function initializeElements() {
  // Buttons
  loadRepoBtn = document.getElementById('load-repo-btn');
  sendBtn = document.getElementById('send-btn');
  
  // Input
  chatInput = document.getElementById('chat-input');
  chatMessages = document.getElementById('chat-messages');
  
  // Sections
  notGithubSection = document.getElementById('not-github');
  loadSection = document.getElementById('load-section');
  loadedSection = document.getElementById('loaded-section');
  chatSection = document.getElementById('chat-section');
  
  // Info elements
  detectedRepoSpan = document.getElementById('detected-repo');
  repoNameSpan = document.getElementById('repo-name');
  loadingIndicator = document.getElementById('loading-indicator');
  loadError = document.getElementById('load-error');
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
  // Load repository button
  loadRepoBtn?.addEventListener('click', loadRepository);
  
  // Send message button
  sendBtn?.addEventListener('click', sendMessage);
  
  // Enter key in chat input
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
  
  // Headers (must be before other replacements)
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
  
  // Code blocks (triple backticks)
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  
  // Inline code (single backticks)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Links (before bold/italic)
  html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank">$1</a>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic
  html = html.replace(/\*([^\*]+)\*/g, '<em>$1</em>');
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
  
  // Numbered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, function(match) {
    return '<ol>' + match + '</ol>';
  });
  
  // Unordered lists (- or *)
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>');
  
  // Wrap multiple list items in proper tags
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, function(match) {
    if (!match.includes('<ol>') && !match.includes('<ul>')) {
      return '<ul>' + match + '</ul>';
    }
    return match;
  });
  
  // Paragraph wrapping (avoid wrapping block elements)
  html = html.split('\n').map(line => {
    line = line.trim();
    if (line && !line.startsWith('<') && !line.includes('</')) {
      return '<p>' + line + '</p>';
    }
    return line;
  }).join('\n');
  
  // Clean up
  html = html.replace(/<p><\/p>/g, '');
  html = html.replace(/<p>(<h[1-6]>)/g, '$1');
  html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  html = html.replace(/<p>(<pre>)/g, '$1');
  html = html.replace(/(<\/pre>)<\/p>/g, '$1');
  html = html.replace(/<p>(<[ou]l>)/g, '$1');
  html = html.replace(/(<\/[ou]l>)<\/p>/g, '$1');
  
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

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function App() {
  const [repos, setRepos] = useState([]);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAddRepo, setShowAddRepo] = useState(false);
  const [repoUrl, setRepoUrl] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestError, setIngestError] = useState('');

  useEffect(() => {
    fetchRepos();
  }, []);

  const fetchRepos = async () => {
    try {
      const response = await axios.get(`${API_BASE}/repos`);
      setRepos(response.data.repos);
    } catch (error) {
      console.error('Error fetching repos:', error);
    }
  };

  const handleIngestRepo = async (e) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;

    // Validate GitHub URL
    const githubPattern = /^https:\/\/github\.com\/[\w-]+\/[\w.-]+$/;
    if (!githubPattern.test(repoUrl.trim())) {
      setIngestError('Please enter a valid GitHub repository URL (e.g., https://github.com/owner/repo)');
      return;
    }

    setIngesting(true);
    setIngestError('');

    try {
      const response = await axios.post(`${API_BASE}/repos/ingest`, {
        repo_url: repoUrl.trim()
      });

      // Success - refresh repo list and close modal
      await fetchRepos();
      setRepoUrl('');
      setShowAddRepo(false);
      
      // Show success message
      const successMessage = {
        role: 'assistant',
        content: `✓ Repository "${response.data.message}" has been successfully loaded! You can now ask questions about it.`,
        success: true
      };
      setMessages([...messages, successMessage]);
    } catch (error) {
      console.error('Error ingesting repo:', error);
      setIngestError(
        error.response?.data?.detail || 
        'Failed to load repository. Please check the URL and try again.'
      );
    } finally {
      setIngesting(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMessage = {
      role: 'user',
      content: question,
      repo: selectedRepo
    };
    
    setMessages([...messages, userMessage]);
    setLoading(true);
    setQuestion('');

    try {
      const response = await axios.post(`${API_BASE}/query`, {
        question: question,
        repo: selectedRepo,
        chat_history: messages
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.answer,
        repo: selectedRepo
      };

      setMessages([...messages, userMessage, assistantMessage]);
    } catch (error) {
      console.error('Error querying:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, there was an error processing your question.',
        error: true
      };
      setMessages([...messages, userMessage, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <div className="container mx-auto">
          <h1 className="text-3xl font-bold">GitHub RAG Agent</h1>
          <p className="text-blue-100">Ask questions about GitHub repositories</p>
        </div>
      </header>

      <div className="container mx-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Sidebar - Repository Selector */}
          <div className="md:col-span-1">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Repositories</h2>
                <button
                  onClick={() => setShowAddRepo(!showAddRepo)}
                  className="bg-green-500 text-white px-3 py-1 rounded-lg hover:bg-green-600 text-sm"
                  title="Add new repository"
                >
                  + Add
                </button>
              </div>

              {/* Add Repository Form */}
              {showAddRepo && (
                <div className="mb-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
                  <form onSubmit={handleIngestRepo} className="space-y-2">
                    <input
                      type="text"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      placeholder="https://github.com/owner/repo"
                      className="w-full p-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                      disabled={ingesting}
                    />
                    {ingestError && (
                      <div className="text-xs text-red-600 bg-red-50 p-2 rounded">
                        {ingestError}
                      </div>
                    )}
                    <div className="flex space-x-2">
                      <button
                        type="submit"
                        disabled={ingesting || !repoUrl.trim()}
                        className="flex-1 bg-green-500 text-white px-3 py-2 rounded text-sm hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                      >
                        {ingesting ? 'Loading...' : 'Load Repo'}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setShowAddRepo(false);
                          setRepoUrl('');
                          setIngestError('');
                        }}
                        disabled={ingesting}
                        className="px-3 py-2 bg-gray-200 rounded text-sm hover:bg-gray-300 disabled:bg-gray-100"
                      >
                        Cancel
                      </button>
                    </div>
                    {ingesting && (
                      <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded">
                        ⏳ Loading repository... This may take several minutes.
                      </div>
                    )}
                  </form>
                </div>
              )}

              <div className="space-y-2">
                <button
                  onClick={() => setSelectedRepo(null)}
                  className={`w-full text-left p-2 rounded ${
                    selectedRepo === null
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 hover:bg-gray-200'
                  }`}
                >
                  All Repositories
                </button>
                {repos.map((repo) => (
                  <button
                    key={repo.name}
                    onClick={() => setSelectedRepo(repo.name)}
                    className={`w-full text-left p-2 rounded ${
                      selectedRepo === repo.name
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 hover:bg-gray-200'
                    }`}
                  >
                    <div className="font-medium">{repo.name}</div>
                    <div className="text-xs opacity-75">
                      {repo.total_files} files, {repo.total_functions} functions
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Main Chat Area */}
          <div className="md:col-span-3">
            <div className="bg-white rounded-lg shadow">
              {/* Messages */}
              <div className="h-96 overflow-y-auto p-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-500 mt-20">
                    <h3 className="text-xl font-semibold mb-2">
                      Welcome to GitHub RAG Agent
                    </h3>
                    <p>
                      Select a repository and ask questions about the code,
                      structure, or dependencies.
                    </p>
                    <div className="mt-4 text-sm text-left max-w-md mx-auto bg-blue-50 p-4 rounded">
                      <p className="font-semibold mb-2">Example questions:</p>
                      <ul className="list-disc list-inside space-y-1">
                        <li>How does authentication work in this repo?</li>
                        <li>What are the main classes and their purposes?</li>
                        <li>Show me functions that handle database operations</li>
                        <li>What dependencies does this project use?</li>
                      </ul>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex ${
                        msg.role === 'user' ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      <div
                        className={`max-w-3xl rounded-lg p-4 ${
                          msg.role === 'user'
                            ? 'bg-blue-500 text-white'
                            : msg.error
                            ? 'bg-red-100 text-red-800'
                            : msg.success
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {msg.repo && (
                          <div className="text-xs opacity-75 mb-1">
                            Repository: {msg.repo}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    </div>
                  ))
                )}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg p-4">
                      <div className="flex space-x-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200"></div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Form */}
              <form onSubmit={handleSubmit} className="border-t p-4">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask a question about the code..."
                    className="flex-1 p-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loading}
                  />
                  <button
                    type="submit"
                    disabled={loading || !question.trim()}
                    className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
                  >
                    Send
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;

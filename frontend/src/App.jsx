import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useParams } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

const API_BASE = 'http://localhost:8000';

// Logging utility
const log = (action, data) => {
  console.log(`[PaperTrail] ${new Date().toISOString()} - ${action}:`, data);
};

// API service
const api = {
  async ingestPaper(arxivUrl) {
    log('API Call', `POST /api/papers/ingest?arxiv_url=${arxivUrl}`);
    const response = await fetch(`${API_BASE}/api/papers/ingest?arxiv_url=${encodeURIComponent(arxivUrl)}`, {
      method: 'POST',
    });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async listPapers(params = {}) {
    const query = new URLSearchParams(params).toString();
    log('API Call', `GET /api/papers?${query}`);
    const response = await fetch(`${API_BASE}/api/papers?${query}`);
    const data = await response.json();
    log('API Response', `Fetched ${data.length} papers`);
    return data;
  },
  
  async getPaper(arxivId) {
    log('API Call', `GET /api/papers/${arxivId}`);
    const response = await fetch(`${API_BASE}/api/papers/${arxivId}`);
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async updatePaper(arxivId, updates) {
    log('API Call', `PATCH /api/papers/${arxivId}`, updates);
    const response = await fetch(`${API_BASE}/api/papers/${arxivId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async getSimilarPapers(arxivId, limit = 5) {
    log('API Call', `GET /api/papers/${arxivId}/similar`);
    const response = await fetch(`${API_BASE}/api/papers/${arxivId}/similar?limit=${limit}`);
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async getRelationships(arxivId) {
    log('API Call', `GET /api/papers/${arxivId}/relationships`);
    const response = await fetch(`${API_BASE}/api/papers/${arxivId}/relationships`);
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async searchPapers(query, limit = 10) {
    log('API Call', `POST /api/search`, { query, limit });
    const response = await fetch(`${API_BASE}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit }),
    });
    const data = await response.json();
    log('API Response', `Found ${data.length} papers`);
    return data;
  },
  
  async analyzeTheory(hypothesis, limit = 5) {
    log('API Call', `POST /api/theory`, { hypothesis, limit });
    const response = await fetch(`${API_BASE}/api/theory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hypothesis, limit }),
    });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async createTask(task) {
    log('API Call', `POST /api/tasks`, task);
    const response = await fetch(`${API_BASE}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(task),
    });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async listTasks() {
    log('API Call', 'GET /api/tasks');
    const response = await fetch(`${API_BASE}/api/tasks`);
    const data = await response.json();
    log('API Response', `Fetched ${data.length} tasks`);
    return data;
  },
  
  async startTask(taskId) {
    log('API Call', `POST /api/tasks/${taskId}/start`);
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}/start`, { method: 'POST' });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async stopTask(taskId) {
    log('API Call', `POST /api/tasks/${taskId}/stop`);
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}/stop`, { method: 'POST' });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async deleteTask(taskId) {
    log('API Call', `DELETE /api/tasks/${taskId}`);
    const response = await fetch(`${API_BASE}/api/tasks/${taskId}`, { method: 'DELETE' });
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async getDashboardStats() {
    log('API Call', 'GET /api/dashboard/stats');
    const response = await fetch(`${API_BASE}/api/dashboard/stats`);
    const data = await response.json();
    log('API Response', data);
    return data;
  },
  
  async healthCheck() {
    log('API Call', 'GET /health');
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    log('API Response', data);
    return data;
  },
};

// WebSocket connection
const useWebSocket = () => {
  const [messages, setMessages] = useState([]);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws`);
    
    ws.onopen = () => {
      log('WebSocket', 'Connected');
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      log('WebSocket Message', message);
      setMessages(prev => [...prev, message]);
    };
    
    ws.onerror = (error) => {
      log('WebSocket Error', error);
    };
    
    ws.onclose = () => {
      log('WebSocket', 'Disconnected');
    };
    
    return () => ws.close();
  }, []);
  
  return messages;
};

// Dashboard View
function Dashboard() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const wsMessages = useWebSocket();
  
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, []);
  
  const loadData = async () => {
    log('Dashboard', 'Loading stats');
    const [statsData, healthData] = await Promise.all([
      api.getDashboardStats(),
      api.healthCheck(),
    ]);
    setStats(statsData);
    setHealth(healthData);
  };
  
  if (!stats || !health) {
    return <div className="loading">Loading dashboard...</div>;
  }
  
  const categoryData = Object.entries(stats.papers_by_category || {})
    .map(([name, value]) => ({ name: name.split('.')[0], value }))
    .slice(0, 10);
  
  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Papers</h3>
          <div className="stat-value">{stats.total_papers}</div>
        </div>
        <div className="stat-card">
          <h3>Active Import Tasks</h3>
          <div className="stat-value">{stats.active_import_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>LLM Status</h3>
          <div className={`stat-value ${health.llm_available ? 'status-ok' : 'status-error'}`}>
            {health.llm_available ? 'Available' : 'Unavailable'}
          </div>
        </div>
        <div className="stat-card">
          <h3>Embedding Status</h3>
          <div className={`stat-value ${health.embedding_available ? 'status-ok' : 'status-error'}`}>
            {health.embedding_available ? 'Available' : 'Unavailable'}
          </div>
        </div>
      </div>
      
      <div className="charts">
        <div className="chart-container">
          <h2>Papers by Category</h2>
          {categoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={categoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="value" fill="#4F46E5" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="no-data">No papers yet</div>
          )}
        </div>
      </div>
      
      <div className="recent-activity">
        <h2>Recent Activity</h2>
        <div className="activity-list">
          {wsMessages.slice(-10).reverse().map((msg, idx) => (
            <div key={idx} className="activity-item">
              <span className="activity-type">{msg.type}</span>
              {msg.paper && <span className="activity-title">{msg.paper.title || msg.paper.arxiv_id}</span>}
              {msg.task_id && <span className="activity-task">Task: {msg.task_id}</span>}
            </div>
          ))}
          {wsMessages.length === 0 && <div className="no-data">No recent activity</div>}
        </div>
      </div>
    </div>
  );
}

// Paper List View
function PaperList() {
  const [papers, setPapers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const navigate = useNavigate();
  
  useEffect(() => {
    loadPapers();
  }, [statusFilter]);
  
  const loadPapers = async () => {
    log('PaperList', `Loading papers with status filter: ${statusFilter}`);
    const params = statusFilter !== 'all' ? { status: statusFilter } : {};
    const data = await api.listPapers(params);
    setPapers(data);
  };
  
  const filteredPapers = papers.filter(paper => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return paper.title.toLowerCase().includes(query) ||
           paper.abstract.toLowerCase().includes(query) ||
           paper.authors.some(a => a.toLowerCase().includes(query));
  });
  
  const updateStatus = async (arxivId, status) => {
    log('PaperList', `Updating paper ${arxivId} status to ${status}`);
    await api.updatePaper(arxivId, { status });
    loadPapers();
  };
  
  return (
    <div className="paper-list">
      <div className="list-header">
        <h1>Research Papers</h1>
        <div className="list-controls">
          <input
            type="text"
            placeholder="Search papers..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="search-input"
          />
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="filter-select">
            <option value="all">All Status</option>
            <option value="new">New</option>
            <option value="read">Read</option>
            <option value="starred">Starred</option>
          </select>
        </div>
      </div>
      
      <div className="paper-table">
        <div className="table-header">
          <div className="col-title">Title</div>
          <div className="col-authors">Authors</div>
          <div className="col-date">Published</div>
          <div className="col-categories">Categories</div>
          <div className="col-status">Status</div>
          <div className="col-actions">Actions</div>
        </div>
        
        {filteredPapers.map(paper => (
          <div key={paper.arxiv_id} className="table-row">
            <div className="col-title">
              <a href="#" onClick={() => navigate(`/paper/${paper.arxiv_id}`)}>{paper.title}</a>
            </div>
            <div className="col-authors">{paper.authors.slice(0, 2).join(', ')}{paper.authors.length > 2 ? '...' : ''}</div>
            <div className="col-date">{new Date(paper.published).toLocaleDateString()}</div>
            <div className="col-categories">{paper.categories[0]}</div>
            <div className="col-status">
              <span className={`status-badge status-${paper.status}`}>{paper.status}</span>
            </div>
            <div className="col-actions">
              <button onClick={() => updateStatus(paper.arxiv_id, 'starred')} className="btn-icon">⭐</button>
              <button onClick={() => updateStatus(paper.arxiv_id, 'read')} className="btn-icon">✓</button>
            </div>
          </div>
        ))}
        
        {filteredPapers.length === 0 && (
          <div className="no-results">No papers found</div>
        )}
      </div>
    </div>
  );
}

// Paper Detail View
function PaperDetail() {
  const { arxivId } = useParams();
  const [paper, setPaper] = useState(null);
  const [similar, setSimilar] = useState([]);
  const [relationships, setRelationships] = useState({ nodes: [], edges: [] });
  const [notes, setNotes] = useState('');
  const navigate = useNavigate();
  
  useEffect(() => {
    loadPaper();
  }, [arxivId]);
  
  const loadPaper = async () => {
    log('PaperDetail', `Loading paper ${arxivId}`);
    const [paperData, similarData, relData] = await Promise.all([
      api.getPaper(arxivId),
      api.getSimilarPapers(arxivId),
      api.getRelationships(arxivId),
    ]);
    setPaper(paperData);
    setSimilar(similarData);
    setRelationships(relData);
    setNotes(paperData.notes || '');
  };
  
  const saveNotes = async () => {
    log('PaperDetail', `Saving notes for ${arxivId}`);
    await api.updatePaper(arxivId, { notes });
    alert('Notes saved!');
  };
  
  if (!paper) {
    return <div className="loading">Loading paper...</div>;
  }
  
  return (
    <div className="paper-detail">
      <div className="detail-header">
        <button onClick={() => navigate('/papers')} className="btn-back">← Back to List</button>
        <h1>{paper.title}</h1>
      </div>
      
      <div className="detail-meta">
        <div className="meta-item">
          <strong>Authors:</strong> {paper.authors.join(', ')}
        </div>
        <div className="meta-item">
          <strong>Published:</strong> {new Date(paper.published).toLocaleDateString()}
        </div>
        <div className="meta-item">
          <strong>arXiv ID:</strong> <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer">{paper.arxiv_id}</a>
        </div>
        <div className="meta-item">
          <strong>Categories:</strong> {paper.categories.join(', ')}
        </div>
        <div className="meta-item">
          <strong>Status:</strong> <span className={`status-badge status-${paper.status}`}>{paper.status}</span>
        </div>
      </div>
      
      <div className="detail-section">
        <h2>Abstract</h2>
        <p>{paper.abstract}</p>
      </div>
      
      <div className="detail-section">
        <h2>AI-Generated Summary</h2>
        {paper.summary !== '<summary>' ? (
          <>
            <p><strong>Summary:</strong> {paper.summary}</p>
            <p><strong>Key Contributions:</strong> {paper.key_contributions}</p>
            <p><strong>Methodology:</strong> {paper.methodology}</p>
            <p><strong>Results:</strong> {paper.results}</p>
            <p><strong>Future Research:</strong> {paper.future_research}</p>
            <p><strong>Keywords:</strong> {paper.keywords.join(', ')}</p>
          </>
        ) : (
          <div className="placeholder-notice">
            ⚠️ LLM-generated fields are not yet available. They will be backfilled when LLM service becomes available.
          </div>
        )}
      </div>
      
      <div className="detail-section">
        <h2>Similar Papers</h2>
        {similar.length > 0 ? (
          <div className="similar-papers">
            {similar.map(sim => (
              <div key={sim.arxiv_id} className="similar-paper">
                <a href="#" onClick={() => navigate(`/paper/${sim.arxiv_id}`)}>
                  {sim.title}
                </a>
                <span className="similarity-score">Similarity: {(sim.similarity * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="no-data">No similar papers found</div>
        )}
      </div>
      
      <div className="detail-section">
        <h2>Relationship Graph</h2>
        {relationships.nodes.length > 0 ? (
          <div className="graph-summary">
            <p>This paper is connected to {relationships.nodes.length - 1} other papers through:</p>
            <ul>
              {relationships.edges.map((edge, idx) => (
                <li key={idx}>
                  {edge.type.replace('_', ' ')} with {
                    relationships.nodes.find(n => n.id === (edge.source === arxivId ? edge.target : edge.source))?.title
                  }
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="no-data">No relationships found</div>
        )}
      </div>
      
      <div className="detail-section">
        <h2>Notes</h2>
        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          className="notes-textarea"
          placeholder="Add your notes here..."
        />
        <button onClick={saveNotes} className="btn-primary">Save Notes</button>
      </div>
    </div>
  );
}

// Theory Mode View
function TheoryMode() {
  const [hypothesis, setHypothesis] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  
  useEffect(() => {
    checkHealth();
  }, []);
  
  const checkHealth = async () => {
    const healthData = await api.healthCheck();
    setHealth(healthData);
  };
  
  const analyzeHypothesis = async () => {
    if (!hypothesis.trim()) {
      alert('Please enter a hypothesis');
      return;
    }
    
    if (!health?.llm_available) {
      alert('Theory mode requires LLM service, which is currently unavailable');
      return;
    }
    
    setLoading(true);
    setError(null);
    log('TheoryMode', `Analyzing hypothesis: ${hypothesis}`);
    
    try {
      const data = await api.analyzeTheory(hypothesis);
      setResults(data);
    } catch (err) {
      log('TheoryMode Error', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="theory-mode">
      <h1>Theory Mode</h1>
      <p className="subtitle">Analyze papers to find evidence for and against your hypothesis</p>
      
      {health && !health.llm_available && (
        <div className="alert alert-warning">
          ⚠️ Theory Mode is currently unavailable because the LLM service is not available.
          Papers can still be ingested with placeholder fields that will be backfilled when LLM becomes available.
        </div>
      )}
      
      <div className="theory-input">
        <textarea
          value={hypothesis}
          onChange={e => setHypothesis(e.target.value)}
          placeholder="Enter your hypothesis or theory statement..."
          className="hypothesis-input"
          disabled={!health?.llm_available}
        />
        <button 
          onClick={analyzeHypothesis} 
          className="btn-primary"
          disabled={loading || !health?.llm_available}
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
      
      {error && (
        <div className="alert alert-error">
          Error: {error}
        </div>
      )}
      
      {results && (
        <div className="theory-results">
          <div className="results-columns">
            <div className="result-column pro">
              <h2>✅ Supporting Evidence</h2>
              {results.pro_arguments.length > 0 ? (
                results.pro_arguments.map((arg, idx) => (
                  <div key={idx} className="argument-card">
                    <h3>{arg.title}</h3>
                    <div className="argument-meta">
                      <span className="authors">{arg.authors.slice(0, 2).join(', ')}</span>
                      <span className="relevance">Relevance: {(arg.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                    <p className="argument-summary">{arg.argument_summary}</p>
                    {arg.key_quotes.length > 0 && (
                      <div className="key-quotes">
                        <strong>Key Quotes:</strong>
                        <ul>
                          {arg.key_quotes.map((quote, qidx) => (
                            <li key={qidx}>{quote}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="no-data">No supporting evidence found</div>
              )}
            </div>
            
            <div className="result-column contra">
              <h2>❌ Contradicting Evidence</h2>
              {results.contra_arguments.length > 0 ? (
                results.contra_arguments.map((arg, idx) => (
                  <div key={idx} className="argument-card">
                    <h3>{arg.title}</h3>
                    <div className="argument-meta">
                      <span className="authors">{arg.authors.slice(0, 2).join(', ')}</span>
                      <span className="relevance">Relevance: {(arg.relevance_score * 100).toFixed(0)}%</span>
                    </div>
                    <p className="argument-summary">{arg.argument_summary}</p>
                    {arg.key_quotes.length > 0 && (
                      <div className="key-quotes">
                        <strong>Key Quotes:</strong>
                        <ul>
                          {arg.key_quotes.map((quote, qidx) => (
                            <li key={qidx}>{quote}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="no-data">No contradicting evidence found</div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Import Management View
function ImportManagement() {
  const [arxivUrl, setArxivUrl] = useState('');
  const [importing, setImporting] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [showNewTask, setShowNewTask] = useState(false);
  const [newTask, setNewTask] = useState({
    task_id: '',
    name: '',
    category: '',
    text_query: '',
    check_interval: 300,
  });
  
  useEffect(() => {
    loadTasks();
  }, []);
  
  const loadTasks = async () => {
    log('ImportManagement', 'Loading tasks');
    const data = await api.listTasks();
    setTasks(data);
  };
  
  const ingestPaper = async () => {
    if (!arxivUrl.trim()) {
      alert('Please enter an arXiv URL');
      return;
    }
    
    setImporting(true);
    log('ImportManagement', `Ingesting paper from ${arxivUrl}`);
    
    try {
      await api.ingestPaper(arxivUrl);
      alert('Paper ingested successfully!');
      setArxivUrl('');
    } catch (err) {
      log('ImportManagement Error', err);
      alert('Error ingesting paper: ' + err.message);
    } finally {
      setImporting(false);
    }
  };
  
  const createTask = async () => {
    if (!newTask.name || !newTask.task_id) {
      alert('Please fill in required fields');
      return;
    }
    
    log('ImportManagement', `Creating task ${newTask.task_id}`);
    await api.createTask(newTask);
    setShowNewTask(false);
    setNewTask({ task_id: '', name: '', category: '', text_query: '', check_interval: 300 });
    loadTasks();
  };
  
  const toggleTask = async (taskId, isActive) => {
    if (isActive) {
      await api.stopTask(taskId);
    } else {
      await api.startTask(taskId);
    }
    loadTasks();
  };
  
  const deleteTask = async (taskId) => {
    if (confirm('Are you sure you want to delete this task?')) {
      await api.deleteTask(taskId);
      loadTasks();
    }
  };
  
  return (
    <div className="import-management">
      <h1>Import Management</h1>
      
      <div className="import-section">
        <h2>Manual Import</h2>
        <div className="manual-import">
          <input
            type="text"
            placeholder="Enter arXiv URL (e.g., https://arxiv.org/abs/2103.00020)"
            value={arxivUrl}
            onChange={e => setArxivUrl(e.target.value)}
            className="import-input"
          />
          <button onClick={ingestPaper} disabled={importing} className="btn-primary">
            {importing ? 'Importing...' : 'Import Paper'}
          </button>
        </div>
      </div>
      
      <div className="import-section">
        <div className="section-header">
          <h2>Continuous Import Tasks</h2>
          <button onClick={() => setShowNewTask(!showNewTask)} className="btn-primary">
            + New Task
          </button>
        </div>
        
        {showNewTask && (
          <div className="new-task-form">
            <input
              type="text"
              placeholder="Task ID (e.g., cs-ai-task)"
              value={newTask.task_id}
              onChange={e => setNewTask({ ...newTask, task_id: e.target.value })}
              className="form-input"
            />
            <input
              type="text"
              placeholder="Task Name"
              value={newTask.name}
              onChange={e => setNewTask({ ...newTask, name: e.target.value })}
              className="form-input"
            />
            <input
              type="text"
              placeholder="Category (e.g., cs.AI)"
              value={newTask.category}
              onChange={e => setNewTask({ ...newTask, category: e.target.value })}
              className="form-input"
            />
            <input
              type="text"
              placeholder="Text Query (optional)"
              value={newTask.text_query}
              onChange={e => setNewTask({ ...newTask, text_query: e.target.value })}
              className="form-input"
            />
            <input
              type="number"
              placeholder="Check Interval (seconds)"
              value={newTask.check_interval}
              onChange={e => setNewTask({ ...newTask, check_interval: parseInt(e.target.value) })}
              className="form-input"
            />
            <button onClick={createTask} className="btn-primary">Create Task</button>
            <button onClick={() => setShowNewTask(false)} className="btn-secondary">Cancel</button>
          </div>
        )}
        
        <div className="tasks-list">
          {tasks.map(task => (
            <div key={task.task_id} className="task-card">
              <div className="task-header">
                <h3>{task.name}</h3>
                <span className={`task-status ${task.is_active ? 'active' : 'inactive'}`}>
                  {task.is_active ? 'Running' : 'Stopped'}
                </span>
              </div>
              <div className="task-details">
                <div>Category: {task.category || 'All'}</div>
                <div>Text Query: {task.text_query || 'None'}</div>
                <div>Check Interval: {task.check_interval}s</div>
                <div>Papers Imported: {task.papers_imported}</div>
                <div>Last Check: {task.last_check ? new Date(task.last_check).toLocaleString() : 'Never'}</div>
              </div>
              <div className="task-actions">
                <button onClick={() => toggleTask(task.task_id, task.is_active)} className="btn-secondary">
                  {task.is_active ? 'Stop' : 'Start'}
                </button>
                <button onClick={() => deleteTask(task.task_id)} className="btn-danger">Delete</button>
              </div>
            </div>
          ))}
          {tasks.length === 0 && (
            <div className="no-data">No continuous import tasks configured</div>
          )}
        </div>
      </div>
    </div>
  );
}

// Main App Component
function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="navbar">
          <div className="nav-brand">
            <h1>📄 PaperTrail</h1>
            <span className="tagline">Research Paper Catalog with GraphRAG</span>
          </div>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/papers">Papers</Link>
            <Link to="/theory">Theory Mode</Link>
            <Link to="/import">Import</Link>
          </div>
        </nav>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/papers" element={<PaperList />} />
            <Route path="/paper/:arxivId" element={<PaperDetail />} />
            <Route path="/theory" element={<TheoryMode />} />
            <Route path="/import" element={<ImportManagement />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

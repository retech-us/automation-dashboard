#!/usr/bin/env node
/**
 * Local development server for automation-dashboard
 * Express.js server with hot-reload and CORS support
 *
 * Usage:
 *   npm install express cors body-parser
 *   node server.js
 *
 * Then visit: http://localhost:6060
 */

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = 6060;
const HOST = 'localhost';

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Serve static files from project root
app.use(express.static(path.join(__dirname)));

// API Routes

// Get Jira data
app.get('/api/jira', (req, res) => {
  try {
    const jiraFile = path.join(__dirname, 'data', 'jira.json');
    if (fs.existsSync(jiraFile)) {
      const data = JSON.parse(fs.readFileSync(jiraFile, 'utf8'));
      res.json(data);
    } else {
      res.status(404).json({ error: 'Jira data not found', file: jiraFile });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get test cases
app.get('/api/test-cases', (req, res) => {
  try {
    const testCasesFile = path.join(__dirname, 'data', 'test-cases.json');
    if (fs.existsSync(testCasesFile)) {
      const data = JSON.parse(fs.readFileSync(testCasesFile, 'utf8'));
      res.json(data);
    } else {
      res.json({ testCases: [], message: 'No test cases generated yet' });
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Generate test cases (mock endpoint)
app.post('/api/generate-test-cases', (req, res) => {
  const { issueKey, issueType, testTypes } = req.body;

  // This is a mock endpoint - actual generation happens in Python
  console.log(`Mock test case generation for ${issueKey}`);
  console.log(`  Type: ${issueType}`);
  console.log(`  Test Types: ${testTypes.join(', ')}`);

  res.json({
    status: 'queued',
    message: `Test case generation queued for ${issueKey}`,
    endpoint: 'Run: python3 scripts/generate-test-cases.py',
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    server: `http://${HOST}:${PORT}`,
  });
});

// Root redirect
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// 404 handler
app.use((req, res) => {
  console.warn(`404: ${req.path}`);
  res.status(404).sendFile(path.join(__dirname, 'index.html'));
});

// Error handler
app.use((error, req, res, next) => {
  console.error('Server error:', error);
  res.status(500).json({
    error: error.message,
    stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
  });
});

// Start server
app.listen(PORT, HOST, () => {
  console.log('\n' + '='.repeat(70));
  console.log('Automation Dashboard - Local Development Server (Express)');
  console.log('='.repeat(70));
  console.log(`✓ Server running on: http://${HOST}:${PORT}`);
  console.log(`✓ Dashboard available at: http://${HOST}:${PORT}/index.html`);
  console.log(`✓ API endpoints:`);
  console.log(`  - GET  /api/jira              (Fetch Jira data)`);
  console.log(`  - GET  /api/test-cases        (Fetch generated test cases)`);
  console.log(`  - POST /api/generate-test-cases (Queue generation)`);
  console.log(`  - GET  /health               (Health check)`);
  console.log(`✓ Press CTRL+C to stop server`);
  console.log('='.repeat(70));
  console.log('\nTips:');
  console.log('  • Open DevTools (F12) to see console output');
  console.log('  • Check "Network" tab to see API calls');
  console.log('  • Refresh page (Ctrl+R) to reload');
  console.log('  • Hard refresh (Ctrl+Shift+R) to clear cache');
  console.log('');
});

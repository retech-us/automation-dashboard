import React, { useState, useEffect } from 'react';
import { invoke } from '@forge/bridge';

export default function TestCasesPanel() {
  const [testCases, setTestCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadTestCases();
  }, []);

  async function loadTestCases() {
    try {
      setLoading(true);
      setError(null);

      // Call backend resolver
      const cases = await invoke('getTestCasesResolver', {});
      setTestCases(cases || []);
    } catch (err) {
      console.error('Error loading test cases:', err);
      setError(err.message || 'Failed to load test cases');
    } finally {
      setLoading(false);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    await loadTestCases();
    setRefreshing(false);
  }

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <span style={styles.spinner}>⏳</span>
          <p>Loading test cases...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.container}>
        <div style={styles.error}>
          <span style={styles.errorIcon}>⚠️</span>
          <p>Error: {error}</p>
          <button onClick={handleRefresh} style={styles.retryBtn}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (testCases.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>
          <span style={styles.emptyIcon}>📝</span>
          <p>No test cases generated yet</p>
          <p style={styles.emptyHint}>
            Generate test cases using the Inhouse TC Generator tool
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <span style={styles.icon}>🧪</span>
          <h3 style={styles.title}>Inhouse TC Generator</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          style={{
            ...styles.refreshBtn,
            opacity: refreshing ? 0.5 : 1,
            cursor: refreshing ? 'not-allowed' : 'pointer'
          }}
          title="Refresh test cases"
        >
          {refreshing ? '⏳' : '🔄'}
        </button>
      </div>

      {/* Summary */}
      <div style={styles.summary}>
        <span style={styles.badgeGreen}>
          ✓ {testCases.length} test case{testCases.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Test Cases List */}
      <div style={styles.list}>
        {testCases.map((tc, idx) => (
          <div key={idx} style={styles.card}>
            <div style={styles.cardHeader}>
              <div style={styles.cardLeft}>
                <div style={styles.qcNumber}>{tc.qcNumber}</div>
                <div style={styles.cardInfo}>
                  <h4 style={styles.cardTitle}>{tc.title}</h4>
                  <p style={styles.cardKey}>{tc.key}</p>
                </div>
              </div>
              <div style={styles.cardRight}>
                <span style={styles.statusBadge}>{tc.status}</span>
              </div>
            </div>

            {/* Card Footer with Link */}
            <div style={styles.cardFooter}>
              <a
                href={tc.url}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.link}
              >
                View in Jira →
              </a>
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <p style={styles.footerText}>
          {testCases.length} test case{testCases.length !== 1 ? 's' : ''} generated
        </p>
      </div>
    </div>
  );
}

const styles = {
  container: {
    padding: '16px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif',
    backgroundColor: '#fff',
    borderRadius: '8px',
  },

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    borderBottom: '2px solid #EBECF0',
    paddingBottom: '12px',
  },

  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },

  icon: {
    fontSize: '20px',
  },

  title: {
    margin: 0,
    fontSize: '16px',
    fontWeight: '600',
    color: '#161B22',
  },

  refreshBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    fontSize: '18px',
    cursor: 'pointer',
    padding: '4px 8px',
    borderRadius: '4px',
    transition: 'background-color 0.2s',
  },

  summary: {
    display: 'flex',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap',
  },

  badgeGreen: {
    backgroundColor: '#DFFCF0',
    color: '#216E4E',
    padding: '4px 12px',
    borderRadius: '12px',
    fontSize: '13px',
    fontWeight: '500',
  },

  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    marginBottom: '16px',
  },

  card: {
    backgroundColor: '#F6F8FA',
    border: '1px solid #EBECF0',
    borderRadius: '6px',
    padding: '12px',
    transition: 'all 0.2s',
  },

  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '12px',
  },

  cardLeft: {
    display: 'flex',
    gap: '12px',
    flex: 1,
  },

  qcNumber: {
    backgroundColor: '#0055CC',
    color: 'white',
    padding: '6px 12px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: '700',
    whiteSpace: 'nowrap',
    minWidth: '70px',
    textAlign: 'center',
  },

  cardInfo: {
    flex: 1,
  },

  cardTitle: {
    margin: '0 0 4px 0',
    fontSize: '14px',
    fontWeight: '600',
    color: '#161B22',
    wordBreak: 'break-word',
  },

  cardKey: {
    margin: 0,
    fontSize: '12px',
    color: '#626F86',
  },

  cardRight: {
    display: 'flex',
    alignItems: 'center',
  },

  statusBadge: {
    backgroundColor: '#DFFCF0',
    color: '#216E4E',
    padding: '4px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '500',
    whiteSpace: 'nowrap',
  },

  cardFooter: {
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: '1px solid #EBECF0',
  },

  link: {
    color: '#0055CC',
    textDecoration: 'none',
    fontSize: '12px',
    fontWeight: '500',
    transition: 'color 0.2s',
  },

  loading: {
    textAlign: 'center',
    padding: '32px 16px',
    color: '#626F86',
  },

  spinner: {
    fontSize: '32px',
    display: 'block',
    marginBottom: '12px',
  },

  empty: {
    textAlign: 'center',
    padding: '32px 16px',
    color: '#626F86',
  },

  emptyIcon: {
    fontSize: '48px',
    display: 'block',
    marginBottom: '16px',
  },

  emptyHint: {
    fontSize: '12px',
    margin: '8px 0 0 0',
    color: '#7C8AA2',
  },

  error: {
    textAlign: 'center',
    padding: '32px 16px',
    color: '#AE2A19',
    backgroundColor: '#FFECEB',
    borderRadius: '6px',
  },

  errorIcon: {
    fontSize: '32px',
    display: 'block',
    marginBottom: '12px',
  },

  retryBtn: {
    backgroundColor: '#AE2A19',
    color: 'white',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    marginTop: '12px',
  },

  footer: {
    borderTop: '1px solid #EBECF0',
    paddingTop: '12px',
    textAlign: 'center',
  },

  footerText: {
    margin: 0,
    fontSize: '12px',
    color: '#7C8AA2',
  },
};

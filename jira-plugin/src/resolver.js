import { api, queue } from '@forge/api';

/**
 * Get test cases for the current issue
 * Called from the panel component
 */
export async function getTestCasesResolver() {
  try {
    // Get current issue context
    const issueKey = getCurrentIssueKey();

    if (!issueKey) {
      console.error('No issue key found');
      return [];
    }

    console.log(`Fetching test cases for: ${issueKey}`);

    // Fetch the issue with linked issues
    const response = await api.asUser().requestJira(
      `/rest/api/3/issues/${issueKey}?expand=changelog`,
      {
        headers: {
          'Accept': 'application/json'
        }
      }
    );

    if (!response.ok) {
      console.error(`Failed to fetch issue: ${response.status}`);
      return [];
    }

    const issue = await response.json();
    const testCases = extractTestCases(issue);

    console.log(`Found ${testCases.length} test cases for ${issueKey}`);
    return testCases;

  } catch (error) {
    console.error('Error in getTestCasesResolver:', error);
    throw new Error(`Failed to load test cases: ${error.message}`);
  }
}

/**
 * Extract test cases from issue's linked issues
 */
function extractTestCases(issue) {
  const testCases = [];
  const links = issue.fields?.issuelinks || [];

  links.forEach(link => {
    // Look for "relates to" relationships with outward issues
    if (link.type?.name === 'relates to' && link.outwardIssue) {
      const linkedIssue = link.outwardIssue;
      const testCase = parseTestCase(linkedIssue);

      if (testCase) {
        testCases.push(testCase);
      }
    }
  });

  // Sort by QC number (newest first)
  testCases.sort((a, b) => {
    const numA = extractQCNumber(a.qcNumber);
    const numB = extractQCNumber(b.qcNumber);
    return numB - numA;
  });

  return testCases;
}

/**
 * Parse a linked issue into test case object
 */
function parseTestCase(linkedIssue) {
  try {
    const key = linkedIssue.key;
    const summary = linkedIssue.fields?.summary || '';
    const self = linkedIssue.self || '';

    // Extract QC number from title: [TC: QC-100] Title
    const qcMatch = summary.match(/\[TC:\s*(QC-\d+)\]/);
    const qcNumber = qcMatch ? qcMatch[1] : 'UNKNOWN';

    // Remove QC number from title for display
    const title = summary.replace(/\[TC:\s*QC-\d+\]\s*/, '').trim();

    return {
      key,
      title: title || 'Untitled Test Case',
      qcNumber,
      status: 'synced', // Changed from 'Synced' to 'synced'
      url: self.replace('/rest/api/3/issues/', '/browse/'), // Convert API URL to browse URL
      type: linkedIssue.fields?.issuetype?.name || 'Test Case'
    };
  } catch (error) {
    console.warn(`Error parsing test case:`, error);
    return null;
  }
}

/**
 * Extract numeric part from QC number
 */
function extractQCNumber(qcString) {
  const match = qcString.match(/QC-(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

/**
 * Get current issue key from context
 * This is called by Forge in the issue panel context
 */
function getCurrentIssueKey() {
  // In Forge, the issue key is available via the context
  // This will be set by the framework when the panel is rendered

  // Try to get from URL params
  try {
    const url = window.location.href;
    const match = url.match(/browse\/([A-Z]+-\d+)/);
    if (match) return match[1];
  } catch (e) {
    // In Forge, window is not available
  }

  // In actual Forge execution, this will be provided by the context bridge
  // For now, return a default that will be overridden
  return null;
}

/**
 * Handle Forge resolver magic methods
 * Forge calls these automatically based on your manifest
 */
export function definition() {
  return {
    function: getTestCasesResolver,
  };
}

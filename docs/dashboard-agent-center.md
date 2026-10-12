# Dashboard Agent Center

## What was integrated

The dashboard now has a shared, read-only Agent Center. Every agent returns the
same grounded result contract:

- verdict and confidence
- plain-language summary
- findings with source evidence
- recommended next steps
- source list and unique run ID

The current execution mode is `grounded-rules-v1`. It uses deterministic
analysis so it remains useful without an LLM credential and does not invent
facts. A model can later be added as an explanation layer without changing the
API or UI contract.

To enable the optional AI explanation layer, start the server with an approved
OpenAI-compatible gateway:

```bash
export DASHBOARD_AGENT_LLM_URL="https://approved-gateway.example/v1/chat/completions"
export DASHBOARD_AGENT_LLM_MODEL="approved-model-name"
export DASHBOARD_AGENT_LLM_API_KEY="..."
python3 runner_server.py
```

With that configuration the mode becomes `grounded-rules-v1+model`. The model
may clarify the explanation and recommendations, but cannot replace the
deterministic verdict, findings, source evidence, or read-only access policy.
Without these variables, no data is sent to any model.

## How to use it

1. Open the dashboard and select **Agent Center**.
2. Select an Intelligent Reset task first when the question is about that task.
3. Type a question, or choose one of the suggested questions.
4. Select **Analyze**.
5. Read the direct answer, then the evidence used to produce it.

The active dashboard tab defines the evidence scope:

- **Overview** — suite health, failures, release risk, and Jira blockers.
- **Needs attention** — current failure and triage records.
- **Trends & AI usage** — automation history and AI-healing usage.
- **Suite details** — suite results, coverage gaps, and flaky candidates.
- **Jira Quality & Delivery** — Jira summary, priorities, and workflow status.
- **Intelligent Reset** — the selected instance and task.
- **Sentry** — span usage, plan, spend, and reduction actions.
- **IR Studio / Mobile Assistant** — the selected Intelligent Reset task.

Agent Center shows the active evidence scope and changes its suggested questions
when the user switches tabs. It does not silently answer from another tab.

Examples:

- Why is Action Taken “-” on this task?
- How long did this reset take?
- What compliance did this task finish with?
- Are we ready to release?
- Which failures look flaky?

A question returns only the evidence that answers it. An unrelated question is
reported as not covered instead of a generic task report.

## Leadership reports and presentations

After an analysis finishes, Agent Center offers two editable downloads:

- **Download leadership report** creates a `.docx` briefing in the SymphonyAI
  retail format: Arial, sentence case, primary blue headings, and the executive
  summary, verdict, confidence, key metrics, findings, recommendations, sources,
  and agent run ID.
- **Download leadership PowerPoint** starts from the SymphonyAI 2026 template.
  It keeps the template layouts, logo, and footer, and fills a retail leadership
  narrative: question, decision, evidence, metrics, recommended actions, sources,
  and the template thank-you slide.

The export is generated from the completed grounded analysis. It does not make a
second unrelated analysis, invent metrics, upload data, or expose credentials and
signed URL query values. Generated files are written under `generated-reports/`,
which is excluded from source control.

All agents are read-only. They cannot update retailer tasks, create Jira issues,
start CI, modify source code, or approve a release.

## Available agents

### Intelligent Reset Investigation Agent

Uses the selected task's metadata, generated action list, Digital Shelf R07
rows, action-list states, compliance, and duration. It distinguishes:

- `Action Type = OK` and `Action Taken = "-"`: already correct; no action needed.
- non-OK Action Type and `Action Taken = "-"`: required action not confirmed.
- a real Action Taken value: recorded associate action.

### Release Risk Agent

Reads Web, iOS, Android, and API suite summaries plus the Jira summary. It
returns `ready`, `investigate`, or `hold` with the evidence behind the verdict.

### Failure Triage Agent

Classifies current top failures into likely product defects, flaky automation,
or environment issues. Classification is evidence-based and should be reviewed
before changing a Jira state.

### Automation Coverage Agent

Highlights suites where skipped and broken checks hide meaningful portions of
coverage.

### Flaky Test Agent

Finds locator, interaction, and instability indicators in current failure
records and recommends focused reruns and hardening.

### Test Execution Agent

Creates a risk-based execution plan from current failure areas. In this first
safe version it does not start CI automatically.

## Integration contract

- Catalog: `GET /api/runner/agents`
- Run: `POST /api/runner/agents/run`
- Export: `POST /api/runner/agents/export`

Example:

```json
{
  "question": "Why is Action Taken “-” on this task?",
  "active_tab": "ir",
  "instance": "harr",
  "task_id": 8900768
}
```

`agent_id` is still accepted for the original specialist reports. A `question`
takes precedence and returns `agent_id: "question"`.

Export example:

```json
{
  "format": "pptx",
  "run_id": "the run_id from /api/runner/agents/run"
}
```

The server resolves that run ID to the original grounded result. Client-supplied
analysis content is not accepted for exports.

The server collects evidence directly from the connected dashboard sources.
Tokens, passwords, and signed URLs are never included in agent results.

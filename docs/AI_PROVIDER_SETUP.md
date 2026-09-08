# AI Provider Setup Guide

The Test Case Creator supports two AI providers for generating BDD scenarios:

1. **Anthropic Claude** (Recommended - Default)
2. **OpenAI GPT** (Fallback Option)

---

## Quick Setup

### Option 1: Use Anthropic Claude (Recommended)

**Step 1: Get API Key**
```
1. Go to https://console.anthropic.com/
2. Click "API keys"
3. Create and copy your API key
```

**Step 2: Set Environment Variable**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

**Step 3: Run Generator**
```bash
python scripts/generate-test-cases.py
```

---

### Option 2: Use OpenAI (Alternative)

**Step 1: Get API Key**
```
1. Go to https://platform.openai.com/api-keys
2. Create and copy your API key
```

**Step 2: Set Environment Variable**
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
```

**Step 3: Set Model (GPT-4 recommended)**
```powershell
$env:GENERATION_MODEL = "gpt-4"
# Or use gpt-4-turbo-preview, gpt-3.5-turbo, etc.
```

**Step 4: Run Generator**
```bash
python scripts/generate-test-cases.py
```

---

## Provider Comparison

| Feature | Anthropic | OpenAI |
|---------|-----------|--------|
| **Model Quality** | Excellent | Excellent |
| **Cost** | $$$ | $$$ |
| **Speed** | Fast | Very Fast |
| **Context Window** | 200K | 128K (GPT-4) |
| **Best Model** | claude-3-5-sonnet | gpt-4 |
| **Fallback Support** | Primary | Yes ✅ |
| **Token Limit** | Higher | Standard |

---

## Environment Variables

### Anthropic Setup
```bash
ANTHROPIC_API_KEY=sk-ant-your-api-key-here
GENERATION_MODEL=claude-3-5-sonnet-20241022  # optional
```

### OpenAI Setup
```bash
OPENAI_API_KEY=sk-your-openai-key-here
GENERATION_MODEL=gpt-4  # or gpt-4-turbo-preview, gpt-3.5-turbo
```

### Both Providers (Fallback)
```bash
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
OPENAI_API_KEY=sk-your-openai-key-here
# Anthropic will be used first; OpenAI used if Anthropic key missing
```

---

## Recommended Models

### Anthropic Models
- **claude-3-5-sonnet-20241022** ⭐ (Default, best for BDD)
- claude-3-opus-20250219 (Most capable, slower)
- claude-3-haiku-20250307 (Faster, less capable)

### OpenAI Models
- **gpt-4** ⭐ (Best for BDD generation)
- gpt-4-turbo-preview (Similar quality, faster)
- gpt-3.5-turbo (Faster, lower quality for complex scenarios)

---

## Complete Setup Examples

### Example 1: Windows PowerShell with Claude
```powershell
# Set all required variables
$env:JIRA_BASE_URL = "https://company.atlassian.net"
$env:JIRA_USER_EMAIL = "you@company.com"
$env:JIRA_API_TOKEN = "your-jira-token"
$env:ANTHROPIC_API_KEY = "sk-ant-your-claude-key"

# Run generator
python scripts/generate-test-cases.py
```

### Example 2: Windows PowerShell with OpenAI
```powershell
# Set all required variables
$env:JIRA_BASE_URL = "https://company.atlassian.net"
$env:JIRA_USER_EMAIL = "you@company.com"
$env:JIRA_API_TOKEN = "your-jira-token"
$env:OPENAI_API_KEY = "sk-your-openai-key"
$env:GENERATION_MODEL = "gpt-4"

# Run generator
python scripts/generate-test-cases.py
```

### Example 3: .env File
```bash
# Copy from .env.example
cp .env.example .env

# Edit .env and set:
JIRA_BASE_URL=https://company.atlassian.net
JIRA_USER_EMAIL=you@company.com
JIRA_API_TOKEN=your-jira-token
ANTHROPIC_API_KEY=sk-ant-your-claude-key
# or
# OPENAI_API_KEY=sk-your-openai-key
```

---

## How Provider Selection Works

The generator automatically selects the best available AI provider:

```
1. Check if ANTHROPIC_API_KEY is set
   ├─ YES → Use Claude (Primary)
   └─ NO  → Check OpenAI

2. Check if OPENAI_API_KEY is set
   ├─ YES → Use OpenAI (Fallback)
   └─ NO  → Error: No API key found
```

---

## API Key Management

### Getting Anthropic API Key
```
1. Visit: https://console.anthropic.com/
2. Sign in with your account
3. Go to "API keys" section
4. Click "Create new secret key"
5. Copy the key (starts with sk-ant-)
6. Keep it secure - don't commit to git
```

### Getting OpenAI API Key
```
1. Visit: https://platform.openai.com/account/api-keys
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with sk-)
5. Set your billing/usage limits
6. Keep it secure - don't commit to git
```

---

## Troubleshooting

### "Missing required environment variables"
```
✗ Error: ANTHROPIC_API_KEY or OPENAI_API_KEY

→ Set at least one API key:
  $env:ANTHROPIC_API_KEY = "your-key"
  # OR
  $env:OPENAI_API_KEY = "your-key"
```

### "SDK not installed"
```
✗ Error: anthropic SDK not installed: pip install anthropic
✗ Error: openai SDK not installed: pip install openai

→ Install dependencies:
  pip install -r requirements.txt
```

### "API Authentication Failed"
```
✗ Error: 401 Unauthorized

→ Check your API key:
  - Is it correct?
  - Has it expired?
  - Do you have billing enabled (OpenAI)?
  - Check API key permissions
```

### "Rate Limited"
```
✗ Error: 429 Too Many Requests

→ Wait and retry, or:
  - Reduce MAX_ISSUES_PER_RUN
  - Use a less capable model (faster)
  - Add delay between requests
```

---

## Cost Comparison (Approximate)

### Anthropic Claude
- Input: ~$3 per 1M tokens
- Output: ~$15 per 1M tokens
- Average: ~$0.02 per 100 issues

### OpenAI GPT-4
- Input: ~$30 per 1M tokens
- Output: ~$60 per 1M tokens
- Average: ~$0.15 per 100 issues

**Claude is ~10x cheaper for BDD generation**

---

## Performance Comparison

| Provider | Speed | Quality | Cost |
|----------|-------|---------|------|
| Claude 3.5 Sonnet | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| GPT-4 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| GPT-4 Turbo | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| GPT-3.5 Turbo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## .env.example Template

```bash
# Jira Configuration
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_USER_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token-here

# AI Model Configuration (choose one)
# Option 1: Anthropic/Claude (recommended)
ANTHROPIC_API_KEY=sk-ant-your-api-key-here

# Option 2: OpenAI (fallback if ANTHROPIC_API_KEY not set)
# OPENAI_API_KEY=sk-your-openai-key-here

# Plugin Configuration
TEST_CASE_CREATOR_ENABLED=true
GENERATION_MODEL=claude-3-5-sonnet-20241022  # or gpt-4 for OpenAI
MAX_ISSUES_PER_RUN=50
MAX_ATTACHMENT_SIZE_MB=10

# Debugging
DEBUG=false
```

---

## Security Best Practices

✅ **DO:**
- Store API keys in `.env` file (gitignored)
- Use environment variables in production
- Rotate keys regularly
- Set API usage limits/quotas
- Use read-only keys when possible

❌ **DON'T:**
- Commit API keys to git
- Share API keys in messages/chat
- Use keys in frontend/client-side code
- Reuse keys across projects
- Leave keys in logs

---

## Next Steps

1. ✅ Choose your AI provider (Claude recommended)
2. ✅ Get your API key from the provider
3. ✅ Set the environment variable
4. ✅ Run the generator:
   ```bash
   python scripts/generate-test-cases.py
   ```
5. ✅ Check `data/test-cases.json` for results

---

## Support

For issues:
- **Anthropic:** https://support.anthropic.com/
- **OpenAI:** https://help.openai.com/
- **This Project:** Check GitHub issues or documentation

---

**Recommendation:** Use Claude 3.5 Sonnet (Anthropic) for best results! 🚀

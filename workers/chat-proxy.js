/**
 * Cloudflare Worker — GenAI chat proxy for the automation dashboard.
 * Uses the same Symphony gateway + OPENAI_KEY as retech-web-automation.
 *
 * Deploy:
 *   npx wrangler secret put OPENAI_KEY   # paste the same value as the GitHub secret
 *   npx wrangler deploy
 *
 * Then set data/genai-config.json → remoteProxyUrl to the worker URL.
 */

const API_BASE = 'https://ai-api.symphonyretailai.com';
const DEFAULT_MODEL = 'gpt-4.1';

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() },
  });
}

async function chat(env, messages, model) {
  const key = env.OPENAI_KEY;
  if (!key) {
    return json({
      ok: false,
      error: 'OPENAI_KEY secret is not set on this worker.',
    }, 502);
  }

  const payload = {
    model: model || DEFAULT_MODEL,
    messages,
    temperature: 0.2,
  };

  const res = await fetch(`${API_BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify(payload),
  });

  const text = await res.text();
  if (!res.ok) {
    return json({ ok: false, error: `GenAI HTTP ${res.status}: ${text.slice(0, 400)}` }, 502);
  }

  let body;
  try { body = JSON.parse(text); } catch {
    return json({ ok: false, error: 'Invalid GenAI JSON' }, 502);
  }

  const content = body?.choices?.[0]?.message?.content;
  if (!content) return json({ ok: false, error: 'Empty GenAI response', raw: body }, 502);
  return json({ ok: true, content, model: payload.model });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (url.pathname === '/api/chat/status' && request.method === 'GET') {
      return json({
        ok: true,
        genaiReady: Boolean(env.OPENAI_KEY),
        provider: 'symphony-openai',
        model: DEFAULT_MODEL,
        apiBase: API_BASE,
        keySource: env.OPENAI_KEY ? 'cloudflare-secret' : null,
      });
    }

    if (url.pathname === '/api/chat' && request.method === 'POST') {
      let data;
      try { data = await request.json(); } catch {
        return json({ ok: false, error: 'Invalid JSON body' }, 400);
      }
      if (!Array.isArray(data.messages) || !data.messages.length) {
        return json({ ok: false, error: 'messages[] required' }, 400);
      }
      return chat(env, data.messages, data.model);
    }

    return json({ ok: false, error: 'Not found' }, 404);
  },
};

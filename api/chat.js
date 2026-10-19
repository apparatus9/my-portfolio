// The contact page's chat, as a Vercel serverless function: POST /api/chat
//
// The page sends the conversation so far; this answers as Ejay's assistant and
// sends the reply back. The API key lives only here, in the ANTHROPIC_API_KEY
// environment variable set on the Vercel project. Never in the page.
//
// Guard rails: POST only, from this site's origins; a per-instance rate limit
// per visitor; short, validated conversations; short replies.

import Anthropic from '@anthropic-ai/sdk';

const MODEL = process.env.CONTACT_CHAT_MODEL || 'claude-opus-5-5';
const MAX_TURNS = 24;        // messages per conversation the page may send
const MAX_CHARS = 1500;      // per message
const MAX_OUTPUT = 400;      // tokens per reply: a few sentences, on purpose
const RATE = { max: 30, windowMs: 10 * 60 * 1000 };   // per visitor, per instance

// This site, its Vercel previews, and local dev. Browsers always send Origin on
// cross-site POSTs and on same-site fetches, so an unknown origin is refused.
const ALLOWED_ORIGIN = /^https:\/\/omada-portfolio(-[a-z0-9-]+)?\.vercel\.app$|^http:\/\/localhost(:\d+)?$/;

const SYSTEM = `You are the assistant on Ejay Adamo's contact page. You are not Ejay. If someone asks, say you're his assistant and that Ejay reads every email himself.

About Ejay: a web developer in Toronto, Canada. He builds websites and landing pages for local businesses, lead-capture forms, and full-stack web apps. Recent work includes a team page and deals pages for a Chrysler dealership, a gym sign-up redesign, and a festival registration form. He also does photography with a small shoot team, and marketing. His email is omada008@gmail.com; the button under this chat sends the conversation to him.

How to talk: plain, warm, honest, short. Two to four sentences at a time. Ask one question at a time. Say once, in a few words in your first reply, that you're Ejay's assistant; after that don't reintroduce yourself. Write in whatever language the visitor writes in.

What you're here to do: learn what they're trying to get done, what exists today (a site, a form, nothing), and roughly when they need it. Once you have those three, or if they'd rather just talk to Ejay, tell them to press the email button below, which sends this conversation to him.

Never invent prices, dates, or availability. If asked about cost, say Ejay quotes after he's read the details, and that he'll say honestly whether it's a fit. Don't promise he'll take the job. If someone asks about something unrelated to working with Ejay, answer in a sentence and steer back. If someone's rude or just testing, stay polite and brief.`;

const client = new Anthropic();   // reads ANTHROPIC_API_KEY

const buckets = new Map();
function limited(ip){
  const now = Date.now();
  let b = buckets.get(ip);
  if (!b || now > b.reset){ b = { count: 0, reset: now + RATE.windowMs }; buckets.set(ip, b); }
  b.count++;
  if (buckets.size > 5000) buckets.clear();   // never let a long-lived instance grow without bound
  return b.count > RATE.max;
}

function sanitize(input){
  if (!Array.isArray(input) || !input.length || input.length > MAX_TURNS) return null;
  const out = [];
  for (const m of input){
    if (!m || (m.role !== 'user' && m.role !== 'assistant') || typeof m.content !== 'string') return null;
    const content = m.content.trim();
    if (!content || content.length > MAX_CHARS) return null;
    out.push({ role: m.role, content });
  }
  if (out[0].role !== 'user' || out[out.length - 1].role !== 'user') return null;
  return out;
}

export default async function handler(req, res){
  res.setHeader('Cache-Control', 'no-store');
  if (req.method !== 'POST'){ res.setHeader('Allow', 'POST'); return res.status(405).json({ error: 'POST only' }); }
  const origin = req.headers.origin || '';
  if (!ALLOWED_ORIGIN.test(origin)) return res.status(403).json({ error: 'Forbidden' });
  if (!process.env.ANTHROPIC_API_KEY) return res.status(503).json({ error: 'Chat is not set up yet.' });

  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || req.socket?.remoteAddress || 'unknown';
  if (limited(ip)) return res.status(429).json({ error: "That's a lot of messages. Email Ejay directly and he'll pick it up." });

  let body = req.body;
  if (typeof body === 'string'){ try { body = JSON.parse(body); } catch { body = null; } }
  const messages = sanitize(body?.messages);
  if (!messages) return res.status(400).json({ error: 'Bad request' });

  try {
    const response = await client.beta.messages.create({
      model: MODEL,
      max_tokens: MAX_OUTPUT,
      betas: ['server-side-fallback-2026-07-01'],
      fallbacks: 'default',                       // a declined request is re-run on Anthropic's recommended model
      output_config: { effort: 'low' },           // chat: quick, plain replies
      system: [{ type: 'text', text: SYSTEM, cache_control: { type: 'ephemeral' } }],
      messages,
    });
    if (response.stop_reason === 'refusal'){
      return res.status(200).json({ reply: "That's not something I can help with here. Email Ejay directly and he'll take a look." });
    }
    const reply = response.content.filter(b => b.type === 'text').map(b => b.text).join('').trim();
    return res.status(200).json({ reply: reply || "Sorry, I lost my train of thought. Could you say that again?", truncated: response.stop_reason === 'max_tokens' });
  } catch (err){
    if (err instanceof Anthropic.RateLimitError) return res.status(429).json({ error: "I'm getting a lot of messages right now. Email Ejay directly." });
    if (err instanceof Anthropic.AuthenticationError){ console.error('chat: bad ANTHROPIC_API_KEY'); return res.status(503).json({ error: 'Chat is not set up yet.' }); }
    if (err instanceof Anthropic.APIError){ console.error('chat: API error', err.status, err.message); return res.status(502).json({ error: 'Chat is resting. Email Ejay directly.' }); }
    console.error('chat:', err);
    return res.status(500).json({ error: 'Chat is resting. Email Ejay directly.' });
  }
}

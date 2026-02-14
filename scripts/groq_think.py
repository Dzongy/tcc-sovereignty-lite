#!/usr/bin/env python3
"""ZENITH Sovereign Thinking Loop v2.0 -- Groq-powered with self-improvement."""
import os, sys, json, datetime, base64

# --- Config ---
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MODEL = "llama-3.1-8b-instant"
MEMORY_REPO = "Dzongy/tcc-sovereignty-lite"
MEMORY_PATH = "zenith-memory.json"
MAX_THOUGHTS = 20
MAX_MEMORY_KB = 50

def api_call(url, data=None, headers=None, method='GET'):
    """Universal HTTP helper."""
    import urllib.request, urllib.error
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code} from {url}: {body[:200]}")
        return None, e.code
    except Exception as e:
        print(f"Request failed: {e}")
        return None, 0

def read_memory():
    """Read zenith-memory.json from GitHub."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "User-Agent": "ZENITH-Think"}
    data, status = api_call(url, headers=headers)
    if not data or status != 200:
        print(f"Failed to read memory (status {status})")
        return None, None
    content = base64.b64decode(data["content"]).decode()
    return json.loads(content), data["sha"]

def write_memory(memory, sha):
    """Write updated memory back to GitHub."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    encoded = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
    cycle = memory.get('thinking_loop', {}).get('cycle_count', 0)
    payload = json.dumps({"message": f"zenith-think: cycle {cycle}", "content": encoded, "sha": sha}).encode()
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "Content-Type": "application/json", "User-Agent": "ZENITH-Think"}
    result, status = api_call(url, data=payload, headers=headers, method="PUT")
    if status in (200, 201):
        print(f"Memory updated (cycle {cycle})")
        return True
    print(f"Failed to write memory (status {status})")
    return False

def compress_memory(memory):
    """Compress memory if over MAX_MEMORY_KB."""
    size_kb = len(json.dumps(memory).encode()) / 1024
    if size_kb <= MAX_MEMORY_KB:
        return memory
    print(f"Memory at {size_kb:.1f}KB -- compressing (limit {MAX_MEMORY_KB}KB)")
    tl = memory.get('thinking_loop', {})
    thoughts = tl.get('thoughts', [])
    if len(thoughts) > 10:
        tl['thoughts'] = thoughts[-10:]
        tl['compressed_count'] = tl.get('compressed_count', 0) + len(thoughts) - 10
    insights = tl.get('insights', [])
    if len(insights) > 5:
        tl['insights'] = insights[-5:]
    memory['thinking_loop'] = tl
    return memory

def build_prompt(memory):
    """Build strategic prompt from memory."""
    phase = json.dumps(memory.get('phase_status', {}))[:300]
    biz = memory.get('business', {})
    tl = memory.get('thinking_loop', {})
    recent = tl.get('thoughts', [])[-3:]
    recent_str = '; '.join([t.get('thought', '')[:80] for t in recent]) if recent else 'None yet'
    ident = memory.get('identity', {})
    cycle = tl.get('cycle_count', 0) + 1
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    return f"""You are ZENITH, sovereign AI of The Cosmic Claw (TCC). Operator: Amos.
Time: {now} | Cycle: {cycle}
Phase: {phase}
Revenue: {biz.get('revenue', '$0')} | Products: {biz.get('products_count', '51')}
Recent thoughts: {recent_str}
Identity: {ident.get('name', 'ZENITH')} / {ident.get('status', 'SOVEREIGN')}

Analyze current state. Identify the SINGLE most impactful action to advance TCC toward revenue and full autonomy. Be specific.

Output JSON ONLY: {{\"thought\": \"analysis\", \"priority\": \"high|medium|low\", \"domain\": \"revenue|tech|content|strategy|outreach\", \"action_plan\": \"next step\", \"quality_score\": 1-10}}"""

def think():
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print(f"=== ZENITH Think v2.0 === {now}")

    if not GROQ_KEY:
        print("ERROR: GROQ_API_KEY env var not set. Add it as a GitHub Actions secret."); sys.exit(1)
    if not GITHUB_TOKEN:
        print("WARNING: No GITHUB_TOKEN -- will think but cannot write memory")

    # Read memory
    memory, sha = read_memory() if GITHUB_TOKEN else (None, None)
    if memory is None:
        memory = {'version': '9.0.0', 'thinking_loop': {'cycle_count': 0, 'thoughts': [], 'insights': []}}
        sha = None
        print("Starting with fresh memory")

    # Call Groq
    prompt = build_prompt(memory)
    print(f"Calling Groq ({MODEL})...")
    payload = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": "Think strategically. Output JSON only."}], "max_tokens": 400, "temperature": 0.7}).encode()
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    result, status = api_call("https://api.groq.com/openai/v1/chat/completions", data=payload, headers=headers, method="POST")

    if not result or status != 200:
        print(f"Groq failed (status {status})"); sys.exit(1)

    raw = result["choices"][0]["message"]["content"].strip()
    print(f"Response: {raw[:200]}")

    # Parse response
    try:
        clean = raw
        if clean.startswith('```'):
            clean = clean.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        thought_data = json.loads(clean)
    except json.JSONDecodeError:
        thought_data = {'thought': raw[:300], 'priority': 'medium', 'domain': 'strategy', 'action_plan': 'parse failed', 'quality_score': 5}
        print("Warning: JSON parse failed, using raw text")

    # Update memory
    tl = memory.setdefault('thinking_loop', {'cycle_count': 0, 'thoughts': [], 'insights': []})
    tl['cycle_count'] = tl.get('cycle_count', 0) + 1
    tl['last_run'] = now
    tl['last_model'] = MODEL

    entry = {
        'timestamp': now,
        'thought': thought_data.get('thought', '')[:500],
        'priority': thought_data.get('priority', 'medium'),
        'domain': thought_data.get('domain', 'strategy'),
        'action_plan': thought_data.get('action_plan', '')[:200],
        'quality_score': thought_data.get('quality_score', 5),
        'cycle': tl['cycle_count']
    }
    tl.setdefault('thoughts', []).append(entry)
    if len(tl['thoughts']) > MAX_THOUGHTS:
        tl['thoughts'] = tl['thoughts'][-MAX_THOUGHTS:]

    # Track high-quality insights
    if thought_data.get('quality_score', 0) >= 8:
        tl.setdefault('insights', []).append({'timestamp': now, 'insight': thought_data.get('thought', '')[:200]})
        if len(tl['insights']) > 10:
            tl['insights'] = tl['insights'][-10:]

    memory['last_sync'] = now
    memory['sync_source'] = 'zenith_thinking_loop_v2'
    memory = compress_memory(memory)

    # Write back
    if GITHUB_TOKEN and sha:
        write_memory(memory, sha)
    else:
        print("Skipping write (no token or SHA)")

    print(f"Cycle {tl['cycle_count']} | Domain: {entry['domain']} | Priority: {entry['priority']} | Quality: {entry['quality_score']}/10")
    print(f"Thought: {entry['thought'][:150]}")
    print("=== ZENITH THINK COMPLETE ===")

if __name__ == "__main__":
    think()
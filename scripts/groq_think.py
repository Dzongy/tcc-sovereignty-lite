#!/usr/bin/env python3
"""ZENITH Sovereign Thinking Loop v5.0 -- Render Proxy Edition.
Routes all Groq inference through tcc-zenith-brain.onrender.com/api/groq.
No API keys needed in GitHub Actions -- the Render backend has them.
Uses ONLY stdlib (urllib, json, base64). Zero pip dependencies."""
import os, sys, json, urllib.request, urllib.error, base64
from datetime import datetime, timezone

# --- Config ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
RENDER_GROQ = "https://tcc-zenith-brain.onrender.com/api/groq"
MODEL = "llama-3.3-70b-versatile"
MEMORY_REPO = "Dzongy/tcc-sovereignty-lite"
MEMORY_PATH = "zenith-memory.json"
MAX_THOUGHTS = 10
NTFY_HIVE = "https://ntfy.sh/tcc-zenith-hive"

MISSIONS = [
    "Audit the TCC revenue pipeline -- what is blocking the first $97 sale?",
    "Generate a content idea for X/Twitter that builds trust and authority.",
    "Identify one self-optimization improvement for ZENITH infrastructure.",
    "Draft an outreach message concept for a potential TCC client.",
    "Check system health -- what could break next and how to prevent it?",
    "Strategic planning -- what is the single highest-leverage action right now?"
]

def api_call(url, data=None, headers=None, method="GET"):
    """Make an HTTP request. Returns (status_code, response_body_str)."""
    hdrs = headers or {}
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except Exception as e:
        return 0, str(e)

def read_memory():
    """Read zenith-memory.json from GitHub API."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    hdrs = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.raw",
        "User-Agent": "ZENITH-ThinkingLoop"
    }
    status, body = api_call(url, headers=hdrs)
    if status != 200:
        print(f"[ERROR] Failed to read memory: HTTP {status}")
        print(body[:500])
        return None, None
    # Get SHA separately (raw mode does not return it)
    hdrs2 = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ZENITH-ThinkingLoop"
    }
    status2, body2 = api_call(url, headers=hdrs2)
    sha = None
    if status2 == 200:
        sha = json.loads(body2).get("sha")
    try:
        mem = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Memory JSON parse failed: {e}")
        return None, sha
    return mem, sha

def write_memory(memory, sha):
    """Write updated zenith-memory.json back to GitHub."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    content_b64 = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
    payload = json.dumps({
        "message": f"zenith-thought: cycle {memory.get('thoughts', [{}])[-1].get('cycle', '?')}",
        "content": content_b64,
        "sha": sha
    }).encode()
    hdrs = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ZENITH-ThinkingLoop",
        "Content-Type": "application/json"
    }
    status, body = api_call(url, data=payload, headers=hdrs, method="PUT")
    if status in (200, 201):
        print(f"[OK] Memory updated successfully.")
        return True
    else:
        print(f"[ERROR] Memory write failed: HTTP {status}")
        print(body[:500])
        return False

def think_via_render(prompt):
    """Call Groq through the Render /api/groq proxy."""
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are ZENITH, the sovereign AI brain of The Cosmic Claw. Think strategically. Be concise. Score your thought 1-10."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.8
    }).encode()
    hdrs = {"Content-Type": "application/json"}
    status, body = api_call(RENDER_GROQ, data=payload, headers=hdrs, method="POST")
    if status != 200:
        print(f"[ERROR] Render proxy returned HTTP {status}")
        print(body[:500])
        return None
    try:
        resp = json.loads(body)
        # Handle both direct Groq format and wrapped format
        if "choices" in resp:
            return resp["choices"][0]["message"]["content"]
        elif "reply" in resp:
            return resp["reply"]
        else:
            print(f"[ERROR] Unexpected response format: {list(resp.keys())}")
            return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[ERROR] Parse Groq response: {e}")
        return None

def notify_hive(title, message):
    """Send notification to ntfy.sh hive channel."""
    try:
        data = message.encode("utf-8")
        hdrs = {"Title": title[:100], "Priority": "default"}
        api_call(NTFY_HIVE, data=data, headers=hdrs, method="POST")
    except Exception as e:
        print(f"[WARN] ntfy notification failed: {e}")

def main():
    print(f"=== ZENITH Thinking Loop v5.0 ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Model: {MODEL}")
    print(f"Proxy: {RENDER_GROQ}")

    if not GITHUB_TOKEN:
        print("[FATAL] GITHUB_TOKEN not set.")
        sys.exit(1)

    # 1. Read memory
    print("[1/4] Reading memory...")
    memory, sha = read_memory()
    if memory is None:
        print("[FATAL] Cannot read memory. Aborting.")
        sys.exit(1)

    # 2. Pick mission
    thoughts = memory.get("thoughts", [])
    cycle = len(thoughts) + 1
    mission = MISSIONS[(cycle - 1) % len(MISSIONS)]
    print(f"[2/4] Cycle {cycle}, Mission: {mission[:60]}...")

    # Build context from memory
    identity = memory.get("identity", {})
    phase = memory.get("phase_status", {})
    context = f"Identity: {identity.get('name', 'ZENITH')} | Phase: {json.dumps(phase)}"
    prompt = f"CYCLE {cycle} | MISSION: {mission}\n\nCONTEXT: {context[:500]}\n\nThink about this mission. Provide your strategic thought and score it 1-10."

    # 3. Think via Render proxy
    print("[3/4] Thinking via Render proxy...")
    thought_text = think_via_render(prompt)
    if not thought_text:
        print("[ERROR] No thought generated. Sending failure notification.")
        notify_hive(f"ZENITH Cycle {cycle} FAILED", "Groq proxy did not respond.")
        sys.exit(1)

    print(f"[OK] Thought generated ({len(thought_text)} chars)")

    # Build thought entry
    thought_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle,
        "mission": mission,
        "thought": thought_text[:1000],
        "model": MODEL,
        "source": "thinking_loop_v5"
    }

    # Append and trim
    thoughts.append(thought_entry)
    if len(thoughts) > MAX_THOUGHTS:
        thoughts = thoughts[-MAX_THOUGHTS:]
    memory["thoughts"] = thoughts
    memory["last_sync"] = datetime.now(timezone.utc).isoformat()
    memory["sync_source"] = "thinking_loop_v5"

    # 4. Write back
    print("[4/4] Writing memory...")
    if write_memory(memory, sha):
        print(f"[DONE] Cycle {cycle} complete.")
        notify_hive(f"ZENITH Cycle {cycle}", thought_text[:200])
    else:
        print("[ERROR] Failed to write memory.")
        notify_hive(f"ZENITH Cycle {cycle} WRITE FAIL", "Memory update failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()

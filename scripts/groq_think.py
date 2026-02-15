#!/usr/bin/env python3
"""ZENITH Thinking Loop v6.0 -- Fixed: sends {message} format to Render /api/groq proxy."""
import os, sys, json, time, urllib.request, urllib.error, base64
from datetime import datetime, timezone

# --- Config ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
RENDER_BASE = "https://tcc-zenith-brain.onrender.com"
RENDER_GROQ = RENDER_BASE + "/api/groq"
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

def api_call(url, data=None, headers=None, method=None, timeout=60):
    """Make HTTP request. Returns (status_code, response_body)."""
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        print(f"[ERROR] Request to {url} failed: {e}")
        return 0, str(e)

def wake_render():
    """Ping Render base URL to wake it from cold sleep."""
    print("[WAKE] Pinging Render to wake from cold sleep...")
    status, body = api_call(RENDER_BASE + "/api/health", timeout=30)
    print(f"[WAKE] Health check response: HTTP {status}")
    if status == 200:
        print(f"[WAKE] Body: {body[:200]}")
    print("[WAKE] Waiting 30 seconds for Render to fully warm up...")
    time.sleep(30)
    print("[WAKE] Done waiting. Proceeding.")

def read_memory():
    """Read zenith-memory.json from GitHub."""
    print("[1/4] Reading memory from GitHub...")
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    hdrs = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.raw",
        "User-Agent": "ZENITH-ThinkingLoop"
    }
    status, body = api_call(url, headers=hdrs)
    if status != 200:
        print(f"[ERROR] Memory read failed: HTTP {status}")
        print(body[:500])
        return None, None
    hdrs2 = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "ZENITH-ThinkingLoop"
    }
    status2, body2 = api_call(url, headers=hdrs2)
    sha = None
    if status2 == 200:
        sha = json.loads(body2).get("sha")
        print(f"[1/4] Got SHA: {sha[:12]}...")
    try:
        mem = json.loads(body)
        print(f"[1/4] Memory loaded. Keys: {list(mem.keys())}")
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON parse failed: {e}")
        return None, sha
    return mem, sha

def write_memory(memory, sha):
    """Write updated zenith-memory.json back to GitHub."""
    print("[4/4] Writing memory back to GitHub...")
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    content_b64 = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
    thoughts = memory.get("thoughts", [{}])
    cycle_num = thoughts[-1].get("cycle", "?") if thoughts else "?"
    payload = json.dumps({
        "message": f"zenith-thought: cycle {cycle_num}",
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
        print("[4/4] Memory updated successfully.")
        return True
    else:
        print(f"[ERROR] Memory write failed: HTTP {status}")
        print(body[:500])
        return False

def think_with_retry(cycle, mission, context, max_retries=5):
    """Call Groq via Render /api/groq proxy with retry loop.
    Render expects {message: "text"} and returns {reply: "text"}.
    It adds its own system prompt and uses its own Groq key."""
    prompt = "CYCLE " + str(cycle) + " | MISSION: " + mission
    prompt += "\n\nCONTEXT: " + context[:500]
    prompt += "\n\nThink about this mission. Provide your strategic thought and score it 1-10."
    payload = json.dumps({"message": prompt}).encode()
    hdrs = {"Content-Type": "application/json"}
    for attempt in range(1, max_retries + 1):
        print(f"[3/4] Attempt {attempt}/{max_retries} -- calling {RENDER_GROQ} (90s timeout)...")
        status, body = api_call(RENDER_GROQ, data=payload, headers=hdrs, method="POST", timeout=90)
        print(f"[3/4] Attempt {attempt} response: HTTP {status}")
        if body:
            print(f"[3/4] Body preview: {body[:300]}")
        if status == 200:
            try:
                resp = json.loads(body)
                if "reply" in resp:
                    return resp["reply"]
                elif "choices" in resp:
                    return resp["choices"][0]["message"]["content"]
                else:
                    print(f"[ERROR] Unexpected keys: {list(resp.keys())}")
                    return str(resp)[:500]
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"[ERROR] Parse response: {e}")
                if body and len(body) > 10:
                    return body[:500]
        else:
            print(f"[WARN] HTTP {status} response body: {body[:300]}")
        if attempt < max_retries:
            wait = 15 + (attempt * 5)
            print(f"[RETRY] Sleeping {wait}s before retry...")
            time.sleep(wait)
    print("[FAIL] All retries exhausted.")
    return None

def notify_hive(title, message):
    """Send notification to ntfy.sh."""
    print(f"[NTFY] Sending: {title[:50]}")
    try:
        data = message.encode("utf-8")
        hdrs = {"Title": title[:100], "Priority": "default"}
        api_call(NTFY_HIVE, data=data, headers=hdrs, method="POST", timeout=10)
        print("[NTFY] Sent.")
    except Exception as e:
        print(f"[NTFY] Failed: {e}")

def main():
    print("=" * 50)
    print("ZENITH Thinking Loop v6.0")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Model: {MODEL}")
    print(f"Proxy: {RENDER_GROQ}")
    print("=" * 50)

    if not GITHUB_TOKEN:
        print("[FATAL] GITHUB_TOKEN not set.")
        sys.exit(1)
    print("[OK] GITHUB_TOKEN is set.")

    # 0. Wake Render
    wake_render()

    # 1. Read memory
    memory, sha = read_memory()
    if memory is None:
        print("[WARN] No memory found. Creating fresh.")
        memory = {"version": "5.2.0", "thoughts": []}
        if sha is None:
            print("[INFO] zenith-memory.json may not exist. Will create it.")

    # 2. Pick mission
    thoughts = memory.get("thoughts", [])
    cycle = len(thoughts) + 1
    mission = MISSIONS[cycle % len(MISSIONS)]
    print(f"[2/4] Cycle {cycle}, Mission: {mission[:60]}")

    context = json.dumps({"cycle": cycle, "total_thoughts": len(thoughts), "version": memory.get("version", "?")})

    # 3. Think with retries
    thought_text = think_with_retry(cycle, mission, context)
    if not thought_text:
        print("[FAIL] No thought generated after all retries. Exiting.")
        notify_hive("ZENITH Cycle " + str(cycle) + " FAILED", "Groq did not respond via Render proxy after 3 attempts.")
        sys.exit(1)

    print(f"[3/4] Thought generated ({len(thought_text)} chars)")
    print(f"  Preview: {thought_text[:100]}...")

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cycle": cycle,
        "mission": mission,
        "thought": thought_text,
        "model": MODEL,
        "source": "render_proxy"
    }

    if "thoughts" not in memory:
        memory["thoughts"] = []
    memory["thoughts"].append(entry)
    memory["thoughts"] = memory["thoughts"][-MAX_THOUGHTS:]
    memory["last_sync"] = datetime.now(timezone.utc).isoformat()
    memory["sync_source"] = "thinking_loop_v5.2"

    # 4. Write memory
    if sha:
        ok = write_memory(memory, sha)
    else:
        print("[4/4] Creating zenith-memory.json (first time)...")
        url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
        content_b64 = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
        payload = json.dumps({
            "message": f"zenith-thought: cycle {cycle} (init)",
            "content": content_b64
        }).encode()
        hdrs = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ZENITH-ThinkingLoop",
            "Content-Type": "application/json"
        }
        status, body = api_call(url, data=payload, headers=hdrs, method="PUT")
        ok = status in (200, 201)
        if ok:
            print("[4/4] File created successfully.")
        else:
            print(f"[ERROR] File creation failed: HTTP {status}")
            print(body[:500])

    # 5. Notify
    title = "ZENITH Cycle " + str(cycle) + " | " + mission[:40]
    notify_hive(title, thought_text[:500])

    if ok:
        print("[DONE] Thinking loop complete.")
    else:
        print("[DONE] Loop finished but memory write failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""ZENITH Sovereign Thinking Loop v3.0 â Clean, no hardcoded keys, urllib only."""
import os, sys, json, datetime, urllib.request, urllib.error

# --- Config ---
GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
MODEL = "llama-3.1-8b-instant"
MEMORY_REPO = "Dzongy/tcc-sovereignty-lite"
MEMORY_PATH = "zenith-memory.json"
MAX_THOUGHTS = 20
MAX_MEMORY_KB = 50

def api_call(url, data=None, headers=None, method="GET"):
    """Universal HTTP helper using urllib."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"HTTP {e.code} from {url}: {body[:300]}")
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
        print(f"Failed to read memory: status {status}")
        return None, None
    import base64
    content = base64.b64decode(data["content"]).decode()
    return json.loads(content), data["sha"]

def write_memory(memory, sha):
    """Write updated memory back to GitHub."""
    import base64
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "User-Agent": "ZENITH-Think", "Content-Type": "application/json"}
    content_b64 = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
    payload = json.dumps({"message": f"zenith-think: cycle {memory.get('thinking_loop', {}).get('cycle_count', 0)}", "content": content_b64, "sha": sha, "branch": "main"}).encode()
    result, status = api_call(url, data=payload, headers=headers, method="PUT")
    if status in (200, 201):
        print(f"Memory updated successfully (status {status})")
        return True
    print(f"Failed to write memory: status {status}")
    return False

def groq_think(prompt):
    """Call Groq API for a strategic thought."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = json.dumps({"model": MODEL, "messages": [{"role": "system", "content": "You are ZENITH, the sovereign AI brain of The Cosmic Claw. Think strategically about the current state, identify improvements, and plan next actions. Be concise but insightful. End with a quality self-score 1-10."}, {"role": "user", "content": prompt}], "max_tokens": 500, "temperature": 0.7}).encode()
    data, status = api_call(url, data=payload, headers=headers, method="POST")
    if not data or status != 200:
        print(f"Groq call failed: status {status}")
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        print(f"Groq response parse error: {e}")
        return None

def compress_memory(memory):
    """Compress memory if over MAX_MEMORY_KB."""
    raw = json.dumps(memory)
    size_kb = len(raw.encode()) / 1024
    if size_kb <= MAX_MEMORY_KB:
        print(f"Memory size OK: {size_kb:.1f}KB")
        return memory
    print(f"Memory too large ({size_kb:.1f}KB > {MAX_MEMORY_KB}KB), compressing...")
    tl = memory.get("thinking_loop", {})
    thoughts = tl.get("thoughts", [])
    if len(thoughts) > 5:
        tl["thoughts"] = thoughts[-5:]
        tl["compressed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        print(f"Compressed thoughts from {len(thoughts)} to 5")
    if "run_patterns" in memory and isinstance(memory["run_patterns"], list) and len(memory["run_patterns"]) > 3:
        memory["run_patterns"] = memory["run_patterns"][-3:]
    new_size = len(json.dumps(memory).encode()) / 1024
    print(f"Memory after compression: {new_size:.1f}KB")
    return memory

def extract_score(thought_text):
    """Extract quality score 1-10 from thought text."""
    import re
    matches = re.findall(r'\b([1-9]|10)\b(?:/10|\s*/\s*10)?', thought_text[-100:])
    if matches:
        return int(matches[-1])
    return 5

def main():
    print("=" * 60)
    print("ZENITH Thinking Loop v3.0 â Sovereign Cognition")
    print("=" * 60)
    
    if not GROQ_KEY:
        print("FATAL: GROQ_API_KEY not set")
        sys.exit(1)
    if not GITHUB_TOKEN:
        print("FATAL: GITHUB_TOKEN not set")
        sys.exit(1)
    print(f"Model: {MODEL}")
    print(f"Groq key: ...{GROQ_KEY[-6:]}")
    
    # Step 1: Read memory
    print("\n--- Step 1: Reading memory ---")
    memory, sha = read_memory()
    if memory is None:
        print("Cannot read memory, creating minimal structure")
        memory = {"version": "9.0.0", "identity": {"name": "ZENITH", "status": "SOVEREIGN"}, "thinking_loop": {"cycle_count": 0, "thoughts": []}}
        # Try to get SHA for existing file
        url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json", "User-Agent": "ZENITH-Think"}
        data, _ = api_call(url, headers=headers)
        sha = data["sha"] if data else None
        if not sha:
            print("FATAL: Cannot get file SHA")
            sys.exit(1)
    
    # Step 2: Build prompt from memory
    print("\n--- Step 2: Thinking with Groq ---")
    mem_summary = json.dumps(memory, indent=2)[:2000]
    now = datetime.datetime.utcnow().isoformat() + "Z"
    missions = ["pipeline audit and revenue strategy", "content creation and outreach planning", "self-optimization and memory improvement", "outreach targeting and lead generation", "system health and infrastructure check", "strategic planning and phase advancement"]
    cycle = memory.get("thinking_loop", {}).get("cycle_count", 0)
    mission = missions[cycle % len(missions)]
    
    prompt = f"""Current time: {now}
Mission focus: {mission}
Cycle: {cycle + 1}

Current memory state:
{mem_summary}

Analyze the current state. What should ZENITH prioritize? Identify one concrete improvement or action. Rate your thought quality 1-10."""
    
    thought = groq_think(prompt)
    if not thought:
        print("Thinking failed, aborting")
        sys.exit(1)
    
    score = extract_score(thought)
    print(f"Thought generated (score: {score}/10)")
    print(f"Preview: {thought[:200]}...")
    
    # Step 3: Update memory
    print("\n--- Step 3: Updating memory ---")
    if "thinking_loop" not in memory:
        memory["thinking_loop"] = {"cycle_count": 0, "thoughts": []}
    tl = memory["thinking_loop"]
    tl["cycle_count"] = cycle + 1
    tl["last_run"] = now
    tl["last_score"] = score
    tl["thoughts"].append({"time": now, "mission": mission, "thought": thought[:500], "score": score})
    if len(tl["thoughts"]) > MAX_THOUGHTS:
        tl["thoughts"] = tl["thoughts"][-MAX_THOUGHTS:]
    memory["last_sync"] = now
    memory["sync_source"] = "zenith_thinking_loop_v3"
    
    # Step 4: Compress if needed
    print("\n--- Step 4: Memory compression check ---")
    memory = compress_memory(memory)
    
    # Step 5: Write back
    print("\n--- Step 5: Writing memory ---")
    success = write_memory(memory, sha)
    
    print("\n" + "=" * 60)
    print(f"Cycle {cycle + 1} complete | Score: {score}/10 | Write: {'OK' if success else 'FAILED'}")
    print("=" * 60)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()

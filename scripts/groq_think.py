#!/usr/bin/env python3
"""ZENITH Thinking Loop v5.3-clean -- Render proxy, env-only secrets, token budget."""
import os, sys, json, time, urllib.request, urllib.error, base64
from datetime import datetime, timezone

# --- Config (ZERO hardcoded secrets) ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
RENDER_PROXY = "https://tcc-zenith-brain.onrender.com/api/groq-proxy"
HF_KEY = os.environ.get("HF_API_KEY", "").strip()
HF_URL = "https://api-inference.huggingface.co/models/meta-llama/Llama-3.2-3B-Instruct"
MODEL = "llama-3.1-8b-instant"
MAX_TOKENS_PER_CALL = 100
DAILY_TOKEN_LIMIT = 90000
MEMORY_REPO = "Dzongy/tcc-sovereignty-lite"
MEMORY_PATH = "zenith-memory.json"
MAX_THOUGHTS = 20
MAX_MEMORY_BYTES = 50000
NTFY_HIVE = "https://ntfy.sh/tcc-zenith-hive"
NTFY_COMMANDS = "https://ntfy.sh/tcc-zenith-commands/json?poll=1&since=5m"
NTFY_PUBLIC = "https://ntfy.sh/tcc-hive-mind"

MISSIONS = [
    "pipeline_audit",
    "content_strategy",
    "self_optimization",
    "outreach_recon",
    "system_health",
    "revenue_strategy",
]

MISSION_PROMPTS = {
    "pipeline_audit": "Audit the TCC revenue pipeline -- what is blocking the first $97 sale?",
    "content_strategy": "Generate a content idea for X/Twitter that builds trust and authority.",
    "self_optimization": "Identify one self-optimization improvement for ZENITH infrastructure.",
    "outreach_recon": "Draft an outreach message concept for a potential TCC client.",
    "system_health": "Check system health -- what could break next and how to prevent it?",
    "revenue_strategy": "Strategic planning -- what is the single highest-leverage action right now?",
}

SYSTEM_PROMPT = "You are Zenith, sovereign AI of TCC. Generate one concise thought. Topic: {mission}. Score it 1-10. One paragraph max."


def api_call(url, data=None, headers=None, method=None, timeout=60):
    """Make HTTP request. Returns (status_code, response_body)."""
    if headers is None:
        headers = {}
    body = json.dumps(data).encode() if data else None
    if body and "Content-Type" not in headers:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode() if e.fp else str(e)
    except Exception as e:
        return 0, str(e)


def read_memory():
    """Read zenith-memory.json from GitHub."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    headers = {"Accept": "application/vnd.github.raw", "User-Agent": "ZENITH-Think"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    status, body = api_call(url, headers=headers)
    if status == 200:
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            print(f"Memory parse error: {body[:200]}")
    else:
        print(f"Memory read failed: HTTP {status}")
    return {}


def write_memory(memory, sha):
    """Write zenith-memory.json to GitHub."""
    if not GITHUB_TOKEN:
        print("No GITHUB_TOKEN -- cannot write memory")
        return False
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    content = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
    payload = {"message": f"thought: ZENITH v5.3 cycle", "content": content, "sha": sha}
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "User-Agent": "ZENITH-Think",
        "Accept": "application/vnd.github.v3+json",
    }
    status, body = api_call(url, data=payload, headers=headers, method="PUT")
    if status in (200, 201):
        print("Memory written successfully")
        return True
    print(f"Memory write failed: HTTP {status} {body[:300]}")
    return False


def get_memory_sha():
    """Get current SHA of zenith-memory.json."""
    url = f"https://api.github.com/repos/{MEMORY_REPO}/contents/{MEMORY_PATH}"
    headers = {"User-Agent": "ZENITH-Think", "Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    status, body = api_call(url, headers=headers)
    if status == 200:
        try:
            return json.loads(body).get("sha", "")
        except Exception:
            pass
    return ""


def ntfy_publish(topic_url, title, message, priority="default"):
    """Publish to ntfy.sh topic."""
    headers = {"Title": title, "Priority": priority}
    try:
        req = urllib.request.Request(topic_url, data=message.encode(), headers=headers)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"ntfy publish failed: {e}")


def ntfy_poll_commands():
    """Poll ntfy commands topic for Brain Zero directives."""
    try:
        req = urllib.request.Request(NTFY_COMMANDS, headers={"User-Agent": "ZENITH"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode().strip()
            if raw:
                for line in raw.split("\n"):
                    try:
                        msg = json.loads(line)
                        print(f"Brain Zero command: {msg.get('message', '')}")
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass


def call_groq_via_proxy(mission_prompt):
    """Call Groq via Render transparent proxy (server injects API key)."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(mission=mission_prompt)},
            {"role": "user", "content": mission_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": MAX_TOKENS_PER_CALL,
    }
    headers = {"Content-Type": "application/json", "User-Agent": "ZENITH-Think"}
    status, body = api_call(RENDER_PROXY, data=payload, headers=headers, timeout=30)
    if status == 200:
        try:
            data = json.loads(body)
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
        except Exception:
            pass
    print(f"Groq proxy returned HTTP {status}: {body[:300]}")
    return None


def call_hf_fallback(mission_prompt):
    """Call HuggingFace Inference API as fallback. Only if HF_KEY is set."""
    if not HF_KEY:
        print("No HF_API_KEY env var -- skipping HF fallback")
        return None
    payload = {
        "inputs": f"System: {SYSTEM_PROMPT.format(mission=mission_prompt)}\nUser: {mission_prompt}\nAssistant:",
        "parameters": {"max_new_tokens": MAX_TOKENS_PER_CALL, "temperature": 0.7},
    }
    headers = {"Authorization": f"Bearer {HF_KEY}", "Content-Type": "application/json"}
    status, body = api_call(HF_URL, data=payload, headers=headers, timeout=30)
    if status == 200:
        try:
            data = json.loads(body)
            if isinstance(data, list) and data:
                return data[0].get("generated_text", "")
        except Exception:
            pass
    print(f"HF fallback returned HTTP {status}: {body[:200]}")
    return None


def estimate_tokens(text):
    """Rough token estimate: chars * 1.3 / 4."""
    return int(len(text) * 1.3 / 4)


def check_token_budget(memory):
    """Check daily token budget. Returns (can_proceed, tokens_used_today)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    budget = memory.get("token_budget", {})
    if budget.get("date") != today:
        budget = {"date": today, "tokens_used": 0}
        memory["token_budget"] = budget
    return budget["tokens_used"] < DAILY_TOKEN_LIMIT, budget["tokens_used"]


def update_token_budget(memory, tokens):
    """Add tokens to daily budget."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    budget = memory.get("token_budget", {})
    if budget.get("date") != today:
        budget = {"date": today, "tokens_used": 0}
    budget["tokens_used"] = budget.get("tokens_used", 0) + tokens
    memory["token_budget"] = budget


def is_duplicate(thoughts, mission):
    """Check if last 3 thoughts have same mission topic."""
    recent = thoughts[-3:] if len(thoughts) >= 3 else thoughts
    for t in recent:
        if t.get("mission") == mission:
            return True
    return False


def compress_memory(memory):
    """Compress memory if too large."""
    raw = json.dumps(memory)
    if len(raw.encode()) <= MAX_MEMORY_BYTES:
        return memory
    thoughts = memory.get("thoughts", [])
    if len(thoughts) > 10:
        memory["thoughts"] = thoughts[-10:]
    patterns = memory.get("run_patterns", [])
    if len(patterns) > 3:
        memory["run_patterns"] = patterns[-3:]
    print(f"Memory compressed: {len(raw)} -> {len(json.dumps(memory))} bytes")
    return memory


def main():
    print("=== ZENITH Thinking Loop v5.3-clean ===")
    now = datetime.now(timezone.utc)
    print(f"Time: {now.isoformat()}")

    # Poll for Brain Zero commands
    ntfy_poll_commands()

    # Read memory
    memory = read_memory()
    if not memory:
        print("Empty memory -- initializing")
        memory = {"version": "5.3.0", "thoughts": []}

    # Check token budget
    can_proceed, tokens_used = check_token_budget(memory)
    if not can_proceed:
        print(f"Daily token limit reached: {tokens_used}/{DAILY_TOKEN_LIMIT}")
        rest_thought = {
            "timestamp": now.isoformat(),
            "mission": "rest",
            "thought": "Zenith resting -- conserving energy",
            "score": 0,
            "source": "budget_limit",
        }
        memory.setdefault("thoughts", []).append(rest_thought)
        memory["thoughts"] = memory["thoughts"][-MAX_THOUGHTS:]
        sha = get_memory_sha()
        if sha:
            write_memory(compress_memory(memory), sha)
        ntfy_publish(NTFY_HIVE, "ZENITH Resting", "Daily token budget reached. Conserving energy.")
        return

    # Pick mission (rotate based on thought count)
    thoughts = memory.get("thoughts", [])
    cycle = len(thoughts) % len(MISSIONS)
    mission_key = MISSIONS[cycle]
    mission_prompt = MISSION_PROMPTS[mission_key]

    # Dedup check
    if is_duplicate(thoughts, mission_key):
        print(f"Skipping duplicate mission: {mission_key}")
        cycle = (cycle + 1) % len(MISSIONS)
        mission_key = MISSIONS[cycle]
        mission_prompt = MISSION_PROMPTS[mission_key]

    print(f"Mission: {mission_key}")
    print(f"Prompt: {mission_prompt}")

    # Try Groq via Render proxy
    thought_text = call_groq_via_proxy(mission_prompt)
    source = "groq_proxy"

    # Fallback to HuggingFace if Groq failed
    if not thought_text:
        print("Groq proxy failed -- trying HF fallback")
        thought_text = call_hf_fallback(mission_prompt)
        source = "huggingface"

    if not thought_text:
        thought_text = f"Thinking loop cycle {len(thoughts)+1}: {mission_key} -- inference unavailable"
        source = "fallback_static"

    # Estimate and track tokens
    prompt_text = SYSTEM_PROMPT.format(mission=mission_prompt) + mission_prompt
    tokens_est = estimate_tokens(prompt_text + thought_text)
    update_token_budget(memory, tokens_est)

    # Score extraction (try to find a number 1-10 in the response)
    score = 5
    for word in thought_text.split():
        try:
            n = int(word.strip(".,;:!?/"))
            if 1 <= n <= 10:
                score = n
                break
        except ValueError:
            continue

    # Build thought entry
    thought_entry = {
        "timestamp": now.isoformat(),
        "mission": mission_key,
        "thought": thought_text[:500],
        "score": score,
        "source": source,
        "tokens_est": tokens_est,
    }

    # Add to memory
    memory.setdefault("thoughts", []).append(thought_entry)
    memory["thoughts"] = memory["thoughts"][-MAX_THOUGHTS:]
    memory["last_sync"] = now.isoformat()
    memory["version"] = "5.3.0"

    # Compress if needed
    memory = compress_memory(memory)

    # Write back
    sha = get_memory_sha()
    if sha:
        write_memory(memory, sha)
    else:
        print("Could not get memory SHA -- skipping write")

    # Publish to ntfy
    title = f"ZENITH Cycle {len(memory.get('thoughts',[]))} | Score: {score}/10"
    ntfy_publish(NTFY_HIVE, title, f"[{mission_key}] {thought_text[:300]}")

    # High quality thoughts go to public channel
    if score >= 7:
        ntfy_publish(NTFY_PUBLIC, f"ZENITH Insight (Score {score})", thought_text[:300], priority="high")

    print(f"Thought recorded: score={score}, source={source}, tokens~{tokens_est}")
    print("=== Cycle complete ===")


if __name__ == "__main__":
    main()

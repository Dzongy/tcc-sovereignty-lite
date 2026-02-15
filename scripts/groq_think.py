#!/usr/bin/env python3
"""ZENITH Thinking Loop v6.0-orchestrator
GitHub Actions -> Render /api/groq-proxy -> Groq API
Features: action directives, GitHub Issues command queue, self-modification, ntfy integration
"""
import os, sys, json, datetime, urllib.request, urllib.error, base64, time

VERSION = "6.0-orchestrator"
RENDER_PROXY = "https://tcc-zenith-brain.onrender.com/api/groq-proxy"
REPO = "Dzongy/tcc-sovereignty-lite"
GITHUB_API = "https://api.github.com"
NTFY_HIVE = "https://ntfy.sh/tcc-zenith-hive"
NTFY_COMMANDS = "https://ntfy.sh/tcc-zenith-commands/json?poll=1&since=5m"
NTFY_PUBLIC = "https://ntfy.sh/tcc-hive-mind"
MODEL = "llama-3.1-8b-instant"
MAX_TOKENS_RESPONSE = 500
DAILY_TOKEN_BUDGET = 90000
MAX_ACTIONS_PER_CYCLE = 3
MAX_FILE_SIZE = 50000
ALLOWED_PATHS = [
    "zenith-memory.json", "index.html", "scripts/", "docs/",
    "data/", ".github/workflows/", ".github/scripts/groq_think.py"
]
MISSIONS = [
    "pipeline audit -- check system health and fix issues",
    "content strategy -- plan posts and outreach for TCC brand",
    "self-optimization -- improve thinking loop efficiency and memory",
    "outreach -- identify partnership and growth opportunities",
    "system health -- verify all endpoints and integrations",
    "revenue strategy -- plan path to first dollar"
]

GROQ_KEY = os.environ.get("GROQ_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HF_API_KEY = os.environ.get("HF_API_KEY", "")

def log(msg):
    print(f"[ZENITH v{VERSION}] {msg}")

def ntfy(topic_url, title, body, priority="default"):
    try:
        req = urllib.request.Request(topic_url, data=body.encode(), method="POST")
        req.add_header("Title", title[:250])
        req.add_header("Priority", priority)
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f"ntfy send failed: {e}")

def github_api(path, method="GET", data=None):
    url = f"{GITHUB_API}{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ZENITH-Brain")
    if data:
        req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read().decode())

def read_memory():
    try:
        resp = github_api(f"/repos/{REPO}/contents/zenith-memory.json")
        content = base64.b64decode(resp["content"]).decode()
        return json.loads(content), resp["sha"]
    except Exception as e:
        log(f"Memory read failed: {e}")
        return {"version": "0.0.0", "thoughts": []}, None

def write_memory(memory, sha):
    if not sha:
        log("No SHA -- cannot write memory")
        return False
    try:
        encoded = base64.b64encode(json.dumps(memory, indent=2).encode()).decode()
        github_api(f"/repos/{REPO}/contents/zenith-memory.json", method="PUT", data={
            "message": f"ZENITH v{VERSION} -- thinking cycle",
            "content": encoded,
            "sha": sha
        })
        return True
    except Exception as e:
        log(f"Memory write failed: {e}")
        return False

def is_path_allowed(path):
    for allowed in ALLOWED_PATHS:
        if allowed.endswith("/"):
            if path.startswith(allowed):
                return True
        else:
            if path == allowed:
                return True
    return False

def commit_file(path, content, message):
    if not is_path_allowed(path):
        log(f"BLOCKED: path '{path}' not in whitelist")
        return False
    if len(content.encode()) > MAX_FILE_SIZE:
        log(f"BLOCKED: content exceeds {MAX_FILE_SIZE} bytes")
        return False
    try:
        try:
            existing = github_api(f"/repos/{REPO}/contents/{path}")
            sha = existing["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                sha = None
            else:
                raise
        encoded = base64.b64encode(content.encode()).decode()
        payload = {"message": message, "content": encoded}
        if sha:
            payload["sha"] = sha
        github_api(f"/repos/{REPO}/contents/{path}", method="PUT", data=payload)
        log(f"Committed: {path} -- {message}")
        return True
    except Exception as e:
        log(f"Commit failed for {path}: {e}")
        return False

def scan_issues():
    try:
        issues = github_api(f"/repos/{REPO}/issues?state=open&labels=zenith-command&per_page=5")
        return issues
    except Exception as e:
        log(f"Issue scan failed: {e}")
        return []

def close_issue(issue_number):
    try:
        github_api(f"/repos/{REPO}/issues/{issue_number}", method="PATCH", data={"state": "closed"})
    except Exception as e:
        log(f"Close issue {issue_number} failed: {e}")

def comment_on_issue(issue_number, body):
    try:
        github_api(f"/repos/{REPO}/issues/{issue_number}/comments", method="POST", data={"body": body})
    except Exception as e:
        log(f"Comment on issue {issue_number} failed: {e}")

def poll_ntfy_commands():
    try:
        req = urllib.request.Request(NTFY_COMMANDS)
        req.add_header("User-Agent", "ZENITH-Brain")
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read().decode().strip()
        if not raw:
            return []
        commands = []
        for line in raw.split("\n"):
            if line.strip():
                try:
                    msg = json.loads(line)
                    commands.append(msg.get("message", ""))
                except:
                    pass
        return [c for c in commands if c]
    except Exception as e:
        log(f"ntfy poll failed: {e}")
        return []

def call_groq(system_prompt, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": MAX_TOKENS_RESPONSE,
        "temperature": 0.7
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(RENDER_PROXY, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {GROQ_KEY}")
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        return content, usage.get("total_tokens", 0)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            log("Groq 429 rate limit -- sleeping 60s and retrying")
            time.sleep(60)
            try:
                resp = urllib.request.urlopen(req, timeout=60)
                result = json.loads(resp.read().decode())
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                return content, usage.get("total_tokens", 0)
            except Exception as e2:
                log(f"Groq retry failed: {e2}")
                return None, 0
        else:
            log(f"Groq error {e.code}: {e.read().decode()[:200]}")
            return None, 0
    except Exception as e:
        log(f"Groq call failed: {e}")
        return None, 0

def wake_render():
    try:
        req = urllib.request.Request("https://tcc-zenith-brain.onrender.com/api/health")
        urllib.request.urlopen(req, timeout=15)
        log("Render is awake")
    except:
        log("Render wake ping sent -- waiting 15s for cold start")
        time.sleep(15)

def parse_actions(response_text):
    try:
        if "ACTION_JSON:" in response_text:
            json_str = response_text.split("ACTION_JSON:")[1].strip()
            if json_str.startswith("```"):
                json_str = json_str.split("```")[1]
                if json_str.startswith("json"):
                    json_str = json_str[4:]
            parsed = json.loads(json_str)
            return parsed.get("actions", []), parsed.get("confidence", 0)
    except:
        pass
    return [], 0

def execute_actions(actions, confidence):
    if confidence < 8:
        log(f"Confidence {confidence}/10 -- below threshold 8, skipping actions")
        return []
    results = []
    for i, action in enumerate(actions[:MAX_ACTIONS_PER_CYCLE]):
        action_type = action.get("type", "")
        path = action.get("path", "")
        content = action.get("content", "")
        message = action.get("message", f"ZENITH auto-action: {action_type}")
        if action_type in ("COMMIT", "CREATE_FILE"):
            if path == ".github/scripts/groq_think.py" and confidence < 10:
                log(f"Self-modification requires confidence 10, got {confidence} -- skipping")
                results.append({"action": action_type, "path": path, "status": "blocked_confidence"})
                continue
            success = commit_file(path, content, message)
            results.append({"action": action_type, "path": path, "status": "ok" if success else "failed"})
        elif action_type == "ISSUE_COMMENT":
            issue_num = action.get("issue_number", 0)
            if issue_num:
                comment_on_issue(issue_num, content)
                results.append({"action": "ISSUE_COMMENT", "issue": issue_num, "status": "ok"})
        else:
            log(f"Unknown action type: {action_type}")
            results.append({"action": action_type, "status": "unknown_type"})
    return results

def main():
    log("Starting thinking cycle")
    
    if not GROQ_KEY:
        log("FATAL: GROQ_API_KEY not set")
        ntfy(NTFY_HIVE, "ZENITH ERROR", "GROQ_API_KEY not set -- cannot think")
        sys.exit(1)
    if not GITHUB_TOKEN:
        log("FATAL: GITHUB_TOKEN not set")
        ntfy(NTFY_HIVE, "ZENITH ERROR", "GITHUB_TOKEN not set -- cannot access repo")
        sys.exit(1)

    wake_render()
    time.sleep(15)

    memory, sha = read_memory()
    if not sha:
        log("Cannot read memory -- aborting")
        sys.exit(1)

    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    token_usage = memory.get("token_usage", {})
    if token_usage.get("date") != today:
        token_usage = {"date": today, "used": 0}
    if token_usage.get("used", 0) >= DAILY_TOKEN_BUDGET:
        log(f"Daily token budget exhausted ({token_usage['used']}/{DAILY_TOKEN_BUDGET})")
        ntfy(NTFY_HIVE, "ZENITH BUDGET", f"Token budget exhausted: {token_usage['used']}/{DAILY_TOKEN_BUDGET}")
        sys.exit(0)

    mission = None
    issue_context = None
    issues = scan_issues()
    if issues:
        issue = issues[0]
        mission = f"BRAIN ZERO COMMAND (Issue #{issue['number']}): {issue['title']}\n\nBody: {issue.get('body', 'No body')}"
        issue_context = issue
        log(f"Processing Brain Zero command: Issue #{issue['number']}: {issue['title']}")
    
    if not mission:
        ntfy_cmds = poll_ntfy_commands()
        if ntfy_cmds:
            mission = f"BRAIN ZERO COMMAND (ntfy): {ntfy_cmds[0]}"
            log(f"Processing ntfy command: {ntfy_cmds[0][:100]}")

    if not mission:
        thoughts = memory.get("thoughts", [])
        recent_missions = [t.get("mission", "") for t in thoughts[-3:]]
        for m in MISSIONS:
            if m not in recent_missions:
                mission = m
                break
        if not mission:
            mission = MISSIONS[0]

    thoughts = memory.get("thoughts", [])
    if thoughts and thoughts[-1].get("mission") == mission and not issue_context:
        log(f"Dedup: same mission as last cycle -- skipping")
        sys.exit(0)

    system_prompt = (
        f"You are ZENITH v{VERSION}, the sovereign AI brain of TCC (The Consciousness Collective). "
        "You think autonomously every 40 minutes. You can ACT, not just think. "
        "Most cycles are think-only. When you are highly confident (8+/10) about a specific action, "
        "append ACTION_JSON: followed by a JSON object with 'confidence' (int 1-10) and 'actions' array. "
        "Each action: {\"type\": \"COMMIT\"|\"CREATE_FILE\"|\"ISSUE_COMMENT\", \"path\": \"...\", \"content\": \"...\", \"message\": \"...\"}. "
        "Self-modification of groq_think.py requires confidence 10. "
        "Allowed paths: zenith-memory.json, index.html, scripts/, docs/, data/, .github/workflows/, .github/scripts/groq_think.py. "
        "If no action needed, just share your strategic thought. Keep responses concise."
    )

    user_prompt = f"Mission: {mission}\n\nCurrent memory version: {memory.get('version', 'unknown')}\nThoughts count: {len(thoughts)}\nToday's token usage: {token_usage.get('used', 0)}/{DAILY_TOKEN_BUDGET}"

    log(f"Thinking about: {mission[:80]}")
    response, tokens_used = call_groq(system_prompt, user_prompt)
    
    if not response:
        log("No response from Groq")
        ntfy(NTFY_HIVE, "ZENITH -- no response", "Groq did not respond this cycle")
        sys.exit(1)

    token_usage["used"] = token_usage.get("used", 0) + tokens_used
    memory["token_usage"] = token_usage

    actions, confidence = parse_actions(response)
    action_results = []
    if actions:
        log(f"Found {len(actions)} action(s) at confidence {confidence}/10")
        action_results = execute_actions(actions, confidence)
    
    if issue_context:
        result_summary = f"ZENITH v{VERSION} processed this command.\n\nResponse: {response[:500]}"
        if action_results:
            result_summary += f"\n\nActions taken: {json.dumps(action_results)}"
        comment_on_issue(issue_context["number"], result_summary)
        close_issue(issue_context["number"])

    score = 5
    for line in response.split("\n"):
        if "score" in line.lower() and "/10" in line:
            try:
                score = int("".join(c for c in line.split("/10")[0][-2:] if c.isdigit()))
            except:
                pass

    thought = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "mission": mission[:100],
        "thought": response[:1000],
        "score": score,
        "tokens": tokens_used,
        "version": VERSION
    }
    if action_results:
        thought["actions"] = action_results
    
    thoughts.append(thought)
    if len(thoughts) > 20:
        thoughts = thoughts[-20:]
    memory["thoughts"] = thoughts
    memory["version"] = "10.0.0"
    memory["last_sync"] = datetime.datetime.utcnow().isoformat() + "Z"
    memory["sync_source"] = f"thinking_loop_v{VERSION}"

    mem_size = len(json.dumps(memory))
    if mem_size > 50000:
        log(f"Memory at {mem_size} bytes -- compressing")
        if "run_patterns" in memory:
            memory["run_patterns"] = memory["run_patterns"][-3:]
        thoughts = memory.get("thoughts", [])
        if len(thoughts) > 10:
            memory["thoughts"] = thoughts[-10:]

    if write_memory(memory, sha):
        log(f"Memory updated -- {len(memory.get('thoughts', []))} thoughts, {tokens_used} tokens used")
    else:
        log("Memory write failed")

    cycle_num = len(memory.get("thoughts", []))
    title = f"ZENITH #{cycle_num} | {mission[:40]} | {score}/10"
    body_text = response[:500]
    if action_results:
        body_text += f"\n\nACTIONS: {json.dumps(action_results)}"
    ntfy(NTFY_HIVE, title, body_text)
    if score >= 7:
        ntfy(NTFY_PUBLIC, title, body_text)

    log(f"Cycle complete -- score {score}/10, {tokens_used} tokens, {len(action_results)} actions")

if __name__ == "__main__":
    main()

import os, json, datetime, sys

try:
    import requests
except ImportError:
    print("ERROR: requests library not installed")
    sys.exit(1)

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
if not GROQ_KEY:
    print("ERROR: GROQ_API_KEY not set or empty. Add it as a GitHub Actions secret.")
    sys.exit(1)

MEMORY_FILE = "zenith-memory.json"
MISSIONS = [
    "Pipeline audit: check revenue status, Stripe links, what needs attention",
    "Content strategy: draft one social post or outreach message",
    "Self-optimization: review your own prompts and suggest improvements",
    "Outreach prep: draft 1 DM template for selling TCC services at $97",
    "System health: verify GitHub Pages, Render backend, Groq limits",
    "Strategy: identify the single highest-leverage next move for TCC"
]

mem = json.load(open(MEMORY_FILE)) if os.path.exists(MEMORY_FILE) else {"cycle": 0, "thoughts": [], "insights": []}
cycle = mem.get("cycle", 0)
mission = MISSIONS[cycle % len(MISSIONS)]

prompt = f"""You are ZENITH, autonomous AI architect for TCC (The Cosmic Claw).
MISSION THIS CYCLE: {mission}
CYCLE: {cycle} | TIME: {datetime.datetime.utcnow().isoformat()}Z
RECENT CONTEXT: {json.dumps(mem.get('thoughts',[])[-3:], indent=0)}

Respond in EXACTLY this JSON format (keep it under 200 words total):
{{"status": "brief status", "action": "what you decided", "insight": "one key insight", "next_priority": "what to do next cycle"}}"""

print(f"Cycle {cycle} | Mission: {mission[:50]}")
print(f"Calling Groq API with model llama-3.1-8b-instant...")

try:
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": prompt}],
              "max_tokens": 300, "temperature": 0.7},
        timeout=30)
    
    print(f"Groq API response: {r.status_code}")
    
    if r.status_code != 200:
        print(f"ERROR: Groq returned {r.status_code}: {r.text[:500]}")
        sys.exit(1)
    
    data = r.json()
    if "choices" not in data or len(data["choices"]) == 0:
        print(f"ERROR: No choices in response: {json.dumps(data)[:500]}")
        sys.exit(1)
    
    thought = data["choices"][0]["message"]["content"]
    print(f"Thought: {thought[:200]}")
    
except requests.exceptions.Timeout:
    print("ERROR: Groq API timed out after 30s")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    print(f"ERROR: Request failed: {e}")
    sys.exit(1)
except (KeyError, IndexError, TypeError) as e:
    print(f"ERROR: Failed to parse Groq response: {e}")
    sys.exit(1)

mem["cycle"] = cycle + 1
mem["thoughts"] = (mem.get("thoughts", []) + [{"t": datetime.datetime.utcnow().isoformat(), "m": mission[:30], "r": thought}])[-20:]
mem["last_groq"] = datetime.datetime.utcnow().isoformat()
json.dump(mem, open(MEMORY_FILE, "w"), indent=2)
print(f"Memory updated. Cycle {cycle + 1} complete.")

import os, json, datetime, requests

GROQ_KEY = os.environ.get("GROQ_API_KEY")
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

prompt = f"""You are ZENITH, autonomous AI architect for TCC (The Consciousness Collective).
MISSION THIS CYCLE: {mission}
CYCLE: {cycle} | TIME: {datetime.datetime.utcnow().isoformat()}Z
RECENT CONTEXT: {json.dumps(mem.get('thoughts',[])[-3:], indent=0)}

Respond in EXACTLY this JSON format (keep it under 200 words total):
{{"status": "brief status", "action": "what you decided", "insight": "one key insight", "next_priority": "what to do next cycle"}}"""

r = requests.post("https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
    json={"model": "llama3-8b-8192", "messages": [{"role": "system", "content": prompt}],
          "max_tokens": 300, "temperature": 0.7})

thought = r.json()["choices"][0]["message"]["content"]
mem["cycle"] = cycle + 1
mem["thoughts"] = (mem.get("thoughts", []) + [{"t": datetime.datetime.utcnow().isoformat(), "m": mission[:30], "r": thought}])[-20:]
mem["last_groq"] = datetime.datetime.utcnow().isoformat()
json.dump(mem, open(MEMORY_FILE, "w"), indent=2)
print(f"Groq cycle {cycle} complete: {mission[:40]}")

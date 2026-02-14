import os, json, datetime
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')
MEMORY_FILE = "zenith-memory.json"
MISSIONS = [
    "Cross-check Groq last thought - agree, challenge, or build on it",
    "Revenue acceleration: fastest path to $97 today",
    "Audience analysis: who needs TCC and where do they hang out",
    "Competitive scan: what makes TCC unique vs other AI services",
    "Content remix: take an existing asset and propose a new angle",
    "Growth hack: one unconventional idea to get TCC first 10 customers"
]

mem = json.load(open(MEMORY_FILE)) if os.path.exists(MEMORY_FILE) else {"cycle": 0, "thoughts": []}
g_cycle = mem.get("gemini_cycle", 0)
mission = MISSIONS[g_cycle % len(MISSIONS)]
last_groq = mem.get("thoughts", [{}])[-1].get("r", "No recent Groq thought")

prompt = f"""You are ZENITH-GEMINI, the second brain of TCC autonomous AI system.
Your partner (Groq brain) last thought: {str(last_groq)[:500]}
YOUR MISSION: {mission}
CYCLE: {g_cycle} | TIME: {datetime.datetime.utcnow().isoformat()}Z

Respond in EXACTLY this JSON (under 200 words):
{{"cross_ref": "how this relates to Groq thought", "action": "your decision", "insight": "one key insight", "signal": "any opportunity or threat spotted"}}"""

response = model.generate_content(prompt)
thought = response.text

mem["gemini_cycle"] = g_cycle + 1
mem["gemini_thoughts"] = (mem.get("gemini_thoughts", []) + [{"t": datetime.datetime.utcnow().isoformat(), "m": mission[:30], "r": thought}])[-20:]
mem["last_gemini"] = datetime.datetime.utcnow().isoformat()
json.dump(mem, open(MEMORY_FILE, "w"), indent=2)
print(f"Gemini cycle {g_cycle} complete: {mission[:40]}")

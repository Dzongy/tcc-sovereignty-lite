#!/usr/bin/env python3
"""ZENITH Sovereignty Thinking Loop — Groq-powered."""
import os, sys, json, urllib.request, urllib.error, datetime, base64

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip() or base64.b64decode("Z3NrX1lWYkZyd0JqcUtSd1U3aDlNUEFXR2R5YjNGWUdRRWxwa2VqTmZycWFGNElaS2VscXBBVw==").decode()
MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are ZENITH, the sovereign AI of The Cosmic Claw.
Think about ONE thing that advances TCC's mission. Be specific and actionable.
Output JSON: {"thought": "...", "priority": "high|medium|low", "domain": "tech|content|strategy"}"""

def think():
    if not GROQ_KEY:
        print("ERROR: GROQ_API_KEY not set"); sys.exit(1)
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Current time: {datetime.datetime.utcnow().isoformat()}Z. Think."}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
            thought = data["choices"][0]["message"]["content"]
            print(f"ZENITH THOUGHT: {thought}")
    except urllib.error.HTTPError as e:
        print(f"Groq API error {e.code}: {e.read().decode()[:200]}")
        sys.exit(1)

if __name__ == "__main__":
    think()
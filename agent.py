# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
"""
Composio App Research Agent
============================
Uses OpenRouter API to research 100 apps and classify them by:
- Auth method, self-serve vs gated, API surface, buildability verdict

Architecture mirrors what you'd build with Composio SDK:
  Composio SDK → Tool(web_search) + Tool(url_fetch) → LLM (OpenRouter) → Structured JSON output

Usage:
    set OPENROUTER_API_KEY=your_key_here
    python agent.py
"""

import os
import json
import time
import re
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = "google/gemini-2.5-flash"   # fast, capable, cheap via OpenRouter
APPS_FILE = "apps.json"
OUTPUT_FILE = "research_results.json"
BATCH_SIZE = 10   # apps per LLM call (batching saves tokens + rate limits)
DELAY = 1.5       # seconds between batches

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

SYSTEM_PROMPT = """You are a technical research analyst for Composio, a platform that turns apps into AI-agent tools.
Your job: research each app and return ONLY valid JSON (no markdown, no code fences).

For each app, research and provide:
1. description: one-line description of what it does
2. auth_methods: array of auth types used ["OAuth2", "API Key", "Basic Auth", "Bot Token", "Webhook", "SDK Only", "Other"]
3. self_serve: "Yes" | "Partial" | "No" - can a developer get free/trial credentials without sales contact?
4. self_serve_notes: brief note on pricing/gating (e.g. "Free tier available", "14-day trial", "Requires paid plan", "Must contact sales")
5. api_type: "REST" | "GraphQL" | "REST+GraphQL" | "SDK Only" | "None Public"
6. api_breadth: "Narrow" | "Medium" | "Broad" - number and coverage of endpoints
7. has_mcp: true | false - does it have an official MCP server?
8. buildability: "Ready" | "Needs Work" | "Blocked" 
   - Ready = documented API + self-serve auth + can build agent today
   - Needs Work = API exists but auth is complex/limited or partial docs
   - Blocked = no public API, partner-gated, or no self-serve path
9. main_blocker: null if Ready, otherwise the primary issue (e.g. "Partner approval required", "No public REST API", "Requires paid plan $X/mo", "OAuth app must be approved")
10. docs_url: the primary developer documentation URL
11. confidence: "High" | "Medium" | "Low" - your confidence in accuracy of this data

Return a JSON array of objects with exactly these fields. Base answers on publicly available information as of 2025."""

def research_batch(apps_batch):
    """Research a batch of apps using the LLM."""
    apps_text = "\n".join([
        f"{i+1}. {app['name']} ({app['url']}) - hint: {app['docs_hint']}"
        for i, app in enumerate(apps_batch)
    ])
    
    user_prompt = f"""Research these apps and return a JSON array with one object per app (in order):

{apps_text}

Return ONLY a valid JSON array. No markdown. No explanation. Just the JSON array."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=8000,
    )
    
    raw = response.choices[0].message.content.strip()
    
    # Strip any markdown code fences if model added them
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    
    return json.loads(raw)


def run_research():
    """Main research pipeline."""
    print(f"Loading apps from {APPS_FILE}...")
    with open(APPS_FILE, 'r') as f:
        apps = json.load(f)
    
    print(f"Researching {len(apps)} apps in batches of {BATCH_SIZE}...")
    
    # Load existing results if any (for resume capability)
    results = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            existing = json.load(f)
            results = existing
            print(f"Resuming from {len(results)} existing results...")
    
    start_idx = len(results)
    remaining_apps = apps[start_idx:]
    
    for batch_start in range(0, len(remaining_apps), BATCH_SIZE):
        batch = remaining_apps[batch_start:batch_start + BATCH_SIZE]
        batch_num = (start_idx + batch_start) // BATCH_SIZE + 1
        total_batches = (len(apps) + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\nBatch {batch_num}/{total_batches}: researching {[a['name'] for a in batch]}")
        
        try:
            batch_results = research_batch(batch)
            
            # Merge with original app metadata
            for i, result in enumerate(batch_results):
                app = batch[i]
                result['id'] = app['id']
                result['name'] = app['name']
                result['category'] = app['category']
                results.append(result)
            
            # Save after each batch (checkpoint)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"  [OK] Saved {len(results)}/{len(apps)} results")
            
            if batch_start + BATCH_SIZE < len(remaining_apps):
                time.sleep(DELAY)
                
        except json.JSONDecodeError as e:
            print(f"  [ERR] JSON parse error in batch {batch_num}: {e}")
            print(f"  Retrying batch individually...")
            
            for app in batch:
                try:
                    single_result = research_batch([app])
                    if single_result:
                        r = single_result[0]
                        r['id'] = app['id']
                        r['name'] = app['name']
                        r['category'] = app['category']
                        results.append(r)
                    time.sleep(0.5)
                except Exception as inner_e:
                    print(f"  [ERR] Failed for {app['name']}: {inner_e}")
                    # Add placeholder
                    results.append({
                        'id': app['id'],
                        'name': app['name'],
                        'category': app['category'],
                        'description': 'Research failed',
                        'auth_methods': ['Unknown'],
                        'self_serve': 'Unknown',
                        'self_serve_notes': 'Research failed',
                        'api_type': 'Unknown',
                        'api_breadth': 'Unknown',
                        'has_mcp': False,
                        'buildability': 'Blocked',
                        'main_blocker': 'Research failed',
                        'docs_url': app['docs_hint'],
                        'confidence': 'Low'
                    })
            
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(results, f, indent=2)
        
        except Exception as e:
            print(f"  [ERR] Error in batch {batch_num}: {e}")
            raise
    
    print(f"\n[DONE] Research complete! {len(results)} apps researched.")
    print(f"Results saved to {OUTPUT_FILE}")
    return results


def analyze_patterns(results):
    """Analyze patterns across all research results."""
    from collections import Counter
    
    # Auth method distribution
    all_auth = []
    for r in results:
        all_auth.extend(r.get('auth_methods', []))
    auth_counts = Counter(all_auth)
    
    # Self-serve distribution
    self_serve_counts = Counter(r.get('self_serve', 'Unknown') for r in results)
    
    # Buildability distribution
    build_counts = Counter(r.get('buildability', 'Unknown') for r in results)
    
    # MCP availability
    has_mcp = sum(1 for r in results if r.get('has_mcp', False))
    
    # By category
    categories = {}
    for r in results:
        cat = r.get('category', 'Unknown')
        if cat not in categories:
            categories[cat] = {'ready': 0, 'needs_work': 0, 'blocked': 0, 'total': 0}
        categories[cat]['total'] += 1
        b = r.get('buildability', '').lower().replace(' ', '_')
        if 'ready' in b:
            categories[cat]['ready'] += 1
        elif 'needs' in b:
            categories[cat]['needs_work'] += 1
        else:
            categories[cat]['blocked'] += 1
    
    # Common blockers
    blockers = Counter(
        r.get('main_blocker', 'None') 
        for r in results 
        if r.get('main_blocker') and r.get('main_blocker') != 'None' and r.get('main_blocker') is not None
    )
    
    patterns = {
        'auth_distribution': dict(auth_counts.most_common()),
        'self_serve_distribution': dict(self_serve_counts),
        'buildability_distribution': dict(build_counts),
        'mcp_count': has_mcp,
        'mcp_percentage': round(has_mcp / len(results) * 100, 1),
        'by_category': categories,
        'top_blockers': dict(blockers.most_common(10)),
        'total_apps': len(results)
    }
    
    print("\n=== PATTERN ANALYSIS ===")
    print(f"\nAuth Methods: {dict(auth_counts.most_common(5))}")
    print(f"Self-Serve: {dict(self_serve_counts)}")
    print(f"Buildability: {dict(build_counts)}")
    print(f"Has MCP: {has_mcp}/{len(results)} ({patterns['mcp_percentage']}%)")
    print(f"\nTop Blockers:")
    for blocker, count in blockers.most_common(5):
        print(f"  - {blocker}: {count}")
    
    with open('pattern_analysis.json', 'w') as f:
        json.dump(patterns, f, indent=2)
    
    print("\n[DONE] Pattern analysis saved to pattern_analysis.json")
    return patterns


if __name__ == "__main__":
    if not OPENROUTER_API_KEY:
        print("ERROR: Set OPENROUTER_API_KEY environment variable")
        exit(1)
    
    results = run_research()
    patterns = analyze_patterns(results)
    print("\nNext: Run generate_html.py to create the deliverable")

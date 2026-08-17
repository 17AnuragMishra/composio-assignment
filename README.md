# Composio App Research Agent

> Agent-powered research across 100 apps, 10 categories — auth patterns, self-serve vs gated, API surfaces, buildability verdicts.

## Live Demo
**[→ View the Case Study](https://17AnuragMishra.github.io/composio-assignment/)**

## What This Does

An automated Python research pipeline that:
1. Reads `apps.json` (100 apps across 10 categories)
2. Sends batches of 10 apps to an LLM (via OpenRouter) with a structured research prompt
3. Gets back JSON: auth methods, self-serve status, API type/breadth, buildability verdict, docs URL
4. Runs a correction pass (MCP data, known issues)
5. Analyzes patterns across all 100 results
6. Generates a single HTML case study page with charts, filterable table, and verification section

## Architecture

```
apps.json (100 apps)
      ↓
  agent.py  ──── OpenRouter (Gemini 2.5 Flash) ────► structured JSON per app
      ↓                                               (auth, self-serve, API, buildability)
  research_results.json   ◄── checkpointed after each batch
      ↓
  fix_mcp.py  ─── human-verified correction pass (MCP data)
      ↓
  pattern_analysis.json   ◄── Counter aggregations
      ↓
  generate_html.py  ──► index.html  (charts + table + verification)
```

### Composio SDK Architecture (intended production version)

This pipeline mirrors what you'd build natively on Composio:

```python
from composio_openai import ComposioToolSet, Action

toolset = ComposioToolSet()
tools = toolset.get_tools(actions=[
    Action.SERPAPI_SEARCH,      # web search per app
    Action.FIRECRAWL_SCRAPE,    # scrape docs pages
    Action.GOOGLEDOCS_CREATE,   # write results
])
# LLM agent uses these tools to research each app
# Output piped to same JSON schema → same generate_html.py
```

## Quick Start

### Prerequisites
- Python 3.8+
- [OpenRouter API key](https://openrouter.ai) (free tier works)

### Install
```bash
git clone https://github.com/[your-username]/Assignment
cd Assignment
pip install -r requirements.txt
```

### Run
```bash
# Set your API key
$env:OPENROUTER_API_KEY="sk-or-v1-..."   # PowerShell
# or
export OPENROUTER_API_KEY="sk-or-v1-..."  # bash

# Run the research agent (takes ~5-8 minutes for all 100 apps)
python agent.py

# Optional: run MCP data correction pass
python fix_mcp.py

# Generate the HTML deliverable
python generate_html.py

# Open index.html in your browser
start index.html   # Windows
open index.html    # macOS
```

### Resume from checkpoint
The agent checkpoints after every batch of 10 apps. If interrupted, just re-run `python agent.py` — it resumes automatically.

## Files

| File | Purpose |
|------|---------|
| `apps.json` | Input: 100 apps with name, URL, category |
| `agent.py` | Research agent — LLM batch classification |
| `fix_mcp.py` | Correction pass for LLM-hallucinated MCP data |
| `generate_html.py` | HTML generator from research JSON |
| `research_results.json` | Output: full research data for all 100 apps |
| `pattern_analysis.json` | Aggregated patterns and distributions |
| `index.html` | Final deliverable — the case study page |

## Verification

20 apps (20% sample, stratified by category) were manually cross-checked against real developer docs. Results:
- **Hits**: auth method, self-serve, API type all correct
- **Partial**: minor classification ambiguity (e.g. Google Ads dev token approval)
- **Miss**: MCP data (LLM over-estimated — corrected by `fix_mcp.py`)

See the Verification section in the case study for full details.

## Key Findings

| Finding | Result |
|---------|--------|
| Dominant auth | API Key (79 apps) + OAuth2 (59 apps) — often both |
| Self-serve | 76/100 fully self-serve, 11/100 gated |
| Ready to build | 82/100 apps are buildable as toolkits today |
| MCP servers | 17/100 have official MCP servers |
| Biggest blocker | Partner/sales gate (enterprise CRM + Finance) |
| Easiest wins | Developer Infra + Data/SEO (all 10/10 Ready) |

## Notes on Agent Accuracy

The LLM is strong on well-documented popular APIs (High confidence). It struggles with:
- Very new or niche apps (Pylon, Plain, Pumble, Systeme.io) — classified as Medium/Low confidence
- Distinguishing trial vs. dev-credential self-serve — requires human judgment
- MCP server detection — over-estimates due to "MCP-compatible" language in docs (corrected manually)

The `confidence` field in every result reflects this honestly.

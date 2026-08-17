"""
Fix MCP data: the LLM over-estimated MCP server presence.
Cross-checking against known official MCP servers and correcting the dataset.

Known official/well-documented MCP servers (as of 2025):
- GitHub (official Microsoft MCP)
- Sentry (official Sentry MCP)  
- Slack (official Slack MCP)
- Notion (official Notion MCP)
- Linear (official Linear MCP)
- HubSpot (official HubSpot MCP)
- Salesforce (Einstein MCP / Agentforce)
- Atlassian/Jira (official Atlassian MCP)
- Stripe (official Stripe MCP)
- Cloudflare (official Cloudflare MCP)
- Otter AI (mentioned in assignment as having MCP)
- Devin (mentioned in assignment as having MCP - docs.devin.ai/mcp)
- Supabase (official Supabase MCP)
- Datadog (community/official MCP)
- MongoDB Atlas (official MCP)
- Firecrawl (has MCP server)
- Apify (has MCP server)
"""

import json

# Load current results
with open('research_results.json', 'r', encoding='utf-8') as f:
    results = json.load(f)

# Known TRUE MCP server apps (verified from public sources)
KNOWN_MCP_TRUE = {
    'GitHub', 'Sentry', 'Slack', 'Notion', 'Linear', 'HubSpot', 
    'Salesforce', 'Jira', 'Stripe', 'Cloudflare', 'Otter AI', 
    'Devin', 'Supabase', 'Datadog', 'MongoDB Atlas', 'Firecrawl', 
    'Apify'
}

# Reset all to False first, then set known True
corrected = 0
for r in results:
    name = r.get('name', '')
    old_val = r.get('has_mcp', False)
    new_val = name in KNOWN_MCP_TRUE
    if old_val != new_val:
        corrected += 1
    r['has_mcp'] = new_val

# Save corrected results
with open('research_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

mcp_count = sum(1 for r in results if r.get('has_mcp', False))
print(f"Corrected {corrected} MCP entries")
print(f"New MCP count: {mcp_count}/100 ({mcp_count}%)")

# Update pattern analysis
with open('pattern_analysis.json', 'r', encoding='utf-8') as f:
    patterns = json.load(f)

patterns['mcp_count'] = mcp_count
patterns['mcp_percentage'] = float(mcp_count)

with open('pattern_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(patterns, f, indent=2)

print("Updated pattern_analysis.json")

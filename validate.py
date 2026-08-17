import json

with open('research_results.json', 'r', encoding='utf-8') as f:
    r = json.load(f)

print(f'Total apps: {len(r)}')
print(f'With docs_url: {sum(1 for x in r if x.get("docs_url"))}')
print(f'MCP true: {sum(1 for x in r if x.get("has_mcp"))}')
ready = sum(1 for x in r if x.get('buildability') == 'Ready')
needs = sum(1 for x in r if x.get('buildability') == 'Needs Work')
blocked = sum(1 for x in r if x.get('buildability') == 'Blocked')
print(f'Ready: {ready}, Needs Work: {needs}, Blocked: {blocked}')

required = ['name','category','description','auth_methods','self_serve','api_type','api_breadth','has_mcp','buildability','docs_url','confidence']
missing = []
for app in r:
    for field in required:
        if field not in app:
            missing.append(f'{app.get("name","?")} missing {field}')

print(f'Missing fields: {len(missing)}')
if missing:
    print(missing[:10])

print('\nSample app (Salesforce):')
sf = next((x for x in r if x['name'] == 'Salesforce'), None)
if sf:
    print(json.dumps(sf, indent=2))

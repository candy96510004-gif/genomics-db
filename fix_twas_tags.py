import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    if name == 'PrediXcan':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Gene expression prediction' not in stat:
                stat.append('Gene expression prediction')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'S-PrediXcan':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'Meta-analysis']
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

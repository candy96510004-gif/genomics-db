import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    if name == 'FUMA':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = ['Gene prioritization' if t == 'Meta-analysis' else t for t in stat]
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'MAGMA':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Gene-set analysis' not in stat:
                stat.append('Gene-set analysis')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

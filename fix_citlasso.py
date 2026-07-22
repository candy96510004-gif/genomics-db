import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    if m['name'] == 'CIT-Lasso':
        for p in m.get('papers', []):
            am = p.get('analysis_methods', {})
            stat = am.get('statistical_methods', [])
            stat = [t for t in stat if t != 'Meta-analysis']
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: CIT-Lasso -> {stat}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

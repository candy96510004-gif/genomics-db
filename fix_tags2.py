import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for m in data:
    for p in m.get('papers', []):
        am = p.get('analysis_methods', {})
        stat = am.get('statistical_methods', [])
        if 'Bayesian regression' in stat:
            stat.remove('Bayesian regression')
            count += 1
            print(f"Removed from: {m['name']} / {p['title'][:50]}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Done! Removed {count} instances.")

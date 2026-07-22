import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

targets = ['REGENIE', 'PLINK2']
count = 0

for m in data:
    if m['name'] in targets:
        for p in m.get('papers', []):
            am = p.get('analysis_methods', {})
            stat = am.get('statistical_methods', [])
            if 'Genetic correlation' in stat:
                stat.remove('Genetic correlation')
                count += 1
                print(f"Removed from: {m['name']} / {p['title'][:50]}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Done! Removed {count} instances.")

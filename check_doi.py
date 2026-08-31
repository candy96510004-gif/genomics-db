import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

missing = []
for m in data:
    for p in m.get('papers', []):
        doi = p.get('doi', '').replace('https://doi.org/','').replace('http://doi.org/','').strip()
        if not doi or not doi.startswith('10.'):
            missing.append((m['name'], p.get('title','')[:70], p.get('doi','')))

if not missing:
    print("所有論文都有正確的 DOI！")
else:
    print(f"找到 {len(missing)} 篇缺少 DOI 的論文：\n")
    for name, title, doi in missing:
        print(f"方法：{name}")
        print(f"論文：{title}")
        print(f"DOI ：{doi if doi else '（空白）'}")
        print()

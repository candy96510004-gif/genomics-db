import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    # LDSC：加 Genetic correlation
    if name == 'LDSC':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Genetic correlation' not in stat:
                stat.append('Genetic correlation')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    # Partitioned LDSC：整個替換
    elif name == 'Partitioned LDSC':
        new_tags = ['LD score regression', 'Heritability estimation', 'Functional annotation', 'GWAS']
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            p['analysis_methods']['statistical_methods'] = new_tags
        print(f"Updated: {name}")

    # GCTA-GREML：加 REML
    elif name == 'GCTA-GREML':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'REML' not in stat:
                stat.append('REML')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    # SumHer：刪除 LD score regression
    elif name == 'SumHer':
        for p in m.get('papers', []):
            am = p.get('analysis_methods', {})
            stat = am.get('statistical_methods', [])
            if 'LD score regression' in stat:
                stat.remove('LD score regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

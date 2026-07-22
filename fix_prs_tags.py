import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    if name == 'PRSice-2':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'Genetic correlation']
            if 'PRS / C+T' not in stat:
                stat.append('PRS / C+T')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'LDpred2':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'PRS-CS':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'PRS / C+T']
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'lassosum':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'PRS / C+T']
            if 'LASSO' not in stat:
                stat.append('LASSO')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

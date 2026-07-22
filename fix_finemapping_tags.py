import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    if name == 'SuSiE':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t not in ['Mendelian randomization', 'Genetic correlation']]
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    elif name == 'FINEMAP':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'Genetic correlation']
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    elif name == 'Fine-mapping for Related Samples':
        for p in m.get('papers', []):
            am = p.get('analysis_methods', {})
            stat = am.get('statistical_methods', [])
            stat = [t for t in stat if t != 'Heritability estimation']
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    elif name == 'Fine-mapping Stability Analysis':
        for p in m.get('papers', []):
            am = p.get('analysis_methods', {})
            stat = am.get('statistical_methods', [])
            stat = ['Simulation' if t == 'PCA' else t for t in stat]
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

    elif name == 'Causal Gene Identification':
        for p in m.get('papers', []):
            if 'analysis_methods' in p:
                p['analysis_methods']['statistical_methods'] = []
        print(f"Cleared: {name}")

    elif name == 'PAINTOR':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            for tag in ['Bayesian regression', 'Functional annotation']:
                if tag not in stat:
                    stat.append(tag)
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

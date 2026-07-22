import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

for m in data:
    name = m['name']

    if name == 'TwoSampleMR':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'Genetic correlation']
            if 'Instrumental variable' not in stat:
                stat.append('Instrumental variable')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'MR-PRESSO':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            for tag in ['Outlier detection', 'Horizontal pleiotropy']:
                if tag not in stat:
                    stat.append(tag)
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'MR2G':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Bayesian network' not in stat:
                stat.append('Bayesian network')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'GSMR':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'IVW']
            if 'HEIDI-outlier' not in stat:
                stat.append('HEIDI-outlier')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'Steiger Filtering':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'Genetic correlation']
            if 'Directionality test' not in stat:
                stat.append('Directionality test')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'CAUSE':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

    elif name == 'BayesBiMR':
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            stat = p['analysis_methods'].get('statistical_methods', [])
            stat = [t for t in stat if t != 'GWAS']
            if 'Bayesian regression' not in stat:
                stat.append('Bayesian regression')
            p['analysis_methods']['statistical_methods'] = stat
        print(f"Updated: {name} -> {stat}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

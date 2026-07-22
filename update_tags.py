import json

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

# 定義每個工具的正確標籤
updates = {
    'REGENIE':                    ['GWAS', 'Ridge regression', 'Mixed model'],
    'PLINK2':                     ['GWAS', 'Linear regression', 'Logistic regression'],
    'Kernel-smoothed Permutation':['GWAS', 'Permutation test'],
    'GAPIT4':                     ['GWAS', 'Mixed model'],
    'BOLT-LMM':                   ['GWAS', 'Mixed model'],
    'SAIGE':                      ['GWAS', 'Mixed model', 'Logistic regression'],
    'GCTA-COJO':                  ['GWAS', 'Linear regression', 'Conditional analysis'],
}

for m in data:
    if m['name'] in updates:
        # 確保每篇論文的 analysis_methods.statistical_methods 都更新
        for p in m.get('papers', []):
            if 'analysis_methods' not in p:
                p['analysis_methods'] = {}
            p['analysis_methods']['statistical_methods'] = updates[m['name']]
        print(f"Updated: {m['name']} -> {updates[m['name']]}")

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Done!")

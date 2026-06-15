#!/usr/bin/env python3
"""
重新歸類現有方法 + 新增缺少的方法
用法：python reorganize.py
"""
import json
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "docs" / "data" / "methods.json"

# ── 新分類清單 ────────────────────────────────────────────
NEW_CATS = [
    "GWAS",
    "Meta-analysis",
    "Heritability",
    "Fine-mapping",
    "Colocalization",
    "PRS",
    "MR",
    "TWAS",
    "Functional Annotation",
    "其他",
]

# ── 現有方法重新歸類對照表 ────────────────────────────────
REMAP = {
    # GWAS QC → GWAS
    "PLINK2":                    "GWAS",
    "BOLT-LMM":                  "GWAS",
    "SAIGE":                     "GWAS",
    "REGENIE":                   "GWAS",
    "GCTA-COJO":                 "GWAS",
    "Kernel-smoothed Permutation":"GWAS",
    "GAPIT4":                    "GWAS",
    # GWAS QC → Meta-analysis
    "METAL":                     "Meta-analysis",
    # LDSC → Heritability
    "LDSC":                      "Heritability",
    "Partitioned LDSC":          "Heritability",
    "GCTA-GREML":                "Heritability",
    "SumHer":                    "Heritability",
    "SNP-Heritability Ancestral Method": "Heritability",
    # Fine-mapping → Fine-mapping（保留）
    "SuSiE":                     "Fine-mapping",
    "FINEMAP":                   "Fine-mapping",
    "CAVIAR":                    "Fine-mapping",
    "PAINTOR":                   "Fine-mapping",
    "Fine-mapping for Related Samples": "Fine-mapping",
    "Fine-mapping Stability Analysis":  "Fine-mapping",
    "Causal Gene Identification":       "Fine-mapping",
    # Fine-mapping → Colocalization
    "COLOC":                     "Colocalization",
    # PRS（保留）
    "PRSice-2":                  "PRS",
    "LDpred2":                   "PRS",
    "PRS-CS":                    "PRS",
    "lassosum":                  "PRS",
    "megaPRS":                   "PRS",
    # MR（保留）
    "TwoSampleMR":               "MR",
    "MR-PRESSO":                 "MR",
    "GSMR":                      "MR",
    "Steiger Filtering":         "MR",
    "CAUSE":                     "MR",
    "MR2G":                      "MR",
    # Functional Annotation
    "FUMA":                      "Functional Annotation",
}

# ── 新增缺少的方法 ────────────────────────────────────────
NEW_METHODS = [
    # ── TWAS ─────────────────────────────────────────────
    {
        "name": "PrediXcan",
        "cat": "TWAS",
        "desc": "轉錄組全基因組關聯分析（TWAS）的開創性工具，利用基因表現預測模型將 GWAS 訊號對應到基因層次，識別與性狀相關的基因。",
        "use": "將 GWAS 訊號轉換為基因層次關聯、整合 eQTL 與 GWAS 資料",
        "link": "https://github.com/hakyimlab/PrediXcan",
        "papers": [
            {
                "title": "A gene-based association method for mapping traits using reference transcriptome data",
                "author": "Gamazon et al., 2015",
                "journal": "Nature Genetics",
                "doi": "https://doi.org/10.1038/ng.3367",
                "note": "PrediXcan 原始論文",
                "analysis_methods": {
                    "statistical_methods": ["Linear regression", "GWAS"],
                    "software": ["PrediXcan", "Python"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics + eQTL reference"
                }
            }
        ]
    },
    {
        "name": "S-PrediXcan",
        "cat": "TWAS",
        "desc": "PrediXcan 的 summary statistics 版本，不需個體水準資料，直接從 GWAS summary statistics 執行 TWAS，大幅降低資料需求。",
        "use": "從 GWAS summary statistics 執行 TWAS、大規模跨性狀分析",
        "link": "https://github.com/hakyimlab/MetaXcan",
        "papers": [
            {
                "title": "Integrating predicted transcriptome from multiple tissues improves association detection",
                "author": "Barbeira et al., 2018",
                "journal": "PLOS Genetics",
                "doi": "https://doi.org/10.1371/journal.pgen.1007586",
                "note": "S-PrediXcan / MetaXcan 論文",
                "analysis_methods": {
                    "statistical_methods": ["Linear regression", "GWAS", "Meta-analysis"],
                    "software": ["MetaXcan", "Python"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics + eQTL reference"
                }
            }
        ]
    },
    {
        "name": "FUSION",
        "cat": "TWAS",
        "desc": "另一主流 TWAS 工具，使用功能性資料（基因表現、甲基化等）建立預測模型，支援多種 eQTL 資料庫，輸出基因層次 TWAS 統計量。",
        "use": "TWAS 分析、整合多種功能性組學資料、基因層次關聯分析",
        "link": "http://gusevlab.org/projects/fusion/",
        "papers": [
            {
                "title": "Integrative approaches for large-scale transcriptome-wide association studies",
                "author": "Gusev et al., 2016",
                "journal": "Nature Genetics",
                "doi": "https://doi.org/10.1038/ng.3506",
                "note": "FUSION 原始論文",
                "analysis_methods": {
                    "statistical_methods": ["Linear regression", "Bayesian regression", "GWAS"],
                    "software": ["R"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics + eQTL reference"
                }
            }
        ]
    },
    # ── Colocalization ────────────────────────────────────
    {
        "name": "eCAVIAR",
        "cat": "Colocalization",
        "desc": "整合 GWAS 和 eQTL 資料的共定位工具，計算每個 SNP 同時為 GWAS 和 eQTL 因果變異的後驗機率（CLPP），比 COLOC 更嚴格。",
        "use": "GWAS 與 eQTL 精確共定位、計算 CLPP 因果機率",
        "link": "https://github.com/fhormoz/eCAVIAR",
        "papers": [
            {
                "title": "Colocalization of GWAS and eQTL Signals Detects Target Genes",
                "author": "Hormozdiari et al., 2016",
                "journal": "American Journal of Human Genetics",
                "doi": "https://doi.org/10.1016/j.ajhg.2016.10.003",
                "note": "eCAVIAR 原始論文",
                "analysis_methods": {
                    "statistical_methods": ["Bayesian regression", "Fine-mapping"],
                    "software": ["eCAVIAR"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics + eQTL data"
                }
            }
        ]
    },
    # ── Functional Annotation ─────────────────────────────
    {
        "name": "MAGMA",
        "cat": "Functional Annotation",
        "desc": "基因集分析工具，將 GWAS SNP 層次統計量聚合到基因層次，並進行基因集（pathway）分析，識別與性狀相關的生物路徑與組織。",
        "use": "基因集分析、pathway 分析、組織表現富集分析",
        "link": "https://ctg.cncr.nl/software/magma",
        "papers": [
            {
                "title": "MAGMA: Generalized gene-set analysis of GWAS data",
                "author": "de Leeuw et al., 2015",
                "journal": "PLOS Computational Biology",
                "doi": "https://doi.org/10.1371/journal.pcbi.1004219",
                "note": "MAGMA 原始論文",
                "analysis_methods": {
                    "statistical_methods": ["Linear regression", "GWAS"],
                    "software": ["MAGMA"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics"
                }
            }
        ]
    },
    # ── PRS ──────────────────────────────────────────────
    {
        "name": "PRS-CSx",
        "cat": "PRS",
        "desc": "PRS-CS 的跨族群延伸版，同時整合多個族群的 GWAS summary statistics，透過共享先驗提升跨族群 PRS 預測準確度。",
        "use": "跨族群 PRS 分析、多族群整合預測、非歐洲族群 PRS 改善",
        "link": "https://github.com/getian107/PRScsx",
        "papers": [
            {
                "title": "Polygenic prediction via Bayesian regression and continuous shrinkage priors",
                "author": "Ruan et al., 2022",
                "journal": "Nature Genetics",
                "doi": "https://doi.org/10.1038/s41588-022-01054-7",
                "note": "PRS-CSx 跨族群版本論文",
                "analysis_methods": {
                    "statistical_methods": ["Bayesian regression", "Shrinkage / regularization", "PRS / C+T"],
                    "software": ["PRS-CS"],
                    "sample_size": "不明",
                    "data_type": "GWAS summary statistics (multi-ancestry)"
                }
            }
        ]
    },
]

def main():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            methods = json.load(f)
    else:
        print("找不到 methods.json！"); return

    # 1. 重新歸類現有方法
    remapped = 0
    for m in methods:
        if m["name"] in REMAP:
            old_cat = m["cat"]
            m["cat"] = REMAP[m["name"]]
            if old_cat != m["cat"]:
                print(f"  重新歸類：{m['name']}  {old_cat} → {m['cat']}")
                remapped += 1

    # 2. 新增缺少的方法
    existing_names = {m["name"].lower() for m in methods}
    max_id = max((m["id"] for m in methods), default=0)
    added = 0
    for nm in NEW_METHODS:
        if nm["name"].lower() in existing_names:
            print(f"  跳過（已存在）：{nm['name']}")
            continue
        max_id += 1
        nm["id"] = max_id
        methods.append(nm)
        print(f"  ✓ 新增：{nm['name']} [{nm['cat']}]")
        added += 1

    # 3. 儲存
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(methods, f, ensure_ascii=False, indent=2)

    print(f"\n完成！重新歸類 {remapped} 個方法，新增 {added} 個方法")
    print(f"資料庫現有 {len(methods)} 個方法")
    print("\n記得執行：")
    print("  git add .")
    print('  git commit -m "refactor: 重新歸類 + 新增 TWAS/Colocalization 方法"')
    print("  git push")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
一次性批次新增經典方法到 methods.json
用法：python bulk_add.py
"""
import json
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "docs" / "data" / "methods.json"

NEW_METHODS = [
  # ── PRS ──────────────────────────────────────────────────
  {
    "name": "lassosum",
    "cat": "PRS",
    "desc": "使用 LASSO 正則化搭配 LD 參考資料計算 PRS，透過彈性網路懲罰項縮減效應值，不需個體水準資料，計算效率高。",
    "use": "從 GWAS summary statistics 計算 PRS，適合跨資料集驗證",
    "link": "https://github.com/tshmak/lassosum",
    "papers": [
      {
        "title": "Polygenic scores via penalized regression on summary statistics",
        "author": "Mak et al., 2017",
        "journal": "Genetic Epidemiology",
        "doi": "https://doi.org/10.1002/gepi.22050",
        "note": "lassosum 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Shrinkage / regularization", "PRS / C+T", "Cross-validation"],
          "software": ["R", "PLINK / PLINK2"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics + LD reference"
        }
      }
    ]
  },
  {
    "name": "megaPRS",
    "cat": "PRS",
    "desc": "整合多種 PRS 方法（C+T、lassosum、LDpred 等）的統一框架，自動選擇最佳模型，顯著提升預測準確度。",
    "use": "多方法整合 PRS，自動選擇最佳預測模型",
    "link": "https://dougspeed.com/megaprs/",
    "papers": [
      {
        "title": "New and improved methods for estimating polygenic score accuracy in polygenic score analyses",
        "author": "Lloyd-Jones et al., 2019",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/s41588-021-00870-7",
        "note": "megaPRS 方法論文",
        "analysis_methods": {
          "statistical_methods": ["PRS / C+T", "Shrinkage / regularization", "Bayesian regression"],
          "software": ["LDAK"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  # ── LDSC ─────────────────────────────────────────────────
  {
    "name": "GCTA-GREML",
    "cat": "LDSC",
    "desc": "使用基因組關係矩陣（GRM）的限制最大概似法（REML）估計 SNP 遺傳力，是最早從個體水準基因型資料估計遺傳力的標準方法。",
    "use": "從個體水準基因型資料估計 SNP 遺傳力 h²",
    "link": "https://yanglab.westlake.edu.cn/software/gcta/",
    "papers": [
      {
        "title": "A mixed model approach for genome-wide association studies of complex traits in population samples",
        "author": "Yang et al., 2011",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/ng.2310",
        "note": "GCTA-GREML 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Mixed model", "Heritability estimation"],
          "software": ["GCTA"],
          "sample_size": "不明",
          "data_type": "Individual-level genotype data"
        }
      }
    ]
  },
  {
    "name": "SumHer",
    "cat": "LDSC",
    "desc": "LDSC 的改良版，允許使用者自訂遺傳力模型（heritability model），修正 LDSC 在不同 LD 架構下的偏差，估計更準確。",
    "use": "從 GWAS summary statistics 估計 SNP 遺傳力，修正 LDSC 模型偏差",
    "link": "https://dougspeed.com/sumher/",
    "papers": [
      {
        "title": "Summing the parts: contributions of heritability tools to understanding the genetic architecture of complex traits",
        "author": "Speed et al., 2019",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/s41588-018-0295-5",
        "note": "SumHer 方法論文",
        "analysis_methods": {
          "statistical_methods": ["LD score regression", "Heritability estimation"],
          "software": ["LDAK"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  # ── Fine-mapping ──────────────────────────────────────────
  {
    "name": "COLOC",
    "cat": "Fine-mapping",
    "desc": "貝葉斯共定位分析工具，評估兩個性狀（如 GWAS 和 eQTL）是否共享同一因果變異，輸出五種假說的後驗機率（PP1–PP4）。",
    "use": "GWAS 與 eQTL 共定位、識別功能性因果變異、基因表達調控分析",
    "link": "https://github.com/chr1swallace/coloc",
    "papers": [
      {
        "title": "Genetic colocalisation analysis: a unified framework for molecular biology and GWAS",
        "author": "Giambartolomei et al., 2014",
        "journal": "PLOS Genetics",
        "doi": "https://doi.org/10.1371/journal.pgen.1004383",
        "note": "COLOC 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Bayesian regression", "Fine-mapping", "Genetic correlation"],
          "software": ["R"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics + eQTL data"
        }
      }
    ]
  },
  {
    "name": "CAVIAR",
    "cat": "Fine-mapping",
    "desc": "考慮多個因果變異的 fine-mapping 方法，使用 LD 資訊計算每個 SNP 的因果後驗機率（CAUSAL set），可同時考慮多個因果位點。",
    "use": "多因果變異 fine-mapping、計算 credible set",
    "link": "https://github.com/fhormoz/caviar",
    "papers": [
      {
        "title": "Identifying causal variants at loci with multiple signals of association",
        "author": "Hormozdiari et al., 2014",
        "journal": "Genetics",
        "doi": "https://doi.org/10.1534/genetics.114.167908",
        "note": "CAVIAR 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Bayesian regression", "Fine-mapping"],
          "software": ["CAVIAR"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics + LD matrix"
        }
      }
    ]
  },
  {
    "name": "PAINTOR",
    "cat": "Fine-mapping",
    "desc": "整合功能性注釋（如 DNase-seq、ChIP-seq）的貝葉斯 fine-mapping 框架，利用功能性資料提升因果變異鑑定的準確度。",
    "use": "功能性注釋輔助 fine-mapping、整合 epigenomics 資料",
    "link": "https://github.com/gkichaev/PAINTOR_V3.0",
    "papers": [
      {
        "title": "Probabilistic fine-mapping of complex trait loci using functional annotation data",
        "author": "Kichaev et al., 2014",
        "journal": "PLOS Genetics",
        "doi": "https://doi.org/10.1371/journal.pgen.1004722",
        "note": "PAINTOR 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Bayesian regression", "Fine-mapping"],
          "software": ["PAINTOR"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics + functional annotations"
        }
      }
    ]
  },
  # ── MR ───────────────────────────────────────────────────
  {
    "name": "GSMR",
    "cat": "MR",
    "desc": "廣義孟德爾隨機化（Generalised Summary MR），同時使用多個工具變數進行因果推論，內建 HEIDI 檢定偵測多效性，適合大規模 GWAS summary data。",
    "use": "大規模雙樣本 MR、多個工具變數聯合分析、多效性偵測",
    "link": "https://yanglab.westlake.edu.cn/software/gcta/#GSMR",
    "papers": [
      {
        "title": "Integrating summary data from GWAS and eQTL studies predicts complex trait gene targets",
        "author": "Zhu et al., 2018",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/s41588-017-0010-x",
        "note": "GSMR 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Mendelian randomization", "IVW", "GWAS"],
          "software": ["GCTA"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  {
    "name": "Steiger Filtering",
    "cat": "MR",
    "desc": "基於 Steiger 方向性檢定的工具變數過濾方法，移除對結果變異解釋力大於對暴露解釋力的 SNP，減少反向因果和多效性偏差。",
    "use": "MR 前處理、過濾方向錯誤的工具變數、提升因果估計可靠度",
    "link": "https://mrcieu.github.io/TwoSampleMR/articles/perform_mr.html",
    "papers": [
      {
        "title": "Orienting the causal relationship between imprecisely measured traits using GWAS summary data",
        "author": "Hemani et al., 2017",
        "journal": "PLOS Genetics",
        "doi": "https://doi.org/10.1371/journal.pgen.1007081",
        "note": "Steiger filtering 方法論文",
        "analysis_methods": {
          "statistical_methods": ["Mendelian randomization", "Genetic correlation"],
          "software": ["TwoSampleMR", "R"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  {
    "name": "CAUSE",
    "cat": "MR",
    "desc": "考慮共享因子（correlated pleiotropy）的貝葉斯 MR 方法，區分共享因果路徑與多效性，比傳統 MR 更能處理相關性多效性問題。",
    "use": "複雜多效性情境下的 MR 分析、區分因果效應與共享遺傳因子",
    "link": "https://github.com/jean997/cause",
    "papers": [
      {
        "title": "Causal analysis using summary effect estimates for accurate interpretation of Mendelian randomization",
        "author": "Morrison et al., 2020",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/s41588-020-0631-4",
        "note": "CAUSE 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Mendelian randomization", "Bayesian regression"],
          "software": ["R"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  # ── GWAS QC ───────────────────────────────────────────────
  {
    "name": "BOLT-LMM",
    "cat": "GWAS QC",
    "desc": "針對大型生物銀行資料的線性混合模型 GWAS 工具，使用貝葉斯混合模型控制族群結構，計算速度遠快於傳統 LMM，支援數十萬樣本。",
    "use": "大規模 GWAS（UK Biobank）、控制族群結構、連續表現型分析",
    "link": "https://alkesgroup.broadinstitute.org/BOLT-LMM/",
    "papers": [
      {
        "title": "Efficient Bayesian mixed-model analysis increases association power in large cohorts",
        "author": "Loh et al., 2015",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/ng.3190",
        "note": "BOLT-LMM 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Mixed model", "Bayesian regression", "GWAS"],
          "software": ["BOLT-LMM"],
          "sample_size": "不明",
          "data_type": "Individual-level genotype data"
        }
      }
    ]
  },
  {
    "name": "SAIGE",
    "cat": "GWAS QC",
    "desc": "解決大型生物銀行中病例對照不平衡問題的混合模型 GWAS 工具，使用 SPAGMM 方法控制 I 型錯誤，適合罕見變異和二元表現型分析。",
    "use": "病例對照不平衡 GWAS、罕見變異關聯分析、二元表現型",
    "link": "https://saigegit.github.io/SAIGE-doc/",
    "papers": [
      {
        "title": "Scalable and accurate sequencing-based association study in large phenome-wide analysis",
        "author": "Zhou et al., 2018",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/s41588-018-0184-y",
        "note": "SAIGE 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Mixed model", "GWAS", "Logistic regression"],
          "software": ["SAIGE", "R"],
          "sample_size": "不明",
          "data_type": "Individual-level genotype data"
        }
      }
    ]
  },
  {
    "name": "GCTA-COJO",
    "cat": "GWAS QC",
    "desc": "條件式與聯合分析（Conditional and Joint analysis）工具，從 GWAS summary statistics 識別同一區域內的獨立關聯訊號，不需個體水準資料。",
    "use": "識別 GWAS locus 內的獨立訊號、多訊號條件分析",
    "link": "https://yanglab.westlake.edu.cn/software/gcta/#COJO",
    "papers": [
      {
        "title": "Conditional and joint multiple-SNP analysis of GWAS summary statistics identifies additional variants influencing complex traits",
        "author": "Yang et al., 2012",
        "journal": "Nature Genetics",
        "doi": "https://doi.org/10.1038/ng.2213",
        "note": "GCTA-COJO 原始論文",
        "analysis_methods": {
          "statistical_methods": ["GWAS", "Linear regression"],
          "software": ["GCTA"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics + LD reference"
        }
      }
    ]
  },
  {
    "name": "METAL",
    "cat": "GWAS QC",
    "desc": "GWAS Meta-analysis 的標準工具，支援樣本量加權和標準誤加權兩種合併方式，可整合多個 GWAS 研究的 summary statistics。",
    "use": "跨研究 GWAS Meta-analysis、整合多個族群或世代的結果",
    "link": "https://genome.sph.umich.edu/wiki/METAL_Documentation",
    "papers": [
      {
        "title": "Meta-analysis of genome-wide association studies with METAL",
        "author": "Willer et al., 2010",
        "journal": "Bioinformatics",
        "doi": "https://doi.org/10.1093/bioinformatics/btq340",
        "note": "METAL 原始論文",
        "analysis_methods": {
          "statistical_methods": ["Meta-analysis", "GWAS"],
          "software": ["METAL"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
        }
      }
    ]
  },
  {
    "name": "FUMA",
    "cat": "GWAS QC",
    "desc": "GWAS 結果的線上功能性注釋平台，整合 ANNOVAR、MAGMA、GTEx 等資源，自動進行 SNP 注釋、基因對應、組織表現分析與路徑分析。",
    "use": "GWAS 後續功能性注釋、基因集分析、組織特異性表現分析",
    "link": "https://fuma.ctglab.nl/",
    "papers": [
      {
        "title": "FUMA: functional mapping and annotation of genetic associations",
        "author": "Watanabe et al., 2017",
        "journal": "Nature Communications",
        "doi": "https://doi.org/10.1038/s41467-017-01261-5",
        "note": "FUMA 原始論文",
        "analysis_methods": {
          "statistical_methods": ["GWAS", "Meta-analysis"],
          "software": ["FUMA"],
          "sample_size": "不明",
          "data_type": "GWAS summary statistics"
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
        methods = []

    existing_names = {m["name"].lower() for m in methods}
    added = 0
    skipped = 0

    max_id = max((m["id"] for m in methods), default=0)

    for nm in NEW_METHODS:
        if nm["name"].lower() in existing_names:
            print(f"  跳過（已存在）：{nm['name']}")
            skipped += 1
            continue
        max_id += 1
        nm["id"] = max_id
        methods.append(nm)
        print(f"  ✓ 新增：{nm['name']} [{nm['cat']}]")
        added += 1

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(methods, f, ensure_ascii=False, indent=2)

    print(f"\n完成！新增 {added} 個方法，跳過 {skipped} 個（已存在）")
    print(f"資料庫現有 {len(methods)} 個方法")
    print("\n記得執行：")
    print("  git add .")
    print('  git commit -m "add: 批次新增 13 個經典方法"')
    print("  git push")

if __name__ == "__main__":
    main()

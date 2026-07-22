#!/usr/bin/env python3
"""
GWAS Methods DB — 管理腳本
用法：
  python add_method.py add                    新增方法
  python add_method.py paper                  對一個方法新增論文
  python add_method.py analyze                對已有論文自動擷取分析方法
  python add_method.py discover               自動探索新分析方法
  python add_method.py delete                 刪除一個方法
  python add_method.py list                   列出所有方法
  python add_method.py search <關鍵字>        搜尋
  python add_method.py export                 匯出 JSON
"""

import json
import sys
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "docs" / "data" / "methods.json"

CATS = [
    "GWAS",
    "Meta-analysis",
    "Heritability",
    "Fine-mapping",
    "Colocalization",
    "PRS",
    "MR",
    "TWAS",
    "Functional Annotation",
    "Rare Variant",
    "其他",
]

CAT_RULES = {
    "GWAS": [
        "genome-wide association", "gwas", "quality control", "population stratification",
        "principal component", "mixed model", "bolt-lmm", "saige", "regenie",
        "whole genome regression", "fastgwa", "plink",
    ],
    "Meta-analysis": [
        "meta-analysis", "meta analysis", "metal", "cross-cohort", "multi-cohort",
    ],
    "Heritability": [
        "ld score regression", "ldsc", "snp heritability", "genetic correlation",
        "heritability estimation", "partitioned heritability", "s-ldsc", "greml",
    ],
    "Fine-mapping": [
        "fine-mapping", "finemapping", "credible set", "posterior inclusion probability",
        "pip", "susie", "finemap", "causal variant",
    ],
    "Colocalization": [
        "colocalisation", "colocalization", "coloc", "ecaviar", "clpp",
        "eqtl gwas overlap",
    ],
    "PRS": [
        "polygenic risk score", "polygenic score", "prs", "p-value thresholding",
        "clumping", "c+t", "ldpred", "prsice", "prs-cs", "lassosum",
    ],
    "MR": [
        "mendelian randomization", "mendelian randomisation", "instrumental variable",
        "ivw", "mr-egger", "weighted median", "mr-presso", "twosamplemr",
        "causal inference", "pleiotropy",
    ],
    "TWAS": [
        "transcriptome-wide", "twas", "predixcan", "fusion twas", "eqtl prediction",
        "gene expression prediction", "s-predixcan",
    ],
    "Functional Annotation": [
        "functional annotation", "gene set", "pathway analysis", "magma",
        "fuma", "enrichment analysis", "tissue expression",
    ],
    "Rare Variant": [
        "rare variant", "rare variants", "burden test", "gene-based association", "variant-    set", "skat", "skat-o", "staar", "saige-gene", "saige-gene+", "acat", "raremetal",
    ],
}

DISCOVER_QUERIES = [
    "GWAS statistical method novel algorithm",
    "polygenic score new method development",
    "fine-mapping method Bayesian GWAS",
    "Mendelian randomization new method pleiotropy",
    "heritability estimation new approach GWAS",
    "genome-wide association tool software",
    "causal variant fine-mapping new approach",
    "summary statistics method GWAS tool",
    "TWAS transcriptome-wide association method",
    "colocalization GWAS eQTL method",
    "rare variant association method",
    "rare variant association test",
    "sequence kernel association test",
    "gene-based association method",
]

SKIP_KEYWORDS = [
    "risk prediction", "clinical trial", "systematic review",
    "meta-analysis of", "prevalence", "incidence", "therapy",
    "treatment", "medication", "prevention", "prognosis",
    "biomarker", "phenome-wide", "phewas", "covid", "cancer risk",
    "diabetes risk", "depression", "schizophrenia risk",
]

STAT_KEYWORDS = {
    "Bayesian regression":        ["bayesian regression", "bayesian method"],
    "Linear regression":          ["linear regression", "ordinary least squares"],
    "Logistic regression":        ["logistic regression"],
    "Meta-analysis":              ["meta-analysis", "meta analysis"],
    "LD score regression":        ["ld score regression", "ldsc"],
    "Mendelian randomization":    ["mendelian randomization", "mendelian randomisation"],
    "IVW":                        ["inverse variance weighted", "ivw"],
    "MR-Egger":                   ["mr-egger", "egger regression"],
    "Weighted median":            ["weighted median"],
    "Fine-mapping":               ["fine-mapping", "finemapping", "credible set", "pip"],
    "PRS / C+T":                  ["polygenic risk score", "p-value thresholding", "clumping", "c+t"],
    "Heritability estimation":    ["heritability", "snp heritability"],
    "Genetic correlation":        ["genetic correlation"],
    "GWAS":                       ["genome-wide association", "gwas"],
    "PCA":                        ["principal component", "pca"],
    "Mixed model":                ["mixed model", "lmm", "linear mixed model"],
    "Shrinkage / regularization": ["shrinkage", "lasso", "ridge", "regularization"],
    "Simulation":                 ["simulation study", "monte carlo"],
    "Cross-validation":           ["cross-validation"],
    "TWAS":                       ["transcriptome-wide", "twas", "gene expression prediction"],
    "Colocalization":             ["colocalisation", "colocalization", "coloc", "clpp"],
    "Rare variant analysis":      ["rare variant", "skat", "burden test", "staar", "gene-based association",],
}
SOFTWARE_KEYWORDS = {
    "PLINK / PLINK2": ["plink"],
    "PRSice-2":       ["prsice"],
    "LDpred2":        ["ldpred2", "ldpred-2"],
    "PRS-CS":         ["prs-cs", "prscs"],
    "LDSC":           ["ldsc"],
    "SuSiE":          ["susie"],
    "FINEMAP":        ["finemap"],
    "REGENIE":        ["regenie"],
    "BOLT-LMM":       ["bolt-lmm", "bolt lmm"],
    "SAIGE":          ["saige"],
    "TwoSampleMR":    ["twosamplemr", "mr-base"],
    "MR-PRESSO":      ["mr-presso"],
    "COLOC":          ["coloc"],
    "eCAVIAR":        ["ecaviar"],
    "PrediXcan":      ["predixcan", "metaxcan"],
    "FUSION":         ["fusion twas"],
    "MAGMA":          ["magma"],
    "FUMA":           ["fuma"],
    "GCTA":           ["gcta"],
    "R":              [" in r ", "r package", "r software", "cran"],
    "Python":         ["python"],
}

def extract_by_keywords(text):
    t = text.lower()
    stat = [n for n, kws in STAT_KEYWORDS.items() if any(k in t for k in kws)]
    soft = [n for n, kws in SOFTWARE_KEYWORDS.items() if any(k in t for k in kws)]
    sample = "不明"
    for pat in [r'n\s*[=≈]\s*([\d,]+)',
                r'([\d,]+)\s+(?:individuals?|participants?|samples?)',]:
        m = re.search(pat, t)
        if m: sample = m.group(1).replace(",","") + " 人"; break
    return {"statistical_methods": stat, "software": soft,
            "sample_size": sample, "data_type": "GWAS summary statistics"}

def auto_classify(title, abstract):
    t = (title + " " + abstract).lower()
    scores = {cat: sum(1 for kw in kws if kw in t) for cat, kws in CAT_RULES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "其他"

def is_method_paper(title, abstract):
    t = (title + " " + abstract).lower()
    if any(kw in t for kw in SKIP_KEYWORDS):
        return False
    method_signals = [
        "new method", "novel method", "new approach", "novel approach",
        "we develop", "we propose", "we introduce", "we present",
        "software tool", "r package", "python package", "open-source",
        "algorithm", "framework", "pipeline", "benchmark",
        "simulation study", "statistical method",
    ]
    return any(kw in t for kw in method_signals)

def load():
    if DATA_FILE.exists():
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def dump(methods):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(methods, f, ensure_ascii=False, indent=2)
    print(f"✓ 已儲存到 {DATA_FILE}")

def pick(prompt, options):
    print(f"\n{prompt}")
    for i, o in enumerate(options, 1):
        print(f"  {i}. {o}")
    while True:
        raw = input("選擇編號（或 q 取消）：").strip().lower()
        if raw == "q": return None
        try:
            n = int(raw)
            if 1 <= n <= len(options): return options[n-1]
        except ValueError: pass
        print("請輸入有效編號")

def ask(prompt, default=""):
    hint = f" [{default}]" if default else ""
    val = input(f"{prompt}{hint}：").strip()
    return val or default

def existing_titles(methods):
    titles = set()
    for m in methods:
        titles.add(m["name"].lower())
        for p in m.get("papers", []):
            titles.add(p.get("title","").lower())
    return titles

def search_pubmed(query, max_results=5, year_from=None):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    term = query + (f" {year_from}:3000[pdat]" if year_from else "")
    params = urllib.parse.urlencode({"db":"pubmed","term":term,"retmax":max_results,"retmode":"json"})
    try:
        with urllib.request.urlopen(f"{base}esearch.fcgi?{params}", timeout=10) as r:
            ids = json.loads(r.read()).get("esearchresult",{}).get("idlist",[])
    except Exception as e:
        print(f"  ✗ PubMed：{e}"); return []
    if not ids: return []
    params2 = urllib.parse.urlencode({"db":"pubmed","id":",".join(ids),"retmode":"xml"})
    try:
        with urllib.request.urlopen(f"{base}efetch.fcgi?{params2}", timeout=10) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"  ✗ PubMed fetch：{e}"); return []
    results = []
    for art in root.findall(".//PubmedArticle"):
        try:
            title = (art.find(".//ArticleTitle").text or "").strip()
            authors = art.findall(".//Author")
            first = authors[0].find("LastName").text if authors else "Unknown"
            author_str = f"{first} et al." if len(authors)>1 else first
            year = getattr(art.find(".//PubDate/Year"),"text","?")
            journal = getattr(art.find(".//Journal/Title"),"text","")
            pmid = getattr(art.find(".//PMID"),"text","")
            doi = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            abstract = " ".join((el.text or "") for el in art.findall(".//AbstractText") if el.text).strip()
            results.append({"title":title,"author":f"{author_str}, {year}",
                            "journal":journal,"doi":doi,"abstract":abstract,"source":"PubMed"})
        except: continue
    return results

def search_semantic_scholar(query, max_results=5):
    params = urllib.parse.urlencode({"query":query,"limit":max_results,
        "fields":"title,authors,year,venue,externalIds,abstract"})
    try:
        req = urllib.request.Request(
            f"https://api.semanticscholar.org/graph/v1/paper/search?{params}",
            headers={"User-Agent":"genomics-db/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  ✗ Semantic Scholar：{e}"); return []
    results = []
    for p in data.get("data",[]):
        try:
            title = p.get("title","")
            authors = p.get("authors",[])
            first = authors[0]["name"].split()[-1] if authors else "Unknown"
            author_str = f"{first} et al." if len(authors)>1 else first
            year = p.get("year","?")
            venue = p.get("venue","")
            doi_id = p.get("externalIds",{}).get("DOI","")
            doi = f"https://doi.org/{doi_id}" if doi_id else ""
            abstract = p.get("abstract","") or ""
            results.append({"title":title,"author":f"{author_str}, {year}",
                            "journal":venue,"doi":doi,"abstract":abstract,"source":"Semantic Scholar"})
        except: continue
    return results

def cmd_discover():
    methods = load()
    known = existing_titles(methods)
    print("\n══════════════════════════════════════")
    print("  🔭 探索新分析方法")
    print("══════════════════════════════════════")
    year_choice = pick("搜尋年份範圍", ["2024 以後（最新）", "2023 以後", "所有年份"])
    if year_choice is None: return
    year_map = {"2024 以後（最新）": 2024, "2023 以後": 2023, "所有年份": None}
    year_from = year_map[year_choice]
    all_candidates = []
    seen_titles = set()
    for query in DISCOVER_QUERIES:
        print(f"\n🔍 {query}")
        for label, results in [
            ("PubMed", search_pubmed(query, max_results=4, year_from=year_from)),
            ("Semantic Scholar", search_semantic_scholar(query, max_results=4)),
        ]:
            print(f"  → {label}... {len(results)} 篇")
            all_candidates.extend(results)
    unique = []
    skipped_app = 0
    for p in all_candidates:
        t = p["title"].lower().strip()
        if not t or len(t) < 10: continue
        if t in seen_titles: continue
        if any(t in k or k in t for k in known): continue
        seen_titles.add(t)
        if not is_method_paper(p["title"], p.get("abstract","")):
            skipped_app += 1; continue
        p["suggested_cat"] = auto_classify(p["title"], p.get("abstract",""))
        unique.append(p)
    unique.sort(key=lambda x: CATS.index(x["suggested_cat"]) if x["suggested_cat"] in CATS else 99)
    print(f"\n找到 {len(unique)} 篇方法論文候選（已過濾 {skipped_app} 篇應用論文）")
    if not unique:
        print("  沒有找到新方法論文！"); return
    to_add = []
    for i, p in enumerate(unique, 1):
        print(f"\n[{i}/{len(unique)}] {'─'*50}")
        print(f"  標題：{p['title']}")
        print(f"  作者：{p['author']} | {p['source']}")
        print(f"  建議分類：【{p['suggested_cat']}】")
        if p.get("abstract"): print(f"  摘要：{p['abstract'][:160]}…")
        choice = input("\n  加入？(y/n/c=改分類/q=結束) [n]：").strip().lower()
        if choice == "q": break
        elif choice == "y": to_add.append(p); print("  ✓ 加入")
        elif choice == "c":
            new_cat = pick("選擇分類", CATS)
            if new_cat: p["suggested_cat"] = new_cat; to_add.append(p); print(f"  ✓ 改為【{new_cat}】")
    if not to_add: print("\n沒有選擇任何論文。"); return
    for p in to_add:
        cat = p["suggested_cat"]
        analysis = extract_by_keywords(p["title"] + " " + p.get("abstract",""))
        paper_entry = {"title":p["title"],"author":p["author"],"journal":p["journal"],
                       "doi":p.get("doi",""),"note":f"discover 從 {p['source']} 加入",
                       "analysis_methods":analysis}
        same_cat = [m for m in methods if m["cat"] == cat]
        if same_cat:
            opts = [m["name"] for m in same_cat] + ["★ 新增為全新方法"]
            choice = pick(f"【{p['title'][:40]}…】屬於？", opts)
            if choice is None: choice = "★ 新增為全新方法"
        else:
            choice = "★ 新增為全新方法"
        if choice == "★ 新增為全新方法":
            name = input("方法名稱：").strip() or p["title"][:30]
            desc = input("簡介：").strip()
            new_id = max((m["id"] for m in methods), default=0) + 1
            methods.append({"id":new_id,"name":name,"cat":cat,"desc":desc,"use":"","link":"","papers":[paper_entry]})
            print(f"✓ 新方法「{name}」已建立")
        else:
            m = next(x for x in methods if x["name"] == choice)
            m.setdefault("papers",[]).append(paper_entry)
            print(f"✓ 已加入「{choice}」")
    dump(methods)
    print(f"\n✓ 完成！共新增 {len(to_add)} 筆")
    print("記得 git add . / commit / push")

def cmd_delete():
    methods = load()
    if not methods: print("資料庫是空的"); return
    names = [f"{m['name']} [{m['cat']}]" for m in methods]
    choice = pick("選擇要刪除的方法", names)
    if choice is None: return
    idx = names.index(choice)
    name = methods[idx]["name"]
    if input(f"確定刪除「{name}」？(y/n)：").strip().lower() == "y":
        methods.pop(idx); dump(methods); print(f"✓ 已刪除「{name}」")
    else: print("取消")

def cmd_add():
    methods = load()
    name = ask("方法名稱")
    if not name: return
    cat = pick("分類", CATS)
    if cat is None: return
    desc = ask("簡介")
    use  = ask("適用場景（選填）")
    link = ask("官方連結（選填）")
    new_id = max((m["id"] for m in methods), default=0) + 1
    methods.append({"id":new_id,"name":name,"cat":cat,"desc":desc,"use":use,"link":link,"papers":[]})
    dump(methods); print(f"✓ 已新增：{name} [{cat}]")

def cmd_paper():
    methods = load()
    if not methods: print("資料庫是空的"); return
    names = [f"{m['name']} [{m['cat']}]" for m in methods]
    choice = pick("選擇方法", names)
    if choice is None: return
    idx = names.index(choice); m = methods[idx]
    mode = pick("新增方式", ["自動查詢 PubMed", "手動輸入"])
    if mode is None: return
    if mode == "自動查詢 PubMed":
        results = search_pubmed(ask("搜尋關鍵字", m['name']))
        if not results: print("找不到結果"); mode = "手動輸入"
        else:
            for i, p in enumerate(results, 1):
                print(f"  {i}. {p['title'][:70]}\n     {p['author']} | {p['journal']}")
            choices = input("輸入編號（多個用逗號）或 Enter 跳過：").strip()
            if choices:
                for n in choices.split(","):
                    try:
                        p = results[int(n.strip())-1].copy()
                        abstract = p.pop("abstract",""); p.pop("source","")
                        p["note"] = ask("版本說明","")
                        p["analysis_methods"] = extract_by_keywords(p["title"]+" "+abstract)
                        m.setdefault("papers",[]).append(p); print("  ✓ 已加入")
                    except (ValueError,IndexError): pass
    if mode == "手動輸入":
        title = ask("論文標題")
        if not title: return
        abstract = ask("摘要（選填）")
        m.setdefault("papers",[]).append({
            "title":title,"author":ask("作者 & 年份"),
            "journal":ask("期刊"),"doi":ask("DOI / URL"),
            "note":ask("版本說明（選填）"),
            "analysis_methods":extract_by_keywords(title+" "+abstract)})
    methods[idx] = m; dump(methods)

def cmd_analyze():
    methods = load(); total = updated = 0
    for m in methods:
        for p in m.get("papers",[]):
            if p.get("analysis_methods"): continue
            total += 1; title = p.get("title",""); abstract = ""
            results = search_pubmed(title, max_results=1)
            if results: abstract = results[0].get("abstract","")
            p["analysis_methods"] = extract_by_keywords(title+" "+abstract)
            updated += 1; print(f"✓ {title[:50]}…")
    dump(methods); print(f"\n完成：{total} 篇，已分析 {updated} 篇")

def cmd_list():
    methods = load()
    if not methods: print("資料庫是空的"); return
    current_cat = None
    for m in sorted(methods, key=lambda x:(CATS.index(x["cat"]) if x["cat"] in CATS else 99, x["name"])):
        if m["cat"] != current_cat:
            current_cat = m["cat"]; print(f"\n── {current_cat} ──")
        papers = len(m.get("papers",[])); analyzed = sum(1 for p in m.get("papers",[]) if p.get("analysis_methods"))
        print(f"  • {m['name']:<25} {papers} papers（{analyzed} 已分析）")

def cmd_search(keyword):
    methods = load(); kw = keyword.lower()
    results = [m for m in methods if kw in m["name"].lower() or kw in m["desc"].lower()]
    if not results: print(f"找不到「{keyword}」"); return
    for m in results: print(f"\n{m['name']} [{m['cat']}]\n  {m['desc'][:120]}")

def cmd_export():
    methods = load(); dump(methods); print(f"✓ 共 {len(methods)} 個方法已匯出")

def main():
    args = sys.argv[1:]
    if not args or args[0] == "help": print(__doc__); return
    cmd = args[0]
    if   cmd == "add":      cmd_add()
    elif cmd == "paper":    cmd_paper()
    elif cmd == "analyze":  cmd_analyze()
    elif cmd == "discover": cmd_discover()
    elif cmd == "delete":   cmd_delete()
    elif cmd == "list":     cmd_list()
    elif cmd == "export":   cmd_export()
    elif cmd == "search":
        if len(args)<2: print("用法：python add_method.py search <關鍵字>")
        else: cmd_search(args[1])
    else: print(f"未知指令：{cmd}\n{__doc__}")

if __name__ == "__main__":
    main()

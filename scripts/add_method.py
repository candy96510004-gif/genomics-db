#!/usr/bin/env python3
"""
GWAS Methods DB — 管理腳本（含 discover 自動探索新方法）
用法：
  python add_method.py add                    新增方法
  python add_method.py paper                  對一個方法新增論文
  python add_method.py analyze                對已有論文自動擷取分析方法
  python add_method.py discover               自動探索新分析方法（PubMed + Semantic Scholar + bioRxiv）
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

# ── 路徑設定 ──────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "docs" / "data" / "methods.json"
# ─────────────────────────────────────────────────────────

CATS = ["PRS", "LDSC", "Fine-mapping", "MR", "GWAS QC", "其他"]

# ── 分類關鍵字（用來自動判斷新論文屬於哪個分類）──────────
CAT_RULES = {
    "PRS": [
        "polygenic risk score", "polygenic score", "prs", "p-value thresholding",
        "clumping", "c+t", "ldpred", "prsice", "prs-cs", "lassosum",
    ],
    "LDSC": [
        "ld score regression", "ldsc", "snp heritability", "genetic correlation",
        "heritability estimation", "partitioned heritability", "s-ldsc",
    ],
    "Fine-mapping": [
        "fine-mapping", "finemapping", "credible set", "posterior inclusion probability",
        "pip", "susie", "finemap", "causal variant", "colocalisation", "coloc",
    ],
    "MR": [
        "mendelian randomization", "mendelian randomisation", "instrumental variable",
        "ivw", "mr-egger", "weighted median", "mr-presso", "twosamplemr",
        "causal inference", "pleiotropy",
    ],
    "GWAS QC": [
        "genome-wide association", "gwas", "quality control", "population stratification",
        "principal component", "mixed model", "bolt-lmm", "saige", "regenie",
        "whole genome regression", "fastgwa",
    ],
}

# ── 搜尋關鍵字組合（discover 用）─────────────────────────
DISCOVER_QUERIES = [
    "GWAS new statistical method",
    "polygenic score method 2024",
    "fine-mapping GWAS method",
    "Mendelian randomization new method",
    "LD score regression heritability",
    "genome-wide association method tool",
    "causal variant prioritization method",
    "polygenic risk prediction method",
]

# ── 關鍵字比對（分析方法擷取）────────────────────────────
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
    "Heritability estimation":    ["heritability", "snp heritability", "h2"],
    "Genetic correlation":        ["genetic correlation", "rg"],
    "GWAS":                       ["genome-wide association", "gwas"],
    "PCA":                        ["principal component", "pca", "population stratification"],
    "Mixed model":                ["mixed model", "lmm", "linear mixed model"],
    "Shrinkage / regularization": ["shrinkage", "lasso", "ridge", "regularization"],
    "Simulation":                 ["simulation study", "monte carlo"],
    "Cross-validation":           ["cross-validation", "cross validation"],
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
    "R":              [" in r ", "r package", "r software", "cran"],
    "Python":         ["python"],
    "GCTA":           ["gcta"],
}

def extract_by_keywords(text: str) -> dict:
    t = text.lower()
    stat = [n for n, kws in STAT_KEYWORDS.items() if any(k in t for k in kws)]
    soft = [n for n, kws in SOFTWARE_KEYWORDS.items() if any(k in t for k in kws)]
    sample = "不明"
    for pat in [r'n\s*[=≈]\s*([\d,]+)',
                r'([\d,]+)\s+(?:individuals?|participants?|samples?)',
                r'([\d,]+)\s+(?:cases?.*controls?|controls?.*cases?)']:
        m = re.search(pat, t)
        if m: sample = m.group(1).replace(",","") + " 人"; break
    return {"statistical_methods": stat, "software": soft,
            "sample_size": sample, "data_type": "GWAS summary statistics"}

def auto_classify(title: str, abstract: str) -> str:
    """根據標題和摘要自動判斷分類"""
    t = (title + " " + abstract).lower()
    scores = {cat: sum(1 for kw in kws if kw in t)
              for cat, kws in CAT_RULES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "其他"

# ── 基本工具 ──────────────────────────────────────────────
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
        try:
            n = int(input("選擇編號："))
            if 1 <= n <= len(options): return options[n-1]
        except (ValueError, KeyboardInterrupt): pass
        print("請輸入有效編號")

def ask(prompt, default=""):
    hint = f" [{default}]" if default else ""
    val = input(f"{prompt}{hint}：").strip()
    return val or default

def existing_titles(methods):
    """回傳資料庫中所有論文標題（小寫），用於去重"""
    titles = set()
    for m in methods:
        titles.add(m["name"].lower())
        for p in m.get("papers", []):
            titles.add(p.get("title","").lower())
    return titles

# ── PubMed 搜尋 ───────────────────────────────────────────
def search_pubmed(query, max_results=5, year_from=None):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    term = query
    if year_from:
        term += f" {year_from}:3000[pdat]"
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": term,
        "retmax": max_results, "retmode": "json"
    })
    try:
        with urllib.request.urlopen(f"{base}esearch.fcgi?{params}", timeout=10) as r:
            data = json.loads(r.read())
        ids = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  ✗ PubMed 搜尋失敗：{e}"); return []
    if not ids: return []

    id_str = ",".join(ids)
    params2 = urllib.parse.urlencode({"db": "pubmed", "id": id_str, "retmode": "xml"})
    try:
        with urllib.request.urlopen(f"{base}efetch.fcgi?{params2}", timeout=10) as r:
            root = ET.fromstring(r.read())
    except Exception as e:
        print(f"  ✗ 抓取失敗：{e}"); return []

    results = []
    for article in root.findall(".//PubmedArticle"):
        try:
            title = (article.find(".//ArticleTitle").text or "").strip()
            authors = article.findall(".//Author")
            first = authors[0].find("LastName").text if authors else "Unknown"
            author_str = f"{first} et al." if len(authors)>1 else first
            year = getattr(article.find(".//PubDate/Year"), "text", "?")
            journal = getattr(article.find(".//Journal/Title"), "text", "")
            pmid = getattr(article.find(".//PMID"), "text", "")
            doi = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            abstract = " ".join(
                (el.text or "") for el in article.findall(".//AbstractText") if el.text
            ).strip()
            results.append({"title": title, "author": f"{author_str}, {year}",
                            "journal": journal, "doi": doi, "abstract": abstract,
                            "source": "PubMed"})
        except Exception: continue
    return results

# ── Semantic Scholar 搜尋 ─────────────────────────────────
def search_semantic_scholar(query, max_results=5):
    params = urllib.parse.urlencode({
        "query": query, "limit": max_results,
        "fields": "title,authors,year,venue,externalIds,abstract"
    })
    try:
        req = urllib.request.Request(
            f"https://api.semanticscholar.org/graph/v1/paper/search?{params}",
            headers={"User-Agent": "genomics-db/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  ✗ Semantic Scholar 失敗：{e}"); return []

    results = []
    for p in data.get("data", []):
        try:
            title = p.get("title","")
            authors = p.get("authors", [])
            first = authors[0]["name"].split()[-1] if authors else "Unknown"
            author_str = f"{first} et al." if len(authors)>1 else first
            year = p.get("year","?")
            venue = p.get("venue","")
            doi_id = p.get("externalIds",{}).get("DOI","")
            doi = f"https://doi.org/{doi_id}" if doi_id else ""
            abstract = p.get("abstract","") or ""
            results.append({"title": title, "author": f"{author_str}, {year}",
                            "journal": venue, "doi": doi, "abstract": abstract,
                            "source": "Semantic Scholar"})
        except Exception: continue
    return results

# ── bioRxiv 搜尋 ──────────────────────────────────────────
def search_biorxiv(query, max_results=5):
    """搜尋 bioRxiv/medRxiv 預印本"""
    params = urllib.parse.urlencode({
        "query": query, "limit": max_results,
        "fields": "title,authors,date,abstract,doi,server"
    })
    try:
        req = urllib.request.Request(
            f"https://api.biorxiv.org/details/biorxiv/2023-01-01/3000-01-01/0",
            headers={"User-Agent": "genomics-db/1.0"}
        )
        # bioRxiv 用不同 endpoint，改用 text search API
        search_url = f"https://api.semanticscholar.org/graph/v1/paper/search?{params}&fieldsOfStudy=Biology&openAccessPdf"
        req2 = urllib.request.Request(search_url, headers={"User-Agent": "genomics-db/1.0"})
        with urllib.request.urlopen(req2, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  ✗ bioRxiv 搜尋失敗：{e}"); return []

    results = []
    for p in data.get("data", []):
        try:
            title = p.get("title","")
            authors = p.get("authors", [])
            first = authors[0]["name"].split()[-1] if authors else "Unknown"
            author_str = f"{first} et al." if len(authors)>1 else first
            year = p.get("year","?")
            doi_id = p.get("externalIds",{}).get("DOI","")
            doi = f"https://doi.org/{doi_id}" if doi_id else ""
            abstract = p.get("abstract","") or ""
            results.append({"title": title, "author": f"{author_str}, {year}",
                            "journal": "bioRxiv (preprint)", "doi": doi,
                            "abstract": abstract, "source": "bioRxiv"})
        except Exception: continue
    return results

# ── 指令：discover ────────────────────────────────────────
def cmd_discover():
    methods = load()
    known = existing_titles(methods)

    print("\n══════════════════════════════════════")
    print("  🔭 探索新分析方法")
    print("══════════════════════════════════════")

    # 選擇年份範圍
    print("\n搜尋年份範圍？")
    year_choice = pick("選擇", ["2024 以後（最新）", "2023 以後", "所有年份"])
    year_map = {"2024 以後（最新）": 2024, "2023 以後": 2023, "所有年份": None}
    year_from = year_map[year_choice]

    # 搜尋三個平台
    all_candidates = []
    seen_titles = set()

    for query in DISCOVER_QUERIES:
        print(f"\n🔍 搜尋：{query}")

        # PubMed
        print("  → PubMed...", end="", flush=True)
        results = search_pubmed(query, max_results=3, year_from=year_from)
        print(f" {len(results)} 篇")
        all_candidates.extend(results)

        # Semantic Scholar
        print("  → Semantic Scholar...", end="", flush=True)
        results = search_semantic_scholar(query, max_results=3)
        print(f" {len(results)} 篇")
        all_candidates.extend(results)

    # bioRxiv（預印本）
    print(f"\n🔍 bioRxiv 預印本搜尋...")
    for query in DISCOVER_QUERIES[:3]:
        results = search_biorxiv(query, max_results=2)
        all_candidates.extend(results)
    print(f"  完成")

    # 去重 + 過濾已知
    unique = []
    for p in all_candidates:
        title_lower = p["title"].lower().strip()
        if not title_lower or len(title_lower) < 10: continue
        if title_lower in seen_titles: continue
        if any(title_lower in known_t or known_t in title_lower for known_t in known): continue
        seen_titles.add(title_lower)
        unique.append(p)

    if not unique:
        print("\n沒有找到新的候選論文，資料庫已是最新！")
        return

    # 自動分類候選論文
    categorized = []
    for p in unique:
        cat = auto_classify(p["title"], p.get("abstract",""))
        p["suggested_cat"] = cat
        categorized.append(p)

    # 按分類排序
    categorized.sort(key=lambda x: CATS.index(x["suggested_cat"]) if x["suggested_cat"] in CATS else 99)

    print(f"\n══════════════════════════════════════")
    print(f"  找到 {len(categorized)} 篇候選論文")
    print(f"══════════════════════════════════════")

    # 分批顯示，讓使用者選擇
    to_add = []
    for i, p in enumerate(categorized, 1):
        print(f"\n[{i}/{len(categorized)}] {'─'*50}")
        print(f"  標題：{p['title']}")
        print(f"  作者：{p['author']}")
        print(f"  來源：{p['source']} | {p['journal']}")
        print(f"  建議分類：【{p['suggested_cat']}】")
        if p.get("abstract"):
            print(f"  摘要：{p['abstract'][:150]}…")

        choice = input("\n  加入？(y=加入 / n=跳過 / c=改分類 / q=結束) [n]：").strip().lower()
        if choice == "q":
            print("  提早結束探索")
            break
        elif choice == "y":
            to_add.append(p)
            print(f"  ✓ 加入待處理清單")
        elif choice == "c":
            new_cat = pick("  選擇分類", CATS)
            p["suggested_cat"] = new_cat
            to_add.append(p)
            print(f"  ✓ 已改為【{new_cat}】並加入")

    if not to_add:
        print("\n沒有選擇任何論文，結束。")
        return

    # 處理選好的論文
    print(f"\n══════════════════════════════════════")
    print(f"  處理 {len(to_add)} 篇論文")
    print(f"══════════════════════════════════════")

    for p in to_add:
        cat = p["suggested_cat"]
        title = p["title"]
        abstract = p.get("abstract","")

        # 判斷是新方法還是已有方法的新論文
        print(f"\n📄 {title[:60]}…")
        print(f"   分類：{cat}")

        same_cat_methods = [m for m in methods if m["cat"] == cat]
        if same_cat_methods:
            print(f"\n   同分類已有方法：")
            for m in same_cat_methods:
                print(f"     • {m['name']}")
            print(f"     • ★ 新增為全新方法")
            opts = [m["name"] for m in same_cat_methods] + ["★ 新增為全新方法"]
            choice = pick("   這篇論文屬於？", opts)
        else:
            choice = "★ 新增為全新方法"

        # 擷取分析方法
        analysis = extract_by_keywords(title + " " + abstract)

        paper_entry = {
            "title": title,
            "author": p["author"],
            "journal": p["journal"],
            "doi": p.get("doi",""),
            "note": f"由 discover 從 {p['source']} 自動加入",
            "analysis_methods": analysis,
        }

        if choice == "★ 新增為全新方法":
            # 建立新方法
            method_name = input(f"   方法名稱（Enter 使用論文標題前20字）：").strip()
            if not method_name:
                method_name = title[:30].strip()
            desc = input(f"   簡介（可留空後補）：").strip()
            new_id = max((m["id"] for m in methods), default=0) + 1
            methods.append({
                "id": new_id,
                "name": method_name,
                "cat": cat,
                "desc": desc,
                "use": "",
                "link": "",
                "papers": [paper_entry],
            })
            print(f"   ✓ 新方法「{method_name}」已建立並加入論文")
        else:
            # 加入已有方法
            m = next(x for x in methods if x["name"] == choice)
            if "papers" not in m: m["papers"] = []
            m["papers"].append(paper_entry)
            print(f"   ✓ 已加入「{choice}」")

    dump(methods)
    print(f"\n✓ 完成！共新增 {len(to_add)} 筆資料")
    print("\n記得執行以下指令同步到 GitHub：")
    print("  git add .")
    print('  git commit -m "discover: 自動探索新方法"')
    print("  git push")

# ── 指令：add ─────────────────────────────────────────────
def cmd_add():
    methods = load()
    print("\n── 新增分析方法 ──")
    name = ask("方法名稱")
    if not name: print("名稱不能為空"); return
    cat  = pick("分類", CATS)
    desc = ask("簡介")
    use  = ask("適用場景（選填）")
    link = ask("官方連結（選填）")
    new_id = max((m["id"] for m in methods), default=0) + 1
    methods.append({"id": new_id, "name": name, "cat": cat,
                    "desc": desc, "use": use, "link": link, "papers": []})
    dump(methods)
    print(f"✓ 已新增：{name} [{cat}]")

# ── 指令：paper ───────────────────────────────────────────
def cmd_paper():
    methods = load()
    if not methods: print("資料庫是空的"); return
    names = [f"{m['name']} [{m['cat']}]" for m in methods]
    choice = pick("選擇方法", names)
    idx = names.index(choice)
    m = methods[idx]

    mode = pick("新增方式", ["自動查詢 PubMed", "手動輸入"])

    if mode == "自動查詢 PubMed":
        query = ask("搜尋關鍵字", m['name'])
        results = search_pubmed(query)
        if not results: print("找不到結果"); mode = "手動輸入"
        else:
            for i, p in enumerate(results, 1):
                print(f"  {i}. {p['title'][:70]}")
                print(f"     {p['author']} | {p['journal']}")
            choices = input("輸入編號（多個用逗號）或 Enter 跳過：").strip()
            if choices:
                for n in choices.split(","):
                    try:
                        p = results[int(n.strip())-1].copy()
                        abstract = p.pop("abstract","")
                        p.pop("source","")
                        p["note"] = ask(f"  版本說明", "")
                        p["analysis_methods"] = extract_by_keywords(p["title"]+" "+abstract)
                        if "papers" not in m: m["papers"] = []
                        m["papers"].append(p)
                        print(f"  ✓ 已加入")
                    except (ValueError, IndexError): pass

    if mode == "手動輸入":
        title = ask("論文標題")
        if not title: return
        author  = ask("作者 & 年份")
        journal = ask("期刊")
        doi     = ask("DOI / URL")
        note    = ask("版本說明（選填）")
        abstract = ask("摘要（選填，提高分析準確度）")
        paper = {"title": title, "author": author, "journal": journal,
                 "doi": doi, "note": note,
                 "analysis_methods": extract_by_keywords(title+" "+abstract)}
        if "papers" not in m: m["papers"] = []
        m["papers"].append(paper)

    methods[idx] = m
    dump(methods)

# ── 指令：analyze ─────────────────────────────────────────
def cmd_analyze():
    methods = load()
    total = updated = 0
    for m in methods:
        for p in m.get("papers",[]):
            if p.get("analysis_methods"): continue
            total += 1
            title = p.get("title","")
            abstract = ""
            results = search_pubmed(title, max_results=1)
            if results: abstract = results[0].get("abstract","")
            p["analysis_methods"] = extract_by_keywords(title+" "+abstract)
            updated += 1
            print(f"✓ {title[:50]}…")
    dump(methods)
    print(f"\n完成：共處理 {total} 篇，已分析 {updated} 篇")

# ── 指令：list ────────────────────────────────────────────
def cmd_list():
    methods = load()
    if not methods: print("資料庫是空的"); return
    current_cat = None
    for m in sorted(methods, key=lambda x:(x["cat"],x["name"])):
        if m["cat"] != current_cat:
            current_cat = m["cat"]
            print(f"\n── {current_cat} ──")
        papers = len(m.get("papers",[]))
        analyzed = sum(1 for p in m.get("papers",[]) if p.get("analysis_methods"))
        print(f"  • {m['name']:<22} {papers} papers（{analyzed} 已分析）")

# ── 指令：search ──────────────────────────────────────────
def cmd_search(keyword):
    methods = load()
    kw = keyword.lower()
    results = [m for m in methods if kw in m["name"].lower() or kw in m["desc"].lower()]
    if not results: print(f"找不到「{keyword}」"); return
    for m in results:
        print(f"\n{m['name']} [{m['cat']}]\n  {m['desc'][:120]}")

# ── 指令：export ──────────────────────────────────────────
def cmd_export():
    methods = load()
    dump(methods)
    print(f"✓ 共 {len(methods)} 個方法已匯出")

# ── 主程式 ────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args or args[0] == "help":
        print(__doc__); return
    cmd = args[0]
    if   cmd == "add":      cmd_add()
    elif cmd == "paper":    cmd_paper()
    elif cmd == "analyze":  cmd_analyze()
    elif cmd == "discover": cmd_discover()
    elif cmd == "list":     cmd_list()
    elif cmd == "export":   cmd_export()
    elif cmd == "search":
        if len(args)<2: print("用法：python add_method.py search <關鍵字>")
        else: cmd_search(args[1])
    else: print(f"未知指令：{cmd}\n"); print(__doc__)

if __name__ == "__main__":
    main()

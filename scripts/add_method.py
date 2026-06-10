#!/usr/bin/env python3
"""
GWAS Methods DB — 管理腳本（含自動分析方法擷取）
用法：
  python add_method.py add                    新增方法
  python add_method.py paper                  對一個方法新增論文（可自動查 PubMed）
  python add_method.py analyze                對已有論文自動擷取分析方法
  python add_method.py list                   列出所有方法
  python add_method.py search <關鍵字>        搜尋
  python add_method.py export                 匯出乾淨的 JSON 到 docs/data/
"""

import json
import sys
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

# ── 路徑設定 ──────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_FILE  = BASE_DIR / "docs" / "data" / "methods.json"
# ─────────────────────────────────────────────────────────

CATS = ["PRS", "LDSC", "Fine-mapping", "MR", "GWAS QC", "其他"]

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
            if 1 <= n <= len(options):
                return options[n - 1]
        except (ValueError, KeyboardInterrupt):
            pass
        print("請輸入有效編號")

def ask(prompt, default=""):
    hint = f" [{default}]" if default else ""
    val = input(f"{prompt}{hint}：").strip()
    return val or default

# ── PubMed 查詢 ───────────────────────────────────────────
def search_pubmed(query, max_results=5):
    """用關鍵字查 PubMed，回傳論文清單（含摘要）"""
    print(f"\n🔍 查詢 PubMed：{query}")
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query,
        "retmax": max_results, "retmode": "json"
    })
    try:
        with urllib.request.urlopen(f"{base}esearch.fcgi?{params}", timeout=10) as r:
            data = json.loads(r.read())
        ids = data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"  ✗ PubMed 搜尋失敗：{e}")
        return []

    if not ids:
        print("  找不到相關論文")
        return []

    id_str = ",".join(ids)
    params2 = urllib.parse.urlencode({"db": "pubmed", "id": id_str, "retmode": "xml"})
    try:
        with urllib.request.urlopen(f"{base}efetch.fcgi?{params2}", timeout=10) as r:
            xml_data = r.read()
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"  ✗ 抓取詳細資料失敗：{e}")
        return []

    results = []
    for article in root.findall(".//PubmedArticle"):
        try:
            title_el = article.find(".//ArticleTitle")
            title = title_el.text if title_el is not None else "（無標題）"

            authors = article.findall(".//Author")
            if authors:
                last = authors[0].find("LastName")
                first_author = last.text if last is not None else "Unknown"
                author_str = f"{first_author} et al." if len(authors) > 1 else first_author
            else:
                author_str = "Unknown"

            year_el = article.find(".//PubDate/Year")
            year = year_el.text if year_el is not None else "?"

            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            doi = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            # ★ 新增：抓摘要
            abstract_texts = article.findall(".//AbstractText")
            abstract = " ".join(
                (el.text or "") for el in abstract_texts if el.text
            ).strip()

            results.append({
                "title": title,
                "author": f"{author_str}, {year}",
                "journal": journal,
                "doi": doi,
                "note": "",
                "abstract": abstract,   # 暫存用，存檔時移除
            })
        except Exception:
            continue

    return results

# ── Claude API：擷取分析方法 ──────────────────────────────
def extract_analysis_methods(title: str, abstract: str) -> dict:
    """
    呼叫 Claude API，從論文標題與摘要擷取分析方法資訊。
    回傳 dict，key 為 statistical_methods / software / sample_size / data_type。
    若 API 呼叫失敗，回傳空 dict。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  ⚠ 找不到 ANTHROPIC_API_KEY，跳過自動擷取")
        return {}

    prompt = f"""你是一位生物統計與基因體學的專家。
請從以下論文的標題與摘要中，擷取分析方法相關資訊。

標題：{title}

摘要：{abstract if abstract else "（無摘要）"}

請以 JSON 格式回答，只輸出 JSON，不要加任何說明文字或 markdown：
{{
  "statistical_methods": ["方法1", "方法2"],
  "software": ["軟體1", "軟體2"],
  "sample_size": "樣本數描述或不明",
  "data_type": "資料類型描述"
}}

若資訊不足，該欄位填空陣列 [] 或「不明」。"""

    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
        text = resp["content"][0]["text"].strip()
        # 去除可能的 markdown 包裹
        text = text.strip("` \n")
        if text.startswith("json"):
            text = text[4:].strip()
        return json.loads(text)
    except Exception as e:
        print(f"  ⚠ Claude API 擷取失敗：{e}")
        return {}

# ── 指令：add ─────────────────────────────────────────────
def cmd_add():
    methods = load()
    print("\n── 新增分析方法 ──")
    name = ask("方法名稱（例：LDpred2）")
    if not name:
        print("名稱不能為空"); return
    cat  = pick("分類", CATS)
    desc = ask("簡介")
    use  = ask("適用場景（選填）")
    link = ask("官方連結（選填）")
    new_id = max((m["id"] for m in methods), default=0) + 1
    methods.append({
        "id": new_id, "name": name, "cat": cat,
        "desc": desc, "use": use, "link": link,
        "papers": []
    })
    dump(methods)
    print(f"✓ 已新增：{name} [{cat}]")

# ── 指令：paper ───────────────────────────────────────────
def cmd_paper():
    methods = load()
    if not methods:
        print("資料庫是空的，請先新增方法"); return

    print("\n── 選擇要新增論文的方法 ──")
    names = [f"{m['name']} [{m['cat']}]" for m in methods]
    choice = pick("方法", names)
    idx = names.index(choice)
    m = methods[idx]

    print("\n如何新增論文？")
    mode = pick("方式", ["自動查詢 PubMed", "手動輸入"])

    if mode == "自動查詢 PubMed":
        query = ask(f"搜尋關鍵字（例：{m['name']} GWAS method）", m['name'])
        results = search_pubmed(query)
        if not results:
            print("沒有找到結果，改為手動輸入"); mode = "手動輸入"
        else:
            print(f"\n找到 {len(results)} 篇，選擇要加入的：")
            for i, p in enumerate(results, 1):
                print(f"  {i}. {p['title'][:70]}")
                print(f"     {p['author']} | {p['journal']}")
            choices = input("輸入編號（多個用逗號，例：1,3）或 Enter 跳過：").strip()
            if choices:
                # 是否自動擷取分析方法
                do_extract = input("\n是否用 Claude API 自動擷取分析方法？(y/n) [y]：").strip().lower()
                do_extract = (do_extract != "n")

                for n in choices.split(","):
                    try:
                        p = results[int(n.strip()) - 1].copy()
                        abstract = p.pop("abstract", "")  # 取出摘要，不存入 JSON
                        note = ask(f"  版本說明（{p['title'][:30]}…）", "")
                        p["note"] = note

                        # ★ 自動擷取分析方法
                        if do_extract:
                            print(f"  🤖 分析中：{p['title'][:50]}…")
                            methods_info = extract_analysis_methods(p["title"], abstract)
                            if methods_info:
                                p["analysis_methods"] = methods_info
                                print(f"  ✓ 擷取成功：{methods_info.get('statistical_methods', [])}")
                            else:
                                p["analysis_methods"] = {}

                        if "papers" not in m: m["papers"] = []
                        m["papers"].append(p)
                        print(f"  ✓ 已加入")
                    except (ValueError, IndexError):
                        print(f"  跳過無效編號：{n}")

    if mode == "手動輸入":
        title   = ask("論文標題")
        if not title: return
        author  = ask("作者 & 年份（例：Wang et al., 2020）")
        journal = ask("期刊")
        doi     = ask("DOI / URL")
        note    = ask("版本說明（選填）")

        paper = {"title": title, "author": author, "journal": journal, "doi": doi, "note": note}

        # 手動輸入也可選擇自動擷取（需要有摘要）
        do_extract = input("\n是否用 Claude API 自動擷取分析方法？需貼入摘要 (y/n) [n]：").strip().lower()
        if do_extract == "y":
            abstract = ask("請貼入論文摘要（可留空）")
            print(f"  🤖 分析中…")
            methods_info = extract_analysis_methods(title, abstract)
            if methods_info:
                paper["analysis_methods"] = methods_info
                print(f"  ✓ 擷取成功：{methods_info.get('statistical_methods', [])}")
            else:
                paper["analysis_methods"] = {}

        if "papers" not in m: m["papers"] = []
        m["papers"].append(paper)

    methods[idx] = m
    dump(methods)

# ── 指令：analyze（對已有論文補充擷取）───────────────────
def cmd_analyze():
    """
    對資料庫中已有的論文，若尚未有 analysis_methods 欄位，
    重新從 PubMed 抓摘要並用 Claude API 補充擷取。
    """
    methods = load()
    if not methods:
        print("資料庫是空的"); return

    total = 0
    updated = 0

    for m in methods:
        for p in m.get("papers", []):
            if p.get("analysis_methods"):
                continue  # 已有資料，跳過

            total += 1
            title = p.get("title", "")
            print(f"\n處理：{title[:60]}…")

            # 先嘗試從 PubMed 抓摘要
            abstract = ""
            if title:
                results = search_pubmed(title, max_results=1)
                if results:
                    abstract = results[0].get("abstract", "")
                    if abstract:
                        print(f"  ✓ 取得摘要（{len(abstract)} 字元）")

            print(f"  🤖 Claude API 分析中…")
            methods_info = extract_analysis_methods(title, abstract)
            if methods_info:
                p["analysis_methods"] = methods_info
                print(f"  ✓ 統計方法：{methods_info.get('statistical_methods', [])}")
                print(f"  ✓ 軟體工具：{methods_info.get('software', [])}")
                updated += 1
            else:
                p["analysis_methods"] = {}

    dump(methods)
    print(f"\n── 完成 ──")
    print(f"  共處理 {total} 篇，成功擷取 {updated} 篇")

# ── 指令：list ────────────────────────────────────────────
def cmd_list():
    methods = load()
    if not methods:
        print("資料庫是空的"); return
    current_cat = None
    for m in sorted(methods, key=lambda x: (x["cat"], x["name"])):
        if m["cat"] != current_cat:
            current_cat = m["cat"]
            print(f"\n── {current_cat} ──")
        papers = len(m.get("papers", []))
        analyzed = sum(1 for p in m.get("papers", []) if p.get("analysis_methods"))
        print(f"  • {m['name']:<20} {papers} papers（{analyzed} 已分析）")

# ── 指令：search ──────────────────────────────────────────
def cmd_search(keyword):
    methods = load()
    kw = keyword.lower()
    results = [m for m in methods if kw in m["name"].lower() or kw in m["desc"].lower()]
    if not results:
        print(f"找不到包含「{keyword}」的方法"); return
    for m in results:
        print(f"\n{m['name']} [{m['cat']}]")
        print(f"  {m['desc'][:120]}")

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
    if cmd == "add":          cmd_add()
    elif cmd == "paper":      cmd_paper()
    elif cmd == "analyze":    cmd_analyze()
    elif cmd == "list":       cmd_list()
    elif cmd == "export":     cmd_export()
    elif cmd == "search":
        if len(args) < 2: print("用法：python add_method.py search <關鍵字>")
        else: cmd_search(args[1])
    else:
        print(f"未知指令：{cmd}\n"); print(__doc__)

if __name__ == "__main__":
    main()

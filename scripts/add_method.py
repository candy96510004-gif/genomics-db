#!/usr/bin/env python3
"""
GWAS Methods DB — 管理腳本
用法：
  python add_method.py add          新增方法
  python add_method.py paper        對一個方法新增論文（可自動查 PubMed）
  python add_method.py list         列出所有方法
  python add_method.py search <關鍵字>  搜尋
  python add_method.py export       匯出乾淨的 JSON 到 docs/data/
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
    """用關鍵字查 PubMed，回傳論文清單"""
    print(f"\n🔍 查詢 PubMed：{query}")
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

    # 先查 ID 清單
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

    # 抓摘要
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

            # 作者
            authors = article.findall(".//Author")
            if authors:
                last = authors[0].find("LastName")
                first_author = last.text if last is not None else "Unknown"
                author_str = f"{first_author} et al." if len(authors) > 1 else first_author
            else:
                author_str = "Unknown"

            # 年份
            year_el = article.find(".//PubDate/Year")
            year = year_el.text if year_el is not None else "?"

            # 期刊
            journal_el = article.find(".//Journal/Title")
            journal = journal_el.text if journal_el is not None else ""

            # PMID → DOI
            pmid_el = article.find(".//PMID")
            pmid = pmid_el.text if pmid_el is not None else ""
            doi = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            results.append({
                "title": title,
                "author": f"{author_str}, {year}",
                "journal": journal,
                "doi": doi,
                "note": "",
            })
        except Exception:
            continue

    return results

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
                print(f"  {i}. {p['title'][:70]}…")
                print(f"     {p['author']} | {p['journal']}")
            choices = input("輸入編號（多個用逗號，例：1,3）或 Enter 跳過：").strip()
            if choices:
                for n in choices.split(","):
                    try:
                        p = results[int(n.strip()) - 1].copy()
                        note = ask(f"  版本說明（{p['title'][:30]}…）", "")
                        p["note"] = note
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
        if "papers" not in m: m["papers"] = []
        m["papers"].append({"title": title, "author": author, "journal": journal, "doi": doi, "note": note})

    methods[idx] = m
    dump(methods)

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
        print(f"  • {m['name']:<20} {papers} papers")

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
    if cmd == "add":       cmd_add()
    elif cmd == "paper":   cmd_paper()
    elif cmd == "list":    cmd_list()
    elif cmd == "export":  cmd_export()
    elif cmd == "search":
        if len(args) < 2: print("用法：python add_method.py search <關鍵字>")
        else: cmd_search(args[1])
    else:
        print(f"未知指令：{cmd}\n"); print(__doc__)

if __name__ == "__main__":
    main()

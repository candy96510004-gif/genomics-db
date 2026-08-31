#!/usr/bin/env python3
"""
GWAS Methods DB — PDF 下載腳本
依序嘗試六個來源：
  1. PubMed Central (PMC)
  2. Unpaywall
  3. Europe PMC
  4. OpenAlex
  5. Semantic Scholar
  6. bioRxiv / medRxiv

用法：
  python download_gwas_pdfs.py
"""

import requests
import os
import re
import time
import json

# ── 設定 ──────────────────────────────────────────────────
METHODS_JSON    = "https://candy96510004-gif.github.io/genomics-db/data/methods.json"
OUT_DIR         = "Downloads/PDFs"
LOG_FILE        = "Downloads/download_log.json"
UNPAYWALL_EMAIL = "candy0220@nhri.edu.tw"  # ← 改成你的 email
# ──────────────────────────────────────────────────────────

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("Downloads", exist_ok=True)

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, encoding="utf-8") as f:
        download_log = json.load(f)
else:
    download_log = {}

def save_log():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(download_log, f, ensure_ascii=False, indent=2)

def clean_doi(doi):
    return doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()

def safe_name(text):
    return re.sub(r'[\\/:*?"<>|]', "_", text)[:120]

def write_pdf(r, filepath):
    if r.status_code == 200 and len(r.content) > 10000:
        with open(filepath, "wb") as f:
            f.write(r.content)
        return True
    return False

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── 來源 1：PubMed Central ────────────────────────────────
def doi_to_pmid(doi):
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db":"pubmed","term":doi+"[DOI]","retmode":"json"}, timeout=15)
        ids = r.json()["esearchresult"].get("idlist", [])
        return ids[0] if ids else None
    except Exception:
        return None

def pmid_to_pmcid(pmid):
    try:
        r = requests.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi",
            params={"dbfrom":"pubmed","db":"pmc","id":pmid,"retmode":"json"}, timeout=15)
        return r.json()["linksets"][0]["linksetdbs"][0]["links"][0]
    except Exception:
        return None

def try_pmc(doi, filepath):
    pmid = doi_to_pmid(doi)
    if not pmid:
        return False
    pmcid = pmid_to_pmcid(pmid)
    if not pmcid:
        return False
    try:
        r = requests.get(f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/pdf/",
            timeout=30, headers=HEADERS)
        return write_pdf(r, filepath)
    except Exception:
        return False

# ── 來源 2：Unpaywall ─────────────────────────────────────
def try_unpaywall(doi, filepath):
    try:
        r = requests.get(f"https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}", timeout=15)
        if r.status_code != 200 or not r.json().get("is_oa"):
            return False
        data = r.json()
        pdf_url = None
        best = data.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or best.get("url")
        if not pdf_url:
            for loc in data.get("oa_locations", []):
                if loc.get("url_for_pdf"):
                    pdf_url = loc["url_for_pdf"]
                    break
        if not pdf_url:
            return False
        r2 = requests.get(pdf_url, timeout=30, headers=HEADERS)
        return write_pdf(r2, filepath)
    except Exception:
        return False

# ── 來源 3：Europe PMC ────────────────────────────────────
def try_europepmc(doi, filepath):
    try:
        r = requests.get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={"query":f"DOI:{doi}","format":"json","resultType":"core"}, timeout=15)
        results = r.json().get("resultList", {}).get("result", [])
        if not results:
            return False
        pmcid = results[0].get("pmcid", "")
        if not pmcid:
            return False
        r2 = requests.get(
            f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf",
            timeout=30, headers=HEADERS)
        return write_pdf(r2, filepath)
    except Exception:
        return False

# ── 來源 4：OpenAlex ──────────────────────────────────────
def try_openalex(doi, filepath):
    try:
        r = requests.get(
            f"https://api.openalex.org/works/https://doi.org/{doi}",
            timeout=15, headers={"User-Agent": f"genomics-db/1.0 (mailto:{UNPAYWALL_EMAIL})"})
        if r.status_code != 200:
            return False
        pdf_url = r.json().get("open_access", {}).get("oa_url")
        if not pdf_url:
            return False
        r2 = requests.get(pdf_url, timeout=30, headers=HEADERS)
        return write_pdf(r2, filepath)
    except Exception:
        return False

# ── 來源 5：Semantic Scholar ──────────────────────────────
def try_semantic_scholar(doi, filepath):
    try:
        r = requests.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=openAccessPdf",
            timeout=15, headers={"User-Agent": "genomics-db/1.0"})
        if r.status_code != 200:
            return False
        oa = r.json().get("openAccessPdf")
        if not oa:
            return False
        pdf_url = oa.get("url")
        if not pdf_url:
            return False
        r2 = requests.get(pdf_url, timeout=30, headers=HEADERS)
        return write_pdf(r2, filepath)
    except Exception:
        return False

# ── 來源 6：bioRxiv / medRxiv ─────────────────────────────
def try_biorxiv(doi, filepath):
    if not doi.startswith("10.1101/"):
        return False
    for base in ["https://www.biorxiv.org/content/", "https://www.medrxiv.org/content/"]:
        try:
            r = requests.get(f"{base}{doi}v1.full.pdf", timeout=30, headers=HEADERS)
            if write_pdf(r, filepath):
                return True
        except Exception:
            continue
    return False

# ── 主程式 ────────────────────────────────────────────────
SOURCES = [
    ("PMC",              try_pmc),
    ("Unpaywall",        try_unpaywall),
    ("Europe PMC",       try_europepmc),
    ("OpenAlex",         try_openalex),
    ("Semantic Scholar", try_semantic_scholar),
    ("bioRxiv/medRxiv",  try_biorxiv),
]

print("載入 methods.json ...")
try:
    methods = requests.get(METHODS_JSON, timeout=20).json()
except Exception as e:
    print(f"無法載入資料：{e}"); exit(1)

success = failed = skipped = 0

for m in methods:
    for p in m.get("papers", []):
        doi = clean_doi(p.get("doi", ""))
        if not doi or not doi.startswith("10."):
            continue

        name     = safe_name(f"{m.get('name','method')}_{p.get('title','paper')}")
        filepath = os.path.join(OUT_DIR, name + ".pdf")

        if doi in download_log and download_log[doi] == "success":
            skipped += 1
            continue
        if os.path.exists(filepath):
            download_log[doi] = "success"
            skipped += 1
            continue

        print(f"\n處理：{m.get('name')} | {doi}")

        downloaded = False
        for source_name, source_fn in SOURCES:
            print(f"  [{source_name}] 嘗試中 ...", end=" ", flush=True)
            try:
                if source_fn(doi, filepath):
                    print("✓ 成功")
                    downloaded = True
                    break
                else:
                    print("✗")
            except Exception as e:
                print(f"✗ ({e})")
            time.sleep(0.3)

        if downloaded:
            download_log[doi] = "success"
            success += 1
        else:
            download_log[doi] = "failed"
            failed += 1
            print(f"  → 六個來源都失敗，請用學校 VPN 手動下載")

        save_log()
        time.sleep(0.5)

print(f"\n{'='*50}")
print(f"完成！成功：{success}｜失敗：{failed}｜跳過（已下載）：{skipped}")
print(f"PDF 存放於：{os.path.abspath(OUT_DIR)}")
failed_dois = [doi for doi, status in download_log.items() if status == "failed"]
if failed_dois:
    print(f"\n需要 VPN 手動下載的論文（{len(failed_dois)} 篇）：")
    for doi in failed_dois:
        print(f"  https://doi.org/{doi}")

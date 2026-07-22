import requests
import os
import re
import time

METHODS_JSON = "https://candy96510004-gif.github.io/genomics-db/data/methods.json"
OUT_DIR = "Downloads/PDFs"
os.makedirs(OUT_DIR, exist_ok=True)

def clean_doi(doi):
    return doi.replace("https://doi.org/", "").strip()

def safe_name(text):
    return re.sub(r'[\\/:*?"<>|]', "_", text)[:120]

def doi_to_pmid(doi):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": doi + "[DOI]",
        "retmode": "json"
    }
    r = requests.get(url, params=params, timeout=20)
    ids = r.json()["esearchresult"].get("idlist", [])
    return ids[0] if ids else None

def pmid_to_pmcid(pmid):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    params = {
        "dbfrom": "pubmed",
        "db": "pmc",
        "id": pmid,
        "retmode": "json"
    }
    r = requests.get(url, params=params, timeout=20)
    data = r.json()

    try:
        links = data["linksets"][0]["linksetdbs"][0]["links"]
        return links[0]
    except Exception:
        return None

def download_pmc_pdf(pmcid, filename):
    pdf_url = f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/pdf/"
    r = requests.get(pdf_url, timeout=30)

    if r.status_code == 200 and r.headers.get("content-type", "").lower().startswith("application/pdf"):
        path = os.path.join(OUT_DIR, filename + ".pdf")
        with open(path, "wb") as f:
            f.write(r.content)
        return path

    return None

methods = requests.get(METHODS_JSON).json()

for m in methods:
    for p in m.get("papers", []):
        doi = clean_doi(p.get("doi", ""))
        if not doi:
            continue

        name = safe_name(f"{m.get('name','method')}_{p.get('title','paper')}")

        print("處理：", m.get("name"), doi)

        pmid = doi_to_pmid(doi)
        if not pmid:
            print("  找不到 PMID")
            continue

        pmcid = pmid_to_pmcid(pmid)
        if not pmcid:
            print("  找不到 PMCID，可能沒有 PMC 全文")
            continue

        path = download_pmc_pdf(pmcid, name)
        if path:
            print("  已下載：", path)
        else:
            print("  找到 PMCID，但 PDF 下載失敗")

        time.sleep(0.4)

print("完成")
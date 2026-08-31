import json
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time

with open('docs/data/methods.json', encoding='utf-8') as f:
    data = json.load(f)

def pmid_from_url(url):
    # 從 https://pubmed.ncbi.nlm.nih.gov/42415357/ 抓 PMID
    url = url.rstrip('/')
    parts = url.split('/')
    for part in reversed(parts):
        if part.isdigit():
            return part
    return None

def get_doi_from_pmid(pmid):
    try:
        params = urllib.parse.urlencode({"db":"pubmed","id":pmid,"retmode":"xml"})
        with urllib.request.urlopen(
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{params}",
            timeout=15) as r:
            root = ET.fromstring(r.read())
        # 找 DOI
        for id_el in root.findall(".//ArticleId"):
            if id_el.get("IdType") == "doi":
                return "https://doi.org/" + id_el.text
        return None
    except Exception as e:
        print(f"  錯誤：{e}")
        return None

fixed = 0
for m in data:
    for p in m.get('papers', []):
        doi = p.get('doi', '')
        if 'pubmed.ncbi.nlm.nih.gov' in doi:
            pmid = pmid_from_url(doi)
            if pmid:
                print(f"修復：{m['name']} / PMID {pmid}")
                real_doi = get_doi_from_pmid(pmid)
                if real_doi:
                    print(f"  → {real_doi}")
                    p['doi'] = real_doi
                    fixed += 1
                else:
                    print(f"  → 找不到 DOI，保留原本")
                time.sleep(0.5)

with open('docs/data/methods.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n完成！修復了 {fixed} 筆 DOI")

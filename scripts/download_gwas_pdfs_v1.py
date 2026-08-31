#!/usr/bin/env python3
"""
GWAS Methods DB — Open Access PDF downloader

Design goals
------------
1. Prefer legal/open-access metadata sources.
2. Do not rely on Selenium or browser automation.
3. Do not assume HTTP 200 means "PDF": verify the PDF file signature.
4. Keep a structured log with the source and failure reason.
5. Continue when one source fails.

Sources attempted
-----------------
1. Unpaywall
2. Europe PMC (core metadata -> PDF links)
3. OpenAlex
4. Semantic Scholar
5. bioRxiv / medRxiv

PMC is still used indirectly through Europe PMC / metadata services, but this
script deliberately does NOT request legacy URLs such as:
    https://pmc.ncbi.nlm.nih.gov/articles/PMCxxxx/pdf/
because direct scripted retrieval can return 403 and PMC's article-dataset
distribution infrastructure changed in August 2026.

Usage
-----
From the project root:
    python scripts/download_gwas_pdfs.py
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ── Settings ────────────────────────────────────────────────────────────────

METHODS_JSON = "https://candy96510004-gif.github.io/genomics-db/data/methods.json"
OUT_DIR = Path("Downloads/PDFs")
LOG_FILE = Path("Downloads/download_log.json")

# Unpaywall requires a real contact email.
UNPAYWALL_EMAIL = "candy0220@nhri.edu.tw"

REQUEST_TIMEOUT = 30
SOURCE_DELAY_SECONDS = 0.4
PAPER_DELAY_SECONDS = 0.6

USER_AGENT = (
    "genomics-db/2.0 "
    f"(mailto:{UNPAYWALL_EMAIL}; OA literature downloader)"
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── HTTP session with conservative retries ─────────────────────────────────

def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,application/json,text/html;q=0.8,*/*;q=0.5",
        }
    )
    return session


SESSION = build_session()


# ── Log helpers ─────────────────────────────────────────────────────────────

def load_log() -> dict[str, Any]:
    if not LOG_FILE.exists():
        return {}
    try:
        with LOG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


download_log = load_log()


def save_log() -> None:
    with LOG_FILE.open("w", encoding="utf-8") as f:
        json.dump(download_log, f, ensure_ascii=False, indent=2)


def status_of(entry: Any) -> str | None:
    """Backward compatible with the old log format ('success'/'failed')."""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return entry.get("status")
    return None


# ── General helpers ─────────────────────────────────────────────────────────

def clean_doi(doi: str) -> str:
    doi = (doi or "").strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = doi.rstrip(" .;,")
    return doi


def safe_name(text: str) -> str:
    text = re.sub(r'[\\/:*?"<>|]', "_", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:150] or "paper"


def unique_nonempty(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value:
            continue
        value = str(value).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def looks_like_pdf(data: bytes) -> bool:
    # Valid PDFs normally begin with %PDF-. A very small leading BOM/whitespace
    # is tolerated by checking the first 1024 bytes.
    return b"%PDF-" in data[:1024]


def download_pdf_url(
    url: str,
    filepath: Path,
    *,
    source: str,
    referer: str | None = None,
) -> tuple[bool, str]:
    """
    Download URL and save only if its bytes really look like a PDF.
    Returns (success, diagnostic_message).
    """
    headers = {}
    if referer:
        headers["Referer"] = referer

    tmp_path = filepath.with_suffix(filepath.suffix + ".part")

    try:
        with SESSION.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            allow_redirects=True,
            stream=True,
        ) as r:
            final_url = r.url
            content_type = (r.headers.get("Content-Type") or "").lower()

            if r.status_code != 200:
                return False, f"HTTP {r.status_code} ({final_url})"

            chunks: list[bytes] = []
            size = 0
            first_bytes = b""

            for chunk in r.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if not first_bytes:
                    first_bytes = chunk[:1024]
                    if not looks_like_pdf(first_bytes):
                        return (
                            False,
                            f"not a PDF; Content-Type={content_type or 'unknown'} "
                            f"({final_url})",
                        )
                chunks.append(chunk)
                size += len(chunk)

            if size < 5_000:
                return False, f"PDF-like response too small ({size} bytes)"

            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            with tmp_path.open("wb") as f:
                for chunk in chunks:
                    f.write(chunk)

            os.replace(tmp_path, filepath)
            return True, f"{size:,} bytes ({final_url})"

    except requests.RequestException as e:
        return False, f"{type(e).__name__}: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


# ── Metadata helpers ────────────────────────────────────────────────────────

def europe_pmc_record(doi: str) -> dict[str, Any] | None:
    """Return Europe PMC core metadata for a DOI."""
    try:
        r = SESSION.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": f'DOI:"{doi}"',
                "format": "json",
                "resultType": "core",
                "pageSize": 5,
            },
            timeout=20,
        )
        if r.status_code != 200:
            return None
        results = r.json().get("resultList", {}).get("result", [])
        if not results:
            return None

        # Prefer an exact DOI match.
        for rec in results:
            if clean_doi(rec.get("doi", "")).lower() == doi.lower():
                return rec
        return results[0]
    except Exception:
        return None


# ── Source 1: Unpaywall ────────────────────────────────────────────────────

def try_unpaywall(doi: str, filepath: Path) -> tuple[bool, str]:
    try:
        r = SESSION.get(
            f"https://api.unpaywall.org/v2/{quote(doi, safe='')}",
            params={"email": UNPAYWALL_EMAIL},
            timeout=20,
        )
        if r.status_code != 200:
            return False, f"metadata HTTP {r.status_code}"

        data = r.json()
        if not data.get("is_oa"):
            return False, "not marked open access"

        locations: list[dict[str, Any]] = []
        best = data.get("best_oa_location")
        if isinstance(best, dict):
            locations.append(best)
        for loc in data.get("oa_locations") or []:
            if isinstance(loc, dict):
                locations.append(loc)

        urls = unique_nonempty(loc.get("url_for_pdf") for loc in locations)
        if not urls:
            return False, "OA metadata found, but no direct PDF URL"

        failures = []
        for url in urls:
            ok, msg = download_pdf_url(url, filepath, source="Unpaywall")
            if ok:
                return True, msg
            failures.append(msg)

        return False, " | ".join(failures[-3:])
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 2: Europe PMC ───────────────────────────────────────────────────

def try_europepmc(doi: str, filepath: Path) -> tuple[bool, str]:
    rec = europe_pmc_record(doi)
    if not rec:
        return False, "DOI not found in Europe PMC"

    pmcid = rec.get("pmcid") or ""
    is_oa = rec.get("isOpenAccess")

    ft_list = (rec.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    if isinstance(ft_list, dict):
        ft_list = [ft_list]

    candidates = []
    for item in ft_list:
        if not isinstance(item, dict):
            continue
        style = str(item.get("documentStyle") or "").lower()
        url = item.get("url")
        if "pdf" in style and url:
            candidates.append(url)

    candidates = unique_nonempty(candidates)

    if not candidates:
        detail = f"PMCID={pmcid or 'none'}, isOpenAccess={is_oa}"
        return False, f"no PDF link in core metadata ({detail})"

    failures = []
    for url in candidates:
        ok, msg = download_pdf_url(url, filepath, source="Europe PMC")
        if ok:
            return True, f"PMCID={pmcid or 'none'}; {msg}"
        failures.append(msg)

    return False, " | ".join(failures[-3:])


# ── Source 3: OpenAlex ─────────────────────────────────────────────────────

def try_openalex(doi: str, filepath: Path) -> tuple[bool, str]:
    try:
        r = SESSION.get(
            f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='/:')}",
            params={"mailto": UNPAYWALL_EMAIL},
            timeout=20,
        )
        if r.status_code != 200:
            return False, f"metadata HTTP {r.status_code}"

        data = r.json()
        candidates: list[str | None] = []

        for key in ("best_oa_location", "primary_location"):
            loc = data.get(key)
            if isinstance(loc, dict):
                candidates.append(loc.get("pdf_url"))

        for loc in data.get("locations") or []:
            if isinstance(loc, dict):
                candidates.append(loc.get("pdf_url"))

        urls = unique_nonempty(candidates)
        if not urls:
            return False, "no OpenAlex pdf_url"

        failures = []
        for url in urls:
            ok, msg = download_pdf_url(url, filepath, source="OpenAlex")
            if ok:
                return True, msg
            failures.append(msg)

        return False, " | ".join(failures[-3:])
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 4: Semantic Scholar ─────────────────────────────────────────────

def try_semantic_scholar(doi: str, filepath: Path) -> tuple[bool, str]:
    try:
        r = SESSION.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi, safe='/')}",
            params={"fields": "openAccessPdf"},
            timeout=20,
        )
        if r.status_code != 200:
            return False, f"metadata HTTP {r.status_code}"

        oa = r.json().get("openAccessPdf")
        if not isinstance(oa, dict) or not oa.get("url"):
            return False, "no openAccessPdf URL"

        return download_pdf_url(
            oa["url"],
            filepath,
            source="Semantic Scholar",
        )
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 5: bioRxiv / medRxiv ────────────────────────────────────────────

def try_biorxiv(doi: str, filepath: Path) -> tuple[bool, str]:
    if not doi.lower().startswith("10.1101/"):
        return False, "not a bioRxiv/medRxiv DOI"

    failures = []
    for base in (
        "https://www.biorxiv.org/content/",
        "https://www.medrxiv.org/content/",
    ):
        # Try common forms. The DOI may already include a version in some datasets.
        candidates = [
            f"{base}{doi}.full.pdf",
            f"{base}{doi}v1.full.pdf",
        ]
        for url in candidates:
            ok, msg = download_pdf_url(url, filepath, source="bioRxiv/medRxiv")
            if ok:
                return True, msg
            failures.append(msg)

    return False, " | ".join(failures[-3:])


SOURCES = [
    ("Unpaywall", try_unpaywall),
    ("Europe PMC", try_europepmc),
    ("OpenAlex", try_openalex),
    ("Semantic Scholar", try_semantic_scholar),
    ("bioRxiv/medRxiv", try_biorxiv),
]


# ── Main program ────────────────────────────────────────────────────────────

def fetch_methods() -> list[dict[str, Any]]:
    r = SESSION.get(METHODS_JSON, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise ValueError("methods.json root is not a list")
    return data


def main() -> None:
    reset_failed = input(
        "是否重新嘗試之前失敗的論文？(y/n) [y]："
    ).strip().lower()

    if reset_failed != "n":
        before = 0
        for doi in list(download_log.keys()):
            if status_of(download_log[doi]) == "failed":
                before += 1
                del download_log[doi]
        if before:
            print(f"已重置 {before} 筆失敗紀錄，重新嘗試下載")
            save_log()

    print("載入 methods.json ...")
    try:
        methods = fetch_methods()
    except Exception as e:
        print(f"無法載入資料：{e}")
        raise SystemExit(1)

    success = failed = skipped = 0

    for method in methods:
        for paper in method.get("papers", []):
            doi = clean_doi(paper.get("doi", ""))
            if not doi or not doi.startswith("10."):
                continue

            name = safe_name(
                f"{method.get('name', 'method')}_{paper.get('title', 'paper')}"
            )
            filepath = OUT_DIR / f"{name}.pdf"

            old_status = status_of(download_log.get(doi))
            if old_status == "success" and filepath.exists():
                skipped += 1
                continue

            # If file exists but old log is absent/outdated, verify its signature.
            if filepath.exists():
                try:
                    with filepath.open("rb") as f:
                        if looks_like_pdf(f.read(1024)):
                            download_log[doi] = {
                                "status": "success",
                                "source": "existing file",
                                "file": str(filepath),
                            }
                            skipped += 1
                            save_log()
                            continue
                except Exception:
                    pass

            print(f"\n處理：{method.get('name')} | {doi}")

            downloaded = False
            attempts: list[dict[str, str]] = []

            for source_name, source_fn in SOURCES:
                print(f"  [{source_name}] 嘗試中 ... ", end="", flush=True)
                try:
                    ok, detail = source_fn(doi, filepath)
                except Exception as e:
                    ok, detail = False, f"{type(e).__name__}: {e}"

                attempts.append(
                    {
                        "source": source_name,
                        "result": "success" if ok else "failed",
                        "detail": detail,
                    }
                )

                if ok:
                    print(f"✓ 成功 ({detail})")
                    download_log[doi] = {
                        "status": "success",
                        "source": source_name,
                        "file": str(filepath),
                        "detail": detail,
                        "attempts": attempts,
                    }
                    success += 1
                    downloaded = True
                    save_log()
                    break
                else:
                    print(f"✗ {detail}")

                time.sleep(SOURCE_DELAY_SECONDS)

            if not downloaded:
                failed += 1
                download_log[doi] = {
                    "status": "failed",
                    "reason": (
                        "No verified open-access PDF was downloadable from the "
                        "configured sources. This does not necessarily mean a VPN "
                        "is required."
                    ),
                    "attempts": attempts,
                }
                print(
                    "  → 未找到可由程式驗證並下載的 OA PDF；"
                    "可能是非 OA、來源限制、URL 失效或暫時性 API 問題。"
                )
                save_log()

            time.sleep(PAPER_DELAY_SECONDS)

    print("\n" + "=" * 60)
    print(f"完成！成功：{success}｜失敗：{failed}｜跳過（已下載）：{skipped}")
    print(f"PDF 存放於：{OUT_DIR.resolve()}")

    failed_dois = [
        doi
        for doi, entry in download_log.items()
        if status_of(entry) == "failed"
    ]
    if failed_dois:
        print(f"\n仍需人工確認的論文（{len(failed_dois)} 篇）：")
        for doi in failed_dois:
            print(f"  https://doi.org/{doi}")


if __name__ == "__main__":
    main()

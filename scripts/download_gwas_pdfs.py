#!/usr/bin/env python3
r"""
GWAS Methods DB — Open Access PDF downloader (v2)

Enhancements over v1
--------------------
- Keeps the reliable OA-source workflow.
- Adds Europe PMC getPdf fallback when a PMCID exists.
- Adds DOI resolver / publisher landing-page fallback.
- Adds Crossref metadata fallback.
- Parses common publisher HTML meta tags such as:
    citation_pdf_url
    dc.identifier
    og:url
- Verifies the downloaded bytes really contain a PDF signature.
- Records detailed failure reasons for every source.

No Selenium is required.

Recommended usage from the project root:
    cd C:\Users\130209\genomics-db
    python scripts\download_gwas_pdfs_v2.py
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ── Settings ────────────────────────────────────────────────────────────────

METHODS_JSON = "https://candy96510004-gif.github.io/genomics-db/data/methods.json"

# Always resolve output relative to project root, not current CMD directory.
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

OUT_DIR = PROJECT_ROOT / "Downloads" / "PDFs"
LOG_FILE = PROJECT_ROOT / "Downloads" / "download_log_v2.json"

# Unpaywall requires a real contact email.
UNPAYWALL_EMAIL = "candy0220@nhri.edu.tw"

REQUEST_TIMEOUT = 30
SOURCE_DELAY_SECONDS = 0.4
PAPER_DELAY_SECONDS = 0.6
MAX_HTML_BYTES = 2_000_000

USER_AGENT = (
    "genomics-db/2.1 "
    f"(mailto:{UNPAYWALL_EMAIL}; OA literature downloader)"
)

OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── HTTP session ────────────────────────────────────────────────────────────

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
            "Accept": "application/pdf,text/html,application/xhtml+xml,"
                      "application/json;q=0.9,*/*;q=0.5",
            "Accept-Language": "en-US,en;q=0.9",
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

        value = html.unescape(str(value).strip())

        if not value or value in seen:
            continue

        seen.add(value)
        out.append(value)

    return out


def looks_like_pdf(data: bytes) -> bool:
    return b"%PDF-" in data[:1024]


def read_existing_pdf_ok(filepath: Path) -> bool:
    if not filepath.exists():
        return False

    try:
        with filepath.open("rb") as f:
            return looks_like_pdf(f.read(1024))
    except Exception:
        return False


# ── PDF downloader ──────────────────────────────────────────────────────────

def download_pdf_url(
    url: str,
    filepath: Path,
    *,
    source: str,
    referer: str | None = None,
) -> tuple[bool, str]:
    """
    Download a URL and save only if its bytes really look like a PDF.
    Returns (success, diagnostic_message).
    """

    headers: dict[str, str] = {}

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

            first = b""
            total = 0

            tmp_path.parent.mkdir(parents=True, exist_ok=True)

            with tmp_path.open("wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue

                    if not first:
                        first = chunk[:1024]

                        if not looks_like_pdf(first):
                            return (
                                False,
                                f"not a PDF; Content-Type={content_type or 'unknown'} "
                                f"({final_url})",
                            )

                    f.write(chunk)
                    total += len(chunk)

            if total < 5_000:
                return False, f"PDF-like response too small ({total} bytes)"

            os.replace(tmp_path, filepath)
            return True, f"{total:,} bytes ({final_url})"

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


# ── HTML helpers ────────────────────────────────────────────────────────────

META_PATTERNS = [
    # name="citation_pdf_url" content="..."
    re.compile(
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        re.I,
    ),
    # content="..." name="citation_pdf_url"
    re.compile(
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url["\']',
        re.I,
    ),
    # property="citation_pdf_url" content="..."
    re.compile(
        r'<meta[^>]+property=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        re.I,
    ),
    # common direct PDF href
    re.compile(
        r'<a[^>]+href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        re.I,
    ),
]


def extract_pdf_candidates_from_html(
    page_url: str,
) -> tuple[list[str], str]:
    """
    Fetch a landing page and extract likely PDF links.
    Does not execute JavaScript.
    """

    try:
        r = SESSION.get(
            page_url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        if r.status_code != 200:
            return [], f"landing page HTTP {r.status_code}"

        content_type = (r.headers.get("Content-Type") or "").lower()

        # Sometimes DOI / publisher URL already resolves directly to a PDF.
        if "application/pdf" in content_type:
            return [r.url], "landing page resolved directly to PDF"

        raw = r.content[:MAX_HTML_BYTES]

        try:
            text = raw.decode(r.encoding or "utf-8", errors="ignore")
        except Exception:
            text = raw.decode("utf-8", errors="ignore")

        candidates: list[str] = []

        for pattern in META_PATTERNS:
            for match in pattern.findall(text):
                candidate = html.unescape(match).strip()
                candidate = urljoin(r.url, candidate)
                candidates.append(candidate)

        return unique_nonempty(candidates), f"parsed publisher page ({r.url})"

    except Exception as e:
        return [], f"{type(e).__name__}: {e}"


def try_landing_page_for_pdf(
    page_url: str,
    filepath: Path,
    *,
    source: str,
) -> tuple[bool, str]:
    candidates, detail = extract_pdf_candidates_from_html(page_url)

    if not candidates:
        return False, f"{detail}; no citation_pdf_url / .pdf link"

    failures: list[str] = []

    for pdf_url in candidates:
        ok, msg = download_pdf_url(
            pdf_url,
            filepath,
            source=source,
            referer=page_url,
        )

        if ok:
            return True, msg

        failures.append(msg)

    return False, " | ".join(failures[-4:])


# ── Europe PMC metadata ─────────────────────────────────────────────────────

def europe_pmc_record(doi: str) -> dict[str, Any] | None:
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

        direct_urls = unique_nonempty(
            loc.get("url_for_pdf")
            for loc in locations
        )

        failures: list[str] = []

        for url in direct_urls:
            ok, msg = download_pdf_url(
                url,
                filepath,
                source="Unpaywall",
            )

            if ok:
                return True, msg

            failures.append(msg)

        # Important v2 enhancement:
        # If Unpaywall knows the OA landing page but not a direct PDF URL,
        # parse the landing page for citation_pdf_url.
        landing_urls = unique_nonempty(
            loc.get("url")
            for loc in locations
        )

        for page_url in landing_urls:
            ok, msg = try_landing_page_for_pdf(
                page_url,
                filepath,
                source="Unpaywall landing page",
            )

            if ok:
                return True, msg

            failures.append(msg)

        if failures:
            return False, " | ".join(failures[-4:])

        return False, "OA metadata found, but no usable PDF or landing URL"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 2: Europe PMC ───────────────────────────────────────────────────

def try_europepmc(doi: str, filepath: Path) -> tuple[bool, str]:
    rec = europe_pmc_record(doi)

    if not rec:
        return False, "DOI not found in Europe PMC"

    pmcid = (rec.get("pmcid") or "").strip()
    is_oa = rec.get("isOpenAccess")

    ft_list = (rec.get("fullTextUrlList") or {}).get("fullTextUrl") or []

    if isinstance(ft_list, dict):
        ft_list = [ft_list]

    candidates: list[str] = []

    for item in ft_list:
        if not isinstance(item, dict):
            continue

        style = str(item.get("documentStyle") or "").lower()
        url = item.get("url")

        if "pdf" in style and url:
            candidates.append(url)

    # v2 fallback observed to work for some PMC records.
    if pmcid:
        candidates.append(
            f"https://europepmc.org/api/getPdf?pmcid={quote(pmcid, safe='')}"
        )

    candidates = unique_nonempty(candidates)

    failures: list[str] = []

    for url in candidates:
        ok, msg = download_pdf_url(
            url,
            filepath,
            source="Europe PMC",
        )

        if ok:
            return True, f"PMCID={pmcid or 'none'}; {msg}"

        failures.append(msg)

    if failures:
        return False, (
            f"PMCID={pmcid or 'none'}, isOpenAccess={is_oa}; "
            + " | ".join(failures[-4:])
        )

    return False, (
        f"no PDF candidate "
        f"(PMCID={pmcid or 'none'}, isOpenAccess={is_oa})"
    )


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

        pdf_candidates: list[str | None] = []
        landing_candidates: list[str | None] = []

        for key in ("best_oa_location", "primary_location"):
            loc = data.get(key)

            if isinstance(loc, dict):
                pdf_candidates.append(loc.get("pdf_url"))
                landing_candidates.append(loc.get("landing_page_url"))

        for loc in data.get("locations") or []:
            if isinstance(loc, dict):
                pdf_candidates.append(loc.get("pdf_url"))
                landing_candidates.append(loc.get("landing_page_url"))

        failures: list[str] = []

        for url in unique_nonempty(pdf_candidates):
            ok, msg = download_pdf_url(
                url,
                filepath,
                source="OpenAlex",
            )

            if ok:
                return True, msg

            failures.append(msg)

        # v2 enhancement: parse landing pages when pdf_url is absent/blocked.
        for page_url in unique_nonempty(landing_candidates):
            ok, msg = try_landing_page_for_pdf(
                page_url,
                filepath,
                source="OpenAlex landing page",
            )

            if ok:
                return True, msg

            failures.append(msg)

        if failures:
            return False, " | ".join(failures[-4:])

        return False, "no OpenAlex PDF or landing-page URL"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 4: Semantic Scholar ─────────────────────────────────────────────

def try_semantic_scholar(
    doi: str,
    filepath: Path,
) -> tuple[bool, str]:
    try:
        r = SESSION.get(
            f"https://api.semanticscholar.org/graph/v1/paper/DOI:{quote(doi, safe='/')}",
            params={"fields": "openAccessPdf,url"},
            timeout=20,
        )

        if r.status_code != 200:
            return False, f"metadata HTTP {r.status_code}"

        data = r.json()
        failures: list[str] = []

        oa = data.get("openAccessPdf")

        if isinstance(oa, dict) and oa.get("url"):
            ok, msg = download_pdf_url(
                oa["url"],
                filepath,
                source="Semantic Scholar",
            )

            if ok:
                return True, msg

            failures.append(msg)

            # If URL was HTML, try parsing it.
            ok, msg = try_landing_page_for_pdf(
                oa["url"],
                filepath,
                source="Semantic Scholar landing page",
            )

            if ok:
                return True, msg

            failures.append(msg)

        page_url = data.get("url")

        if page_url:
            ok, msg = try_landing_page_for_pdf(
                page_url,
                filepath,
                source="Semantic Scholar page",
            )

            if ok:
                return True, msg

            failures.append(msg)

        if failures:
            return False, " | ".join(failures[-4:])

        return False, "no openAccessPdf URL"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 5: Crossref ─────────────────────────────────────────────────────

def try_crossref(doi: str, filepath: Path) -> tuple[bool, str]:
    """
    Crossref often provides a publisher landing page rather than a guaranteed OA
    PDF. We only follow metadata / landing-page links and still verify PDF bytes.
    """

    try:
        r = SESSION.get(
            f"https://api.crossref.org/works/{quote(doi, safe='')}",
            params={"mailto": UNPAYWALL_EMAIL},
            timeout=20,
        )

        if r.status_code != 200:
            return False, f"metadata HTTP {r.status_code}"

        message = r.json().get("message") or {}
        failures: list[str] = []

        # Some Crossref records contain link entries with content-type PDF.
        links = message.get("link") or []

        for item in links:
            if not isinstance(item, dict):
                continue

            url = item.get("URL")
            content_type = str(item.get("content-type") or "").lower()

            if url and "pdf" in content_type:
                ok, msg = download_pdf_url(
                    url,
                    filepath,
                    source="Crossref",
                )

                if ok:
                    return True, msg

                failures.append(msg)

        # Publisher resource URL / DOI landing page.
        page_candidates = unique_nonempty(
            [
                (message.get("resource") or {}).get("primary", {}).get("URL")
                if isinstance(message.get("resource"), dict)
                else None,
                message.get("URL"),
                f"https://doi.org/{doi}",
            ]
        )

        for page_url in page_candidates:
            ok, msg = try_landing_page_for_pdf(
                page_url,
                filepath,
                source="Crossref / publisher landing page",
            )

            if ok:
                return True, msg

            failures.append(msg)

        if failures:
            return False, " | ".join(failures[-5:])

        return False, "Crossref record contains no usable PDF/landing link"

    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Source 6: DOI resolver / publisher page ────────────────────────────────

def try_doi_resolver(doi: str, filepath: Path) -> tuple[bool, str]:
    return try_landing_page_for_pdf(
        f"https://doi.org/{doi}",
        filepath,
        source="DOI resolver / publisher page",
    )


# ── Source 7: bioRxiv / medRxiv ────────────────────────────────────────────

def try_biorxiv(doi: str, filepath: Path) -> tuple[bool, str]:
    if not doi.lower().startswith("10.1101/"):
        return False, "not a bioRxiv/medRxiv DOI"

    failures: list[str] = []

    for base in (
        "https://www.biorxiv.org/content/",
        "https://www.medrxiv.org/content/",
    ):
        candidates = [
            f"{base}{doi}.full.pdf",
            f"{base}{doi}v1.full.pdf",
        ]

        for url in candidates:
            ok, msg = download_pdf_url(
                url,
                filepath,
                source="bioRxiv/medRxiv",
            )

            if ok:
                return True, msg

            failures.append(msg)

    return False, " | ".join(failures[-4:])


SOURCES = [
    ("Unpaywall", try_unpaywall),
    ("Europe PMC", try_europepmc),
    ("OpenAlex", try_openalex),
    ("Semantic Scholar", try_semantic_scholar),
    ("Crossref", try_crossref),
    ("DOI resolver", try_doi_resolver),
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

            if read_existing_pdf_ok(filepath):
                download_log[doi] = {
                    "status": "success",
                    "source": "existing verified PDF",
                    "file": str(filepath),
                }
                skipped += 1
                save_log()
                continue

            old_status = status_of(download_log.get(doi))

            if old_status == "success":
                # Log says success but file is gone/bad -> retry.
                pass

            print(f"\n處理：{method.get('name')} | {doi}")

            downloaded = False
            attempts: list[dict[str, str]] = []

            for source_name, source_fn in SOURCES:
                print(
                    f"  [{source_name}] 嘗試中 ... ",
                    end="",
                    flush=True,
                )

                try:
                    ok, detail = source_fn(doi, filepath)

                except Exception as e:
                    ok = False
                    detail = f"{type(e).__name__}: {e}"

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

                print(f"✗ {detail}")
                time.sleep(SOURCE_DELAY_SECONDS)

            if not downloaded:
                failed += 1

                download_log[doi] = {
                    "status": "failed",
                    "reason": (
                        "No verified open-access PDF was downloadable from "
                        "the configured metadata, repository, DOI or publisher "
                        "landing-page routes."
                    ),
                    "attempts": attempts,
                }

                print(
                    "  → 未找到可驗證的 OA PDF；"
                    "可能是非 OA、出版社限制、403、動態 JavaScript 頁面、"
                    "連結失效或暫時性 API 問題。"
                )

                save_log()

            time.sleep(PAPER_DELAY_SECONDS)

    print("\n" + "=" * 65)

    print(
        f"完成！成功：{success}｜失敗：{failed}｜"
        f"跳過（已有有效 PDF）：{skipped}"
    )

    print(f"PDF 存放於：{OUT_DIR.resolve()}")
    print(f"下載紀錄：{LOG_FILE.resolve()}")

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

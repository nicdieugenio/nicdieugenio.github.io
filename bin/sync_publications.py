#!/usr/bin/env python3
"""Sync _bibliography/papers.bib with ORCID (published work) and arXiv (preprints).

The script is deliberately additive: it never edits or deletes an entry that is
already in papers.bib, because those entries carry hand-curated al-folio fields
(`preview`, `selected`, `abbr`, custom `html` links). It only

  1. appends entries for works that are not in the file yet, and
  2. reports preprints whose published version now has a DOI, so the upgrade can
     be done by hand.

Usage:
    python3 bin/sync_publications.py                 # write new entries
    python3 bin/sync_publications.py --dry-run       # print, change nothing
    python3 bin/sync_publications.py --report out.md # also write a summary

Only the standard library is used, so it runs on a bare CI runner.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# --- configuration -----------------------------------------------------------

ORCID_ID = "0009-0001-0682-855X"
# arXiv is searched by author name; every hit must match one of these spellings
# before it is accepted, otherwise a namesake's preprints would leak in.
ARXIV_AUTHOR_QUERY = 'au:"Di Eugenio, Niccolo"'
ARXIV_ACCEPTED_AUTHORS = {
    "niccolo di eugenio",
    "n di eugenio",
    "niccolo dieugenio",
}
BIB_PATH = Path("_bibliography/papers.bib")

USER_AGENT = "nicdieugenio.github.io publication sync (mailto:niccolo.dieugenio@polito.it)"
TITLE_MATCH_RATIO = 0.88

# --- helpers -----------------------------------------------------------------


def fetch(url: str, accept: str = "application/json", retries: int = 3) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:  # pragma: no cover - network
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url}: {last_error}")


GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "θ": "theta", "λ": "lambda", "μ": "mu", "ν": "nu", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi", "ω": "omega",
}


def normalise_title(title: str) -> str:
    """Reduce a title to comparable letters+digits.

    Journal and arXiv metadata spell the same formula very differently
    (``YBa$_2$Cu$_3$O$_{7-\\delta}$`` vs ``YBa2Cu3O7-δ``), so LaTeX markup,
    Greek letters and every separator are stripped before comparison.
    """
    text = title.lower()
    text = re.sub(r"<[^>]+>", "", text)
    for symbol, name in GREEK.items():
        text = text.replace(symbol, name)
    text = re.sub(r"\\[a-z]+", lambda m: m.group(0)[1:], text)  # \delta -> delta
    return re.sub(r"[^a-z0-9]", "", text)


def titles_match(left: str, right: str) -> bool:
    a, b = normalise_title(left), normalise_title(right)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= TITLE_MATCH_RATIO


def html_to_latex(text: str) -> str:
    """Crossref titles carry markup; turn the useful parts into LaTeX math."""
    text = re.sub(r"<sub>(.*?)</sub>", r"$_{\1}$", text, flags=re.I | re.S)
    text = re.sub(r"<sup>(.*?)</sup>", r"$^{\1}$", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", text).strip()


# --- reading the existing bibliography ---------------------------------------


class BibEntry:
    def __init__(self, key: str, raw: str):
        self.key = key
        self.raw = raw
        self.title = self._field("title")
        self.doi = (self._field("doi") or "").lower().strip()
        self.arxiv = self._field("arxiv") or self._field("eprint") or ""

    def _field(self, name: str) -> str:
        match = re.search(rf"\b{name}\s*=\s*\{{", self.raw, re.I)
        if not match:
            return ""
        depth, start = 1, match.end()
        for index in range(start, len(self.raw)):
            if self.raw[index] == "{":
                depth += 1
            elif self.raw[index] == "}":
                depth -= 1
                if depth == 0:
                    return self.raw[start:index].strip()
        return ""


def read_bibliography(path: Path) -> list[BibEntry]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    entries: list[BibEntry] = []
    for match in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        depth, start = 1, match.end()
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    entries.append(BibEntry(match.group(2), text[match.start():index + 1]))
                    break
    return entries


# --- remote sources ----------------------------------------------------------


def orcid_dois(orcid_id: str) -> list[dict]:
    data = json.loads(fetch(f"https://pub.orcid.org/v3.0/{orcid_id}/works"))
    works = []
    for group in data.get("group", []):
        ids = {
            e["external-id-type"].lower(): e["external-id-value"]
            for e in group.get("external-ids", {}).get("external-id", [])
        }
        summary = group["work-summary"][0]
        doi = ids.get("doi")
        if not doi:
            continue
        works.append({
            "doi": doi.lower().strip(),
            "title": summary.get("title", {}).get("title", {}).get("value", ""),
            "type": summary.get("type", ""),
        })
    return works


def crossref_entry(doi: str) -> dict | None:
    try:
        payload = json.loads(fetch(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"))
    except RuntimeError as error:
        print(f"  ! Crossref lookup failed for {doi}: {error}", file=sys.stderr)
        return None
    work = payload["message"]

    authors = []
    for person in work.get("author", []):
        given, family = person.get("given", "").strip(), person.get("family", "").strip()
        authors.append(f"{given} {family}".strip() if family else person.get("name", "").strip())

    date = work.get("issued", {}).get("date-parts", [[None]])[0]
    year = date[0] if date and date[0] else ""

    return {
        "kind": "article",
        "title": html_to_latex(" ".join(work.get("title", [])) or ""),
        "author": " and ".join(a for a in authors if a),
        "journal": html_to_latex(" ".join(work.get("container-title", [])) or ""),
        "volume": work.get("volume", ""),
        "number": work.get("issue", ""),
        "pages": work.get("page", "") or work.get("article-number", ""),
        "year": str(year),
        "doi": work.get("DOI", doi),
        "html": f"https://doi.org/{work.get('DOI', doi)}",
    }


ARXIV_NS = {"a": "http://www.w3.org/2005/Atom"}


def arxiv_preprints(query: str, max_results: int = 60) -> list[dict]:
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode({
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        })
    )
    root = ET.fromstring(fetch(url, accept="application/atom+xml"))

    results = []
    for entry in root.findall("a:entry", ARXIV_NS):
        authors = [
            (a.findtext("a:name", default="", namespaces=ARXIV_NS) or "").strip()
            for a in entry.findall("a:author", ARXIV_NS)
        ]
        normalised = {normalise_author(a) for a in authors}
        if not (normalised & ARXIV_ACCEPTED_AUTHORS):
            continue

        raw_id = entry.findtext("a:id", default="", namespaces=ARXIV_NS)
        arxiv_id = re.sub(r"^.*/abs/", "", raw_id).split("v")[0]
        published = entry.findtext("a:published", default="", namespaces=ARXIV_NS)
        primary = entry.find("{http://arxiv.org/schemas/atom}primary_category")

        results.append({
            "kind": "misc",
            "title": re.sub(r"\s+", " ", entry.findtext("a:title", default="", namespaces=ARXIV_NS)).strip(),
            "author": " and ".join(authors),
            "year": published[:4],
            "arxiv": arxiv_id,
            "primaryClass": primary.get("term") if primary is not None else "",
            "doi": (entry.findtext("{http://arxiv.org/schemas/atom}doi", default="") or "").lower().strip(),
        })
    return results


def normalise_author(name: str) -> str:
    text = name.lower().strip()
    for accented, plain in (("ò", "o"), ("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ù", "u")):
        text = text.replace(accented, plain)
    text = re.sub(r"[^a-z\s]", "", text)
    return re.sub(r"\s+", " ", text).strip()


# --- writing new entries -----------------------------------------------------


def make_key(entry: dict, used: set[str]) -> str:
    first_author = entry["author"].split(" and ")[0] if entry["author"] else "unknown"
    surname = re.sub(r"[^a-z]", "", normalise_author(first_author).split(" ")[-1]) or "unknown"
    words = [w for w in re.findall(r"[a-z]+", normalise_title(entry["title"])[:60])] or ["work"]
    stem = f"{surname}{entry.get('year', '')}{''.join(words)[:28]}"
    key, suffix = stem, 1
    while key in used:
        suffix += 1
        key = f"{stem}{suffix}"
    used.add(key)
    return key


def format_entry(entry: dict, key: str) -> str:
    if entry["kind"] == "article":
        fields = [
            ("title", entry["title"]),
            ("author", entry["author"]),
            ("journal", entry["journal"]),
            ("volume", entry["volume"]),
            ("number", entry["number"]),
            ("pages", entry["pages"]),
            ("year", entry["year"]),
            ("doi", entry["doi"]),
            ("html", entry["html"]),
            ("bibtex_show", "true"),
        ]
    else:
        fields = [
            ("title", entry["title"]),
            ("author", entry["author"]),
            ("year", entry["year"]),
            ("eprint", entry["arxiv"]),
            ("archivePrefix", "arXiv"),
            ("primaryClass", entry.get("primaryClass", "")),
            ("arxiv", entry["arxiv"]),
            ("bibtex_show", "true"),
        ]

    # The hint sits outside the entry: BibTeX has no in-entry comment syntax, so a
    # "%" line between the braces would be parsed as junk by jekyll-scholar.
    lines = [
        "% added automatically by bin/sync_publications.py",
        "% to give this paper a thumbnail, put an image in assets/img/publication_preview/",
        "% and add a  preview = {your-image.jpg}  line below.",
        f"@{entry['kind']}{{{key},",
    ]
    rendered = [f"      {name} = {{{value}}}" for name, value in fields if str(value).strip()]
    lines.append(",\n".join(rendered))
    lines.append("}")
    return "\n".join(lines)


# --- main --------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print what would change, write nothing")
    parser.add_argument("--report", type=Path, help="write a Markdown summary to this path")
    parser.add_argument("--no-arxiv", action="store_true", help="skip the arXiv preprint search")
    parser.add_argument("--bib", type=Path, default=BIB_PATH)
    args = parser.parse_args()

    existing = read_bibliography(args.bib)
    print(f"papers.bib currently holds {len(existing)} entries")

    known_dois = {e.doi for e in existing if e.doi}
    known_arxiv = {e.arxiv for e in existing if e.arxiv}
    used_keys = {e.key for e in existing}

    def already_present(candidate: dict) -> BibEntry | None:
        if candidate.get("doi") and candidate["doi"] in known_dois:
            return next(e for e in existing if e.doi == candidate["doi"])
        if candidate.get("arxiv") and candidate["arxiv"] in known_arxiv:
            return next(e for e in existing if e.arxiv == candidate["arxiv"])
        for entry in existing:
            if entry.title and titles_match(entry.title, candidate["title"]):
                return entry
        return None

    additions: list[str] = []
    promotions: list[str] = []

    print(f"\nquerying ORCID {ORCID_ID} ...")
    for work in orcid_dois(ORCID_ID):
        match = already_present(work)
        if match:
            # The paper is on the site, but as a preprint without this DOI.
            if not match.doi:
                promotions.append(
                    f"- `{match.key}` is still a preprint here, but is now published: "
                    f"[{work['title']}](https://doi.org/{work['doi']}) — `doi = {{{work['doi']}}}`"
                )
            continue

        entry = crossref_entry(work["doi"])
        if not entry or not entry["title"]:
            continue
        key = make_key(entry, used_keys)
        additions.append(format_entry(entry, key))
        known_dois.add(entry["doi"])
        print(f"  + new article: {entry['title'][:70]}")

    if not args.no_arxiv:
        print("\nquerying arXiv ...")
        for preprint in arxiv_preprints(ARXIV_AUTHOR_QUERY):
            if already_present(preprint):
                continue
            key = make_key(preprint, used_keys)
            additions.append(format_entry(preprint, key))
            known_arxiv.add(preprint["arxiv"])
            print(f"  + new preprint: {preprint['title'][:70]}")

    print(f"\n{len(additions)} new entr{'y' if len(additions) == 1 else 'ies'}, "
          f"{len(promotions)} preprint(s) now published")

    if additions and not args.dry_run:
        text = args.bib.read_text(encoding="utf-8").rstrip("\n")
        text += "\n\n" + "\n\n".join(additions) + "\n"
        args.bib.write_text(text, encoding="utf-8")
        print(f"wrote {args.bib}")
    elif additions:
        print("\n--- dry run, would append ---\n")
        print("\n\n".join(additions))

    if args.report:
        lines = []
        if additions:
            lines.append(f"### {len(additions)} new publication(s) added\n")
            lines.append("Each new entry has a commented-out `preview` line — drop an image in "
                         "`assets/img/publication_preview/` and uncomment it to give the paper a thumbnail.\n")
        if promotions:
            lines.append("### Preprints that now have a published version\n")
            lines.append("These were left untouched so your `preview` images and custom fields "
                         "survive. Update them by hand if you want the journal reference:\n")
            lines.extend(promotions)
            lines.append("")
        if not lines:
            lines.append("No changes — `papers.bib` is up to date with ORCID and arXiv.")
        args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())

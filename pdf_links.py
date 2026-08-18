"""Re-add the report's internal jump-links to the generated PDF.

Chrome's `--print-to-pdf` (used by pdfgen) drops `<a href="#id">` in-document
anchors, so the beautiful cross-links in the report ("See your chart ->",
"See the timeline ->", ...) are clickable on the web page but dead in the
downloaded PDF. This walks the same HTML that produced the PDF, maps each
`#pN` anchor target to its PDF page (page-cards render one-section-per-page,
in order), finds each cross-link's text on its own page, and inserts a real
PDF GoTo link annotation there.

Deterministic and self-healing: if the section count doesn't match the PDF
page count (a card overflowed and shifted the mapping), it bails and returns
the PDF untouched rather than inserting wrong links. Never raises.
"""
import re

_SEC = re.compile(r'(<section class="page)')
_ID = re.compile(r'id="(p\d+)"')
_XLINK = re.compile(r'<a class="xlink" href="#(p\d+)">([^<]+)</a>')


def add_internal_links(pdf_bytes: bytes, html: str) -> bytes:
    """Return `pdf_bytes` with the report's `.xlink` cross-links inserted as
    internal GoTo annotations. Returns the input unchanged on any problem."""
    try:
        import pymupdf  # lazy: keep the import off the hot path / optional dep
    except Exception:
        return pdf_bytes
    try:
        parts = _SEC.split(html)
        secs = [parts[i] + parts[i + 1] for i in range(1, len(parts), 2)]
        if not secs:
            return pdf_bytes

        id_page: dict[str, int] = {}
        xlinks: list[tuple[int, str, str]] = []   # (source_page, target_id, text)
        for idx, sec in enumerate(secs, 1):
            for m in _ID.finditer(sec):
                id_page[m.group(1)] = idx
            for m in _XLINK.finditer(sec):
                xlinks.append((idx, m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()))
        if not xlinks:
            return pdf_bytes

        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        # One page-card == one PDF page, in order. If that invariant broke
        # (content overflow), the page mapping is unreliable -> do nothing.
        if doc.page_count != len(secs):
            return pdf_bytes

        # Chrome's --print-to-pdf ALREADY emits a NAMED-destination link for each
        # #pN anchor. Left in place, that named link plus our GOTO link overlap on
        # the same spot, and some viewers follow the named link by re-opening the
        # document URL (#pN) -> the site -> the login page. Strip every existing
        # internal link first, then add one clean, portable GOTO per cross-link.
        removed = 0
        for pg in doc:
            for lk in list(pg.get_links()):
                if lk.get("kind") in (pymupdf.LINK_NAMED, pymupdf.LINK_GOTO):
                    pg.delete_link(lk)
                    removed += 1

        added = 0
        for src, tid, text in xlinks:
            tgt = id_page.get(tid)
            if not tgt or src > doc.page_count or tgt > doc.page_count:
                continue
            needle = text.replace("→", "").replace("↗", "").strip()  # drop arrows
            if not needle:
                continue
            page = doc[src - 1]
            for rect in page.search_for(needle):
                page.insert_link({"kind": pymupdf.LINK_GOTO,
                                  "from": rect, "page": tgt - 1})
                added += 1
        return doc.tobytes() if (added or removed) else pdf_bytes
    except Exception:
        return pdf_bytes

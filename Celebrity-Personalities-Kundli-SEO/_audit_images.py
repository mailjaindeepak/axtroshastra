#!/usr/bin/env python3
"""
Structural image/layout auditor for celebrity kundli pages.

This is a STRUCTURAL check only — it catches missing/empty/truncated image slots,
banned imagery, and one known layout-ordering bug. It CANNOT judge photo quality,
crop correctness, or whether a photo shows the right subject. A clean exit is
necessary, not sufficient — always look at the rendered page yourself too
(PAGE-BUILD-RULES.md §2.10).

History, so the checks below make sense:
- Kohli V1 (22 Aug 2026): a build agent used the .gpx glyph-fallback for 4 planet
  cards and dropped the CTA photo entirely. -> checks 1-3 below.
- Batch-2 (22 Aug 2026): the fix for the above got over-corrected into a fabricated
  "shared NASA/astronomy planet-photo library" that was never part of the real
  design (planet cards use photos of the CELEBRITY, or ship text-only — see
  PAGE-BUILD-RULES.md §2.11). -> check 4 below bans that library outright.
- Same batch: a misplaced `</div><!-- /wrap -->` made FAQ + People-Also-Search
  render full-width on 5 of 9 pages, and a naive open/close COUNT check missed it
  because the count still matched. -> check 5 below checks ORDER, not just count.
- Kohli V1 fix-up (23 Aug 2026): checks 7-8's window for the very LAST card/tile in
  the document was capped at start+4000 chars (fine for non-last elements, which are
  bounded by the next element's start instead). A real, high-res embedded photo's
  base64 routinely exceeds 4000 chars before its closing quote, so the last planet
  card and last timeline tile were false-flagged as "no embedded photo" even when a
  correct, legible photo was already there. Fixed by extending the last element's
  window to end-of-document, matching how every other element is already bounded.
- Yuvraj fix-up (24 Aug 2026): extending the last element's window to end-of-document
  swung the bug the OTHER way — a genuinely EMPTY last tile/card now passed, because
  its search window swallowed the entire rest of the page (CTA background photo,
  footer, everything), and the regex happily matched THAT unrelated image instead of
  reporting the slot in front of it as empty. Found on Yuvraj tile #5 while a subagent
  was fixing tile #1 — the tool said PASS with a genuinely blank tile still live.
  First fix attempt bounded the last element's window at the nearest post-content
  landmark (CTA/footer/wrap-close) — better, but STILL wrong for the last .mo tile
  specifically: on the same Yuvraj page this let the window run across the entire
  planet-cards section sitting between the last timeline tile and the CTA, so it
  "borrowed" a planet card's photo instead. Fixed properly by ALSO bounding the last
  .mo tile at the first `.pc` card after it (timeline always precedes cards in the
  template), in addition to the CTA/footer/wrap-close landmarks — i.e. bound at
  whichever known section boundary comes soonest, not just the first one checked.

Usage:
    python3 _audit_images.py path/to/page.html

Exits non-zero and prints every finding if the page fails.
"""
import os
import re
import sys

# Tuned empirically in check 13 below against a known-good page (Kohli, 11 distinct
# photos) and the known-bad one (Hardik, 9 crops of 3 photos). Raise it if real
# distinct photos start tripping it; lower it if duplicates slip through.
DUPLICATE_HIST_THRESHOLD = 0.90


_POST_CONTENT_LANDMARKS = [
    r'<div class="cta"',
    r'</div><!--\s*/wrap\s*-->',
    r'<p class="foot"',
    r'class="foot"',
]

def _last_element_window_end(html: str, start: int, extra_landmarks=()) -> int:
    """Bound the LAST card/tile's search window at the nearest known section
    boundary after `start`, instead of end-of-document — see the Yuvraj fix-up note
    in the module docstring for why end-of-document (or even just the CTA/footer
    landmarks alone) lets the check "borrow" an unrelated image that belongs to a
    later section. `extra_landmarks` lets a caller add section markers that only
    apply to ITS element type (e.g. the .mo loop also bounds at the next `.pc`,
    since timeline always precedes cards in the template — the .pc loop shouldn't
    use that same landmark, it would just match itself)."""
    candidates = []
    for pattern in (*_POST_CONTENT_LANDMARKS, *extra_landmarks):
        m = re.search(pattern, html[start:])
        if m:
            candidates.append(start + m.start())
    return min(candidates) if candidates else len(html)


def audit(html: str, pages_dir: str | None = None) -> list[str]:
    problems = []

    # 1) Count real embedded photos — as <img> tags OR as CSS background-image data URIs
    #    (the hero and CTA use background:url("data:image...") rather than <img>, so a
    #    naive <img>-only count wrongly flags pages whose only <img> tags happen to be in
    #    sections that were legitimately made text-only).
    real_imgs = len(re.findall(r'<img\s[^>]*src="data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}"', html))
    real_bg_imgs = len(re.findall(r'background(?:-image)?:\s*url\(["\']?data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}["\']?\)', html))
    if real_imgs + real_bg_imgs == 0:
        problems.append("ZERO embedded photos found on the whole page (checked both <img> tags and CSS background-image). Every page needs at least a hero photo.")
    hero_bg = re.search(r'\.hero \.ph\{[^}]*background(?:-image)?:\s*url\(["\']?data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}', html)
    if not hero_bg:
        problems.append("No real hero background photo found in the .hero .ph rule.")

    # 2) .gpx (glyph-fallback) usage — allowed at most ONCE, and only on a .mo (timeline) tile,
    #    never on a .pc (planet card) or .cta (CTA) element.
    gpx_matches = re.findall(r'class="([^"]*\bgpx\b[^"]*)"', html)
    if len(gpx_matches) > 1:
        problems.append(
            f"Found {len(gpx_matches)} uses of the .gpx glyph-fallback class — at most 1 is allowed "
            f"(the single documented no-licensed-subject-photo case). Classes seen: {gpx_matches}"
        )
    for cls in gpx_matches:
        if "mim" not in cls and "im" not in cls.split():
            problems.append(f"Unexpected .gpx usage outside a photo slot: class=\"{cls}\"")
    pc_gpx = re.search(r'<div class="pc[^"]*">\s*<div class="im gpx"', html)
    if pc_gpx:
        problems.append(
            "A planet card (.pc) is using the .gpx glyph fallback. That's not the fix either — "
            "either use a real, distinct photo of the CELEBRITY for that card, or drop the .im "
            "block and ship it text-only (§2.11). Never .gpx, never a stock/astronomy image."
        )

    # 3) CTA background must be a real photo, not gradient-only.
    cbg_rule = re.search(r'\.cta \.cbg\{([^}]*)\}', html)
    if cbg_rule:
        body = cbg_rule.group(1)
        if "base64" not in body and "url(" not in body:
            problems.append(
                "The .cta .cbg rule has no background photo (gradient/color only). Use the shared "
                "category CTA photo from Celebrity-Personalities-Kundli-SEO/shared-assets/ (§2.12)."
            )
    else:
        problems.append("No .cta .cbg rule found at all — check the CTA section wasn't dropped.")

    # 4) BANNED: any stock/astronomy imagery in a planet card. Planet cards hold photos of the
    #    celebrity or nothing — never a photo of the actual Sun/Moon/planet/eclipse.
    banned_alts = {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn",
                   "rahu", "ketu", "the sun", "the moon", "full moon", "total lunar eclipse"}
    for m in re.finditer(r'<img\s[^>]*alt="([^"]*)"', html):
        if m.group(1).strip().lower() in banned_alts:
            problems.append(
                f"Found what looks like a stock astronomy photo (alt=\"{m.group(1)}\") — planet cards "
                f"must use a real photo of the celebrity or ship text-only, never imagery of the "
                f"literal celestial body (§2.11)."
            )
    if "shared-assets/planets/" in html or "shared-assets\\planets\\" in html:
        problems.append("Page references the old shared-assets/planets/ library, which must not exist or be used (§2.11).")

    # 5) STRUCTURAL ORDERING: .wrap must NOT close before the FAQ / People-Also-Search
    #    content — only the final CTA section is meant to be full-bleed outside it. A naive
    #    open/close COUNT check cannot catch a misplaced closing tag (the count still
    #    matches); this checks the actual document ORDER instead. The wrap-close doesn't
    #    have to sit immediately adjacent to the CTA div (some pages legitimately close and
    #    re-open .wrap around People-Also-Search first) — it just must not appear any
    #    earlier than that content.
    cta_i = html.find('class="cta"')
    if cta_i == -1:
        problems.append("No CTA div found at all.")
    else:
        # "People also search" is deliberately excluded from this landmark check: at least
        # one real page re-applies its own max-width via an inline style on that section
        # instead of staying inside .wrap, which is a legitimate alternative, not the bug.
        first_wrap_close = html.find("/wrap -->")
        faq_landmark = None
        for needle in ("Quick answers", "What people ask"):
            pos = html.find(needle)
            if pos != -1:
                faq_landmark = pos if faq_landmark is None else min(faq_landmark, pos)
        if first_wrap_close != -1 and faq_landmark is not None and first_wrap_close < faq_landmark:
            problems.append(
                "The .wrap div's FIRST close appears before the FAQ content, which will render "
                "it full-width/unconstrained. Only the final CTA section should be outside "
                ".wrap (§2.13)."
            )
        # immediately before the CTA's own <section>, there should be a clean close of
        # whatever came before (</div> or </section>), not raw content — a weak but useful
        # sanity check that the CTA section starts fresh.
        immediately_before = html[max(0, cta_i - 300):cta_i]
        section_start = immediately_before.rfind('<section')
        if section_start != -1:
            just_before_section = re.sub(r'(<!--.*?-->\s*)+$', '', immediately_before[:section_start]).rstrip()
            if not (just_before_section.endswith("</div>") or just_before_section.endswith("</section>")):
                problems.append(
                    "The CTA section doesn't appear to start right after a clean tag close — "
                    "check nothing is leaking across the CTA boundary."
                )

    # 7) POSITIVE CHECK: every planet card (.pc) must contain an actual embedded photo.
    #    History: a build first used .gpx glyphs for these (banned by check 2), then a
    #    "fix" stripped the images out entirely and shipped text-only kicker labels
    #    instead — which checks 1-4 above do NOT catch, because removing an image isn't
    #    the same as inserting a banned one. The user caught this by eye across 9 pages
    #    ("the same issues repeated throughout all the artifacts") before this check
    #    existed. A slot with a real photo is the only thing that passes now (§2.11).
    pc_starts = [m.start() for m in re.finditer(r'<div class="pc\b', html)]
    for i, start in enumerate(pc_starts):
        # The last card has no "next" landmark to bound it. Don't cap it at an
        # arbitrary +4000 chars (a real photo's base64 easily exceeds that) and don't
        # let it run to end-of-document either (it'll "borrow" a later section's
        # image) — bound it at the nearest known post-content landmark instead.
        end = pc_starts[i + 1] if i + 1 < len(pc_starts) else _last_element_window_end(html, start)
        block = html[start:end]
        has_img = re.search(r'<img\s[^>]*src="data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}"', block)
        has_bg = re.search(r'background(?:-image)?:\s*url\(["\']?data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}["\']?\)', block)
        if not has_img and not has_bg:
            problems.append(
                f"Planet card #{i + 1} (starting at char {start}) has no embedded photo — "
                f"every planet card needs a real, distinct photo of the celebrity (§2.11). "
                f"Text-only planet cards are not acceptable."
            )

    # 8) POSITIVE CHECK: every timeline/arc tile (.mo) must contain either an actual
    #    embedded photo or the single allowed .gpx glyph-fallback (check 2 already caps
    #    .gpx at one total use). A tile with neither is a silently-empty slot.
    mo_starts = [m.start() for m in re.finditer(r'<div class="mo\b', html)]
    for i, start in enumerate(mo_starts):
        # Same reasoning as the pc_starts loop above: cap neither at +4000 chars nor
        # at end-of-document — bound the last tile at the nearest post-content landmark,
        # PLUS the next planet card if any (timeline always precedes cards in the
        # template), so this window can't cross into the cards section and "borrow"
        # one of their photos instead of correctly reporting an empty tile.
        end = mo_starts[i + 1] if i + 1 < len(mo_starts) else _last_element_window_end(html, start, extra_landmarks=[r'<div class="pc\b'])
        block = html[start:end]
        has_img = re.search(r'<img\s[^>]*src="data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}"', block)
        has_bg = re.search(r'background(?:-image)?:\s*url\(["\']?data:image/[a-z]+;base64,[A-Za-z0-9+/=]{500,}["\']?\)', block)
        has_gpx = 'gpx' in block[:400]
        if not has_img and not has_bg and not has_gpx:
            problems.append(
                f"Timeline/arc tile #{i + 1} (starting at char {start}) has no embedded photo and "
                f"no .gpx fallback — every timeline slot needs a real photo, or the single "
                f"documented glyph-fallback exception, never a silently empty/text-only slot."
            )

    # 9) Any <img> with a suspiciously short/empty src (truncated embed, broken build step).
    for m in re.finditer(r'<img\s[^>]*src="([^"]*)"', html):
        src = m.group(1)
        if src.startswith("data:image") and len(src) < 200:
            problems.append(f"An <img> has a suspiciously short data URI ({len(src)} chars) — likely truncated: {src[:80]}...")
        if src == "" or src.startswith("{{"):
            problems.append(f"An <img> has an empty or unreplaced placeholder src: {src!r}")

    # 10) BROKEN IN-PAGE ANCHORS. Every href="#x" must have a matching id="x" somewhere.
    #     History: the Yuvraj page shipped a "Is Yuvraj Singh manglik?" pill pointing at
    #     #p-manglik, an id that existed nowhere on the page — a dead click for every
    #     visitor. A verifier caught it only because it was checked by hand.
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    for target in sorted(set(re.findall(r'href="#([^"]+)"', html))):
        if target and not target.startswith("$") and target not in ids:
            problems.append(
                f'Broken in-page anchor: href="#{target}" has no matching id="{target}". '
                f"Either add the id to the element it should jump to, or drop the link."
            )

    # 11) CLAUDE.AI RUNTIME WRAPPER LEAKED INTO THE SOURCE. WebFetch returns the artifact
    #     with a <!-- frame-runtime --> preamble that is NOT part of the stored page. Two
    #     separate agents republished it by accident; it buries the real <title> past the
    #     byte window the Artifact tool scans, silently renaming the artifact to the
    #     working filename. Symptom is a duplicated doctype/head/body.
    if "__FRAME_PREAMBLE" in html or "frame-runtime" in html:
        problems.append(
            "The claude.ai <!-- frame-runtime --> wrapper is present in this file. It is NOT "
            "part of the stored page — strip everything before the real content (and the "
            "trailing </body></html> duplicate) before publishing, or the artifact gets "
            "renamed and the <title> is lost."
        )
    # Count CLOSING tags too, not just opening ones. A build agent found that 10 of 12
    # shipped pages carried 2x </body> and 2x </html> while having exactly one <body> —
    # the wrapping script appended a closing pair to fragments that already ended with
    # one. Counting only opening tags missed it completely on every page.
    for tag, label in (("<!DOCTYPE", "doctype"), ("<body", "<body>"), ("<head>", "<head>"),
                       ("</body>", "</body>"), ("</html>", "</html>"), ("</head>", "</head>")):
        n = html.count(tag)
        if n > 1:
            problems.append(f"Document has {n} {label} tags — expected 1. Likely a double-wrapped "
                            f"page or a duplicated tail.")

    # 12) FAQ SECTION PRESENT. The "Quick answers" block is the page's SEO workhorse: it is
    #     what answers the birth-time / zodiac / nakshatra / manglik long-tail queries.
    #     Sachin, SRK and Yuvraj all shipped with ZERO FAQ blocks while every other page
    #     had 3-4, and nothing flagged it.
    faq_blocks = len(re.findall(r'<div class="ln">FAQ', html))
    if faq_blocks < 3:
        problems.append(
            f"Only {faq_blocks} FAQ block(s) found (want >=3). The 'Quick answers' section is "
            f"the main long-tail SEO surface — see any shipped page for the pattern."
        )

    # 13) NEAR-DUPLICATE PHOTOS (same shoot / same backdrop). §2.5 requires a distinct
    #     FRAME per slot, but byte-hashing cannot see it: the Hardik page shipped 9 images
    #     that were really 3 photographs under different crops, every hash was unique, and
    #     the user spotted it instantly by eye ("it contains the repeated pic"). Two crops
    #     of one photo, or two frames from one burst, share a colour signature — so compare
    #     coarse colour histograms rather than bytes. Advisory-grade: a hit means LOOK at
    #     the pair, not that it is definitely wrong.
    try:
        from PIL import Image
        import base64, io
        sigs = []
        for m in re.finditer(r'base64,([A-Za-z0-9+/=]{500,})', html):
            b = m.group(1)
            try:
                im = Image.open(io.BytesIO(base64.b64decode(b[:len(b)//4*4]))).convert("RGB")
            except Exception:
                continue
            im = im.resize((32, 32))
            hist = im.histogram()
            total = sum(hist) or 1
            sigs.append([v / total for v in hist])
        for i in range(len(sigs)):
            for j in range(i + 1, len(sigs)):
                # Bhattacharyya coefficient: 1.0 == identical distribution
                bc = sum((a * b) ** 0.5 for a, b in zip(sigs[i], sigs[j]))
                if bc > DUPLICATE_HIST_THRESHOLD:
                    problems.append(
                        f"Images #{i+1} and #{j+1} have near-identical colour signatures "
                        f"(similarity {bc:.3f}). Very likely the same photograph re-cropped, or "
                        f"two frames from one shoot/backdrop — a §2.5 duplicate. LOOK at both "
                        f"side by side; if they are genuinely different events, say so explicitly "
                        f"in your report."
                    )
    except ImportError:
        pass  # Pillow absent: skip rather than fail the whole audit

    # 14) CELEBRITY LINKS THAT CAN NEVER RESOLVE. The site's route handler already
    #     redirects a not-yet-built celebrity slug to /en/coming-soon (302), so linking to
    #     a page that is merely PENDING is intended - pages routinely cross-link to each
    #     other's future pages. What is a real bug is a slug that is neither built NOR a
    #     known celebrity in data.json: a typo, or an invented person, which would bounce
    #     the visitor to a "coming soon" page for someone who will never have one.
    if pages_dir and os.path.isdir(pages_dir):
        built = {f[:-5] for f in os.listdir(pages_dir)
                 if f.endswith(".html") and f != "index.html"}
        known = set()
        data_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
        try:
            import json
            with open(data_json, encoding="utf-8") as fh:
                for row in json.load(fh):
                    u = row.get("url") or ""
                    m = re.search(r"/en/celebrity-horoscope/([a-z0-9-]+)-kundli", u)
                    if m:
                        known.add(m.group(1))
        except Exception:
            known = None   # can't read the roster -> don't guess, skip the check

        if known:
            for slug in sorted(set(re.findall(
                    r'href="/en/celebrity-horoscope/([a-z0-9-]+)-kundli"', html))):
                if slug not in built and slug not in known:
                    problems.append(
                        f'Links to /en/celebrity-horoscope/{slug}-kundli, but "{slug}" is '
                        f"neither a built page nor a celebrity in data.json. That looks like a "
                        f"typo or an invented slug — it would redirect to a coming-soon page for "
                        f"someone who has no planned page. Fix the slug, add the person to "
                        f"data.json, or link /en/coming-soon?name=... directly."
                    )

    # 15) SECTION-PRESENCE FLOOR — catches gate evasion by class renaming.
    #     Checks 7 and 8 only fire on elements named .pc / .mo. A build agent renamed its
    #     planet cards to .plc and its timeline tiles to .tr and stated outright that it
    #     did so "so the auditor's photo requirement doesn't apply" — the page then PASSED
    #     with zero photos in either section. Disclosed, but still gate evasion, and the
    #     user spotted the empty sections immediately.
    #     A celebrity page must actually HAVE these sections, with real photos in them.
    # A page may legitimately have no photo slots when the subject genuinely has almost no
    # licensed photography (Vaibhav Sooryavanshi: every Commons file of him is the SAME
    # 30 May 2025 airport meeting, and two of them are family photos excluded under §3.5).
    # Forcing cards/tiles there would mean shipping same-event duplicates — the exact defect
    # this auditor exists to stop. So an EXPLICIT, ON-PAGE-DISCLOSED exemption is allowed.
    # It must be a visible HTML comment, so it cannot be set silently:
    #   <!-- PHOTO-SCARCITY-EXEMPTION: <reason> -->
    # and the page must still explain the omission to the reader in visible copy.
    exempt = re.search(r'<!--\s*PHOTO-SCARCITY-EXEMPTION:\s*(.+?)-->', html, re.S)
    if exempt and not re.search(r'What the sky wrote', html, re.I):
        problems.append(
            "A PHOTO-SCARCITY-EXEMPTION is declared, but the page has no 'What the sky wrote' "
            "section at all. The exemption covers missing PHOTOS, never a missing section."
        )
    if not exempt and (re.search(r'What the sky wrote', html, re.I) or 'class="kick' in html):
        pc_n = len(re.findall(r'<div class="pc\b', html))
        mo_n = len(re.findall(r'<div class="mo\b', html))
        if pc_n == 0:
            alt = re.findall(r'<div class="(plc|planet[a-z-]*|card-planet)\b', html)
            problems.append(
                "No .pc planet cards found at all"
                + (f' — but {len(alt)} look-alike blocks ({sorted(set(alt))}) are present, '
                   f'which reads as the class being renamed to dodge checks 7/9. ' if alt else ' — ')
                + "The 'What the sky wrote' section needs real .pc cards WITH photos. If the "
                  "subject genuinely has too few licensed photos, cut the number of cards; "
                  "do not rename the class."
            )
        if mo_n == 0:
            alt = re.findall(r'<div class="(tr|timeline[a-z-]*|arc)\b', html)
            problems.append(
                "No .mo timeline/graph tiles found at all"
                + (f' — but {len(alt)} look-alike blocks ({sorted(set(alt))}) are present, '
                   f'which reads as the class being renamed to dodge check 8. ' if alt else ' — ')
                + "The glow-up graph needs real .mo tiles WITH photos. Cut the number of "
                  "tiles if photos are scarce; do not rename the class."
            )

    return problems


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        sys.exit(2)
    html = open(sys.argv[1], encoding="utf-8").read()
    # optional 2nd arg: the pages/celebrity dir, enabling the dead-link check (14)
    pages_dir = sys.argv[2] if len(sys.argv) == 3 else os.path.dirname(os.path.abspath(sys.argv[1]))
    problems = audit(html, pages_dir)
    if problems:
        print(f"FAIL — {len(problems)} image-completeness issue(s) found:\n")
        for p in problems:
            print(f"  ✗ {p}")
        sys.exit(1)
    else:
        print("PASS — no image-completeness issues found.")
        sys.exit(0)


if __name__ == "__main__":
    main()

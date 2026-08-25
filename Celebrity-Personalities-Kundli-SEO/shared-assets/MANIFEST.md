# Shared image assets — CTA backgrounds only

**There is no shared "planet photo" library, and there never should be.** An earlier
version of this project built one (NASA/Commons astronomy photos for Sun, Moon, Venus,
etc.) after misreading a complaint about the planet-card sections. Checked against the
real Sachin/SRK reference pages: their `.pc .im` planet-card slots hold real photos of
THE CELEBRITY, not the celestial body. See PAGE-BUILD-RULES.md §2.11. If you're looking
for a planet-card photo, go source a real photo of the person instead — there is nothing
to reuse here for that.

What IS shared and reusable: one fixed CTA background photo per site category, used
byte-for-byte identical across every page in that category (PAGE-BUILD-RULES.md §2.12).

## `cta-cricketer-common.jpg`
Packed floodlit stadium, ICC Men's T20 World Cup (Narendra Modi Stadium). Source:
Wikimedia Commons, extracted from the live Sachin Tendulkar V3.1 page's `.cta .cbg` rule.
Confirmed correct by the user 2026-08-22 — keep using this one as-is.

## `cta-bollywood-common.jpg`
A packed, single-screen cinema hall mid-screening — rows of silhouetted audience heads
facing a lit blue screen, ornate theatre architecture. Supplied directly by the user
2026-08-23, replacing the previous Raj Mandir Cinema facade photo (which the user found
insufficiently evocative for the actor/Bollywood category). No named individual is
identifiable — the audience is seen from behind/in silhouette. Applied byte-for-byte
identical across all 6 actor-category pages (Katrina, Deepika, Kareena, Rashmika, Alia,
Anushka) in the same pass that fixed the timeline/planet-card photo gaps (see
PAGE-BUILD-RULES.md §2.11 history).

Previous version (superseded, kept here for the record only, do not reuse): Raj Mandir
Cinema, Jaipur — the "Show Palace of the Nation" facade, daytime, sharp. Source:
Wikimedia Commons, *File:Jaipur Raj Mandir Cinema 15-07-2022 (img1).jpg*, CC BY-SA 4.0.

## `cta-politics-common.jpg`
Rajpath / Kartavya Path at dusk, looking east from Raisina Hill — the North and South
Block secretariat facades framing an empty ceremonial avenue, with India Gate on the
horizon. No identifiable individual (the only figures are distant, unlit silhouettes
several hundred metres away). Established 25 Aug 2026 as the fixed CTA photo for the
`politics` category, sourced during the Narendra Modi build — the first politics page,
so there was no existing category asset to reuse.
Source: Wikimedia Commons, *File:Rashtrapati Bhavan, New Delhi (2018).jpg*, by
User:J.srivastava44, **CC BY-SA 4.0** (verified via the Commons API, not from prose).
Cropped to 16:9 / 1600×900 and lightly colour-graded to the palette; use this file
byte-for-byte on every future politics page (Rahul Gandhi, Yogi Adityanath, Amit Shah).

## `cta-business-common.jpg`
Mumbai at night seen from height — a dense cluster of lit high-rises across the middle
band, orange arterial roads threading the dark foreground, moody backlit cloud above. No
person is visible anywhere in the frame, so there is no identifiable individual. Source:
Wikimedia Commons, *File:Mumbai Night City (18219784390).jpg*, photographer **Skye Vidur**,
**CC BY-SA 2.0** (licence read from the Commons API `extmetadata.LicenseShortName`, and
re-verified independently before first use). Original 5456×3632; cropped full-width at a
320px vertical offset to 16:9 and resized to 1600×900, q88.

Established 25 Aug 2026 as the fixed CTA photo for the **business** category, first used on
the Mukesh Ambani page. Reuse byte-for-byte on every business-category page — do not re-crop,
re-blur or swap it. Note CC BY-SA is share-alike: the page footer must carry the photographer
credit and the licence name (the Ambani page's `.foot` block shows the wording to copy).

## `../coming-soon.html`
Not a photo — the shared fallback page for internal links (capsule pills and
inline prose links) that point at a celebrity whose page isn't built yet (see
PAGE-BUILD-RULES.md §2.14). Royal Parchment skin, lists every currently-live
kundli, personalizes its heading via `?name=<Display+Name>`. Route:
`/en/coming-soon`. Added 24 Aug 2026 after dead links were found live on 11 of
13 published pages (family members, co-stars, spouses never added to
data.json — e.g. Vicky Kaushal linked 3× from Katrina's page).

## Adding a new category
Source ONE real, sharp, evocative, no-identifiable-individual atmosphere photo that
fits the category, save it here as `cta-<category>-common.jpg`, add an entry to this
file, and use it verbatim on every page in that category from then on. Check this file
first before sourcing — do not let two builds each pick their own for the same category.

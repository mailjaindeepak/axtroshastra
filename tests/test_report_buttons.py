"""Every paid report page must ship its two action buttons: the one-tap PDF
download and the WhatsApp share. The server wires the PDF button by swapping
the `window.print();return false;` sentinel for axPdfDl() (which fetches the
headless-chrome /report/{rid}/pdf), so a renderer that forgets the button
ships a report with no way to save or share it. This shipped twice (vyapar,
blueprint) before these tests existed — a missing button here must fail CI
and block the deploy.

Covers every renderer a customer can actually be served:
  marriage (render_report_v2), milan (milan_v2), blueprint, vidyarthi, vyapar.
"""
import pytest

KUNDLI = {"name": "Button Check", "dob": "1995-08-15", "tob": "10:30",
          "time_quality": "T0", "place": "Delhi", "gender": "male"}

MILAN = {"p1_name": "Button Nisha", "p1_dob": "1994-04-18", "p1_tob": "10:30",
         "p1_place": "Jaipur", "p1_gender": "female",
         "p2_name": "Button Rahul", "p2_dob": "1993-04-18", "p2_tob": "10:30",
         "p2_place": "Jaipur", "p2_gender": "male", "variant": "/milan"}


def _paid_report_html(client, product):
    if product == "milan":
        r = client.post("/api/milan", json=MILAN)
    else:
        body = dict(KUNDLI)
        if product is not None:
            body["product"] = product
        r = client.post("/api/kundli", json=body)
    assert r.status_code == 200, r.text
    rid = r.json()["report_id"]
    assert client.post(f"/api/_demo_pay/{rid}").status_code == 200
    page = client.get(f"/report/{rid}")
    assert page.status_code == 200
    return page.text


@pytest.mark.parametrize("product",
                         [None, "milan", "blueprint", "vidyarthi", "vyapar",
                          "career_growth"],
                         ids=["marriage", "milan", "blueprint", "vidyarthi",
                              "vyapar", "career_growth"])
def test_report_page_has_pdf_and_whatsapp_buttons(client, product):
    html = _paid_report_html(client, product)
    # one-tap PDF: the renderer's sentinel must exist AND be swapped by
    # _wire_pdf_download — axPdfDl present, no raw print sentinel left.
    assert "axPdfDl" in html, "PDF download button missing or not wired"
    assert "window.print();return false;" not in html, \
        "print sentinel survived — _wire_pdf_download did not swap it"
    # WhatsApp share: the axShare hook (navigator.share / wa.me fallback).
    assert "axShare" in html, "WhatsApp share button missing"

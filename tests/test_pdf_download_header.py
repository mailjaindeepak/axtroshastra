"""A Hindi report's name can be Devanagari (e.g. "आशा शर्मा"). HTTP headers are
latin-1 only, so building the PDF download filename from the raw name used to
raise UnicodeEncodeError -> 500 -> the browser fell back to the print dialog.
This was the real cause of "the Hindi marriage PDF only gives the fallback".
"""
from tests.test_contact_capture import _new_report


def _pay_and_get_pdf(client, pay_webhook, name):
    rid = _new_report(client, name=name, variant="/hi/marriage")
    pay_webhook(client, rid, "pay_pdf_1", "+919812345678")
    return client.get(f"/report/{rid}/pdf")


def test_pdf_download_header_survives_devanagari_name(client, pay_webhook):
    r = _pay_and_get_pdf(client, pay_webhook, "आशा शर्मा")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    cd = r.headers["content-disposition"]
    cd.encode("latin-1")                      # must NOT raise (the old bug)
    assert 'filename="Axtroshastra_Report.pdf"' in cd    # ASCII fallback
    assert "filename*=UTF-8''" in cd                      # real name for modern browsers


def test_pdf_dotext_route_also_survives_devanagari_name(client, pay_webhook):
    # The .pdf route is what Twilio fetches for the WhatsApp attachment.
    rid = _new_report(client, name="विक्रम कुमार", variant="/hi/marriage")
    pay_webhook(client, rid, "pay_pdf_2", "+919812345678")
    r = client.get(f"/report/{rid}.pdf")
    assert r.status_code == 200, r.text
    r.headers["content-disposition"].encode("latin-1")   # must not raise

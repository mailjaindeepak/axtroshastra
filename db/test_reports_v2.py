"""Tests for reports_v2 (the legacy report-dict <-> v2-tables bridge).

Imports ONLY reports_v2/db_v2 — NOT api.py (which would load .env/RDS and connect).
The round-trip tests use the shared `conn` fixture (throwaway v2 schema) from
conftest.py. The two pure tests need no DB.

Run against LOCAL MySQL:  DB_PASSWORD='<local>' python3 -m pytest db/test_reports_v2.py -v
(No api import => no load_dotenv => it uses your shell DB_*, which default to localhost.)
"""
import db_v2  # noqa: F401  (ensures db/ is importable via conftest's sys.path insert)
import reports_v2


# ---- pure, no DB ----------------------------------------------------------
def test_norm_lang_maps_english_to_en():
    assert reports_v2.norm_lang({"meta": {"lang": "english"}}) == "en"   # create_kundli value
    assert reports_v2.norm_lang({"meta": {"lang": "hi"}}) == "hi"
    assert reports_v2.norm_lang({"meta": {"lang": "en"}}) == "en"        # milan value
    assert reports_v2.norm_lang({"meta": {}}) == "en"
    assert reports_v2.norm_lang({}) == "en"


def test_b2n_blanks_to_none():
    assert reports_v2._b2n("") is None
    assert reports_v2._b2n("   ") is None
    assert reports_v2._b2n(None) is None
    assert reports_v2._b2n("x") == "x"


# ---- round-trip against a real throwaway v2 DB ----------------------------
def _report(lang="english"):
    return {"teaser": {"x": 1}, "meta": {"lang": lang, "variant": "/en/marriage",
                                         "_email": "a@b.com", "_fbc": "fbcX"}}


def test_solo_report_saved_and_read_back(conn):
    report = _report()
    subj = {"role": "self", "name": "Asha", "gender": "female", "dob": "1990-05-01",
            "tob": "12:30", "time_quality": "T1", "birth_place": "Jaipur",
            "birth_lat": 26.9, "birth_lon": 75.8, "birth_tz": 5.5}
    uid = reports_v2.save_report(conn, "rep_solo1", report, [subj], product="marriage")
    conn.commit()
    assert uid is None                                   # no phone -> no user yet
    got = reports_v2.read_report(conn, "rep_solo1")
    assert got["payload"] == report                      # whole blob preserved (attribution incl.)
    assert got["paid"] is False
    assert got["order_id"] == "" and got["phone"] == "" and got["user_phone"] == ""
    with conn.cursor() as c:
        c.execute("SELECT role,name,gender FROM report_subjects WHERE report_id=%s", ("rep_solo1",))
        assert list(c.fetchall()) == [("self", "Asha", "female")]
        c.execute("SELECT lang,product,variant,user_id FROM reports WHERE id=%s", ("rep_solo1",))
        assert c.fetchone() == ("en", "marriage", "/en/marriage", None)  # english -> en


def test_milan_creates_user_and_two_subjects(conn):
    report = _report(lang="hi")
    subs = [
        {"role": "self", "name": "A", "gender": "male", "dob": "1990-01-01", "tob": "10:00",
         "birth_place": "Delhi", "birth_lat": 28.6, "birth_lon": 77.2, "birth_tz": 5.5},
        {"role": "partner", "name": "B", "gender": "female", "dob": "1992-02-02", "tob": "",
         "birth_place": "Pune", "birth_lat": 18.5, "birth_lon": 73.8, "birth_tz": 5.5},
    ]
    uid = reports_v2.save_report(conn, "rep_milan1", report, subs, product="milan",
                                 phone="+91 98765 43210")
    conn.commit()
    assert uid is not None                               # phone present -> user (lead) created
    got = reports_v2.read_report(conn, "rep_milan1")
    assert got["user_phone"] == "+919876543210"          # cc + mobile reassembled
    with conn.cursor() as c:
        c.execute("SELECT role FROM report_subjects WHERE report_id=%s ORDER BY id", ("rep_milan1",))
        assert [r[0] for r in c.fetchall()] == ["self", "partner"]
        c.execute("SELECT tob FROM report_subjects WHERE report_id=%s AND role='partner'", ("rep_milan1",))
        assert c.fetchone()[0] is None                   # blank tob -> NULL, not ''


def test_read_missing_report_returns_none(conn):
    assert reports_v2.read_report(conn, "nope_nope") is None


def test_attach_user_creates_and_links_the_lead(conn):
    # solo report starts with no user (the deferred 5a case)
    reports_v2.save_report(conn, "rep_att", _report(), [{"role": "self", "name": "Z"}],
                           product="marriage")
    conn.commit()
    assert reports_v2.read_report(conn, "rep_att")["user_phone"] == ""
    # popup arrives at /api/order -> attach the user (the lead is identified)
    full = reports_v2.attach_user(conn, "rep_att", "+91 90000 11111", "buyer@x.com")
    conn.commit()
    assert full == "+919000011111"
    got = reports_v2.read_report(conn, "rep_att")
    assert got["user_phone"] == "+919000011111"          # report now linked to the user
    with conn.cursor() as c:
        c.execute("SELECT user_id FROM reports WHERE id=%s", ("rep_att",))
        assert c.fetchone()[0] is not None
        c.execute("SELECT email FROM users WHERE mobile=%s", ("9000011111",))
        assert c.fetchone()[0] == "buyer@x.com"          # email backfilled onto the user


def test_attach_user_blank_phone_is_noop(conn):
    reports_v2.save_report(conn, "rep_att2", _report(), [{"role": "self"}], product="marriage")
    conn.commit()
    assert reports_v2.attach_user(conn, "rep_att2", "", None) == ""   # no valid phone -> ""
    with conn.cursor() as c:
        c.execute("SELECT user_id FROM reports WHERE id=%s", ("rep_att2",))
        assert c.fetchone()[0] is None                    # still unattached


def test_store_attribution_writes_into_report_body(conn):
    reports_v2.save_report(conn, "rep_attr", _report(), [{"role": "self"}], product="marriage")
    conn.commit()
    reports_v2.store_attribution(conn, "rep_attr", fbc="fbcABC", li_fat_id="li999", ua="UA")
    conn.commit()
    meta = reports_v2.read_report(conn, "rep_attr")["payload"]["meta"]
    assert meta["_fbc"] == "fbcABC" and meta["_li_fat_id"] == "li999" and meta["_ua"] == "UA"
    assert meta["_email"] == "a@b.com"                    # existing body keys preserved

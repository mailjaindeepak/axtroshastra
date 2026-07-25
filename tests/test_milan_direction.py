"""Milan direction fix: Varna & Gana are direction-sensitive (groom vs bride).

Regression guard for the bug where entering the girl first flipped those two
kootas (and could change the guna total and verdict tier). With a gender on
either person, the result must be identical no matter which partner is entered
first. Without gender, behaviour is unchanged (p1 = groom, the classical
default)."""
import products

_LOC = {"tz": 5.5, "lat": 28.61, "lon": 77.21}
BOY  = {"name": "Boy",  "dob": "2003-09-11", "tob": "11:00", "gender": "male",   **_LOC}
GIRL = {"name": "Girl", "dob": "2004-08-11", "tob": None,    "gender": "female", **_LOC}


def _scores(r):
    return {k["name"]: k["score"] for k in r["kootas"]}


def test_gender_makes_result_order_independent():
    girl_first = products.compute_milan(GIRL, BOY)
    boy_first = products.compute_milan(BOY, GIRL)
    assert _scores(girl_first) == _scores(boy_first), \
        "with gender supplied, koota scores must not depend on input order"
    assert girl_first["total"] == boy_first["total"]
    assert girl_first["verdict"] == boy_first["verdict"]


def test_only_varna_and_gana_are_direction_carriers():
    # The other six kootas are symmetric regardless of gender/order.
    a = _scores(products.compute_milan(GIRL, BOY))
    b = _scores(products.compute_milan({**GIRL, "gender": None},
                                       {**BOY, "gender": None}))
    for k in ("Vashya", "Tara", "Yoni", "Graha Maitri", "Bhakoot", "Nadi"):
        assert a[k] == b[k], f"{k} should be unaffected by gender/direction"


def test_default_without_gender_still_runs():
    ng = {k: v for k, v in GIRL.items() if k != "gender"}
    nb = {k: v for k, v in BOY.items() if k != "gender"}
    r = products.compute_milan(nb, ng)   # no gender -> p1 (boy) is groom
    assert len(r["kootas"]) == 8 and r["max_total"] == 36

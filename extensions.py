"""
Feature endpoints wired onto the FastAPI app, kept out of api.py to minimise churn
in the core web layer. api.py calls `install(app, ctx)` once.

ctx keys:
  db                 -> sqlite connection factory
  get_report(rid)    -> {"payload","paid","order_id"} | None
  render(product, payload) -> HTML string for a paid report
  valid_admin_key(key) -> bool

Endpoints added:
  GET  /report/{rid}/pdf   server-side PDF of a paid report            (#7)
  GET  /api/deep/{rid}     divisional charts + yogas + ashtakavarga    (#8)
  GET  /api/i18n           supported languages + a language catalog    (#9)
  POST /api/reconcile      admin: reconcile unpaid reports w/ Razorpay (#6)
  POST /api/refund         admin: issue a refund                       (#6)
"""
from datetime import datetime, timedelta

from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response

import divisional
import i18n
import payments
import delivery


def install(app, ctx):
    db = ctx["db"]
    get_report = ctx["get_report"]
    render = ctx["render"]
    valid_admin_key = ctx["valid_admin_key"]

    @app.get("/report/{rid}/pdf", include_in_schema=False)
    def report_pdf(rid: str):
        rec = get_report(rid)
        if not rec or not rec["paid"]:
            raise HTTPException(404, "report not found or payment pending")
        payload = rec["payload"]
        html = render(payload.get("product", "marriage"), payload)
        pdf = delivery.html_to_pdf(html)
        if pdf is None:
            raise HTTPException(503, "PDF renderer not installed on server")
        name = (payload.get("meta", {}).get("name") or "report").replace(" ", "_")
        return Response(content=pdf, media_type="application/pdf",
                        headers={"Content-Disposition":
                                 f'attachment; filename="axtroshastra_{name}.pdf"'})

    @app.get("/api/deep/{rid}")
    def deep_analysis(rid: str):
        rec = get_report(rid)
        if not rec:
            raise HTTPException(404, "report not found")
        if not rec["paid"]:
            raise HTTPException(402, "payment required")
        birth = rec["payload"].get("meta", {}).get("_birth")
        if not birth:
            raise HTTPException(409, "birth data unavailable for this report")
        from engine import compute_chart
        local = datetime.fromisoformat(f"{birth['dob']}T{birth['tob']}:00")
        dt_utc = local - timedelta(hours=birth["tz"])
        chart = compute_chart(dt_utc, birth["lat"], birth["lon"])
        return divisional.analyze(chart)

    @app.get("/api/i18n")
    def i18n_catalog(lang: str = ""):
        code = i18n.normalize_lang(lang)
        return {"lang": code,
                "supported": [{"code": c, "name": i18n.LANG_NAMES[c],
                               "coverage": round(i18n.coverage(c), 2)}
                              for c in i18n.SUPPORTED],
                "catalog": {k: i18n.t(k, code)
                            for k in i18n.CATALOG[i18n.DEFAULT_LANG]}}

    @app.post("/api/reconcile")
    def reconcile(key: str = ""):
        if not valid_admin_key(key):
            raise HTTPException(403, "forbidden")
        return payments.reconcile(db)

    @app.post("/api/refund")
    def refund(key: str = "", payment_id: str = "", amount_paise: int | None = None):
        if not valid_admin_key(key):
            raise HTTPException(403, "forbidden")
        if not payment_id:
            raise HTTPException(422, "payment_id required")
        try:
            return payments.refund(db, payment_id, amount_paise)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=502)

"""Browser viewer around the five preview cards: toolbar with PDF download, a purchase bar that is
visible outside the PDF (eligible pairs only), and the Razorpay checkout script. The script talks
only to our own /api/mulank/* routes; the price, the order and the unlock all stay server side.
Nothing here is rendered for or sent to an ad or analytics vendor."""
import json
import re

import mulank_pricing
import numerology_preview as P

VIEWER_CSS = """
body{padding-bottom:96px}
.vw-top{width:min(430px,92vw);margin:0 auto 14px;display:flex;align-items:center;justify-content:space-between;gap:10px}
.vw-brand{font-family:var(--serif);font-weight:600;font-size:17px;color:var(--ink);text-decoration:none}
.vw-dl{display:inline-flex;align-items:center;gap:7px;background:#fff;color:var(--ink);border:1.5px solid var(--gold);border-radius:100px;padding:9px 15px;font:700 13px var(--sans);cursor:pointer}
.vw-dl[disabled]{opacity:.65;cursor:progress}
.vw-msg{width:min(430px,92vw);margin:0 auto 14px;padding:11px 14px;border-radius:12px;background:#FFF3E8;border:1px solid #E9C9AE;color:#6B2F12;font:500 14px/1.45 var(--sans)}
.vw-msg[hidden]{display:none}
.vw-bar{position:fixed;left:0;right:0;bottom:0;z-index:50;background:rgba(250,245,237,.97);border-top:1px solid #E1D3B3;padding:10px 14px calc(10px + env(safe-area-inset-bottom));display:flex;justify-content:center}
.vw-bar-in{width:min(430px,100%);display:flex;align-items:center;gap:12px}
.vw-price{font-family:var(--sans);line-height:1.2;color:var(--ink);flex:0 0 auto}
.vw-price s{color:var(--muted);font-size:13px;margin-right:5px}
.vw-price b{font:600 22px var(--serif)}
.vw-price span{display:block;font-size:11px;color:var(--muted)}
.vw-bar .pv-cta{margin:0;flex:1;width:auto;padding:13px 14px;font-size:14px}
.vw-ov{position:fixed;inset:0;z-index:100;background:rgba(27,29,42,.55);display:none;align-items:center;justify-content:center;padding:24px}
.vw-ov.on{display:flex}
.vw-ov-box{background:var(--cream);border-radius:16px;padding:22px 26px;text-align:center;font:600 15px/1.4 var(--sans);color:var(--ink);max-width:320px}
.vw-spin{width:28px;height:28px;margin:0 auto 12px;border:3px solid #E1D3B3;border-top-color:var(--gold);border-radius:50%;animation:vwspin 1s linear infinite}
@keyframes vwspin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.vw-spin{animation:none}}
@media print{.vw-top,.vw-bar,.vw-msg,.vw-ov{display:none!important}}
"""

VIEWER_JS = r"""
(function(){
  var RID=__RID__;
  var msg=document.getElementById('vwMsg'), ov=document.getElementById('vwOv'), ovt=document.getElementById('vwOvT');
  function say(t){ if(!t){msg.hidden=true;return;} msg.textContent=t; msg.hidden=false; msg.scrollIntoView({block:'nearest',behavior:'smooth'}); }
  function busy(t){ if(t){ovt.textContent=t;ov.classList.add('on');}else{ov.classList.remove('on');} }
  function post(url,body){ return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'same-origin'}); }
  function sleep(ms){ return new Promise(function(r){setTimeout(r,ms);}); }

  var dl=document.getElementById('vwDl');
  if(dl){ dl.addEventListener('click',function(){
    dl.disabled=true; var old=dl.textContent; dl.textContent='Preparing your PDF…'; say('');
    fetch('/en/numerology/preview/'+encodeURIComponent(RID)+'.pdf',{credentials:'same-origin'}).then(function(r){
      if(!r.ok) throw new Error('pdf');
      return r.blob();
    }).then(function(b){
      var a=document.createElement('a'); a.href=URL.createObjectURL(b); a.download='Axtroshastra-Numerology-Preview.pdf';
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(function(){URL.revokeObjectURL(a.href);},4000);
    }).catch(function(){ say('The PDF could not be prepared just now. You can keep reading your preview on this page, or try the download again in a minute.'); })
    .then(function(){ dl.disabled=false; dl.textContent=old; });
  }); }

  /*CHECKOUT_START*/
  function loadRzp(){ return new Promise(function(ok,no){
    if(window.Razorpay) return ok();
    var s=document.createElement('script'); s.src='https://checkout.razorpay.com/v1/checkout.js'; s.onload=ok; s.onerror=no; document.head.appendChild(s); }); }

  async function confirm(resp){
    busy('Confirming your payment…');
    for(var i=0;i<8;i++){
      try{
        var r=await post('/api/mulank/verify',{razorpay_order_id:resp.razorpay_order_id,razorpay_payment_id:resp.razorpay_payment_id,razorpay_signature:resp.razorpay_signature});
        var d=await r.json().catch(function(){return {};});
        if(r.ok && d.ok){ location.href='/en/numerology/report/'+encodeURIComponent(RID); return; }
        if(r.ok && d.status==='pending'){ await sleep(3000); continue; }
        if(r.status===502){ await sleep(3000); continue; }
        break;
      }catch(e){ await sleep(3000); }
    }
    busy(false);
    say('We could not confirm your payment yet. If money was deducted, please do not pay again. Come back to this same page in a few minutes and your payment will be recognised.');
  }

  async function checkout(){
    say(''); busy('Opening secure checkout…');
    try{
      var r=await post('/api/mulank/order',{report_id:RID}); var d=await r.json().catch(function(){return {};});
      var code=(d&&d.detail)||'';
      if(r.status===409){ busy(false); hideBuy(); say('The complete report is not available for your numbers yet. Your free preview stays on this page.'); return; }
      if(d.already_paid){ location.href='/en/numerology/report/'+encodeURIComponent(RID); return; }
      if(r.status===503){ busy(false); say('Checkout is not available right now. Your preview is saved at this page, so please try again a little later.'); return; }
      if(!r.ok||!d.razorpay_order_id||!d.key_id){ busy(false); say('We could not start checkout. Please try again.'); return; }
      await loadRzp();
      var rz=new Razorpay({key:d.key_id,amount:d.amount,currency:d.currency,order_id:d.razorpay_order_id,name:'Axtroshastra',
        description:'Complete numerology report',theme:{color:'#B4572B'},handler:confirm,
        modal:{ondismiss:function(){busy(false);say('Payment was not completed. You can try again whenever you are ready.');}}});
      rz.on('payment.failed',function(){busy(false);say('That payment did not go through. You have not been charged for the report, and you can try again.');});
      busy(false); rz.open();
    }catch(e){ busy(false); say('Something went wrong while opening checkout. Please check your connection and try again.'); }
  }
  function hideBuy(){ var b=document.getElementById('vwBar'); if(b) b.style.display='none'; document.body.style.paddingBottom='24px'; }
  document.addEventListener('click',function(e){ var t=e.target.closest('[data-action="checkout"]'); if(t){ e.preventDefault(); checkout(); } });
  /*CHECKOUT_END*/
})();
"""


def render_viewer(doc_html: str, rid: str, eligible: bool) -> str:
    """Wrap the preview document (from numerology_preview.build_preview) for the browser."""
    top = ('<div class="vw-top"><a class="vw-brand" href="/">Axtroshastra</a>'
           '<button type="button" class="vw-dl" id="vwDl">Download PDF</button></div>'
           '<div class="vw-msg" id="vwMsg" role="status" aria-live="polite" hidden></div>')
    bar = ""
    if eligible:
        bar = ('<div class="vw-bar" id="vwBar"><div class="vw-bar-in"><div class="vw-price">'
               f'<s>{P.inr(mulank_pricing.MULANK_LIST_PRICE_PAISE)}</s><b>{P.inr(mulank_pricing.MULANK_PRICE_PAISE)}</b>'
               '<span>Complete report</span></div>'
               f'<button type="button" class="pv-cta" data-action="checkout">{P.CTA2}</button></div></div>')
    overlay = '<div class="vw-ov" id="vwOv" role="alert"><div class="vw-ov-box"><div class="vw-spin"></div><div id="vwOvT"></div></div></div>'
    js = VIEWER_JS.replace("__RID__", json.dumps(rid).replace("</", "<\\/"))
    if eligible:
        js = js.replace("/*CHECKOUT_START*/", "").replace("/*CHECKOUT_END*/", "")
    else:                                   # unavailable pairs get no checkout code at all
        js = re.sub(r"/\*CHECKOUT_START\*/.*?/\*CHECKOUT_END\*/", "", js, flags=re.S)
    out = doc_html.replace("</style>\n</head>", VIEWER_CSS + "</style>\n</head>", 1)
    out = out.replace("<body>\n", "<body>\n" + top, 1)
    return out.replace("</body>", bar + overlay + "<script>" + js + "</script>\n</body>", 1)

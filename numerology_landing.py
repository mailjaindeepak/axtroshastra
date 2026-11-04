"""Landing-page offer blocks, chosen on the server so the page never promises something that cannot be delivered.

state "off"       nothing can be sold or pre-ordered: no price anywhere, an honest "not available yet" notice
state "sale"      at least one combination can be sold now: price and a free-vs-complete comparison (the report is
                  still only offered after the free preview, and only for combinations that are ready)
state "preorder"  the owner opened pre-orders: the same, worded as a pre-order with the delivery promise and refund link

The Rs 499 regular price appears (struck through, with the saving) only after the owner confirms it
(MULANK_LIST_PRICE_CONFIRMED=1). No countdowns, no stock counters, no invented urgency.
"""
import html as _html

import mulank_pricing

esc = lambda s: _html.escape(str(s), quote=True)


def _inr(paise: int) -> str:
    return "₹%s" % format(int(paise) // 100, ",")


NOT_YET_NOTICE = ('<div class="mk-notice" id="mkNotice"><b>Good to know:</b> your free preview is ready now. The complete '
                  'numerology report is not available yet, so there is nothing to buy on this page.</div>')

FREE_POINTS = ("Your Mulank and Bhagyank, with their ruling planets",
               "The step-by-step working, shown for your date of birth",
               "How your two numbers sit together",
               "A look at what the complete report covers")
PAID_POINTS = ("Personality, strengths and growth areas",
               "Career and working style",
               "Relationships and bonds",
               "Your personal years, this year and next, with reflection prompts",
               "Lucky numbers, colours, days and gemstones")


def price_block() -> str:
    price, listp = mulank_pricing.MULANK_PRICE_PAISE, mulank_pricing.MULANK_LIST_PRICE_PAISE
    was = save = ""
    if mulank_pricing.show_list_price():            # only after the owner confirms Rs 499 is a genuine regular price
        was = f'<s class="mk-was"><span class="mk-sr">Regular price </span>{_inr(listp)}</s>'
        save = f'<span class="mk-save">Save {_inr(listp - price)}</span>'
    return (f'<div class="mk-price"><div class="mk-row">{was}<span class="mk-now"><span class="mk-sr">Now </span>{_inr(price)}</span>{save}</div>'
            '<div class="mk-sub">One-time payment, no subscription</div></div>')


def price_banner() -> str:
    """The price shown under the hero while nothing can be bought yet. Selling price only (the regular price appears only once the
    owner confirms it); no badge, countdown or urgency. The notice that follows says plainly that purchase is not open yet."""
    return ('<div class="mk-banner"><div class="mk-banner-t">Complete 15-page numerology report</div>' + price_block() +
            '<div class="mk-banner-s">View your personalised five-page preview first.</div></div>')


def hero_offer(state: str, pre: dict) -> str:
    """The short line under the hero text that tells visitors a paid report exists separately."""
    if state == "off":
        return price_banner() + NOT_YET_NOTICE
    price = _inr(mulank_pricing.MULANK_PRICE_PAISE)
    if state == "preorder":
        return ('<div class="mk-notice" id="mkNotice"><b>Good to know:</b> your free preview is ready now. The complete report is not '
                f'ready yet for every combination of numbers, so after your preview you may be offered a pre-order for {price}, '
                f'delivered {esc(pre["promise"])}.</div>')
    return (f'<div class="mk-notice" id="mkNotice"><b>Free preview now.</b> The complete 15-page report is a separate purchase, {price}, '
            'offered after your preview for the number combinations we have prepared.</div>')


def btn_note(state: str) -> str:
    if state == "off":
        return "Free to view. Nothing is charged on this page."
    return f"Free to view. The complete report is a separate purchase, {_inr(mulank_pricing.MULANK_PRICE_PAISE)}."


def compare_section(state: str, pre: dict) -> str:
    """Free preview next to the complete report. Empty while nothing can be bought."""
    if state == "off":
        return ""
    free = "".join(f"<li>{esc(p)}</li>" for p in FREE_POINTS)
    paid = "".join(f"<li>{esc(p)}</li>" for p in PAID_POINTS)
    if state == "preorder":
        foot = (f'<p class="cmp-foot"><b>This is a pre-order, not an instant download.</b> It is delivered {esc(pre["promise"])} to your private link. '
                f'Refunds and cancellation: see our <a href="{esc(pre["refund_url"])}">refund policy</a>.</p>')
        tag = "Pre-order"
    else:
        foot = ('<p class="cmp-foot">Private link and a PDF you can download. Offered for the combinations of numbers we have prepared; '
                'we tell you straight after your free preview.</p>')
        tag = "Complete report"
    return f'''<section class="offer" id="offer"><div class="wrap">
    <div class="eyebrow">Two ways to read your numbers</div>
    <h2>Start free. Go deeper when you are ready.</h2>
    <div class="cmp">
      <div class="cmp-card">
        <div class="cmp-tag free">Free</div>
        <h3>Your free preview</h3>
        <ul>{free}</ul>
        <p class="cmp-foot">No payment. Takes under a minute.</p>
        <a class="cmp-btn ghost" href="#hero">Generate my free preview</a>
      </div>
      <div class="cmp-card paid">
        <div class="cmp-tag paid">{tag}</div>
        <h3>Your complete numerology report</h3>
        {price_block()}
        <ul>{paid}</ul>
        {foot}
        <a class="cmp-btn" href="#hero">Start with my free preview</a>
      </div>
    </div>
    <p class="cmp-note">Numerology is a belief system, not a science. Readings follow contemporary writing, for reflection only.</p>
  </div></section>'''

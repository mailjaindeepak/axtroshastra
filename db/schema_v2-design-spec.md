# Axtroshastra DB v2 — Design Specification

**Status: FROZEN — this is the source of truth.** `db/schema_v2.sql` implements this spec exactly;
the built database must match it. If a change is needed, change *this doc first* (deliberately),
then the SQL, then rebuild — never let the SQL or the live DB drift from this document.

- **Engine / charset:** every table `ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci`.
- **Server:** MySQL 8.4.
- **14 tables**, grouped: identity/auth (4), reports (2), payments (4), analytics (2), infra (2).

---

## Conventions (apply to every table)

- **Public ids = opaque strings** (URL-safe, don't leak volume): `users.id`, `reports.id`,
  `payments.id`, `refunds.id`, `visitors.visitor_id`, `visit_sessions.visit_id`. Suggested prefixes:
  `u_`, `rep_`, `pmt_`, `rfnd_`, `vis_`, `vst_`. **Internal-only ids = `BIGINT AUTO_INCREMENT`**:
  `report_subjects.id`, `events.id`.
- **Timestamps = real `DATETIME`.** `created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP`;
  `updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`.
- **Booleans = `TINYINT(1)` `NOT NULL DEFAULT 0`.**
- **Fixed value sets = `ENUM`** (the DB rejects anything off-list). Full enum list at the bottom.
- **Foreign keys**: named `fk_<child>_<parent>`; every FK also has a supporting index. Delete rules
  are chosen per relationship (see each table): `RESTRICT` = protect (block parent delete),
  `CASCADE` = children owned by parent (delete together), `SET NULL` = keep child, drop the link.
- **Money** is `amount_paise INT` (paise, never floats); **currency** `CHAR(3)` default `'INR'`.
- **Coordinates** `DECIMAL(9,6)` (lat/lon), timezone offset `DECIMAL(4,2)` (e.g. `5.50`).

---

## Identity & auth

### `users` — one known person (the account holder)
Pure identity. No birth details here. Created at **form-fill (lead)**, not only at payment.

| column | type | null | default | notes |
|---|---|---|---|---|
| id | VARCHAR(32) | no | — | **PK**, opaque `u_…` |
| country_code | VARCHAR(6) | no | `'+91'` | e.g. `+91` |
| mobile | VARCHAR(20) | no | — | national number, no country code |
| email | VARCHAR(255) | yes | NULL | real email or NULL — **never** `void@razorpay.com` |
| name | VARCHAR(120) | yes | NULL | account label, user-editable |
| mobile_verified | TINYINT(1) | no | 0 | set to 1 on successful OTP |
| email_verified | TINYINT(1) | no | 0 | |
| status | ENUM | no | `active` | `active` / `blocked` / `deleted` |
| created_at | DATETIME | no | CURRENT_TIMESTAMP | |
| updated_at | DATETIME | no | CURRENT_TIMESTAMP on update | |

Keys: PK `id`; **UNIQUE `(country_code, mobile)`** (this enforces "one account per phone");
INDEX `(email)`. No FKs out.

### `visitors` — one anonymous browser + the stitch to a known user
| column | type | null | notes |
|---|---|---|---|
| visitor_id | VARCHAR(40) | no | **PK**, the first-party cookie value |
| user_id | VARCHAR(32) | yes | **FK → users.id**, NULL until identified |
| first_seen | DATETIME | no | |
| last_seen | DATETIME | no | |
| first_utm_source / _medium / _campaign | VARCHAR(120) | yes | first-ever source |
| first_landing_url | VARCHAR(512) | yes | |
| first_referrer | VARCHAR(512) | yes | site they first arrived from |

FK: `fk_visitors_user` → `users(id)` **ON DELETE SET NULL**. INDEX `(user_id)`.

### `visit_sessions` — one browsing session (analytics visit)
Session duration + the source captured once at landing. Every event points here via `visit_id`.

| column | type | null | notes |
|---|---|---|---|
| visit_id | VARCHAR(40) | no | **PK**, `vst_…` |
| visitor_id | VARCHAR(40) | no | **FK → visitors.visitor_id** |
| user_id | VARCHAR(32) | yes | **FK → users.id**, once identified |
| started_at | DATETIME | no | |
| ended_at | DATETIME | no | bumped to the latest event's time; session time = ended − started |
| page_count | INT | no (def 0) | |
| landing_url | VARCHAR(512) | yes | first page of the session |
| referrer | VARCHAR(512) | yes | |
| utm_source / _medium / _campaign | VARCHAR(120) | yes | this session's source |
| fbc / fbp | VARCHAR(255) | yes | Meta click/browser ids |
| li_fat_id | VARCHAR(255) | yes | LinkedIn id |
| ga_client_id | VARCHAR(64) | yes | **newly captured** (old code missed it) |
| user_agent | VARCHAR(400) | yes | |
| ip | VARCHAR(45) | yes | fits IPv6 |

FKs: `fk_visit_sessions_visitor` → `visitors` **ON DELETE CASCADE**; `fk_visit_sessions_user` →
`users` **ON DELETE SET NULL**. INDEXes `(visitor_id)`, `(user_id)`.

### `login_sessions` — login tokens (staying logged in)
| column | type | null | notes |
|---|---|---|---|
| token | VARCHAR(48) | no | **PK**, `s_…` |
| user_id | VARCHAR(32) | no | **FK → users.id** |
| created_at | DATETIME | no | |
| expires_at | DATETIME | no | |

FK: `fk_login_sessions_user` → `users` **ON DELETE CASCADE**. INDEX `(user_id)`.

### `login_otps` — one-time login codes (hashed)
Keyed by the number being verified; a re-request overwrites. **No FK** (may precede a user row).

| column | type | null | notes |
|---|---|---|---|
| msisdn | VARCHAR(20) | no | **PK**, full number incl. country code |
| code_hash | VARCHAR(128) | yes | **hashed** OTP — never the raw code |
| mc_verification_id | VARCHAR(64) | yes | Message Central id (their-side verify) |
| expires_at | DATETIME | no | |
| attempts | INT | no (def 0) | |

---

## Reports

### `reports` — one generated report
| column | type | null | notes |
|---|---|---|---|
| id | VARCHAR(32) | no | **PK**, `rep_…`, the `/report/{id}` slug |
| user_id | VARCHAR(32) | yes | **FK → users.id**, NULL at preview |
| product | VARCHAR(40) | no | milan / marriage / vyapar / vidyarthi / career_growth / career_intelligence / blueprint |
| variant | VARCHAR(64) | yes | funnel / ad variant |
| lang | ENUM | no (def `en`) | `en` / `hi` |
| status | ENUM | no (def `preview`) | `preview` / `paid` — toggles on the **same row** |
| extra_inputs | JSON | yes | rare per-product inputs (employment/experience, stage/field) |
| report_data | JSON | yes | the computed report body (a document) |
| created_at | DATETIME | no | |
| updated_at | DATETIME | no | |

FK: `fk_reports_user` → `users` **ON DELETE RESTRICT** (can't delete a user with reports).
INDEXes `(user_id)`, `(product)`, `(created_at)`.

### `report_subjects` — one row per person on a report (solo=1, compatibility=2)
| column | type | null | notes |
|---|---|---|---|
| id | BIGINT AI | no | **PK** (internal) |
| report_id | VARCHAR(32) | no | **FK → reports.id** |
| role | ENUM | no (def `self`) | `self` / `partner` |
| name | VARCHAR(120) | yes | |
| gender | ENUM | yes | `male` / `female` / `other` |
| dob | DATE | yes | real date |
| tob | TIME | yes | NULL if birth time unknown |
| time_quality | VARCHAR(4) | yes | `T0`–`T3` (how precise the time is) |
| birth_place | VARCHAR(200) | yes | |
| birth_lat / birth_lon | DECIMAL(9,6) | yes | |
| birth_tz | DECIMAL(4,2) | yes | offset in hours, e.g. `5.50` |

FK: `fk_subjects_report` → `reports` **ON DELETE CASCADE** (subjects owned by the report).
INDEX `(report_id)`.

---

## Payments

### `payments` — one transaction (a free pass is `method='free_pass'`, amount 0)
| column | type | null | notes |
|---|---|---|---|
| id | VARCHAR(32) | no | **PK**, internal `pmt_…` |
| report_id | VARCHAR(32) | no | **FK → reports.id** |
| user_id | VARCHAR(32) | no | **FK → users.id** |
| razorpay_order_id | VARCHAR(40) | yes | |
| razorpay_payment_id | VARCHAR(40) | yes | **UNIQUE**; `pay_…`; NULL for free_pass |
| amount_paise | INT | no (def 0) | the **actual charged** amount, never recomputed |
| currency | CHAR(3) | no (def `INR`) | |
| status | ENUM | no (def `created`) | `created` / `captured` / `failed` / `refunded` |
| method | ENUM | yes | `upi` / `card` / `netbanking` / `wallet` / `free_pass` |
| upi_vpa | VARCHAR(120) | yes | UPI handle, when method=upi |
| payment_email | VARCHAR(255) | yes | email Razorpay had (real, or NULL — never void@) |
| payment_contact | VARCHAR(20) | yes | number used at payment (may differ from account) |
| paid_at | DATETIME | yes | set when captured |
| created_at | DATETIME | no | |

FKs: `fk_pay_report` → `reports` **ON DELETE RESTRICT**; `fk_pay_user` → `users` **ON DELETE
RESTRICT** (never lose a payment). UNIQUE `(razorpay_payment_id)`; INDEXes `(report_id)`,
`(user_id)`, `(razorpay_order_id)`.

### `passes` — free-pass tokens
| column | type | null | notes |
|---|---|---|---|
| token | VARCHAR(40) | no | **PK** |
| used | TINYINT(1) | no (def 0) | |
| used_by_payment_id | VARCHAR(32) | yes | **FK → payments.id** (the payment it created) |
| created_at | DATETIME | no | |
| used_at | DATETIME | yes | |

FK: `fk_passes_payment` → `payments` **ON DELETE SET NULL**. INDEX `(used_by_payment_id)`.

### `refunds` — manual for now
| column | type | null | notes |
|---|---|---|---|
| id | VARCHAR(32) | no | **PK**, `rfnd_…` |
| payment_id | VARCHAR(32) | no | **FK → payments.id** |
| amount_paise | INT | no | |
| status | ENUM | no (def `pending`) | `pending` / `processed` / `failed` |
| reason | VARCHAR(255) | yes | |
| created_at | DATETIME | no | |

FK: `fk_refunds_payment` → `payments` **ON DELETE RESTRICT**. INDEX `(payment_id)`.

### `webhook_events` — Razorpay idempotency ledger (no double-delivery)
No FK (an event can arrive before its payment row commits).

| column | type | null | notes |
|---|---|---|---|
| event_id | VARCHAR(64) | no | **PK**, Razorpay's unique event id |
| event_type | VARCHAR(40) | yes | e.g. `payment.captured` |
| razorpay_payment_id | VARCHAR(40) | yes | |
| report_id | VARCHAR(32) | yes | |
| processed_at | DATETIME | no | |

INDEX `(razorpay_payment_id)`.

---

## Analytics

### `events` — unified click-stream + funnel stream (append-only)
User data & source are **not copied** here — joined via `visit_id` / `user_id`.

| column | type | null | notes |
|---|---|---|---|
| id | BIGINT AI | no | **PK** |
| visit_id | VARCHAR(40) | yes | **FK → visit_sessions.visit_id** |
| visitor_id | VARCHAR(40) | no | **FK → visitors.visitor_id**, always present |
| user_id | VARCHAR(32) | yes | **FK → users.id**, once identified |
| login_session_id | VARCHAR(48) | yes | `login_sessions.token`, if logged in |
| event_name | ENUM | no | page_view / form_start / generate_lead / begin_checkout / purchase / payment_failed / identify |
| report_id | VARCHAR(32) | yes | **FK → reports.id**, from Lead onward |
| product | VARCHAR(40) | yes | |
| page_url | VARCHAR(512) | yes | this event's own page (saved on every event) |
| sequence | INT | yes | page order within the visit |
| entry_time / exit_time | DATETIME | yes | → time-on-page |
| value_paise | INT | yes | checkout/purchase |
| currency | CHAR(3) | yes | |
| is_free_unlock | TINYINT(1) | no (def 0) | |
| data_json | JSON | yes | event-specific extras only |
| created_at | DATETIME | no | |

FKs: `fk_events_visit` → `visit_sessions` **ON DELETE CASCADE**; `fk_events_visitor` → `visitors`
**ON DELETE CASCADE**; `fk_events_user` → `users` **ON DELETE SET NULL**; `fk_events_report` →
`reports` **ON DELETE SET NULL**. INDEXes `(visit_id)`, `(visitor_id)`, `(user_id)`, `(event_name)`,
`(report_id)`, `(created_at)`.

---

## Infra

### `geocache` — place → coordinates cache (self-rebuilding, standalone)
`place` VARCHAR(200) **PK**; `lat`/`lon` DECIMAL(9,6); `tz` DECIMAL(4,2); `source` VARCHAR(40);
`created_at` DATETIME.

### `health_check` — DB-alive sentinel (standalone)
`token` VARCHAR(48) **PK**; `ts` DATETIME NOT NULL.

---

## Cross-table invariants (the rules the data must always satisfy)

These are what the monthly `db_audit.py` checks — the design is only "correct" if these hold:

1. **One account per phone:** `(country_code, mobile)` unique in `users`.
2. **One row per Razorpay payment:** `razorpay_payment_id` unique in `payments`.
3. **Paid report ⇒ a real payment:** every `reports.status='paid'` has ≥1 `payments` row with
   `status IN ('captured','refunded')`.
4. **Captured payment ⇒ complete record:** it has a `user_id` and its report has ≥1 `report_subject`.
5. **No placeholder email:** `users.email` is never `void@razorpay.com`, `%@axtroshastra.test`, etc.
6. **Subject count matches product:** compatibility (`milan`) reports have exactly 2 `report_subjects`
   (self + partner); solo products have 1.
7. **Session sanity:** `visit_sessions.ended_at >= started_at`; every `events` row has a `visitor_id`.
8. **Amount sanity:** captured non-free `amount_paise` ∈ the known price list (₹499=49900, ₹1999=199900).
9. **Birth data present on paid:** paid reports' subjects have `dob` and `birth_place` populated.

---

## Enum value reference (change here first if a value is ever added)

- `users.status`: `active`, `blocked`, `deleted`
- `reports.lang`: `en`, `hi`
- `reports.status`: `preview`, `paid`
- `report_subjects.role`: `self`, `partner`
- `report_subjects.gender`: `male`, `female`, `other`
- `payments.status`: `created`, `captured`, `failed`, `refunded`
- `payments.method`: `upi`, `card`, `netbanking`, `wallet`, `free_pass`
- `refunds.status`: `pending`, `processed`, `failed`
- `events.event_name`: `page_view`, `form_start`, `generate_lead`, `begin_checkout`, `purchase`, `payment_failed`, `identify`

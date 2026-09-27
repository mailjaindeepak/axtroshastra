-- ============================================================================
-- Axtroshastra — clean schema v2  (MySQL 8.4 / InnoDB)
-- ============================================================================
-- Design-first rebuild. Real types, real foreign keys. Run against a NEW,
-- empty database (does NOT touch the live one):
--
--     CREATE DATABASE axtroshastra_v2
--       CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
--     USE axtroshastra_v2;
--     -- then run this file
--
-- Tables are created parent-before-child so the foreign keys resolve.
--
-- Conventions used throughout:
--   * Opaque string ids (VARCHAR) for public-facing rows (users/reports/payments)
--     — URL-safe, don't leak volume. BIGINT auto-increment only for internal-only
--     rows (report_subjects, events).
--   * created_at / updated_at are real DATETIME. updated_at uses
--     "ON UPDATE CURRENT_TIMESTAMP" so MySQL refreshes it automatically on any edit.
--   * ENUM restricts a column to a fixed set of valid values (invalid data is
--     rejected by the DB, not just by the app).
--   * TINYINT(1) is the MySQL convention for a boolean (0/1) flag.
--   * FK delete behaviour is chosen per relationship — see the comment on each:
--       RESTRICT  = block deleting the parent while children exist (protect data)
--       CASCADE   = delete the children with the parent (children fully owned by it)
--       SET NULL  = keep the child, just drop the link (preserve history/analytics)
-- ============================================================================


-- ---------------------------------------------------------------- users ------
-- One row per KNOWN person (the account holder / buyer). Pure identity — NO
-- birth details here (those are per-report, on report_subjects). Created at
-- form-fill (lead), not only at payment.
CREATE TABLE users (
    id              VARCHAR(32)   NOT NULL,               -- opaque id, e.g. "u_ab12cd34ef56"
    country_code    VARCHAR(6)    NOT NULL DEFAULT '+91', -- e.g. "+91"
    mobile          VARCHAR(20)   NOT NULL,               -- national number, no country code
    email           VARCHAR(255)  NULL,                   -- real email or NULL (never the void@ sentinel)
    name            VARCHAR(120)  NULL,                   -- account label, user-editable
    mobile_verified TINYINT(1)    NOT NULL DEFAULT 0,
    email_verified  TINYINT(1)    NOT NULL DEFAULT 0,
    status          ENUM('active','blocked','deleted') NOT NULL DEFAULT 'active',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_phone (country_code, mobile),     -- "one account per phone" lives here now
    KEY idx_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
-- NOTE: dropped the old `city` column — it was never written to, and birth place
-- lives on report_subjects. Add it back only if a real "residential city" need appears.


-- ------------------------------------------------------------- visitors ------
-- One row per anonymous browser (the visitor_id cookie). Links to a user once
-- we identify them; holds first-touch attribution. This is what stitches the
-- anonymous top-of-funnel to the eventual sale.
CREATE TABLE visitors (
    visitor_id        VARCHAR(40)  NOT NULL,   -- random id set on first page load
    user_id           VARCHAR(32)  NULL,       -- filled in once identified (form-fill / login)
    first_seen        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    first_utm_source  VARCHAR(120) NULL,
    first_utm_medium  VARCHAR(120) NULL,
    first_utm_campaign VARCHAR(120) NULL,
    first_landing_url VARCHAR(512) NULL,
    first_referrer    VARCHAR(512) NULL,
    PRIMARY KEY (visitor_id),
    KEY idx_visitors_user (user_id),
    CONSTRAINT fk_visitors_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE   -- delete a user -> visitor stays, just anonymised
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -------------------------------------------------------- visit_sessions ------
-- One row per BROWSING SESSION (analytics visit — distinct from a login session).
-- Holds the session's start/end (=> duration), the source captured ONCE at landing
-- (UTM / referrer / ad-ids), and the visitor->user link. Every event points at a
-- visit via visit_id, so the source applies to all of a session's events by join,
-- and session time = ended_at - started_at.
CREATE TABLE visit_sessions (
    visit_id      VARCHAR(40) NOT NULL,
    visitor_id    VARCHAR(40) NOT NULL,
    user_id       VARCHAR(32) NULL,             -- filled once identified during the visit
    started_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- bumped to the latest event's time
    page_count    INT NOT NULL DEFAULT 0,
    landing_url   VARCHAR(512) NULL,            -- the FIRST page of the session
    referrer      VARCHAR(512) NULL,            -- the site they arrived from (document.referrer)
    utm_source    VARCHAR(120) NULL,
    utm_medium    VARCHAR(120) NULL,
    utm_campaign  VARCHAR(120) NULL,
    fbc           VARCHAR(255) NULL,
    fbp           VARCHAR(255) NULL,
    li_fat_id     VARCHAR(255) NULL,
    ga_client_id  VARCHAR(64)  NULL,
    user_agent    VARCHAR(400) NULL,
    ip            VARCHAR(45)  NULL,            -- fits IPv6
    PRIMARY KEY (visit_id),
    KEY idx_visit_sessions_visitor (visitor_id),
    KEY idx_visit_sessions_user (user_id),
    CONSTRAINT fk_visit_sessions_visitor FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_visit_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------- login_sessions ------
-- Login sessions (a token that keeps someone logged in until it expires).
CREATE TABLE login_sessions (
    token       VARCHAR(48) NOT NULL,
    user_id     VARCHAR(32) NOT NULL,
    created_at  DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME    NOT NULL,
    PRIMARY KEY (token),
    KEY idx_login_sessions_user (user_id),
    CONSTRAINT fk_login_sessions_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE    -- delete a user -> their login sessions go too
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ----------------------------------------------------------- login_otps ------
-- One-time login codes. Keyed by the full number being verified; a re-request
-- overwrites the pending code. NO foreign key on purpose: an OTP is often
-- requested for a number that has no user row yet.
CREATE TABLE login_otps (
    msisdn             VARCHAR(20)  NOT NULL,   -- full number incl. country code, e.g. "+919876543210"
    code_hash          VARCHAR(128) NULL,       -- HASHED code (never store the raw OTP)
    mc_verification_id VARCHAR(64)  NULL,       -- Message Central id (when they verify on their side)
    expires_at         DATETIME     NOT NULL,
    attempts           INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (msisdn)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------- reports -------
-- One generated report. Created at preview (user_id NULL until identified).
-- The big computed body stays as JSON; birth INPUTS are on report_subjects.
CREATE TABLE reports (
    id            VARCHAR(32) NOT NULL,          -- opaque id, the /report/{id} slug
    user_id       VARCHAR(32) NULL,              -- NULL at preview, set when identified
    product       VARCHAR(40) NOT NULL,          -- marriage / milan / vyapar / vidyarthi / ...
    variant       VARCHAR(64) NULL,              -- funnel/ad variant
    lang          ENUM('en','hi') NOT NULL DEFAULT 'en',
    status        ENUM('preview','paid') NOT NULL DEFAULT 'preview',
    extra_inputs  JSON NULL,                     -- per-product inputs (employment/experience, stage/field)
    report_data   JSON NULL,                     -- the computed report body (a document, not queried)
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_reports_user (user_id),
    KEY idx_reports_product (product),
    KEY idx_reports_created (created_at),
    CONSTRAINT fk_reports_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE     -- can't delete a user who has reports (handle them first)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------ report_subjects ------
-- One row PER PERSON on a report. Solo product = 1 row; compatibility = 2 rows.
-- This is where birth details live, as real typed columns.
CREATE TABLE report_subjects (
    id           BIGINT      NOT NULL AUTO_INCREMENT,   -- internal-only, so a plain counter is fine
    report_id    VARCHAR(32) NOT NULL,
    role         ENUM('self','partner') NOT NULL DEFAULT 'self',
    name         VARCHAR(120) NULL,
    gender       ENUM('male','female','other') NULL,
    dob          DATE NULL,
    tob          TIME NULL,                             -- NULL when birth time is unknown
    time_quality VARCHAR(4) NULL,                       -- T0..T3 (how precise the birth time is)
    birth_place  VARCHAR(200) NULL,
    birth_lat    DECIMAL(9,6) NULL,
    birth_lon    DECIMAL(9,6) NULL,
    birth_tz     DECIMAL(4,2) NULL,                     -- offset in hours, e.g. 5.50
    PRIMARY KEY (id),
    KEY idx_subjects_report (report_id),
    CONSTRAINT fk_subjects_report FOREIGN KEY (report_id) REFERENCES reports(id)
        ON DELETE CASCADE ON UPDATE CASCADE             -- subjects are wholly owned by their report
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------- payments ------
-- One row per transaction. A free-pass unlock is just method='free_pass',
-- amount_paise=0. This is the ONLY home for payment method / UPI / payment email.
CREATE TABLE payments (
    id                  VARCHAR(32) NOT NULL,            -- internal opaque id
    report_id           VARCHAR(32) NOT NULL,
    user_id             VARCHAR(32) NOT NULL,
    razorpay_order_id   VARCHAR(40) NULL,
    razorpay_payment_id VARCHAR(40) NULL,                -- NULL for free_pass; unique when present
    amount_paise        INT NOT NULL DEFAULT 0,          -- the ACTUAL amount charged (never recomputed later)
    currency            CHAR(3) NOT NULL DEFAULT 'INR',
    status              ENUM('created','captured','failed','refunded') NOT NULL DEFAULT 'created',
    method              ENUM('upi','card','netbanking','wallet','free_pass') NULL,
    upi_vpa             VARCHAR(120) NULL,               -- the UPI handle, when method='upi'
    payment_email       VARCHAR(255) NULL,               -- email Razorpay had (real one, or NULL — never void@)
    payment_contact     VARCHAR(20)  NULL,               -- the phone used AT PAYMENT (may differ from account)
    paid_at             DATETIME NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pay_rzp (razorpay_payment_id),         -- one Razorpay payment id = one row (NULLs allowed many)
    KEY idx_pay_report (report_id),
    KEY idx_pay_user (user_id),
    KEY idx_pay_order (razorpay_order_id),
    CONSTRAINT fk_pay_report FOREIGN KEY (report_id) REFERENCES reports(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,            -- never lose a payment by deleting its report
    CONSTRAINT fk_pay_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- --------------------------------------------------------------- passes ------
-- Free-pass tokens. A redeemed pass points at the payment row it created.
CREATE TABLE passes (
    token              VARCHAR(40) NOT NULL,
    used               TINYINT(1)  NOT NULL DEFAULT 0,
    used_by_payment_id VARCHAR(32) NULL,
    created_at         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    used_at            DATETIME    NULL,
    PRIMARY KEY (token),
    KEY idx_passes_payment (used_by_payment_id),
    CONSTRAINT fk_passes_payment FOREIGN KEY (used_by_payment_id) REFERENCES payments(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- -------------------------------------------------------------- refunds ------
-- Manual for now. Protected FK to payments (can't delete a payment with refunds).
CREATE TABLE refunds (
    id          VARCHAR(32) NOT NULL,
    payment_id  VARCHAR(32) NOT NULL,
    amount_paise INT NOT NULL,
    status      ENUM('pending','processed','failed') NOT NULL DEFAULT 'pending',
    reason      VARCHAR(255) NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_refunds_payment (payment_id),
    CONSTRAINT fk_refunds_payment FOREIGN KEY (payment_id) REFERENCES payments(id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------- webhook_events ------
-- Razorpay idempotency ledger: one row per event we've processed, so a duplicate
-- webhook can't double-deliver. Loose links (no FK): an event can arrive before
-- the payment row is committed.
CREATE TABLE webhook_events (
    event_id            VARCHAR(64) NOT NULL,   -- Razorpay's unique event/entity id
    event_type          VARCHAR(40) NULL,       -- e.g. "payment.captured"
    razorpay_payment_id VARCHAR(40) NULL,
    report_id           VARCHAR(32) NULL,
    processed_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    KEY idx_webhook_pay (razorpay_payment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- --------------------------------------------------------------- events ------
-- Unified click-stream + funnel stream (the GA4 replacement). One append-only
-- row per event. User data is NOT copied here — join to users/reports via FK.
CREATE TABLE events (
    id             BIGINT      NOT NULL AUTO_INCREMENT,
    visit_id       VARCHAR(40) NULL,            -- the browsing session this event belongs to
    visitor_id     VARCHAR(40) NOT NULL,        -- always present (set before any user_id exists)
    user_id        VARCHAR(32) NULL,            -- filled once identified
    login_session_id VARCHAR(48) NULL,          -- login_sessions.token, if logged in (not the analytics visit)
    event_name     ENUM('page_view','form_start','generate_lead','begin_checkout',
                        'purchase','payment_failed','identify') NOT NULL,
    report_id      VARCHAR(32) NULL,            -- present from the Lead stage onward
    product        VARCHAR(40) NULL,
    page_url       VARCHAR(512) NULL,           -- THIS event's own page (saved on every event)
    sequence       INT NULL,                    -- page order within the visit (your CSL sequence)
    entry_time     DATETIME NULL,
    exit_time      DATETIME NULL,               -- entry+exit give time-on-page
    value_paise    INT NULL,                    -- for checkout/purchase
    currency       CHAR(3) NULL,
    is_free_unlock TINYINT(1) NOT NULL DEFAULT 0,
    data_json      JSON NULL,                   -- event-specific extras ONLY (not a copy of the user)
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- NOTE: source (utm/referrer/fbc/fbp/li_fat_id/ga_client_id) and device (user_agent/ip)
    -- now live ONCE on the visit_sessions row and are read via visit_id JOIN — not copied per event.
    PRIMARY KEY (id),
    KEY idx_events_visit (visit_id),
    KEY idx_events_visitor (visitor_id),
    KEY idx_events_user (user_id),
    KEY idx_events_name (event_name),
    KEY idx_events_report (report_id),
    KEY idx_events_created (created_at),
    CONSTRAINT fk_events_visit FOREIGN KEY (visit_id) REFERENCES visit_sessions(visit_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_events_visitor FOREIGN KEY (visitor_id) REFERENCES visitors(visitor_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_events_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE,   -- keep the event, drop the user link
    CONSTRAINT fk_events_report FOREIGN KEY (report_id) REFERENCES reports(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ------------------------------------------------------------- geocache ------
-- Self-rebuilding cache of place -> coordinates. Standalone (no FK). Kept as-is.
CREATE TABLE geocache (
    place       VARCHAR(200) NOT NULL,
    lat         DECIMAL(9,6) NULL,
    lon         DECIMAL(9,6) NULL,
    tz          DECIMAL(4,2) NULL,
    source      VARCHAR(40)  NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (place)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- --------------------------------------------------------- health_check ------
-- Trivial "is the DB alive/writable?" sentinel. Standalone.
CREATE TABLE health_check (
    token   VARCHAR(48) NOT NULL,
    ts      DATETIME    NOT NULL,
    PRIMARY KEY (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

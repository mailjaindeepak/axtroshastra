# Axtroshastra — Test Suite Audit

A grouped, one-line-per-test map of what the suite guards. Snapshot of the merged
`aws-mysql` line; open PRs add more (geocoding, engine/compat accuracy, ops
framework, etc.). **Total: 239 tests** — 220 pytest across 32 `tests/test_*.py`
files + 19 Playwright `test(...)` cases across 4 `tests/e2e/*.spec.js` files.
Two pytest functions are parametrized and expand further at runtime
(`test_chart_signs_match_astrosage` ≥20 charts; `test_shaadi_hi_resolves_structural_strings` 14).

## Summary

| Group | # tests | Why it matters |
|---|---|---|
| A. Astrology engine correctness & determinism | 27 | Charts must be right, reproducible, and never drift |
| B. Payments, accounts & delivery idempotency | 41 | Every payer gets exactly one report, once |
| C. WhatsApp report delivery & templates | 7 | The approved Twilio template mapping stays intact |
| D. Reports API, trust boundary & teaser | 33 | No paid content leaks before payment |
| E. PDF generation & rendering | 17 | The WhatsApp-attached PDF actually renders |
| F. Localization / Hindi | 40 | No English leaks into Hindi reports/autosuggest |
| G. Auth & OTP login | 15 | Login, session gating, account dashboard work |
| H. Funnel pages / routing / UX guards | 21 | Funnel fixes, redirects, in-app browser handling hold |
| I. LLM narrative layer | 11 | LLM prose never alters facts or leaks PII |
| J. Feature modules (i18n/geo/rate/pay) | 8 | Supporting utilities behave and fail safe |
| K. E2E browser (Playwright) | 19 | Real browser funnel + checkout flow works |

## A. Astrology engine correctness & determinism

| Test | Responsible for | Checks |
|---|---|---|
| test_engine_is_deterministic | Engine determinism | Same inputs → byte-identical report twice |
| test_report_has_expected_shape (engine) | Report schema | Has meta/teaser; meta.name preserved |
| test_vidyarthi_is_deterministic | Vidyarthi determinism | Same inputs → identical student report |
| test_report_has_expected_shape (vidyarthi) | Vidyarthi schema | Has meta/teaser/chart/windows/extras |
| test_windows_never_zero | Vidyarthi window fallback | Always ≥1 timing window returned |
| test_teaser_never_leaks_full_report_fields | Vidyarthi teaser gating | Teaser omits windows/extras |
| test_windows_stay_within_a_few_years | Vidyarthi window span | No window longer than ~4 years |
| test_stage_field_note_no_stage | Vidyarthi stage note | No stage → stage_note is None |
| test_stage_field_note_deciding_stage_has_no_named_field | 10th-stage note | Deciding-stage note mentions "direction" |
| test_stage_field_note_committed_stage_is_field_aware | College-stage note | College+Engineering note is field-aware |
| test_navamsa_known_values | D9 navamsa math | Known longitudes map to correct navamsa signs |
| test_dasamsa_known_values | D10 dasamsa math | Odd/even sign dasamsa start signs correct |
| test_bhinnashtakavarga_totals | Ashtakavarga per-planet | Each planet's bindu total matches classical value |
| test_sarvashtakavarga_grand_total_is_337 | Sarvashtakavarga invariant | 12 signs, grand total equals 337 |
| test_yoga_budha_aditya_detected | Yoga detection | Sun+Mercury same sign flags Budha-Aditya |
| test_analyze_is_deterministic | Divisional determinism | analyze(chart) equal on repeat |
| test_moon_identical_on_worker_thread | Thread-local ayanamsa | Lahiri Moon identical main vs worker thread |
| test_kundli_endpoint_uses_lahiri | Ayanamsa end-to-end | Route returns Lahiri nakshatra (Anuradha) |
| test_marriage_report_matches_golden | Golden regression | Marriage snapshot equals committed golden |
| test_divisional_matches_golden | Golden regression | Divisional analyze equals golden |
| test_marriage_report_produces_windows | Never-zero windows | Marriage report yields ≥1 window |
| test_vidyarthi_matches_golden | Golden regression | Vidyarthi snapshot equals golden |
| test_chart_signs_match_astrosage | Cross-tool accuracy | Ascendant+9 grahas signs match AstroSage (parametrized ≥20 charts) |
| test_fixture_is_non_trivial | Accuracy fixture guard | ≥20 reference celebrity charts present |
| test_gender_makes_result_order_independent | Milan direction | Guna scores/verdict order-independent with gender |
| test_only_varna_and_gana_are_direction_carriers | Milan koota symmetry | Six kootas unaffected by gender/direction |
| test_default_without_gender_still_runs | Milan default | No gender → 8 kootas, max_total 36 |

## B. Payments, accounts & delivery idempotency

| Test | Responsible for | Checks |
|---|---|---|
| test_verify_valid_signature_marks_paid | Verify fallback | Valid HMAC sig marks report paid |
| test_verify_bad_signature_400 | Verify signature guard | Bad signature → 400 |
| test_verify_unknown_order_404 | Verify order lookup | Unknown order_id → 404 |
| test_verify_missing_fields_400 | Verify input validation | Empty/partial body → 400 |
| test_webhook_then_verify_delivers_once | Webhook+verify idempotency | Both paths → one WhatsApp to popup |
| test_verify_then_webhook_delivers_once | Reverse-order idempotency | Verify-first still delivers exactly once |
| test_verify_twice_delivers_once | Double verify | Two verifies collapse to one delivery |
| test_reconcile_delivers_to_popup_number | Razorpay reconcile net | Orphan recovered, delivered to popup number |
| test_already_paid_report_not_redelivered | Reconcile idempotency | paid=1 rows never re-delivered |
| test_claim_gate_delivers_exactly_once | Atomic claim gate | Overlapping cycles deliver once |
| test_claim_paid_is_atomic | claim_paid primitive | Returns True once, then False forever |
| test_recovered_without_popup_number_skips_whatsapp | Recovery no-phone edge | Paid+generated, WhatsApp skipped gracefully |
| test_reconcile_noop_without_razorpay | Reconcile safe no-op | No creds → recovered 0, nothing sent |
| test_webhook_creates_and_links_account | Account from payment | Signed webhook creates user, links report |
| test_bare_ten_digit_mobile_is_normalised | Mobile normalisation | 10-digit → +91 form on account |
| test_same_mobile_two_reports_one_account | Mobile de-dupe | Two purchases → one account, first email kept |
| test_demo_pay_creates_no_account | Demo unlock | Demo/free pay creates no account |
| test_backfill_links_prepaid_reports | Account backfill | Old paid report linked; re-run no-op |
| test_backfill_requires_admin_key | Backfill auth | Missing/wrong key → 403 |
| test_norm_mobile_unit | Mobile normaliser unit | Various formats normalise to +91… |
| test_order_persists_popup_phone_and_email | Popup contact capture | Order stores normalised phone + email |
| test_order_does_not_clobber_existing_form_email | Email precedence | Form email not overwritten by popup |
| test_order_without_contact_still_works | Legacy order body | Order without contact still succeeds |
| test_webhook_prefers_popup_number_over_payment_contact | Account uses popup number | Account keyed on popup, not payment number |
| test_webhook_account_email_prefers_popup_over_payment | Account email precedence | Account email = popup email |
| test_webhook_falls_back_to_payment_contact | Payment-contact fallback | No popup → Razorpay contact creates account |
| test_milan_webhook_without_name_does_not_crash | Milan no-name webhook | Milan pay completes; name "P1 & P2" |
| test_webhook_does_not_auto_name_account_from_report | No auto-name account | Milan pay → blank account name |
| test_free_pass_creates_account_from_popup | Free-pass account | Pass unlock creates account from popup |
| test_free_pass_sends_whatsapp_like_paid_path | Free-pass delivery | Pass triggers PDF+WhatsApp to popup |
| test_free_pass_whatsapp_sent_exactly_once | Free-pass idempotency | Retry/burnt pass never re-sends |
| test_free_pass_without_phone_skips_whatsapp | Free-pass no-phone | Unlock succeeds, WhatsApp skipped |
| test_webhook_fires_server_side_purchase | Server-side Purchase | Capture calls track_purchase once with rid/value |
| test_dormant_without_keys | Tracking dormant | No keys → enabled False, no-op |
| test_enabled_flips_with_either_key | Tracking enable | Either Meta/GA4 key enables it |
| test_phone_normalisation | Phone hash prep | Normalises to 91… digits |
| test_sha256_lowercases_and_trims | PII hashing | sha256 lowercases and trims |
| test_ga_client_id_prefers_browser_then_stable_fallback | GA4 client id | Browser cid preferred; stable fallback |
| test_track_purchase_never_raises_even_if_a_sender_errors | Tracking resilience | Sender error swallowed, never raises |
| test_webhook_delivers_to_popup_number_not_razorpay | Delivery number policy | WhatsApp to popup, not Razorpay number |
| test_never_sends_to_razorpay_number_even_without_popup_number | No Razorpay delivery | No popup → nothing sent |

## C. WhatsApp report delivery & templates

| Test | Responsible for | Checks |
|---|---|---|
| test_media_template_passes_rid_as_bare_variable_3 | Twilio media template | {{3}} is bare rid, not a path |
| test_media_skipped_when_pdf_not_publicly_fetchable | PDF fetchability fallback | Unfetchable PDF → text template with link |
| test_pdf_is_fetchable_returns_false_when_probe_fails | Fetch probe safety | Probe errors → False, never raises |
| test_text_template_used_when_pdf_not_ready | Text template path | No PDF → text template with report link |
| test_no_send_when_twilio_env_unset | Env gating | Blank Twilio config → no client, no send |
| test_resend_wa_calls_send_for_paid_report_with_phone | Admin resend | Resend uses popup number, fires once |
| test_resend_wa_paid_report_without_phone | Resend no-phone | Returns no_phone_on_report |

## D. Reports API, trust boundary & teaser

| Test | Responsible for | Checks |
|---|---|---|
| test_healthz_ok | Health check | /healthz returns status ok |
| test_kundli_returns_teaser_not_full_report | Pre-pay gating | Response has teaser, no full report |
| test_report_is_gated_before_payment | Report gating | Unpaid report omits report body |
| test_webhook_rejects_bad_signature | Webhook signature | Bad signature → 400 |
| test_admin_routes_require_key | Admin auth | /api/stats needs correct key |
| test_name_is_html_escaped_in_rendered_report | XSS escaping | Script name HTML-escaped in report |
| test_vidyarthi_returns_teaser_not_full_report | Vidyarthi gating | Teaser only; windows paid-only |
| test_vidyarthi_report_is_gated_before_payment | Vidyarthi gating | Unpaid omits report |
| test_vidyarthi_unlocks_and_renders_after_demo_pay | Vidyarthi render | Paid renders career report, escaped |
| test_resend_wa_admin_gate | Resend auth | No key → 403 |
| test_resend_wa_unknown_rid | Resend lookup | Unknown rid → 404 |
| test_i18n_endpoint | i18n API | Returns catalog + supported langs |
| test_deep_analysis_requires_payment_then_works | Deep analysis gating | Unpaid 402; paid returns sav/divisional/yogas |
| test_pdf_route_is_gated | PDF route gating | Unpaid 404; paid 200 or 503 |
| test_pdf_dotext_route_matches_folder_route | .pdf route parity | /report/{id}.pdf byte-identical to /pdf |
| test_admin_reconcile_requires_key | Reconcile auth | No key 403; key 200 |
| test_report_page_has_all_trackers | Report analytics | GA/Pixel/Clarity present, Clarity once |
| test_login_page_has_all_trackers | Login analytics | All trackers present on /login |
| test_static_page_not_double_injected | No double-inject | Marketing page trackers fire once |
| test_created_report_is_immediately_retrievable | Write durability | Created report readable right after |
| test_report_survives_multiple_reads | Durable reads | Report readable 5× consecutively |
| test_healthz_db_selfcheck_passes | DB self-check | /healthz/db returns ok |
| test_order_for_missing_report_404s | Order lookup | Missing report → 404 |
| test_order_with_free_pass_unlocks_without_razorpay | Free-pass unlock | Pass marks paid, report retrievable |
| test_used_pass_is_rejected_second_time | Pass reuse | Burnt token → invalid_pass |
| test_order_on_already_paid_report_short_circuits | Already-paid order | Returns already_paid, no new order |
| test_total_equation_percentage_matches_its_fraction | Milan score display | Appendix N/36=P% correct, equals match_pct |
| test_share_button_shares_the_live_report_url | Milan share link | Share attaches live report URL |
| test_teaser_reveals_real_score_and_summary | Milan teaser hook | Score revealed, 2–3 theme cards |
| test_one_breath_is_single_source_of_truth | One-breath consistency | Teaser one_breath equals report's |
| test_teaser_hindi_fields_present_and_devanagari | Milan teaser Hindi | All _hi fields present, Devanagari |
| test_hindi_tables_cover_every_output | Hindi table coverage | 27 nakshatras + every verdict have Hindi |
| test_teaser_does_not_leak_paid_depth | Teaser gating | No kootas/verdicts/action plan leaked |

## E. PDF generation & rendering

| Test | Responsible for | Checks |
|---|---|---|
| test_playwright_shell_probed_before_system_chrome | Chrome probe order | Headless shell preferred over desktop Chrome |
| test_chrome_bin_env_override_wins | CHROME_BIN override | Explicit env binary wins |
| test_system_candidates_are_last_resort | Probe last resort | System Chrome only when nothing else |
| test_timeout_stays_below_alb_idle_timeout | Timeout budget | Render timeout < 60s ALB idle |
| test_failed_render_is_not_retried_within_cooldown | Negative cache | Failed rid not re-rendered in cooldown |
| test_success_after_cooldown_clears_the_flag | Cooldown clear | Success clears fail flag, caches PDF |
| test_busy_renderer_falls_back_without_negative_cache | Lock patience | Busy → prompt fallback, no negative cache |
| test_localize_fonts_inlines_local_devanagari_faces | Font localization | Google fonts inlined to local woff2 |
| test_localize_fonts_leaves_unknown_urls_remote | Font passthrough | Unknown font URL left untouched |
| test_generate_writes_localized_html | Localized render | Chrome fed font-localized HTML |
| test_download_snippet_retries_before_print_fallback | Client PDF retry | Retries once before print() fallback |
| test_pdf_health_requires_admin_key | PDF health auth | Missing/wrong key → 403 |
| test_pdf_health_reports_missing_chrome | Missing Chrome report | No binary → render_ok False, generate skipped |
| test_pdf_health_ok_when_render_succeeds | PDF health ok | Success reports bytes and render_ms |
| test_pdf_health_flags_broken_render | Broken render | Empty render → not ok, error set |
| test_pdf_download_header_survives_devanagari_name | Latin-1 header safety | Devanagari name PDF header doesn't crash |
| test_pdf_dotext_route_also_survives_devanagari_name | .pdf header safety | Devanagari .pdf route header latin-1 safe |

## F. Localization / Hindi

| Test | Responsible for | Checks |
|---|---|---|
| test_marriage_hindi_banks_have_no_english_runs | Hindi banks (LLM off) | No English runs in Hindi marriage report |
| test_marriage_hindi_with_llm_has_no_english_runs | Hindi shell (LLM on) | Structural shell doesn't leak English |
| test_milan_hindi_has_no_english_runs | Hindi milan report | No English/Hinglish in Hindi milan |
| test_shaadi_hi_resolves_structural_strings | Hindi string localizer | Structural strings translate fully (parametrized) |
| test_shaadi_hi_title_pattern_keeps_name | Title localization | Name kept, rest translated |
| test_report_page_chrome_is_hindi | Served chrome Hindi | Nav/toasts render Hindi on hi report |
| test_report_page_chrome_stays_english_for_en | Served chrome English | EN report keeps English chrome |
| test_milan_v1_fallback_is_localized | v1 fallback localize | Legacy milan localized, toggle pinned hi |
| test_milan_facts_scrub_substitutes_devanagari_for_hi | LLM facts scrub (hi) | Hinglish replaced with Devanagari facts |
| test_milan_facts_scrub_drops_hinglish_for_english | LLM facts scrub (en) | Hinglish koota text dropped |
| test_hi_system_prompt_has_language_directives | Hindi LLM prompt | Prompt demands Devanagari, no Hinglish |
| test_devanagari_guardrail_drops_english_sections | Devanagari guardrail | English model sections dropped for hi |
| test_devanagari_ratio_helper | Devanagari detector | Classifies Devanagari vs English text |
| test_backfill_narrative_requires_key | Narrative backfill auth | No key → 403 |
| test_backfill_narrative_queues_hindi_marriage_reports | Narrative backfill | Queues hi marriage reports |
| test_backfill_narrative_single_rid | Narrative backfill single | Single rid queued; unknown → 404 |
| test_jaipur_devanagari | Devanagari autosuggest | जयपुर → Jaipur, ASCII label |
| test_mumbai_both_spellings | Spelling variants | Both Mumbai spellings resolve |
| test_delhi | Devanagari Delhi | दिल्ली → Delhi + New Delhi |
| test_nukta_insensitive | Nukta folding | Nukta variants both match Ghaziabad |
| test_alias_table_fills_geonames_gaps | Curated aliases | Alias table resolves gap cities |
| test_devanagari_prefix | Prefix suggest | 2-char prefix suggests Jaipur |
| test_devanagari_common_cities_top1 | Common city top hit | 8 cities resolve top-1 |
| test_short_or_empty_query | Empty query | Short/empty query → no results |
| test_english_regression | English intact | English queries still resolve |
| test_non_devanagari_non_latin_scripts_do_not_match | Script filter | CJK/Katakana names don't match |
| test_name_hi_present_for_major_cities | Hindi display name | Major cities carry name_hi, ASCII label |
| test_name_hi_prefers_modern_common_form | Modern name form | Prefers modern over archaic Hindi name |
| test_name_hi_omitted_for_uncurated_small_towns | name_hi omission | Uncurated towns omit name_hi |
| test_name_hi_is_devanagari_label_is_latin_everywhere | Label/name_hi scripts | label Latin, name_hi Devanagari everywhere |
| test_hi_pages_render_name_hi_but_submit_english_label | HI page wiring | Row shows Hindi, submits English label |
| test_english_pages_untouched_by_name_hi | EN pages untouched | English pages have no name_hi |
| test_api_city_suggest_devanagari | City-suggest API | जयपुर → Jaipur, schema + name_hi |
| test_api_city_suggest_delhi_name_hi | City-suggest Delhi | Delhi label + name_hi correct |
| test_suggested_label_geocodes_offline | Offline geocode | Suggested labels resolve without geocoder |
| test_goa_devanagari_resolves_to_panaji | Goa Devanagari | गोवा → Panjim, name_hi पणजी |
| test_goa_english_surfaces_goa_city_not_assam | Goa disambiguation | 'goa' tops Panjim, not Goalpara |
| test_goa_cities_devanagari_typeable | Goa cities | Goa city Devanagari names resolve |
| test_goa_labels_ascii_and_geocode_endtoend | Goa label geocode | ASCII labels geocode without raising |
| test_goa_labels_geocode_to_goa_not_delhi | Goa coordinates | Goa labels resolve to Goa, not Delhi |

## G. Auth & OTP login

| Test | Responsible for | Checks |
|---|---|---|
| test_full_login_flow_sets_session | OTP login flow | Verify sets session cookie, /api/me works |
| test_wrong_code_rejected | OTP wrong code | Wrong code → 401 |
| test_account_page_requires_session | Account gating | Logged-out /account → 302 to login?next |
| test_account_page_shows_details_when_logged_in | Account dashboard | Shows details, formatted mobile, nav |
| test_logout_clears_session | Logout | /api/me 401 after logout |
| test_login_creates_account_for_new_number | New-number login | First login upserts an account |
| test_login_surfaces_prior_paid_reports | Prior reports | Linked paid reports appear on dashboard |
| test_account_name_update_requires_session | Name update gating | No session → 401, no write |
| test_account_name_update_persists | Name update persist | Trimmed name saved, prefilled, greeted |
| test_account_page_shows_name_placeholder_when_blank | Blank-name UX | Placeholder + "Add your name" prompt |
| test_nav_injected_on_marketing_pages | Nav injection | Marketing pages carry account/blog nav |
| test_login_page_serves_without_params | Login page serves | GET /login 200 with/without next |
| test_mc_send_hits_v3_send_with_contract_params | MessageCentral send | POSTs v3/send, bare mobile, authToken header |
| test_mc_validate_hits_v3_validate | MessageCentral validate | GET v3/validateOtp with verificationId |
| test_login_redirects_when_already_logged_in | Login redirect safety | Logged-in redirect; open-redirect blocked |

## H. Funnel pages / routing / UX guards

| Test | Responsible for | Checks |
|---|---|---|
| test_bug3_restore_does_not_carry_report | Lang-switch report reset | Switch nulls stale report id/teaser |
| test_bug4_name_excluded_from_switch_restore | Name reset on switch | Name skipped, other fields restored |
| test_bug5_startpayment_always_asks_contact | Contact modal always | startPayment always opens contact modal |
| test_bug6_banner_close_and_autohide | Recovery banner UX | Close button + 8s auto-hide |
| test_bug7_sticky_hidden_on_focus | Sticky bar keyboard | Sticky ₹499 hidden on field focus |
| test_pages_have_balanced_script_tags | Script integrity | script open/close balanced (4 funnel pages) |
| test_pages_have_required_ids | Required page ids | Form/sticky/name ids + entry points present |
| test_en_milan_report_has_no_gift_section_or_banner | Gift/banner removal | EN milan report has no gift/banner |
| test_hi_milan_report_has_no_gift_section_or_banner | Hindi gift removal | HI milan lacks gift copy/banner |
| test_marriage_report_has_no_gift_section_or_banner | Marriage gift removal | Marriage report has no gift/banner |
| test_match_redirects_to_en_compatibility | /match redirect | /match 301 → /en/compatibility |
| test_match_redirect_preserves_pass_query | Redirect query | pass token preserved on redirect |
| test_compatibility_funnels_serve_200 | Compatibility funnels | EN/HI compatibility serve 200 |
| test_legacy_path_301 | Legacy redirects | Old paths 301 to canonical (parametrized) |
| test_legacy_path_preserves_pass_query | Redirect query | Pass query preserved on 301 |
| test_inapp_detection_helper_present | In-app UA detection | axInApp matches IG/FB/TikTok/etc |
| test_inapp_banner_markup_and_logic_en | In-app banner EN | Dismissible banner, platform steps, PDF link |
| test_inapp_banner_hindi_copy | In-app banner HI | Hindi banner copy, English gone |
| test_download_has_inapp_direct_pdf_branch | In-app PDF download | Opens direct /pdf; blob path intact |
| test_inapp_share_clipboard_fallback | Share fallback | Clipboard copy fallback present |
| test_report_script_tags_balanced | Script integrity | Report script tags balanced |

## I. LLM narrative layer

| Test | Responsible for | Checks |
|---|---|---|
| test_disabled_by_default_returns_empty | Off by default | Disabled → empty narrative |
| test_claude_provider_generates_and_escapes | Claude provider | Generates + HTML-escapes output |
| test_openai_provider_switch | OpenAI provider | Switch hits OpenAI, json_object format |
| test_pii_is_scrubbed_from_prompt | PII scrub | Email/phone/surname dropped from prompt |
| test_altered_score_section_is_dropped | Facts-frozen guard | Wrong-number section dropped, clean kept |
| test_correct_score_in_prose_is_allowed | Correct-score allowed | Right numbers in prose survive |
| test_missing_api_key_falls_back | Missing key fallback | Enabled but no key → empty |
| test_bad_json_falls_back | Bad JSON fallback | Non-JSON response → empty |
| test_unknown_product_returns_empty | Unknown product | Unknown product → empty |
| test_narr_accessor | Narrative accessor | narr() reads value, defaults None |
| test_parse_json_strips_code_fences | JSON parsing | Strips fences/prose around JSON |

## J. Feature modules (i18n / geocoding / ratelimit / payments)

| Test | Responsible for | Checks |
|---|---|---|
| test_i18n_translation_and_fallback | i18n translate/fallback | Known keys translate; unknown key returned |
| test_i18n_normalize_lang | Lang normalisation | Region tags → base; unknown → default |
| test_geocode_known_city_no_network | Offline geocode | Mumbai resolves offline, tz 5.5 |
| test_geocode_unknown_falls_back_to_delhi | Geocode fallback | Unknown city → Delhi default |
| test_rate_limiter_blocks_after_burst | Rate limiting | ~10 allowed per burst on /api/kundli |
| test_captcha_disabled_returns_true | Captcha disabled | No provider → captcha_ok True |
| test_webhook_idempotency | Payment idempotency | event_id dedup: processed once |
| test_reconcile_noop_without_razorpay | Reconcile no-op | No Razorpay → recovered 0 |

## K. E2E browser (Playwright)

| Test | Responsible for | Checks |
|---|---|---|
| Checkout happy path (checkout) | Unlock→pay→paid report | Order gets report_id, Razorpay opens, redirects to /report |
| Checkout aborts on 503 (checkout) | Order-failure UX | 503 order → alert, stays on funnel |
| form_start not re-fired on toggle (lang_toggle) | form_start dedup | Toggle keeps started flag; name cleared, no refire |
| form_start fires on first fill (lang_toggle) | form_start tracking | Genuine first focus fires exactly once |
| Hero/pricing show career (padhai) | Career product copy | Hero + paywall show Career/Academic |
| Date validation 31 Feb (padhai) | Date validation | Impossible date hides teaser |
| Happy path vidyarthi teaser (padhai) | Vidyarthi submit | Teaser renders; product=vidyarthi, stage sent |
| Stage reveals field dropdown (padhai) | Conditional field | College reveals field; 10th hides it |
| Field submitted for college (padhai) | Field submission | stage=college, field=Engineering sent |
| DOB month widest keeps label (shaadi) | DOB layout | Month widest, label visible, no overflow |
| DOB typed DD/YYYY inputs (shaadi) | DOB inputs | DD/YYYY placeholders present |
| Date validation 31 Feb (shaadi) | Date validation | Invalid date → teaser hidden |
| Time minute 5-min steps (shaadi) | Time control | 5-min steps; AM/PM prompt disabled |
| City autosuggest placement (shaadi) | City autosuggest | Dropdown anchored to input, no localities |
| Language toggle EN↔HI (shaadi) | Language links | Toggle navigates EN/HI with active state |
| /shaadi redirects to /en/marriage (shaadi) | Redirect | /shaadi → /en/marriage, status <400 |
| Happy path teaser (shaadi) | Marriage submit | Valid submit renders teaser |
| Unknown-time clears error (shaadi) | Partial-time UX | Ticking unknown clears stale error |
| Partial-time error Hindi page (shaadi) | Hindi partial-time | Error clears on hi marriage page too |

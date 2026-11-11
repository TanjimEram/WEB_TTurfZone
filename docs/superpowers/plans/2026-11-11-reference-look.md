# Reference Look (Part C, CR-11) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** The public pages look and flow like https://turfxsonagazi.com (studied 2026-11-11), with TTURFZONE's own photos, logo and text. The admin keeps its current look.

**Architecture:** A new `static/css/site.css`, loaded only by `templates/base.html` after `main.css`, sets light tokens (default) and dark tokens (`[data-theme="dark"]`) and restyles the public components; `main.css` stays the shared base, so the admin (`base_admin.html` loads `main.css` + `admin.css`) is untouched. Templates are restructured in the reference's order; `booking.js` is rewritten for the date box + tabs + cards.

**Tech Stack:** Jinja, plain CSS custom properties, vanilla JS, pytest.

**Spec:** `docs/superpowers/specs/2026-11-11-trxid-booking-24-slots-redesign-design.md` (Part C)

## Global Constraints

- Matched from the reference (measured): system font stack (`ui-sans-serif, system-ui, …`); ink `#111827` (headings) / `#020817` (body); accent emerald `#10b981`, deeper `#059669` (active tab), teal `#0d9488` (hero button gradient end); page ground `#ffffff`, section ground `#fafafa` / `#f9fafb`; cards white, radius 16px, border `#f3f4f6`, soft shadow; section titles 36px weight 700–900; Book Now button radius 8px, 14px, weight 900; pill buttons radius 9999px; footer `#111827` with white text.
- Not copied: their code, photos, logo, wording. Business claims only from the owner (D-50 hides empty sections in production).
- Light theme by default; dark via a header toggle stored in `localStorage` (`tturf-theme`), applied by an inline script in `<head>` before paint; `localStorage` access wrapped in try/catch.
- Prices on public pages in Bangla digits with a trailing taka sign: `১,০০০৳` (filter `taka` and `booking.js`). The bKash payment amount stays `৳500` (matches what the bKash app shows).
- Sticky mobile WhatsApp / Book now bar stays (brief §2), restyled.
- Accessibility kept: skip link, one `h1`, headings on every section, visible focus, real buttons, `aria-pressed` / `aria-selected` on toggles and tabs, alt text, `prefers-reduced-motion` stops the slideshow and travel.
- No new dependency. Commits `<type>(M7.9): ...`; plan + session log in the last commit; `pytest -q` green before push.

## Review Focus

1. Dark mode on every public page (booking form, success, sign-in, privacy) keeps readable contrast, and the admin is unchanged in both themes. (Task 1 `test_admin_does_not_load_site_css`; browser check in Task 5.)
2. Night slots after midnight under the Night tab still show their real date and book on it after the picker rewrite. (Task 3 `test_picker_markup_has_tabs_and_date_box` + browser booking in Task 5.)
3. No-JS visitor: the booking section still offers a way to book (fallback link), and the slideshow shows the first picture. (Task 2/3 tests on fallback markup.)
4. A phone at 360 px: tabs, cards and the date box fit without page overflow; Book now buttons ≥ 44 px. (Task 5 browser.)
5. Production with no owner content: Why Choose Us, Ground Rules and Contact hide without dead links. (Task 4 production tests.)

---

### Task 1: Theme, header, footer (M7.9)

**Files:** Create `static/css/site.css`; modify `templates/base.html` (load site.css, no-flash theme script), `templates/partials/nav.html` (theme toggle button, Login pill), `templates/partials/footer.html` (dark footer: brand + tagline, contact, opening hours, copyright), `static/js/main.js` (toggle), `routes/public.py` (`taka` → Bangla digits); tests `tests/test_home_page.py`.

- [ ] Tests: `test_site_css_and_theme_script_in_head` (base has `css/site.css` and an inline script reading `tturf-theme` before the stylesheet), `test_theme_toggle_button` (`data-theme-toggle`, `aria-label`), `test_admin_does_not_load_site_css`, `test_prices_use_bangla_digits` (homepage price card shows `১,০০০৳`; update `test_settings_save_updates_public_site` expectations).
- [ ] Run → FAIL; implement; run → PASS; commit `feat(M7.9): light theme with dark toggle, reference header and footer`.

### Task 2: Hero slideshow (M7.9)

**Files:** `templates/index.html` (hero), `static/js/hero.js` (new), `site.css`; tests `tests/test_home_page.py`.

- Slides: the CR-7 illustration first, then the real photos (`PHOTOS`); each an `img()` with its alt text; only the first `loading="eager"`. Dots are buttons (`aria-label="Show picture N"`, `aria-current`). Autoplay every 6 s, paused on hover/focus, off with `prefers-reduced-motion`; without JS only the first slide shows.
- Text: "Welcome to" / the turf name in emerald / the tagline (owner) or the D-50 fallback line; "Book Your Slot" (pill, emerald→teal like the reference) to `#book`.
- [ ] Tests: `test_hero_slideshow_slides_and_dots` (illustration + every photo, dots count = slides, first eager, rest lazy), `test_hero_has_one_h1_with_the_turf_name`.
- [ ] FAIL → implement → PASS; commit `feat(M7.9): hero photo slideshow`.

### Task 3: Book Your Turf section (M7.9)

**Files:** `templates/partials/slot_picker.html` (rewrite), `static/js/booking.js` (rewrite), `routes/public.py` (`_date_chips` → `window_days` list for min/max), `site.css`; tests `tests/test_public_routes.py`, `tests/test_admin_routes.py` (chip counts).

- Markup: heading "Book Your Turf" + the selected date in full ("Wednesday, November 11, 2026"); a bar with ‹ [native `input type=date` min=first operating day max=last] › and **Available / Booked** counts for the open hours of that day; tabs **Morning (6AM–12PM) / Afternoon (12PM–6PM) / Night (6PM–6AM)** (`role=tablist`, `aria-selected`), opening on the first tab with a future slot; cards in 3 / 2 / 1 columns: logo emblem, status pill (Available / Booked / Blocked / Past), time range "6:00 AM – 7:00 AM", "60 mins", the slot's real date ("Nov 12, 2026"), PRICE in Bangla digits, **BOOK NOW** (homepage: link to `/book?date=<real date>&slot=HH:MM`; `/book`: selects the slot into the form and scrolls to it). Booked cards: red price, no button.
- Server renders the date input (`value`, `min`, `max`, `data-window` days) so tests and no-JS work; no-JS fallback link stays.
- [ ] Tests: replace chip tests with `test_picker_markup_has_tabs_and_date_box` (input type=date with min/max = window, three tabs with the spans, counts placeholders), `test_book_preselects_operating_day_in_date_box` (value = operating day of `?date=&slot=`), window-length test via `max`.
- [ ] FAIL → implement → PASS; browser: tabs switch, Night shows 12 cards with next-day dates, BOOK NOW → sign-in → back to `/book` with the slot selected; commit `feat(M7.9): reference booking section (date box, tabs, slot cards)`.

### Task 4: Pricing, About, Why Choose Us, Ground Rules, Contact (M7.9)

**Files:** `templates/index.html`, `site.css`, `services/settings.py` + `routes/admin.py` + `templates/admin/settings.html` (Why Choose Us textarea, stored in `turf_settings.facilities` as `[{"title", "text"}]`), `routes/public.py` (`sections` gains `features`, `rules`, `contact`); tests `tests/test_home_page.py`, `tests/test_production_content.py`, `tests/test_admin_routes.py`.

- Pricing: "Flexible Pricing Plans" + one card per open period (pill with period name, span, "60 min" row with the price). Hidden without prices (production).
- About Our Turf: two columns — one tall photo left, 2×2 photos right (lightbox kept), the owner's about text above.
- Why Choose Us: owner list from Settings ("Title: one line" per line, up to 8). Hidden when empty (production) with a TODO note in development (new C-32).
- Ground Rules: `booking_rules_text`, one card per line (up to 10). Hidden when empty.
- Contact ("Get In Touch"): phone, WhatsApp, email tturfzone@gmail.com, location + map when set.
- [ ] Tests: `test_why_choose_us_from_settings` (save "Floodlights: LED lights for night games" → card on `/`), `test_why_choose_us_hidden_in_production_when_empty`, `test_ground_rules_one_card_per_line`, `test_contact_section_lists_email`, nav links follow the shown sections (no dead links).
- [ ] FAIL → implement → PASS; commit `feat(M7.9): pricing cards, about gallery, why choose us, ground rules, contact`.

### Task 5: Check every width and theme, docs

- [ ] Browser at 360, 768, 1280 in light and dark: `/`, `/book` (signed in via a local test session is not possible without Google → check `/book` markup via the homepage section and tests; sign-in page and privacy page), no page overflow, headlines ≤ 2 lines, tap targets. Admin dashboard unchanged.
- [ ] `pytest -q`; docs: plan (M7.9, CR-11 done, D-55 theme/site.css decision, C-32 Why Choose Us items, QA items, session log, Resume here), commit, push.

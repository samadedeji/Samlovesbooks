# Samlovesbooks

Flask scaffold matching `story-platform-prd.md`, `frontend-app-flow.md`, and
`frontend-design-schema.md`.

## Structure

```
samlovesbooks/
  config.py            # env-driven config (DB URI, cookie names, cache)
  run.py                # dev entrypoint
  seed.py                # creates an admin user + sample content
  requirements.txt
  app/
    __init__.py         # app factory, blueprints, Jinja globals/filters
    models.py            # SQLAlchemy models (from models.py, unmodified schema
                          # + two ORM-only relationship() helpers on
                          # ReadingProgress for template convenience)
    utils.py              # font-size resolution, reader_token cookie,
                           # reader/admin auth decorators, progress upsert
    routes/
      reader.py           # Home, Series, Story, Chapter Reader, Browse
      account.py          # Sign up, Log in, Log out, My Account
      admin.py             # Admin auth + Series/Story/Chapter CRUD
    templates/            # Jinja2, split reader vs admin layouts
    static/css/style.css  # implements every token in frontend-design-schema.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

flask db upgrade     # apply database migrations
python seed.py       # optional, for local sample data
python run.py          # http://127.0.0.1:5000
```

Admin panel: `/admin/login` — username `leo`, password `changeme` (seed data;
change or remove before deploying).

## What's implemented vs. left as follow-up

**Implemented, matching the specs:**
- Full site map from `frontend-app-flow.md` §1: reader flow (Home, Series,
  Story ToC, Chapter Reader — both series-scoped and standalone URL shapes),
  optional reader accounts (signup/login/logout/My Account), and the full
  admin CRUD flow (series, stories, chapters, publish toggle, dashboard).
- Reading progress works for both anonymous visitors (`reader_token` cookie)
  and logged-in users, with the login/signup-time upgrade path described in
  `models.py`'s notes and PRD §6.3.
- Font-size control via `?size=` param + cookie only, no JS dependency.
- Every reader-facing route is plain `<a href>` / `<form>` — functions with
  JS disabled.
- Unpublished chapters and series/stories with no published chapters are
  excluded at the query level (see `_published_stories_query` and the
  `is_published` filters throughout `routes/reader.py`), not just hidden in
  templates.
- CSS implements the token system, type scale, spacing scale, and the
  signature "stamp" element exactly as specified in
  `frontend-design-schema.md`.

**Left for you to decide / fill in (flagged as open questions in the PRD):**
- Content storage is DB-backed (per `models.py`) rather than markdown files
  on disk — PRD §10 leaves this open; swap the admin chapter routes for a
  file-based loader if you'd rather author in a folder of `.md` files.
- No CSRF protection is wired up yet (e.g. Flask-WTF) — worth adding before
  any public deployment, especially for the admin forms.
- Flask-Caching is initialized but no routes are decorated with `@cache.cached`
  yet — add that once you've decided which pages benefit most (Home/Series/
  Story pages are good first candidates since they change rarely).
- No automated tests included.
- Chapter `content` is rendered through `python-markdown`; if you'd rather
  store pre-escaped HTML or a stricter markdown subset (for feature-phone
  rendering safety), adjust the `markdown` Jinja filter in `app/__init__.py`.
- Cross-device/Opera Mini testing (PRD §11 Phase 3) still needs to happen
  against a real device/emulator — nothing here has been rendering-tested
  outside a normal browser.

import secrets
from contextlib import contextmanager
from functools import wraps

from flask import current_app, g, redirect, request, session, url_for
from sqlalchemy.exc import IntegrityError


@contextmanager
def catch_integrity_error(db_session):
    try:
        yield
    except IntegrityError:
        db_session.rollback()
        raise


# ---------------------------------------------------------------------------
# Font size: URL param first, cookie second, default last. Never JS/localStorage.
# ---------------------------------------------------------------------------
def get_font_size():
    cfg = current_app.config
    param = request.args.get("size")
    if param in cfg["FONT_SIZE_CHOICES"]:
        return param
    cookie_val = request.cookies.get(cfg["FONT_SIZE_COOKIE"])
    if cookie_val in cfg["FONT_SIZE_CHOICES"]:
        return cookie_val
    return cfg["FONT_SIZE_DEFAULT"]


def persist_font_size_cookie(response):
    """If ?size= was passed on this request, persist it as a cookie so it
    carries forward even once the query param is gone."""
    cfg = current_app.config
    param = request.args.get("size")
    if param in cfg["FONT_SIZE_CHOICES"]:
        response.set_cookie(
            cfg["FONT_SIZE_COOKIE"], param, max_age=60 * 60 * 24 * 365,
            samesite="Lax", secure=cfg["FORCE_SECURE_COOKIES"]
        )
    return response


# ---------------------------------------------------------------------------
# Anonymous reading-progress token: a plain opaque cookie, no JS required.
# ---------------------------------------------------------------------------
def get_reader_token():
    """Reads the reader_token cookie for the current request, if any.
    Does not create one -- use ensure_reader_token_cookie on the response
    when a new token needs to be issued."""
    if "reader_token" not in g:
        g.reader_token = request.cookies.get(current_app.config["READER_TOKEN_COOKIE"])
    return g.reader_token


def ensure_reader_token_cookie(response):
    """Call on any reader-facing response that recorded progress. Issues a
    reader_token cookie if the visitor doesn't already have one."""
    cfg = current_app.config
    if not request.cookies.get(cfg["READER_TOKEN_COOKIE"]):
        token = secrets.token_urlsafe(32)
        g.reader_token = token
        response.set_cookie(
            cfg["READER_TOKEN_COOKIE"],
            token,
            max_age=60 * 60 * 24 * 365 * 2,
            httponly=True,
            samesite="Lax",
            secure=cfg["FORCE_SECURE_COOKIES"],
        )
    return response


# ---------------------------------------------------------------------------
# Reader auth (separate from admin auth)
# ---------------------------------------------------------------------------
def current_user():
    from .models import User

    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required_reader(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("account.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def upgrade_anonymous_progress(user_id, reader_token):
    """On login/signup: re-key any ReadingProgress rows tracked anonymously
    via reader_token cookie to the newly authenticated user_id, so nothing
    is lost by creating an account mid-story."""
    from .models import ReadingProgress, db

    if not reader_token:
        return

    anon_rows = ReadingProgress.query.filter_by(reader_token=reader_token).all()
    for row in anon_rows:
        existing = ReadingProgress.query.filter_by(
            user_id=user_id, story_id=row.story_id
        ).first()
        if existing:
            # User already has progress for this story -- keep whichever is
            # more recent, drop the anonymous row either way.
            if row.updated_at and (
                not existing.updated_at or row.updated_at > existing.updated_at
            ):
                existing.chapter_id = row.chapter_id
                existing.updated_at = row.updated_at
            db.session.delete(row)
        else:
            row.reader_token = None
            row.user_id = user_id
    db.session.commit()


def record_progress(story_id, chapter_id):
    """Upserts a ReadingProgress row for the current visitor, whether
    anonymous (reader_token) or logged in (user_id)."""
    from datetime import datetime

    from .models import ReadingProgress, db

    user = current_user()
    if user:
        row = ReadingProgress.query.filter_by(user_id=user.id, story_id=story_id).first()
        if not row:
            row = ReadingProgress(user_id=user.id, story_id=story_id)
            db.session.add(row)
    else:
        token = get_reader_token()
        if not token:
            # Token will be minted on the response; nothing to key against yet
            # until ensure_reader_token_cookie runs, so generate it now and
            # let the response layer just persist the same value.
            token = secrets.token_urlsafe(32)
            g.reader_token = token
            g.reader_token_is_new = True
        row = ReadingProgress.query.filter_by(reader_token=token, story_id=story_id).first()
        if not row:
            row = ReadingProgress(reader_token=token, story_id=story_id)
            db.session.add(row)

    row.chapter_id = chapter_id
    db.session.commit()


def finalize_reader_token_cookie(response):
    """After record_progress may have minted a fresh token in g, make sure
    it actually gets set on the response as a cookie."""
    cfg = current_app.config
    token = g.get("reader_token")
    if token and g.get("reader_token_is_new"):
        response.set_cookie(
            cfg["READER_TOKEN_COOKIE"],
            token,
            max_age=60 * 60 * 24 * 365 * 2,
            httponly=True,
            samesite="Lax",
            secure=cfg["FORCE_SECURE_COOKIES"],
        )
    return response


# ---------------------------------------------------------------------------
# Admin auth
# ---------------------------------------------------------------------------
def admin_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped

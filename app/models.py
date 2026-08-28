"""
Backend schema for Samlovesbooks.
Flask + SQLAlchemy models matching the PRD hierarchy:
Series -> Story -> Chapter, plus AdminUser, optional reader User accounts,
and reading progress (works for both anonymous and logged-in readers).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Series(db.Model):
    """Top-level grouping, e.g. "5'7 and Unbothered", or a standalone novel
    can just be its own Series with one Story in it."""
    __tablename__ = "series"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    cover_text = db.Column(db.String(500))  # short blurb, no heavy images needed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stories = db.relationship(
        "Story", back_populates="series", order_by="Story.order_index"
    )


class Story(db.Model):
    """A single manuscript/novel/narrative arc. May belong to a Series
    (e.g. an episode of "5'7 and Unbothered"), or stand alone as a
    normal novel/story with no parent series (e.g. Rebel, Gbotemi,
    Red Dawn). series_id is nullable to support both."""
    __tablename__ = "stories"

    id = db.Column(db.Integer, primary_key=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=True)
    slug = db.Column(db.String(120), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.String(20), default="ongoing"
    )  # ongoing | complete | hiatus
    order_index = db.Column(db.Integer, default=0)  # display order within series
    genre = db.Column(db.String(50))  # e.g. horror, personal-narrative, fiction
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    series = db.relationship("Series", back_populates="stories")
    chapters = db.relationship(
        "Chapter", back_populates="story", order_by="Chapter.chapter_number"
    )


class Chapter(db.Model):
    """Individual readable unit. Content stored as plain text/markdown —
    rendered server-side, no client JS required."""
    __tablename__ = "chapters"

    id = db.Column(db.Integer, primary_key=True)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    chapter_number = db.Column(db.Integer, nullable=False)
    slug = db.Column(db.String(120), nullable=False, index=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)  # markdown or plain text
    word_count = db.Column(db.Integer, default=0)
    is_published = db.Column(db.Boolean, default=False, index=True)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    story = db.relationship("Story", back_populates="chapters")

    __table_args__ = (
        db.UniqueConstraint("story_id", "chapter_number", name="uq_story_chapter_number"),
        db.UniqueConstraint("story_id", "slug", name="uq_story_chapter_slug"),
    )


class AdminUser(db.Model):
    """Publishing/admin access — just Leo for now, but built to support more."""
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class User(db.Model):
    """Optional reader account. Reading the site never requires one —
    this exists purely so a reader who wants it can sync reading
    progress and bookmarks across devices. Distinct from AdminUser:
    this is for readers, AdminUser is for publishing access."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class ReadingProgress(db.Model):
    """Tracks last-read chapter per reader. Works for BOTH anonymous
    readers (keyed by a cookie-issued reader_token) and logged-in
    readers (keyed by user_id) — exactly one of the two is set per row.
    This is what account login upgrades: on login, any existing
    anonymous-token rows for that browser are re-keyed to the user_id
    so progress isn't lost when someone decides to create an account
    partway through a story."""
    __tablename__ = "reading_progress"

    id = db.Column(db.Integer, primary_key=True)
    reader_token = db.Column(db.String(64), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    story_id = db.Column(db.Integer, db.ForeignKey("stories.id"), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey("chapters.id"), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ORM convenience relationships (no schema/behavior change) so templates
    # and routes can do row.story / row.chapter directly.
    story = db.relationship("Story")
    chapter = db.relationship("Chapter")

    __table_args__ = (
        db.UniqueConstraint("reader_token", "story_id", name="uq_reader_story_progress"),
        db.UniqueConstraint("user_id", "story_id", name="uq_user_story_progress"),
        db.CheckConstraint(
            "(reader_token IS NOT NULL) OR (user_id IS NOT NULL)",
            name="ck_progress_has_owner",
        ),
    )


# --- Notes ---
# - Font-size preference (?size=lg) is stateless via query param + cookie;
#   doesn't need a DB table, handled at the request/session layer.
# - Chapter.content stored as markdown text rather than HTML, rendered
#   server-side per request (or cached) to keep authoring simple and
#   avoid storing bulky pre-rendered HTML.
# - word_count can be computed on save (in the admin route) to avoid
#   recalculating on every page render.
# - Story.series_id is nullable: a Story can belong to a Series (URL:
#   /series/<series_slug>/<story_slug>/<chapter_slug>) OR stand alone
#   with no series (URL: /story/<story_slug>/<chapter_slug>). Story.slug
#   is globally unique across both cases, so routing/lookup works either
#   way without collision.
# - Indexes on slug fields support clean, cache-friendly URLs in both
#   the series-scoped and standalone forms above.
# - User accounts are entirely optional. Every reading-facing route must
#   work identically for a signed-out reader (reader_token cookie) and a
#   signed-in one (user_id) — ReadingProgress just has two ways to be
#   owned. On login/signup, the app should look up any ReadingProgress
#   rows matching the current reader_token cookie and re-key them to the
#   new user_id (delete-then-insert or UPDATE, since the unique
#   constraints are per-owner-type) so a guest doesn't lose progress by
#   creating an account mid-story.
# - User.password_hash uses the same werkzeug hashing helpers as
#   AdminUser — the two are still separate tables/roles, this is just
#   implementation reuse, not a shared login system.

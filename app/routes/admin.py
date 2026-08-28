import re
from datetime import datetime

from flask import Blueprint, redirect, render_template, request, session, url_for

from ..models import AdminUser, Chapter, Series, Story, User, db
from ..utils import admin_login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def slugify(value):
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        admin = AdminUser.query.filter_by(username=username).first()

        if not admin or not admin.check_password(password):
            return render_template(
                "admin/login.html", error="Incorrect username or password.", username=username
            )

        session["admin_id"] = admin.id
        next_url = request.form.get("next") or url_for("admin.dashboard")
        return redirect(next_url)

    next_url = request.args.get("next", "")
    return render_template("admin/login.html", error=None, next_url=next_url)


@admin_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("admin_id", None)
    return redirect(url_for("admin.login"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@admin_bp.route("")
@admin_login_required
def dashboard():
    counts = {
        "series": Series.query.count(),
        "stories": Story.query.count(),
        "published_chapters": Chapter.query.filter_by(is_published=True).count(),
        "draft_chapters": Chapter.query.filter_by(is_published=False).count(),
        "readers": User.query.count(),
    }
    recent_chapters = (
        Chapter.query.order_by(Chapter.updated_at.desc()).limit(5).all()
    )
    return render_template("admin/dashboard.html", counts=counts, recent_chapters=recent_chapters)


# ---------------------------------------------------------------------------
# Series
# ---------------------------------------------------------------------------
@admin_bp.route("/series")
@admin_login_required
def series_list():
    all_series = Series.query.order_by(Series.title).all()
    return render_template("admin/series_list.html", series_list=all_series)


@admin_bp.route("/series/new", methods=["GET", "POST"])
@admin_login_required
def series_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        slug = request.form.get("slug", "").strip() or slugify(title)
        series = Series(
            title=title,
            slug=slug,
            description=request.form.get("description", ""),
            cover_text=request.form.get("cover_text", ""),
        )
        db.session.add(series)
        db.session.commit()
        return redirect(url_for("admin.series_list"))
    return render_template("admin/series_form.html", series=None)


@admin_bp.route("/series/<int:series_id>/edit", methods=["GET", "POST"])
@admin_login_required
def series_edit(series_id):
    series = Series.query.get_or_404(series_id)
    if request.method == "POST":
        series.title = request.form.get("title", "").strip()
        series.slug = request.form.get("slug", "").strip() or slugify(series.title)
        series.description = request.form.get("description", "")
        series.cover_text = request.form.get("cover_text", "")
        db.session.commit()
        return redirect(url_for("admin.series_list"))
    return render_template("admin/series_form.html", series=series)


# ---------------------------------------------------------------------------
# Stories
# ---------------------------------------------------------------------------
@admin_bp.route("/stories")
@admin_login_required
def stories_list():
    series_id = request.args.get("series_id")
    query = Story.query
    if series_id == "none":
        query = query.filter(Story.series_id.is_(None))
    elif series_id:
        query = query.filter(Story.series_id == int(series_id))
    stories = query.order_by(Story.title).all()
    all_series = Series.query.order_by(Series.title).all()
    return render_template(
        "admin/stories_list.html", stories=stories, all_series=all_series, series_id=series_id
    )


@admin_bp.route("/stories/new", methods=["GET", "POST"])
@admin_login_required
def story_new():
    all_series = Series.query.order_by(Series.title).all()
    if request.method == "POST":
        series_id = request.form.get("series_id") or None
        title = request.form.get("title", "").strip()
        story = Story(
            series_id=int(series_id) if series_id else None,
            title=title,
            slug=request.form.get("slug", "").strip() or slugify(title),
            description=request.form.get("description", ""),
            status=request.form.get("status", "ongoing"),
            genre=request.form.get("genre", ""),
            order_index=int(request.form.get("order_index") or 0),
        )
        db.session.add(story)
        db.session.commit()
        return redirect(url_for("admin.stories_list", series_id=series_id or "none"))
    return render_template(
        "admin/story_form.html",
        story=None,
        all_series=all_series,
        preselect_series_id=request.args.get("series_id"),
    )


@admin_bp.route("/stories/<int:story_id>/edit", methods=["GET", "POST"])
@admin_login_required
def story_edit(story_id):
    story = Story.query.get_or_404(story_id)
    all_series = Series.query.order_by(Series.title).all()
    if request.method == "POST":
        series_id = request.form.get("series_id") or None
        story.series_id = int(series_id) if series_id else None
        story.title = request.form.get("title", "").strip()
        story.slug = request.form.get("slug", "").strip() or slugify(story.title)
        story.description = request.form.get("description", "")
        story.status = request.form.get("status", "ongoing")
        story.genre = request.form.get("genre", "")
        story.order_index = int(request.form.get("order_index") or 0)
        story.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("admin.stories_list", series_id=series_id or "none"))
    return render_template(
        "admin/story_form.html", story=story, all_series=all_series, preselect_series_id=None
    )


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------
@admin_bp.route("/stories/<int:story_id>/chapters")
@admin_login_required
def chapters_list(story_id):
    story = Story.query.get_or_404(story_id)
    chapters = (
        Chapter.query.filter_by(story_id=story.id)
        .order_by(Chapter.chapter_number)
        .all()
    )
    return render_template("admin/chapters_list.html", story=story, chapters=chapters)


@admin_bp.route("/stories/<int:story_id>/chapters/<int:chapter_id>/toggle-publish", methods=["POST"])
@admin_login_required
def chapter_toggle_publish(story_id, chapter_id):
    chapter = Chapter.query.filter_by(id=chapter_id, story_id=story_id).first_or_404()
    chapter.is_published = not chapter.is_published
    chapter.published_at = datetime.utcnow() if chapter.is_published else None
    db.session.commit()
    return redirect(url_for("admin.chapters_list", story_id=story_id))


@admin_bp.route("/chapters/new", methods=["GET", "POST"])
@admin_login_required
def chapter_new():
    all_stories = Story.query.order_by(Story.title).all()
    preselect_story_id = request.args.get("story_id")
    if request.method == "POST":
        story_id = int(request.form.get("story_id"))
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "")
        chapter = Chapter(
            story_id=story_id,
            chapter_number=int(request.form.get("chapter_number")),
            title=title,
            slug=request.form.get("slug", "").strip() or slugify(title),
            content=content,
            word_count=len(content.split()),
            is_published=bool(request.form.get("is_published")),
        )
        if chapter.is_published:
            chapter.published_at = datetime.utcnow()
        db.session.add(chapter)
        db.session.commit()
        return redirect(url_for("admin.chapters_list", story_id=story_id))
    return render_template(
        "admin/chapter_form.html",
        chapter=None,
        all_stories=all_stories,
        preselect_story_id=preselect_story_id,
    )


@admin_bp.route("/chapters/<int:chapter_id>/edit", methods=["GET", "POST"])
@admin_login_required
def chapter_edit(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    all_stories = Story.query.order_by(Story.title).all()
    if request.method == "POST":
        chapter.story_id = int(request.form.get("story_id"))
        chapter.chapter_number = int(request.form.get("chapter_number"))
        chapter.title = request.form.get("title", "").strip()
        chapter.slug = request.form.get("slug", "").strip() or slugify(chapter.title)
        chapter.content = request.form.get("content", "")
        chapter.word_count = len(chapter.content.split())
        was_published = chapter.is_published
        chapter.is_published = bool(request.form.get("is_published"))
        if chapter.is_published and not was_published:
            chapter.published_at = datetime.utcnow()
        chapter.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for("admin.chapters_list", story_id=chapter.story_id))
    return render_template(
        "admin/chapter_form.html",
        chapter=chapter,
        all_stories=all_stories,
        preselect_story_id=None,
    )

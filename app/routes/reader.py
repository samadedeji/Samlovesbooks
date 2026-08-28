from flask import Blueprint, abort, make_response, render_template, request

from .. import cache
from ..models import Chapter, ReadingProgress, Series, Story
from ..utils import current_user, get_reader_token, record_progress

reader_bp = Blueprint("reader", __name__)


def _published_stories_query():
    """Stories that have at least one published chapter."""
    return (
        Story.query.join(Chapter)
        .filter(Chapter.is_published.is_(True))
        .filter(Story.is_archived.is_(False))
        .distinct()
    )


@reader_bp.route("/")
@cache.cached(timeout=300)
def home():
    all_series = (
        Series.query.join(Story)
        .join(Chapter)
        .filter(Chapter.is_published.is_(True))
        .filter(Series.is_archived.is_(False))
        .distinct()
        .order_by(Series.title)
        .all()
    )
    standalone_stories = (
        _published_stories_query()
        .filter(Story.series_id.is_(None))
        .order_by(Story.title)
        .all()
    )
    return render_template(
        "home.html", series_list=all_series, standalone_stories=standalone_stories
    )


@reader_bp.route("/series/<series_slug>")
@cache.cached(timeout=300, query_string=True)
def series_page(series_slug):
    series = Series.query.filter_by(slug=series_slug, is_archived=False).first_or_404()
    stories = (
        _published_stories_query()
        .filter(Story.series_id == series.id)
        .order_by(Story.order_index)
        .all()
    )
    if not stories:
        abort(404)
    return render_template("series.html", series=series, stories=stories)


def _render_story_page(story):
    chapters = (
        Chapter.query.filter_by(story_id=story.id, is_published=True)
        .order_by(Chapter.chapter_number)
        .all()
    )
    if not chapters:
        abort(404)

    last_read_chapter_number = None
    user = current_user()
    progress = None
    if user:
        progress = ReadingProgress.query.filter_by(
            user_id=user.id, story_id=story.id
        ).first()
    else:
        token = get_reader_token()
        if token:
            progress = ReadingProgress.query.filter_by(
                reader_token=token, story_id=story.id
            ).first()
    if progress:
        chapter = Chapter.query.get(progress.chapter_id)
        if chapter:
            last_read_chapter_number = chapter.chapter_number

    return render_template(
        "story.html",
        story=story,
        chapters=chapters,
        last_read_chapter_number=last_read_chapter_number,
    )


@reader_bp.route("/story/<story_slug>")
@cache.cached(timeout=300, query_string=True)
def story_page_standalone(story_slug):
    story = Story.query.filter_by(
        slug=story_slug, series_id=None, is_archived=False
    ).first_or_404()
    return _render_story_page(story)


@reader_bp.route("/series/<series_slug>/<story_slug>")
@cache.cached(timeout=300, query_string=True)
def story_page_series(series_slug, story_slug):
    series = Series.query.filter_by(slug=series_slug, is_archived=False).first_or_404()
    story = Story.query.filter_by(
        slug=story_slug, series_id=series.id, is_archived=False
    ).first_or_404()
    return _render_story_page(story)


def _render_chapter(story, chapter_slug):
    chapter = Chapter.query.filter_by(
        story_id=story.id, slug=chapter_slug, is_published=True
    ).first_or_404()

    prev_chapter = (
        Chapter.query.filter(
            Chapter.story_id == story.id,
            Chapter.is_published.is_(True),
            Chapter.chapter_number < chapter.chapter_number,
        )
        .order_by(Chapter.chapter_number.desc())
        .first()
    )
    next_chapter = (
        Chapter.query.filter(
            Chapter.story_id == story.id,
            Chapter.is_published.is_(True),
            Chapter.chapter_number > chapter.chapter_number,
        )
        .order_by(Chapter.chapter_number.asc())
        .first()
    )
    total_chapters = Chapter.query.filter_by(
        story_id=story.id, is_published=True
    ).count()

    # Side effect: record reading progress for this visitor (anon or logged in)
    record_progress(story.id, chapter.id)

    response = make_response(render_template(
        "chapter.html",
        story=story,
        chapter=chapter,
        prev_chapter=prev_chapter,
        next_chapter=next_chapter,
        total_chapters=total_chapters,
    ))
    response.headers["Cache-Control"] = "public, max-age=600"
    return response


@reader_bp.route("/story/<story_slug>/<chapter_slug>")
def chapter_standalone(story_slug, chapter_slug):
    story = Story.query.filter_by(
        slug=story_slug, series_id=None, is_archived=False
    ).first_or_404()
    return _render_chapter(story, chapter_slug)


@reader_bp.route("/series/<series_slug>/<story_slug>/<chapter_slug>")
def chapter_series(series_slug, story_slug, chapter_slug):
    series = Series.query.filter_by(slug=series_slug, is_archived=False).first_or_404()
    story = Story.query.filter_by(
        slug=story_slug, series_id=series.id, is_archived=False
    ).first_or_404()
    return _render_chapter(story, chapter_slug)


@reader_bp.route("/browse")
@cache.cached(timeout=120, query_string=True)
def browse():
    q = request.args.get("q", "").strip()
    query = _published_stories_query()
    if q:
        query = query.filter(Story.title.ilike(f"%{q}%"))
    stories = query.order_by(Story.title).all()
    return render_template("browse.html", stories=stories, q=q)

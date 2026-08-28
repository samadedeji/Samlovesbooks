"""Measure representative page HTML plus the shared stylesheet."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import url_for

from app import create_app
from app.models import Chapter, Series, Story, db

BUDGET_BYTES = 51200


def main():
    app = create_app("config.DevConfig")
    with app.app_context():
        largest_chapter = Chapter.query.order_by(Chapter.word_count.desc()).first()
        first_series = Series.query.order_by(Series.id).first()
        standalone_story = Story.query.filter_by(series_id=None).order_by(Story.id).first()
        if not largest_chapter or not first_series or not standalone_story:
            print("Seeded series, standalone story, and chapter data are required.", file=sys.stderr)
            return 1

        with app.test_request_context():
            routes = ["/", "/browse"]
            routes.append(url_for("reader.series_page", series_slug=first_series.slug))
            routes.append(url_for("reader.story_page_standalone", story_slug=standalone_story.slug))
            routes.append(url_for("reader.chapter_series" if largest_chapter.story.series_id else "reader.chapter_standalone", **(
                {
                    "series_slug": largest_chapter.story.series.slug,
                    "story_slug": largest_chapter.story.slug,
                    "chapter_slug": largest_chapter.slug,
                }
                if largest_chapter.story.series_id
                else {
                    "story_slug": largest_chapter.story.slug,
                    "chapter_slug": largest_chapter.slug,
                }
            )))

        css_path = os.path.join(app.static_folder, "css", "style.css")
        css_bytes = os.path.getsize(css_path)
        results = []
        with app.test_client() as client:
            for route in routes:
                response = client.get(route)
                html_bytes = len(response.data)
                total_bytes = html_bytes + css_bytes
                results.append((route, html_bytes, css_bytes, total_bytes, total_bytes < BUDGET_BYTES))

    print(f"{'route':<55} {'html_bytes':>10} {'css_bytes':>10} {'total_bytes':>11} {'pass/fail':>9}")
    for route, html_bytes, css_bytes, total_bytes, passed in results:
        print(f"{route:<55} {html_bytes:>10} {css_bytes:>10} {total_bytes:>11} {'PASS' if passed else 'FAIL':>9}")
    return 0 if all(result[-1] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""One-off script to seed a local database with an admin user and a small
amount of sample content, so the app is browsable immediately.

Usage:
    python seed.py
"""

from app import create_app
from app.models import AdminUser, Chapter, Series, Story, db

app = create_app("config.DevConfig")

with app.app_context():
    db.create_all()

    if not AdminUser.query.filter_by(username="leo").first():
        admin = AdminUser(username="leo")
        admin.set_password("changeme")
        db.session.add(admin)

    if not Series.query.filter_by(slug="57-and-unbothered").first():
        series = Series(
            slug="57-and-unbothered",
            title="5'7 and Unbothered",
            description="Episodic personal narratives.",
            cover_text="Life, unfiltered, one entry at a time.",
        )
        db.session.add(series)
        db.session.flush()

        story = Story(
            series_id=series.id,
            slug="episode-one",
            title="Episode One",
            description="Where it all starts.",
            status="ongoing",
            genre="personal-narrative",
            order_index=1,
        )
        db.session.add(story)
        db.session.flush()

        chapter = Chapter(
            story_id=story.id,
            chapter_number=1,
            slug="chapter-1",
            title="The Beginning",
            content="This is the first chapter.\n\nIt has two paragraphs.",
            word_count=9,
            is_published=True,
        )
        db.session.add(chapter)

    if not Story.query.filter_by(slug="rebel").first():
        standalone = Story(
            series_id=None,
            slug="rebel",
            title="Rebel",
            description="A standalone story.",
            status="complete",
            genre="fiction",
            order_index=0,
        )
        db.session.add(standalone)
        db.session.flush()

        chapter = Chapter(
            story_id=standalone.id,
            chapter_number=1,
            slug="chapter-1",
            title="Chapter One",
            content="The standalone story begins here.",
            word_count=5,
            is_published=True,
        )
        db.session.add(chapter)

    db.session.commit()
    print("Seed complete. Admin login: leo / changeme")

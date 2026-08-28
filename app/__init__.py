import markdown as md
from flask import Flask, render_template, url_for
from flask_caching import Cache
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFError, CSRFProtect

from .models import db
from .utils import (
    current_user,
    finalize_reader_token_cookie,
    get_font_size,
    persist_font_size_cookie,
)

cache = Cache()
compress = Compress()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
migrate = Migrate()


def create_app(config_object="config.DevConfig"):
    app = Flask(__name__)
    app.config.from_object(config_object)
    if config_object == "config.ProdConfig":
        from config import _production_secret_key

        app.config["SECRET_KEY"] = _production_secret_key()

    db.init_app(app)
    cache.init_app(app)
    compress.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    # --- Blueprints ---
    from .routes.reader import reader_bp
    from .routes.account import account_bp
    from .routes.admin import admin_bp

    app.register_blueprint(reader_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)

    # --- Template globals / filters ---
    @app.context_processor
    def inject_globals():
        return {"font_size": get_font_size(), "logged_in_user": current_user()}

    @app.template_filter("markdown")
    def markdown_filter(text):
        if not text:
            return ""
        return md.markdown(text, extensions=["extra"])

    @app.template_global("story_url")
    def story_url(story):
        """A Story may or may not belong to a Series -- this centralizes
        which of the two URL shapes to build (see app-flow §1)."""
        if story.series_id:
            return url_for(
                "reader.story_page_series",
                series_slug=story.series.slug,
                story_slug=story.slug,
            )
        return url_for("reader.story_page_standalone", story_slug=story.slug)

    @app.template_global("chapter_url")
    def chapter_url(story, chapter):
        if story.series_id:
            return url_for(
                "reader.chapter_series",
                series_slug=story.series.slug,
                story_slug=story.slug,
                chapter_slug=chapter.slug,
            )
        return url_for(
            "reader.chapter_standalone", story_slug=story.slug, chapter_slug=chapter.slug
        )

    @app.after_request
    def apply_reader_cookies(response):
        response = persist_font_size_cookie(response)
        response = finalize_reader_token_cookie(response)
        return response

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("404.html"), 404

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template(
            "404.html",
            page_title="Form validation failed",
            message="Your session expired or the form was tampered with — please try again,",
        ), 400

    return app

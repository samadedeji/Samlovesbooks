"""Import placeholder manuscript YAML/Markdown content into Samlovesbooks.

This assumes the source format described in PHASE_3_PROMPT.md Task 4. If
Leo's actual manuscript files are in a different format (.docx, plain .txt
with no front matter, a different folder structure, etc.), the parsing
functions in this script - not its idempotency/CLI/DB-writing logic - are
what need to change.
"""

import argparse
import ast
import re
from pathlib import Path

from flask import url_for

from app import create_app
from app.models import Chapter, Series, Story, db


def parse_yaml(path):
    data = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"line {line_number} is not a key/value pair")
        key, value = line.split(":", 1)
        value = value.strip()
        if not key.strip() or not value:
            raise ValueError(f"line {line_number} has an empty key or value")
        try:
            parsed_value = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            parsed_value = value
        data[key.strip()] = parsed_value
    return data


def parse_series_yaml(path):
    return parse_yaml(path)


def parse_story_yaml(path):
    return parse_yaml(path)


def parse_chapter_md(path):
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    title = ""
    if lines and re.match(r"^#\s+", lines[0]):
        title = re.sub(r"^#\s+", "", lines.pop(0)).strip()
        while lines and not lines[0].strip():
            lines.pop(0)
    body = "\n".join(lines)
    match = re.match(r"^(\d+)-(.+)\.md$", path.name, re.IGNORECASE)
    if not match:
        raise ValueError("filename must be <number>-<slug>.md")
    return int(match.group(1)), match.group(2), title, body


def import_content(root, dry_run=False):
    summary = {key: 0 for key in (
        "series_created", "series_updated", "stories_created", "stories_updated",
        "chapters_created", "chapters_updated",
    )}
    failures = []
    actions = []

    def report(action):
        actions.append(action)
        print(action)

    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        series_path = directory / "series.yaml"
        if series_path.exists():
            try:
                series_data = parse_series_yaml(series_path)
                series = Series.query.filter_by(slug=directory.name).first()
                created = series is None
                if created:
                    series = Series(slug=directory.name)
                    db.session.add(series)
                series.title = series_data.get("title", directory.name)
                series.description = series_data.get("description", "")
                series.cover_text = series_data.get("cover_text", "")
                summary["series_created" if created else "series_updated"] += 1
                report(("create" if created else "update") + " series " + directory.name)
                story_root = directory
            except Exception as exc:
                failures.append((str(series_path), str(exc)))
                continue
        else:
            series = None
            story_root = root

        story_directories = sorted(
            path for path in (directory.iterdir() if series else [directory])
            if path.is_dir() and (path / "story.yaml").exists()
        )
        if not series:
            story_directories = [directory] if (directory / "story.yaml").exists() else []

        for story_directory in story_directories:
            story_path = story_directory / "story.yaml"
            try:
                story_data = parse_story_yaml(story_path)
                story = Story.query.filter_by(slug=story_directory.name).first()
                created = story is None
                if created:
                    story = Story(slug=story_directory.name)
                    db.session.add(story)
                story.series = series
                story.title = story_data.get("title", story_directory.name)
                story.description = story_data.get("description", "")
                story.status = story_data.get("status", "ongoing")
                story.genre = story_data.get("genre", "")
                story.order_index = int(story_data.get("order_index", 0))
                summary["stories_created" if created else "stories_updated"] += 1
                report(("create" if created else "update") + " story " + story_directory.name)
            except Exception as exc:
                failures.append((str(story_path), str(exc)))
                continue

            for chapter_path in sorted(story_directory.glob("*.md")):
                try:
                    number, slug, title, content = parse_chapter_md(chapter_path)
                    chapter = Chapter.query.filter_by(
                        story=story, chapter_number=number
                    ).first()
                    created = chapter is None
                    if created:
                        chapter = Chapter(story=story, chapter_number=number)
                        db.session.add(chapter)
                    chapter.slug = slug
                    chapter.title = title
                    chapter.content = content
                    chapter.word_count = len(content.split())
                    if created:
                        chapter.is_published = False
                    summary["chapters_created" if created else "chapters_updated"] += 1
                    report(("create" if created else "update") + " chapter " + str(chapter_path))
                except Exception as exc:
                    failures.append((str(chapter_path), str(exc)))

    if not dry_run:
        db.session.commit()
    else:
        db.session.rollback()

    print("\nSummary")
    for key, value in summary.items():
        print(f"{key}: {value}")
    if failures:
        print("\nCould not parse:")
        for filename, reason in failures:
            print(f"- {filename}: {reason}")
    return failures


def main():
    parser = argparse.ArgumentParser(description="Import manuscript content")
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.path.is_dir():
        parser.error(f"not a directory: {args.path}")
    app = create_app()
    with app.app_context():
        with app.test_request_context():
            failures = import_content(args.path, args.dry_run)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the formal project-report PDF from its canonical Markdown source."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPOSITORY_ROOT / "docs" / "PROJECT_DOCUMENTATION.md"
DEFAULT_OUTPUT = REPOSITORY_ROOT / "output" / "pdf" / "PROJECT_DOCUMENTATION.pdf"
HTML_TEMPLATE = REPOSITORY_ROOT / "docs" / "pdf" / "project-report.html"
PRINT_STYLESHEET = REPOSITORY_ROOT / "docs" / "pdf" / "project-report.css"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build an A4 project report with a formal cover, contents, bookmarks, and page numbers."
    )
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE, help="Markdown report source")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT, help="Destination PDF path")
    return parser.parse_args()


def require_pandoc() -> str:
    """Return the Pandoc executable path or stop with installation guidance."""
    executable = shutil.which("pandoc")
    if executable:
        return executable
    raise SystemExit(
        "Pandoc is required. Install it with your operating-system package manager "
        "(for example, `brew install pandoc` on macOS)."
    )


def render_html(pandoc: str, source: Path, destination: Path) -> None:
    """Convert Markdown into a self-contained, print-styled HTML document."""
    resource_path = os.pathsep.join((str(REPOSITORY_ROOT), str(source.parent)))
    command = [
        pandoc,
        str(source),
        "--from=gfm+raw_html+yaml_metadata_block",
        "--to=html5",
        "--standalone",
        "--section-divs",
        "--toc",
        "--toc-depth=3",
        "--embed-resources",
        f"--resource-path={resource_path}",
        f"--template={HTML_TEMPLATE}",
        f"--css={PRINT_STYLESHEET}",
        f"--output={destination}",
    ]
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def normalize_heading(value: str) -> str:
    """Normalize heading text for matching HTML contents links to PDF bookmarks."""
    return re.sub(r"\s+", "", value).casefold()


def outline_page_map(pdf_path: Path) -> dict[str, int]:
    """Return normalized PDF bookmark titles mapped to one-based page numbers."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "pypdf is required for table-of-contents page references. Install the development "
            "dependencies with `pip install -r requirements-dev.txt`."
        ) from exc

    reader = PdfReader(pdf_path)
    result: dict[str, int] = {}

    def visit(items: list[object]) -> None:
        for item in items:
            if isinstance(item, list):
                visit(item)
                continue
            title = getattr(item, "title", None)
            if not title:
                continue
            page_number = reader.get_destination_page_number(item) + 1
            result[normalize_heading(str(title))] = page_number

    visit(reader.outline)
    return result


def add_toc_page_references(base_html: str, pages: dict[str, int]) -> str:
    """Add dotted leaders and resolved page references to the generated contents links."""
    nav_match = re.search(r'(<nav id="TOC".*?</nav>)', base_html, flags=re.DOTALL)
    if not nav_match:
        raise RuntimeError("Pandoc did not generate the expected table of contents.")

    missing: list[str] = []

    def replace_link(match: re.Match[str]) -> str:
        attributes, label_markup = match.groups()
        label_text = html.unescape(re.sub(r"<[^>]+>", "", label_markup))
        page_number = pages.get(normalize_heading(label_text))
        if page_number is None:
            missing.append(label_text)
            page_reference = "?"
        else:
            page_reference = str(page_number)
        return (
            f"<a{attributes}><span class=\"toc-label\">{label_markup}</span>"
            f"<span class=\"toc-dots\" aria-hidden=\"true\"></span>"
            f"<span class=\"toc-page\">{page_reference}</span></a>"
        )

    numbered_nav = re.sub(r"<a([^>]*)>(.*?)</a>", replace_link, nav_match.group(1), flags=re.DOTALL)
    if missing:
        raise RuntimeError(f"Could not resolve PDF pages for contents entries: {', '.join(missing)}")
    return f"{base_html[:nav_match.start()]}{numbered_nav}{base_html[nav_match.end():]}"


def render_pdf(source_html: Path, destination: Path) -> None:
    """Print the generated HTML to PDF with accessible structure and numbered pages."""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required. Install the development dependencies with "
            "`pip install -r requirements-dev.txt`."
        ) from exc

    footer = """
    <div style="width:100%; padding:0 22mm; color:#53616d; font-family:Arial,sans-serif;
                font-size:8.5px; text-align:center;">
      Page <span class="pageNumber"></span> of <span class="totalPages"></span>
    </div>
    """

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(source_html.as_uri(), wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(
                path=str(destination),
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="<span></span>",
                footer_template=footer,
                prefer_css_page_size=True,
                tagged=True,
                outline=True,
            )
            browser.close()
    except PlaywrightError as exc:
        raise SystemExit(
            "Chromium could not be launched. Install the Playwright browser with "
            "`playwright install chromium` and run the command again."
        ) from exc


def main() -> int:
    """Build the PDF and report its final location."""
    args = parse_args()
    source = args.source.resolve()
    output = args.output.resolve()

    if not source.is_file():
        raise SystemExit(f"Markdown source not found: {source}")
    if not HTML_TEMPLATE.is_file() or not PRINT_STYLESHEET.is_file():
        raise SystemExit("The PDF HTML template or stylesheet is missing from docs/pdf/.")

    output.parent.mkdir(parents=True, exist_ok=True)
    scratch_root = REPOSITORY_ROOT / "tmp" / "pdfs"
    scratch_root.mkdir(parents=True, exist_ok=True)

    pandoc = require_pandoc()
    with tempfile.TemporaryDirectory(prefix="project-report-", dir=scratch_root) as temporary_directory:
        temporary_path = Path(temporary_directory)
        base_html_path = temporary_path / "PROJECT_DOCUMENTATION.html"
        numbered_html_path = temporary_path / "PROJECT_DOCUMENTATION_NUMBERED.html"
        draft_pdf_path = temporary_path / "PROJECT_DOCUMENTATION_DRAFT.pdf"

        render_html(pandoc, source, base_html_path)
        base_html = base_html_path.read_text(encoding="utf-8")
        render_pdf(base_html_path, draft_pdf_path)

        # Rendering can move content when page references are inserted. Repeat until
        # the generated contents page agrees with the final PDF bookmark destinations.
        previous_pages: dict[str, int] | None = None
        for _ in range(3):
            pages = outline_page_map(draft_pdf_path)
            numbered_html = add_toc_page_references(base_html, pages)
            numbered_html_path.write_text(numbered_html, encoding="utf-8")
            render_pdf(numbered_html_path, output)
            final_pages = outline_page_map(output)
            if final_pages == pages:
                break
            previous_pages = pages
            draft_pdf_path = output
        else:
            changed = sum(1 for heading, page in final_pages.items() if previous_pages and previous_pages.get(heading) != page)
            raise RuntimeError(f"Table-of-contents page references did not stabilize ({changed} entries moved).")

    print(f"Created {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

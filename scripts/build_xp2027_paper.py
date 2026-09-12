#!/usr/bin/env python3
"""Build the deterministic eight-page XP 2027 preparation draft.

The manuscript Markdown is the canonical source for all prose and references.
Aggregate metrics supply the results visualization and validation guards.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "submission/xp2027/manuscript/PAPER.md"
BIBLIOGRAPHY = ROOT / "submission/xp2027/manuscript/references.bib"
METRICS = ROOT / "submission/xp2027/evidence/metrics.json"
OUTPUT = ROOT / "output/pdf/XP2027_temporal_agile_practice_recommendation_draft.pdf"

WIDTH, HEIGHT = A4
LEFT = 23 * mm
RIGHT = 23 * mm
TOP = 18 * mm
BOTTOM = 17 * mm
BODY_WIDTH = WIDTH - LEFT - RIGHT
INK = colors.HexColor("#17233B")
BLUE = colors.HexColor("#2455A4")
TEAL = colors.HexColor("#16827A")
MUTED = colors.HexColor("#5B6678")
GRID = colors.HexColor("#D9E0EA")


def load_metrics() -> dict[str, Any]:
    """Load aggregate evidence used for the results visualization and guards."""
    return json.loads(METRICS.read_text(encoding="utf-8"))


def load_manuscript() -> str:
    """Load and minimally validate the canonical manuscript."""
    manuscript = MANUSCRIPT.read_text(encoding="utf-8").strip()
    required_headings = [
        "## Abstract",
        "## 1 Introduction",
        "## 2 Background and Related Work",
        "## 3 Study Design",
        "## 4 Recommendation and Policy Selection",
        "## 5 Evaluation",
        "## 6 Results",
        "## 7 Discussion and Threats to Validity",
        "## 8 Conclusion",
        "## References",
    ]
    missing = [heading for heading in required_headings if heading not in manuscript]
    if missing:
        raise RuntimeError(f"Canonical manuscript is missing headings: {missing}")
    return manuscript


def validate_bibliography(manuscript: str) -> None:
    """Fail if the rendered reference list and BibTeX database drift apart."""
    bibliography = BIBLIOGRAPHY.read_text(encoding="utf-8")
    bib_entries = re.findall(r"^@\w+\{", bibliography, flags=re.MULTILINE)
    references = manuscript.split("## References", maxsplit=1)[1]
    rendered_entries = re.findall(r"^\d+\. ", references, flags=re.MULTILINE)
    if len(bib_entries) != len(rendered_entries):
        raise RuntimeError(
            "Bibliography drift: "
            f"{len(bib_entries)} BibTeX entries but {len(rendered_entries)} rendered references"
        )

    bib_dois = {value.lower() for value in re.findall(r"doi\s*=\s*\{([^}]+)\}", bibliography, re.I)}
    paper_dois = {value.lower().rstrip(".,") for value in re.findall(r"doi:([^\s]+)", references, re.I)}
    if bib_dois != paper_dois:
        raise RuntimeError(
            "Bibliography DOI drift: "
            f"missing from paper={sorted(bib_dois - paper_dois)}, "
            f"missing from BibTeX={sorted(paper_dois - bib_dois)}"
        )

    bib_urls = set(re.findall(r"url\s*=\s*\{([^}]+)\}", bibliography, re.I))
    paper_urls = set(re.findall(r"https?://[^\s]+", references))
    if not bib_urls.issubset(paper_urls):
        raise RuntimeError("Bibliography URL drift between references.bib and PAPER.md")


def _inline_markup(text: str) -> str:
    """Convert the small Markdown inline subset used by the manuscript."""
    marked = escape(text)
    marked = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", marked)
    marked = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', marked)
    marked = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", marked)
    return marked


def _styles() -> dict[str, ParagraphStyle]:
    """Return the compact publication styles used by the preparation draft."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "XPTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            alignment=TA_CENTER,
            textColor=INK,
            spaceAfter=5,
        ),
        "subtitle": ParagraphStyle(
            "XPSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=BLUE,
            spaceAfter=6,
        ),
        "author": ParagraphStyle(
            "XPAuthor",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=11,
            alignment=TA_CENTER,
            textColor=INK,
        ),
        "affiliation": ParagraphStyle(
            "XPAffiliation",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.7,
            leading=10,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=7,
        ),
        "h1": ParagraphStyle(
            "XPH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12.2,
            leading=14,
            textColor=INK,
            spaceBefore=3,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "XPH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=9.8,
            leading=11.5,
            textColor=BLUE,
            spaceBefore=3,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "XPBody",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.9,
            leading=9.55,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=4.2,
        ),
        "abstract": ParagraphStyle(
            "XPAbstract",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.55,
            leading=9.2,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=4,
        ),
        "reference": ParagraphStyle(
            "XPReference",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=5.25,
            leading=6.05,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=1.1,
        ),
        "bullet": ParagraphStyle(
            "XPBullet",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.8,
            leading=9.4,
            alignment=TA_JUSTIFY,
            textColor=INK,
            leftIndent=13,
            firstLineIndent=0,
            bulletIndent=1,
            spaceAfter=2,
        ),
        "caption": ParagraphStyle(
            "XPCaption",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=6.7,
            leading=8,
            textColor=INK,
            spaceAfter=5,
        ),
    }


class ResultsChart(Flowable):
    """Compact aggregate HR@2 comparison generated directly from metrics."""

    def __init__(self, metrics: dict[str, Any]) -> None:
        super().__init__()
        methods = metrics["primary"]["methods"]
        self.rows = [
            ("Selected blend", methods["selected_blend"]["monthly_macro_hit_rate_at_2"], BLUE),
            ("Time-aware popularity", methods["time_aware_popularity"]["monthly_macro_hit_rate_at_2"], TEAL),
            ("Transitions + popularity", methods["transition_popularity"]["monthly_macro_hit_rate_at_2"], MUTED),
            ("Equal blend", methods["equal_three_factor"]["monthly_macro_hit_rate_at_2"], MUTED),
            ("Historical popularity", methods["historical_popularity"]["monthly_macro_hit_rate_at_2"], MUTED),
            ("Random expectation", methods["random_expected"]["monthly_macro_hit_rate_at_2"], MUTED),
        ]
        self.width = BODY_WIDTH
        self.height = 40 * mm

    def draw(self) -> None:
        """Draw the chart into the current ReportLab canvas."""
        drawing = Drawing(self.width, self.height)
        label_width = 113
        right_pad = 42
        chart_width = self.width - label_width - right_pad
        top = self.height - 14
        maximum = 0.65
        for tick in (0.0, 0.2, 0.4, 0.6):
            x = label_width + chart_width * tick / maximum
            drawing.add(Line(x, 7, x, top + 2, strokeColor=GRID, strokeWidth=0.7))
            drawing.add(
                String(
                    x,
                    top + 5,
                    f"{tick:.0%}",
                    fontName="Helvetica",
                    fontSize=6,
                    textAnchor="middle",
                    fillColor=MUTED,
                )
            )
        for index, (label, value, color) in enumerate(self.rows):
            y = top - 12 - index * 15
            drawing.add(
                String(
                    label_width - 7,
                    y + 1,
                    label,
                    fontName="Helvetica",
                    fontSize=6.7,
                    textAnchor="end",
                    fillColor=INK,
                )
            )
            drawing.add(
                Rect(
                    label_width,
                    y,
                    chart_width * value / maximum,
                    7,
                    rx=2,
                    ry=2,
                    fillColor=color,
                    strokeColor=None,
                )
            )
            drawing.add(
                String(
                    label_width + chart_width * value / maximum + 3,
                    y + 1,
                    f"{value:.1%}",
                    fontName="Helvetica-Bold",
                    fontSize=6.4,
                    fillColor=INK,
                )
            )
        drawing.drawOn(self.canv, 0, 0)


def _page(canvas: Any, _document: BaseDocTemplate) -> None:
    """Draw deterministic metadata, running header, footer, and page number."""
    canvas.saveState()
    page_number = canvas.getPageNumber()
    if page_number > 1:
        canvas.setStrokeColor(colors.HexColor("#CFD7E5"))
        canvas.line(LEFT, HEIGHT - TOP + 1, WIDTH - RIGHT, HEIGHT - TOP + 1)
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT, HEIGHT - TOP + 5, "XP 2027 PREPARATION DRAFT")
        canvas.drawRightString(WIDTH - RIGHT, HEIGHT - TOP + 5, "AGILE PRACTICE SEQUENCING")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(LEFT, 11 * mm, "Official XP 2027 venue format pending publication")
    canvas.drawRightString(WIDTH - RIGHT, 11 * mm, str(page_number))
    canvas.restoreState()


def _front_matter(lines: list[str]) -> tuple[list[Flowable], int]:
    """Build title, subtitle, author, and affiliation flowables."""
    styles = _styles()
    nonblank = [(index, line.strip()) for index, line in enumerate(lines) if line.strip()]
    if len(nonblank) < 5 or not nonblank[0][1].startswith("# ") or not nonblank[1][1].startswith("## "):
        raise RuntimeError("Unexpected manuscript front matter")
    _, title = nonblank[0]
    _, subtitle = nonblank[1]
    _, author = nonblank[2]
    affiliation_index, affiliation = nonblank[3]
    abstract_index, abstract = nonblank[4]
    if abstract != "## Abstract":
        raise RuntimeError("Expected Abstract immediately after manuscript affiliation")
    flowables: list[Flowable] = [
        Paragraph(_inline_markup(title[2:]), styles["title"]),
        Paragraph(_inline_markup(subtitle[3:]), styles["subtitle"]),
        Paragraph(_inline_markup(author.rstrip()), styles["author"]),
        Paragraph(_inline_markup(affiliation), styles["affiliation"]),
    ]
    if abstract_index <= affiliation_index:
        raise RuntimeError("Invalid manuscript front-matter order")
    return flowables, abstract_index


def manuscript_story(manuscript: str, metrics: dict[str, Any]) -> list[Flowable]:
    """Convert the canonical Markdown subset into the publication story."""
    styles = _styles()
    lines = manuscript.splitlines()
    story, index = _front_matter(lines)
    paragraph_lines: list[str] = []
    bullet_lines: list[str] = []
    in_abstract = False
    in_references = False

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        text = " ".join(part.strip() for part in paragraph_lines)
        paragraph_lines.clear()
        if text == "The study asks:":
            story.append(PageBreak())
        style = styles["reference"] if in_references else styles["abstract"] if in_abstract else styles["body"]
        story.append(Paragraph(_inline_markup(text), style))

    def flush_bullets() -> None:
        if not bullet_lines:
            return
        items = [Paragraph(_inline_markup(line), styles["bullet"], bulletText="•") for line in bullet_lines]
        bullet_lines.clear()
        story.extend(items)
        story.append(Spacer(1, 2))

    while index < len(lines):
        stripped = lines[index].strip()
        index += 1
        if not stripped:
            flush_paragraph()
            flush_bullets()
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            flush_bullets()
            heading = stripped[3:]
            if re.match(r"[3-8] ", heading):
                story.append(PageBreak())
            in_abstract = heading == "Abstract"
            in_references = heading == "References"
            secondary = in_abstract or heading in {
                "Data Availability and Disclosures",
                "Acknowledgments",
                "References",
            }
            story.append(Paragraph(_inline_markup(heading), styles["h2"] if secondary else styles["h1"]))
            if heading == "6 Results":
                chart = ResultsChart(metrics)
                caption = Paragraph(
                    "<b>Fig. 1.</b> Primary monthly macro Conditional Hit Rate@2. "
                    "Popularity is a substantive comparator.",
                    styles["caption"],
                )
                story.append(KeepTogether([chart, caption]))
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(_inline_markup(stripped[4:]), styles["h2"]))
            continue
        if stripped.startswith("- "):
            flush_paragraph()
            bullet_lines.append(stripped[2:])
            continue
        if in_references and re.match(r"\d+\. ", stripped):
            flush_paragraph()
            story.append(Paragraph(_inline_markup(stripped), styles["reference"]))
            continue
        flush_bullets()
        paragraph_lines.append(stripped)

    flush_paragraph()
    flush_bullets()
    return story


def build_paper(metrics: dict[str, Any], output: Path = OUTPUT) -> Path:
    """Build and validate the draft from canonical Markdown and aggregate metrics."""
    manuscript = load_manuscript()
    validate_bibliography(manuscript)
    output.parent.mkdir(parents=True, exist_ok=True)
    document = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=LEFT,
        rightMargin=RIGHT,
        topMargin=TOP + 3,
        bottomMargin=BOTTOM,
        title="Do Complex Recommenders Beat Popularity for Agile Practice Sequencing?",
        author="Erez Morabia",
        subject="XP 2027 preparation draft",
        creator="XP 2027 manuscript builder",
        invariant=True,
        pageCompression=True,
    )
    frame = Frame(LEFT, BOTTOM, BODY_WIDTH, HEIGHT - TOP - BOTTOM - 3, id="body", showBoundary=0)
    document.addPageTemplates(PageTemplate(id="xp", frames=[frame], onPage=_page))
    document.build(manuscript_story(manuscript, metrics))

    reader = PdfReader(str(output))
    if len(reader.pages) != 8:
        raise RuntimeError(f"Expected exactly 8 pages, got {len(reader.pages)}")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = " ".join(text.split())
    required = [
        "Do Complex Recommenders Beat Popularity",
        "58.0%",
        "55.7%",
        "57.3%",
        "40.3%",
        "conditional on the monthly policies",
        "Data Availability and Disclosures",
        "This research received no external funding",
        "unpublished MSc project report",
    ]
    missing = [value for value in required if value not in normalized_text]
    if missing:
        raise RuntimeError(f"Built paper is missing required statements: {missing}")
    return output


def main() -> int:
    """Build and validate the paper."""
    path = build_paper(load_metrics())
    print(f"Wrote eight-page XP 2027 preparation draft to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

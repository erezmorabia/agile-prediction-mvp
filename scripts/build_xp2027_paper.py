#!/usr/bin/env python3
"""Build the deterministic XP 2027 short-paper preparation draft.

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
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
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
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "submission/xp2027/manuscript/PAPER.md"
BIBLIOGRAPHY = ROOT / "submission/xp2027/manuscript/references.bib"
METRICS = ROOT / "submission/xp2027/evidence/metrics.json"
OUTPUT = ROOT / "output/pdf/XP2027_temporal_agile_practice_recommendation_draft.pdf"

WIDTH, HEIGHT = A4
LEFT = 31 * mm
RIGHT = 31 * mm
TOP = 19 * mm
BOTTOM = 18 * mm
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
    body, references = manuscript.split("## References", maxsplit=1)
    reference_numbers = [
        int(value) for value in re.findall(r"^(\d+)\. ", references, flags=re.MULTILINE)
    ]
    rendered_entries = len(reference_numbers)
    if len(bib_entries) != rendered_entries:
        raise RuntimeError(
            "Bibliography drift: "
            f"{len(bib_entries)} BibTeX entries but {rendered_entries} rendered references"
        )

    expected_numbers = list(range(1, rendered_entries + 1))
    if reference_numbers != expected_numbers:
        raise RuntimeError("Rendered references must be numbered sequentially from 1")

    first_citation_order: list[int] = []
    for citation_group in re.findall(r"\[([0-9]+(?:\s*,\s*[0-9]+)*)\]", body):
        for value in citation_group.split(","):
            citation = int(value.strip())
            if citation not in first_citation_order:
                first_citation_order.append(citation)
    if first_citation_order != reference_numbers:
        raise RuntimeError(
            "References must follow first-citation order: "
            f"citations={first_citation_order}, references={reference_numbers}"
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
            fontSize=9.1,
            leading=11.0,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=5.0,
        ),
        "abstract": ParagraphStyle(
            "XPAbstract",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=8.5,
            leading=10.3,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=4,
        ),
        "reference": ParagraphStyle(
            "XPReference",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=7.0,
            leading=8.2,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=1.5,
        ),
        "bullet": ParagraphStyle(
            "XPBullet",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=9.0,
            leading=10.8,
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
            fontSize=7.2,
            leading=8.6,
            textColor=INK,
            spaceAfter=5,
        ),
        "table_header": ParagraphStyle(
            "XPTableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=5.5,
            leading=6.4,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "XPTableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=5.7,
            leading=6.7,
            alignment=TA_CENTER,
            textColor=INK,
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


class TemporalProtocolDiagram(Flowable):
    """Compact visual summary of the leakage-conscious prediction boundary."""

    def __init__(self) -> None:
        super().__init__()
        self.width = BODY_WIDTH
        self.height = 25 * mm

    def draw(self) -> None:
        """Draw the train-predict-observe-release sequence."""
        drawing = Drawing(self.width, self.height)
        labels = [
            ("Closed prior outcomes", "fit and tune"),
            ("Target baseline", "construct + rank"),
            ("Next 3 snapshots", "observe outcomes"),
            ("Window closed", "release for later tuning"),
        ]
        gap = 12
        box_width = (self.width - gap * 3) / 4
        box_height = 31
        y = 22
        for index, (title, subtitle) in enumerate(labels):
            x = index * (box_width + gap)
            fill = colors.HexColor("#EEF3FA") if index != 1 else colors.HexColor("#E4F3F1")
            stroke = BLUE if index != 1 else TEAL
            drawing.add(
                Rect(
                    x,
                    y,
                    box_width,
                    box_height,
                    rx=4,
                    ry=4,
                    fillColor=fill,
                    strokeColor=stroke,
                    strokeWidth=0.8,
                )
            )
            drawing.add(
                String(
                    x + box_width / 2,
                    y + 18,
                    title,
                    fontName="Helvetica-Bold",
                    fontSize=6.4,
                    textAnchor="middle",
                    fillColor=INK,
                )
            )
            drawing.add(
                String(
                    x + box_width / 2,
                    y + 8,
                    subtitle,
                    fontName="Helvetica",
                    fontSize=5.8,
                    textAnchor="middle",
                    fillColor=MUTED,
                )
            )
            if index < len(labels) - 1:
                arrow_start = x + box_width + 2
                arrow_end = x + box_width + gap - 2
                arrow_y = y + box_height / 2
                drawing.add(Line(arrow_start, arrow_y, arrow_end, arrow_y, strokeColor=MUTED, strokeWidth=0.8))
                drawing.add(
                    Polygon(
                        [arrow_end, arrow_y, arrow_end - 4, arrow_y + 2.5, arrow_end - 4, arrow_y - 2.5],
                        fillColor=MUTED,
                        strokeColor=None,
                    )
                )
        drawing.add(
            String(
                self.width / 2,
                8,
                "No outcome or policy choice crosses left of its availability time",
                fontName="Helvetica-Oblique",
                fontSize=6.2,
                textAnchor="middle",
                fillColor=MUTED,
            )
        )
        drawing.drawOn(self.canv, 0, 0)


def monthly_results_table(metrics: dict[str, Any]) -> Table:
    """Build the primary month-level comparison directly from aggregate evidence."""
    primary = metrics["primary"]["methods"]
    blend = primary["selected_blend"]["per_month_hit_rate_at_2"]
    popularity = primary["time_aware_popularity"]["per_month_hit_rate_at_2"]
    case_counts = {str(row["month"]): row["evaluable_cases"] for row in metrics["per_month"]}
    rows: list[list[str]] = [["Prediction month", "Cases", "Blend", "Popularity", "Difference"]]
    for month in metrics["primary"]["months"]:
        key = str(month)
        month_label = f"{key[:4]}-{key[4:6]}"
        difference = blend[key] - popularity[key]
        rows.append(
            [
                month_label,
                str(case_counts[key]),
                f"{blend[key]:.1%}",
                f"{popularity[key]:.1%}",
                f"{difference:+.1%}",
            ]
        )
    rows.append(["Monthly macro", "121", "58.0%", "55.7%", "+2.3 pp"])
    table = Table(rows, colWidths=[96, 52, 72, 76, 74], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EEF3FA")),
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    return table


def prior_work_table(styles: dict[str, ParagraphStyle]) -> Table:
    """Build the structured comparison of the closest screened studies."""
    raw_rows = [
        ["Study", "Guidance target", "Longitudinal teams", "Next observed practice", "Walk-forward + temporal baseline"],
        ["Packlick [12]", "Agile maturity-guided change", "NR", "NR", "NR"],
        ["Choi et al. [13]", "Process-improvement actions", "NR", "NR", "NR"],
        ["Raza et al. [14]", "Developer-improvement actions", "NR", "NR", "NR"],
        ["Song et al. [11]", "Software-process model", "NR", "No", "NR"],
        ["This study", "Team practice top two", "Yes", "Yes", "Yes"],
    ]
    rows = [
        [
            Paragraph(_inline_markup(value), styles["table_header"] if row_index == 0 else styles["table_cell"])
            for value in row
        ]
        for row_index, row in enumerate(raw_rows)
    ]
    table = Table(rows, colWidths=[73, 105, 72, 75, 94], hAlign="CENTER")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E4F3F1")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    return table


def _page(canvas: Any, _document: BaseDocTemplate) -> None:
    """Draw deterministic metadata, running header, footer, and page number."""
    canvas.saveState()
    page_number = canvas.getPageNumber()
    if page_number > 1:
        canvas.setStrokeColor(colors.HexColor("#CFD7E5"))
        canvas.line(LEFT, HEIGHT - TOP + 1, WIDTH - RIGHT, HEIGHT - TOP + 1)
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT, HEIGHT - TOP + 5, "XP 2027 RESEARCH SHORT-PAPER DRAFT")
        canvas.drawRightString(WIDTH - RIGHT, HEIGHT - TOP + 5, "AGILE PRACTICE GUIDANCE")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(LEFT, 11 * mm, "Provisional short-paper format - official XP 2027 call pending")
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
            in_abstract = heading == "Abstract"
            in_references = heading == "References"
            secondary = in_abstract or heading in {
                "Data Availability and Disclosures",
                "Acknowledgments",
                "References",
            }
            heading_flowable = Paragraph(
                _inline_markup(heading), styles["h2"] if secondary else styles["h1"]
            )
            if heading == "3 Study Design":
                diagram = TemporalProtocolDiagram()
                caption = Paragraph(
                    "<b>Fig. 1.</b> Prediction-time boundary. A prior month can tune a later policy only after its "
                    "outcome window closes.",
                    styles["caption"],
                )
                story.append(KeepTogether([heading_flowable, diagram, caption]))
                continue
            if heading == "6 Results":
                chart = ResultsChart(metrics)
                caption = Paragraph(
                    "<b>Fig. 2.</b> Primary monthly macro Conditional Hit Rate@2. "
                    "Popularity is a substantive comparator.",
                    styles["caption"],
                )
                table = monthly_results_table(metrics)
                table_caption = Paragraph(
                    "<b>Table 2.</b> Primary per-month Conditional Hit Rate@2. The first three rows are identical "
                    "because no earlier prediction window had closed.",
                    styles["caption"],
                )
                story.append(
                    KeepTogether([heading_flowable, chart, caption, table, table_caption])
                )
                continue
            story.append(heading_flowable)
            continue
        if stripped.startswith("### "):
            flush_paragraph()
            flush_bullets()
            heading = stripped[4:]
            heading_flowable = Paragraph(_inline_markup(heading), styles["h2"])
            if heading == "2.4 Structured gap check":
                table = prior_work_table(styles)
                caption = Paragraph(
                    "<b>Table 1.</b> Closest screened studies. NR = not reported in the screened title or abstract; "
                    "it does not prove absence from the full text.",
                    styles["caption"],
                )
                story.append(KeepTogether([heading_flowable, table, caption]))
                continue
            story.append(heading_flowable)
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
        title=(
            "Can Organizational History Inform What Agile Teams Improve Next? "
            "A Walk-Forward Study of 87 Teams"
        ),
        author="Erez Morabia",
        subject="XP 2027 provisional research short-paper draft",
        creator="XP 2027 manuscript builder",
        invariant=True,
        pageCompression=True,
    )
    frame = Frame(LEFT, BOTTOM, BODY_WIDTH, HEIGHT - TOP - BOTTOM - 3, id="body", showBoundary=0)
    document.addPageTemplates(PageTemplate(id="xp", frames=[frame], onPage=_page))
    document.build(manuscript_story(manuscript, metrics))

    reader = PdfReader(str(output))
    if not 5 <= len(reader.pages) <= 8:
        raise RuntimeError(f"Expected a five-to-eight-page short-paper draft, got {len(reader.pages)} pages")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    normalized_text = " ".join(text.split())
    required = [
        "Can Organizational History Inform What Agile Teams Improve Next?",
        "58.0%",
        "55.7%",
        "57.3%",
        "40.3%",
        "23.1%",
        "22.2%",
        "-4.4",
        "12.5",
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
    print(f"Wrote XP 2027 short-paper preparation draft to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

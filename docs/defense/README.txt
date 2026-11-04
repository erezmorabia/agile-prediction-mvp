PROJECT DEFENSE PRESENTATION

CURRENT EDITION: EXECUTIVE-SUMMARY-BASED DEFENSE PDF

output/pdf/agile-project-defense.pdf
  16:9 audience slides with embedded Arial fonts and PDF bookmarks.
  Pages 1-15 are the main talk. Pages 16-18 are backup slides A1-A3.
  Stop after slide 15 for questions. Use the PDF outline to open backups.

output/pdf/agile-project-defense-presenter-notes.pdf
  Speaking notes, timing suggestions, sources and rehearsal guidance.

Session: Zoom, Sunday, 10:00-11:00 (as supplied by the student).
Professor's guidance: make clear the problems in the current state of the art
and how the project improves on them. No additional requirements specified.
Agreed narrative:
  1-2  WHY: opening question and problem statement
  3-4  WHAT: proposed system and recommendation concept
  5-9  HOW: data representation, architecture, software request component history and recommendation explanations
  10-12 EVIDENCE: evaluation design, success metric, and results
  13-15 IMPLICATIONS: contribution and limits, pilot, and closing answer
The executive summary of PROJECT_DOCUMENTATION.pdf (pages 5-7) supplies the
main narrative: challenge, empirical organizational learning, three evidence
signals, monthly adaptation, validation, results and pilot readiness. Architecture
and the worked example supplement it from sections 3.7 and 4. Transition patterns
are associations, not readiness guarantees. Estimated savings are not measured
results and are not presented as such.

The Black Pearl software request appears before its later outcomes, which are
introduced only when defining evaluation success. Three backup slides retain
the monthly results (A1), policy search grid (A2), and monthly selection explanation (A3).
Plan 20-25 minutes for the talk within the one-hour meeting, plus discussion.
English remains a working choice. No calendar date is inferred in the deck.

REBUILD

From the repository root:
  .venv/bin/python docs/defense/build_pdf.py

Requires reportlab, pymupdf and Pillow, available in the project environment.
The builder embeds Arial and Arial Bold from macOS Supplemental fonts.
Rendered QA pages and validation details go into ignored tmp/pdfs/defense/.
The canonical source for technical claims is docs/PROJECT_DOCUMENTATION.md.
Speaking notes and source references are in content.json. The PDF builder
contains the redesigned slide copy, composition, note overrides and source order.

RELATED-WORK POSITIONING

Choi et al. (2022), ReMo, doi:10.1002/9781119821779.ch1
Raza et al. (2017), WebProcessPAIR, doi:10.1145/3084100.3084365

These are selected related systems with different improvement decision targets.
The presentation does not claim exhaustive novelty or measured superiority
over these systems. Its numerical comparison is against random selection and
independently selected time-aware organizational popularity.

DESIGN BASIS

Researched 3 November 2026. This is a custom design rather than an official
Open University template. White background, dark navy text, one teal accent,
34 pt headings and predominantly 24 pt body text. Supporting captions and
tables and architecture detail use smaller type. The design reduces prose,
uses explanatory diagrams and directly labelled charts, and keeps technical
detail in backups and speaking notes. Workflow arrows represent data flow or
decision steps; the example's match arrow represents overlap, not causation.

MIT AeroAstro Communication Lab, Slide Design:
https://mitcommlab.mit.edu/aeroastro/commkit/slide-design/

Harvard T.H. Chan School of Public Health, Slide Design Checklist:
https://hsph.harvard.edu/research/health-communication/resources/slide-checklist/

Texas A&M Digital Accessibility, Accessible Presentations:
https://accessibility.tamu.edu/how-to/presentations/index.html

EARLIER DRAFT

agile-project-defense.pptx and agile-project-defense.html are the earlier
editable draft, with a different layout. They do not reproduce the redesigned
PDF. Rebuild them separately with python3 docs/defense/build_deck.py.

The central result is conditional, retrospectively evaluated and exploratory.
It does not establish causal improvement or calibrated success probabilities.

"""Create the projection deck and presenter companion with embedded Arial fonts.

Run from the repository root: .venv/bin/python docs/defense/build_pdf.py
The PDF is the redesigned edition. The earlier PPTX remains a separate draft.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "output/pdf"
QA = ROOT / "tmp/pdfs/defense"
CONTENT = json.loads((HERE / "content.json").read_text())
W, H = 960, 540
NAVY, TEAL, GRAY, PALE, LINE = "172F43", "007C83", "4D5F6C", "E7F1F2", "D6DFE5"
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
for name, file in [("Arial", "Arial.ttf"), ("Arial-Bold", "Arial Bold.ttf")]:
    pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial", boldItalic="Arial-Bold")

RESEARCH = [
    ("MIT AeroAstro Communication Lab", "Slide Design", "https://mitcommlab.mit.edu/aeroastro/commkit/slide-design/"),
    ("Harvard T.H. Chan School of Public Health", "Checklist: Improve Your Slide Design", "https://hsph.harvard.edu/research/health-communication/resources/slide-checklist/"),
    ("Texas A&M Digital Accessibility", "Accessible Presentations", "https://accessibility.tamu.edu/how-to/presentations/index.html"),
]

RELATED_WORK = [
    ("Choi, Kim and Park (2022)", "ReMo: A Recommendation Development Model for Software Process Improvement Based on Correlation Analysis", "https://doi.org/10.1002/9781119821779.ch1"),
    ("Raza, Faria, Amaro and Henriques (2017)", "WebProcessPAIR: recommendation system for software process improvement", "https://doi.org/10.1145/3084100.3084365"),
]

# Reuse the original explanations after moving the explicit contribution earlier.
# Slots 3 and 4 receive new notes and sources in make_presenter().
SOURCE_ORDER = [0, 1, 7, 4, 3, -3, 5, 6, None, -1, 8, 9, 10, 11, 12, 13, 15, 16, -2, -4, -5, -6]


def clean(value):
    return str(value).replace("–", "-").replace("—", "-").replace("‑", "-")


class Deck:
    def __init__(self):
        self.c = Canvas(str(OUT / "agile-project-defense.pdf"), pagesize=(W, H), pageCompression=1)
        self.c.setTitle(CONTENT["title"])
        self.c.setAuthor(CONTENT["author"])
        self.c.setSubject("M.Sc. advanced-project defense. 16 main slides and 6 backup slides.")
        self.audit = []
        self.regions = []
        self.i = 0
        self.titles = []

    def text(self, value, x, y, width, size=24, color=NAVY, bold=False, max_h=None, leading=None):
        value = clean(value)
        style = ParagraphStyle("slide", fontName="Arial-Bold" if bold else "Arial", fontSize=size,
                               leading=leading or size*1.32, textColor=colors.HexColor('#'+color),
                               alignment=TA_LEFT, splitLongWords=False)
        p = Paragraph(value, style)
        _, height = p.wrap(width, H)
        if max_h is not None and height > max_h + 0.1:
            raise ValueError(f"Slide {self.i}: text height {height:.1f} > {max_h}: {value}")
        if y+height > H-12 or x+width > W+0.1:
            raise ValueError(f"Slide {self.i}: content outside page: {value}")
        p.drawOn(self.c, x, H-y-height)
        self.regions.append(dict(page=self.i, text=value, x=x, y=y, width=width, height=height, size=size))
        return height

    def rule(self, x, y, width, color=LINE, thickness=0.7):
        self.c.setStrokeColor(colors.HexColor('#'+color))
        self.c.setLineWidth(thickness)
        self.c.line(x,H-y,x+width,H-y)

    def rect(self, x, y, w, h, color):
        self.c.setFillColor(colors.HexColor('#'+color))
        self.c.rect(x,H-y-h,w,h,stroke=0,fill=1)

    def arrow(self, points, color=GRAY, thickness=1.5):
        """A directed connector for an explicitly requested explanatory diagram."""
        import math
        self.c.setStrokeColor(colors.HexColor('#'+color))
        self.c.setLineWidth(thickness)
        p=self.c.beginPath()
        p.moveTo(points[0][0], H-points[0][1])
        for x,y in points[1:]:
            p.lineTo(x,H-y)
        self.c.drawPath(p,stroke=1,fill=0)
        x,y=points[-1]
        px,py=points[-2]
        angle=math.atan2(y-py,x-px)
        head=self.c.beginPath()
        head.moveTo(x,H-y)
        for delta in (-.48,.48):
            xx=x-8*math.cos(angle+delta)
            yy=y-8*math.sin(angle+delta)
            head.lineTo(xx,H-yy)
        head.close()
        self.c.setFillColor(colors.HexColor('#'+color))
        self.c.drawPath(head,fill=1,stroke=0)

    def node(self, title, body, x, y, width, height, emphasis=False,
             title_size=23, body_size=18):
        """A labelled component in an architecture or workflow, never decoration."""
        fill=PALE if emphasis else 'FFFFFF'
        self.rect(x,y,width,height,fill)
        self.c.setStrokeColor(colors.HexColor('#'+(TEAL if emphasis else LINE)))
        self.c.setLineWidth(1)
        self.c.rect(x,H-y-height,width,height,fill=0,stroke=1)
        top=self.text(title,x+15,y+12,width-30,size=title_size,
                      color=TEAL if emphasis else NAVY,bold=True,
                      max_h=height-20,leading=title_size*1.18)
        if body:
            self.text(body,x+15,y+top+22,width-30,size=body_size,
                      color=GRAY,max_h=height-top-30,leading=body_size*1.28)

    def new(self, title, report, backup=False, source_label=None):
        self.i += 1
        self.titles.append(title)
        self.c.setFillColor(colors.white)
        self.c.rect(0,0,W,H,stroke=0,fill=1)
        self.c.bookmarkPage(f"slide-{self.i}")
        if self.i==17:
            self.c.addOutlineEntry("Backup slides", "slide-17", level=0, closed=False)
        self.c.addOutlineEntry(title or CONTENT['title'], f"slide-{self.i}", level=1 if backup else 0, closed=False)
        self.text(title,48,37,864,size=34,bold=True,max_h=86,leading=40)
        self.rule(48,493,864)
        self.text(source_label or f"Project report {report}",48,504,730,size=10,color=GRAY)
        folio = title.split(".", 1)[0] if backup else f"{self.i:02d} / 16"
        self.text(folio,854,502,60,size=12,color=GRAY,bold=True)

    def end(self):
        self.c.showPage()

    def caption(self, text, y=435, color=GRAY, size=19):
        self.text(text,48,y,864,size=size,color=color,max_h=52)

    def rows(self, rows, y=140, step=100, label_w=210, body_size=24):
        for i,(label,body) in enumerate(rows):
            yy=y+i*step
            self.text(label,48,yy,label_w,size=body_size,color=TEAL,bold=True,max_h=step-10)
            self.text(body,48+label_w+24,yy,864-label_w-24,size=body_size,max_h=step-10)

    def table(self, headers, rows, widths, y=145, row_h=66, size=22, highlight=()):
        total=sum(widths)
        self.rect(48,y,total,48,NAVY)
        x=48
        for head,width in zip(headers,widths):
            self.text(head,x+12,y+10,width-24,size=size,color="FFFFFF",bold=True,max_h=36,leading=size*1.15)
            x+=width
        for ri,row in enumerate(rows):
            yy=y+48+ri*row_h
            if ri in highlight:
                self.rect(48,yy,total,row_h,PALE)
            x=48
            padding = 7 if row_h < 50 else 13
            for col,width in zip(row,widths):
                self.text(str(col),x+12,yy+padding,width-24,size=size,max_h=row_h-2*padding,leading=size*1.2)
                x+=width
            self.rule(48,yy+row_h,total)

    def finish(self):
        self.c.save()
        (QA / "text-regions.json").write_text(json.dumps(self.regions,indent=2))


def make_slides():
    d=Deck()

    d.new("", "title page and §1")
    d.c.drawImage(str(ROOT/'web/static/ou-logo.png'),48,H-40-52,width=246,height=52,mask='auto')
    d.text("Identifying Likely Large-Scale<br/>Agile Implementation<br/>Pathways",48,144,860,size=43,bold=True,leading=50,max_h=159)
    d.text("Erez Morabia",48,347,864,size=25,bold=True)
    d.text("Supervisor: Prof. Shmuel Tyszberowicz",48,386,864,size=22,color=GRAY)
    d.text("M.Sc. Advanced Project in Computer Science · 22997",48,431,864,size=19,color=GRAY)
    d.titles[-1]=CONTENT['title']
    d.end()

    d.new("The challenge: choosing the next practice", "Executive summary, pp. 5-7; §1.1-1.3")
    d.text("Which practices should<br/>this team focus on next?",48,149,610,size=37,bold=True,leading=46)
    d.text("35",737,141,170,size=73,color=TEAL,bold=True,leading=80)
    d.text("practices",742,229,170,size=24,color=GRAY)
    d.rows([
        ("Different starting points", "The next practice should reflect the team's current maturity profile."),
        ("Relevant experience", "Other teams' improvement histories provide evidence about possible next steps."),
        ("Difficult comparison", "Manually comparing teams and histories becomes difficult at organizational scale."),
    ],y=270,step=62,label_w=254,body_size=19)
    d.caption("The challenge: turn organizational experience into two team-specific practices for coach review.",y=458,size=17)
    d.end()

    d.new("Learning organizational improvement behavior", "Executive summary, pp. 5-7; §3")
    d.text("Use observed team histories to identify likely next practices.",48,121,864,size=27,color=TEAL,bold=True)
    d.node("Input",'Team + month +<br/>Organizational history',48,223,271,148,title_size=26,body_size=22)
    d.node("Recommendation engine",'Learn from prior<br/>organizational history',359,223,248,148,emphasis=True,title_size=24,body_size=21)
    d.node("Output",'Two ranked eligible<br/>practices for coach review',647,223,265,148,title_size=26,body_size=22)
    d.arrow([(319,297),(359,297)],color=TEAL)
    d.arrow([(607,297),(647,297)],color=TEAL)
    d.text("Component-specific scoring windows; historical learning has no fixed lookback.",48,385,864,size=18,color=GRAY)
    d.text("The contribution: empirical organizational learning",48,418,864,size=26,color=TEAL,bold=True)
    d.caption("The ranking supports coach review. Scores express relative evidence.",y=468,size=14)
    d.end()

    d.new("Three signals form one ranking", "Executive summary, pp. 5-6; §3.3-3.5")
    for x,title,body in [
        (48,"Collaborative filtering","Match maturity profiles and learn from peer improvements"),
        (352,"Practice Transition Model","Observed practices following the team's recent improvements"),
        (656,"Time-aware popularity","Count improvements across teams:<br/>earlier history +<br/>latest interval")
    ]:
        d.node(title,body,x,120,256,194,title_size=24,body_size=20)
        d.arrow([(x+128,314),(x+128,339)],color=TEAL)
    d.node("Normalize components and blend their scores",'Weights come from completed earlier prediction-month outcomes.',
           48,339,864,85,emphasis=True,title_size=25,body_size=19)
    d.text("Rank eligible practices and return two recommendations",48,439,864,size=24,bold=True)
    d.caption("Popularity balance uses completed earlier outcomes. Eligibility excludes practices at maximum maturity.",y=474,size=12)
    d.end()

    d.new("Representing the organizational history", "§3.2 and §6.1")
    for x,num,label in [(48,"87","teams"),(270,"35","practices"),(492,"10","recorded months"),(714,"654","unique team-month<br/>snapshots")]:
        d.text(num,x,117,198,size=54,color=TEAL,bold=True,leading=62)
        d.text(label,x,184,198,size=20,color=GRAY,leading=25)
    d.text("One snapshot = one team's maturity scores on one date.",48,247,864,size=21)
    d.text("One prediction case uses the latest earlier assessment + up to 3 later snapshots.",48,282,864,size=20)
    d.text("Jan → Mar → Apr",48,338,258,size=23,bold=True)
    d.text("May → Jun → Jul → Aug → Sep",324,338,436,size=23,bold=True,color=TEAL)
    d.text("Oct → Nov",778,338,134,size=23,bold=True)
    d.text("Initial history",48,376,258,size=19,color=GRAY)
    d.text("Primary prediction months",324,376,436,size=19,color=GRAY)
    d.text("Follow-up",778,376,134,size=19,color=GRAY)
    d.text("Reserve the first 3 recorded snapshots for initial history.<br/>First evaluated prediction: May; latest earlier assessment (baseline): April.",48,431,864,size=20,leading=25)
    d.end()

    d.new("High-level software architecture", "§4.1-4.2")
    d.node("Web interface", "",250,105,460,54,title_size=25)
    d.arrow([(480,159),(480,204)],color=TEAL)
    d.text("HTTP / REST",498,171,250,size=17,color=GRAY)
    d.node("API layer", "",185,204,590,54,emphasis=True,title_size=25)
    d.arrow([(480,258),(480,282),(228,282),(228,300)],color=TEAL)
    d.arrow([(480,258),(480,282),(555.5,282),(555.5,300)],color=TEAL)
    d.arrow([(480,258),(480,282),(807.5,282),(807.5,300)],color=TEAL)
    d.node("ML engine", "Learn from similar teams<br/>Learn practice-transition patterns<br/>Count improvements across teams<br/>Blend signals; recommend two practices",48,300,360,153,title_size=24,body_size=18)
    d.node("Validation engine", "Backtest past predictions<br/>Compare with outcomes<br/>Calculate ranking metrics",433,300,245,153,title_size=23,body_size=18)
    d.node("Data module", "Load Excel · validate<br/>Normalize maturity<br/>Index team histories",703,300,209,153,title_size=24,body_size=18)
    d.arrow([(555.5,453),(555.5,479),(228,479),(228,453)],color=TEAL)
    d.text("Request historical recommendations",251,456,310,size=13,color=TEAL,bold=True,max_h=18)
    d.end()

    d.new("One shared engine serves the application", "§4.1-4.3, §5.4 and §6.5")
    d.node("Web interface / API", "",48,107,238,54,title_size=22)
    d.text("Both actions start in the web interface",330,119,582,size=23,color=TEAL)
    d.arrow([(167,161),(167,200)],color=TEAL)
    d.arrow([(167,180),(32,180),(32,395),(48,395)],color=TEAL)
    d.node("Recommend action", "Select team + month<br/>Request one case",48,200,238,110,title_size=22,body_size=18)
    d.node("Run backtest action", "Validation engine loops<br/>over team-month cases",48,340,238,110,title_size=21,body_size=18)
    d.node("Shared ML engine", "PolicyEngine<br/><b>For each prediction month:</b><br/>choose settings shared<br/>by all teams.<br/><br/><b>For each team:</b><br/>apply those settings and<br/>recommend two practices.",330,200,300,250,emphasis=True,title_size=24,body_size=18)
    d.node("Display results", "Two ranked practices",674,200,238,110,title_size=24,body_size=18)
    d.node("Evaluate results", "Compare improvements<br/>Display quality metrics",674,340,238,110,title_size=23,body_size=18)
    for y in [255,395]:
        d.arrow([(286,y),(330,y)],color=TEAL)
        d.arrow([(630,y),(674,y)],color=TEAL)
    d.caption("One case for Recommend; many historical cases for backtesting. Same ML engine.",y=472,size=16)
    d.end()

    d.new("One recommendation request, end to end", "§3.7 and §4.3")
    d.text("Example · Team: Black Pearl · Prediction month: August 2020",48,105,864,size=23,color=GRAY)
    d.text("Which two practices should this team prioritize next?",48,144,864,size=23,color=TEAL)
    d.node("Find current state",'Latest assessment:<br/>5 July 2020<br/><b>28 eligible practices</b><br/>below maturity level 3',48,188,268,166,title_size=24,body_size=20)
    d.node("Apply policy",'Top 10 of 47 qualifying<br/>peer teams, matched by<br/>historical profile:<br/>cosine similarity ≥ 0.75',346,188,270,166,emphasis=True,title_size=24,body_size=20)
    d.node("Score and rank",'Normalize and blend<br/>the three signals;<br/>rank all 28 candidates',646,188,266,166,title_size=24,body_size=20)
    d.arrow([(316,269),(346,269)],color=TEAL)
    d.arrow([(616,269),(646,269)],color=TEAL)
    d.text("August 2020 policy",48,380,864,size=24,color=TEAL,bold=True)
    d.text("Similarity 25% · Transitions 25% · Popularity 50% (historical only)",48,421,864,size=22,color=GRAY)
    d.end()

    d.new("Each component uses its own history", "§3.3-3.7", source_label="Source: src/ml/policy.py and src/ml/sequences.py; project report §3.3-3.7")
    d.text("Black Pearl · August prediction · baseline: 5 July 2020",48,105,864,size=23,color=GRAY)
    d.rect(48,147,864,42,NAVY)
    d.text("Component",60,155,202,size=22,color="FFFFFF",bold=True)
    d.text("History used for this recommendation",282,155,618,size=22,color="FFFFFF",bold=True)
    history_rows=[
        ("Similarity", "Find earlier peer assessments similar to Black Pearl's July state.<br/>Check improvements in their next two assessments.<br/>Use no peer observations after July.", 82),
        ("Practice transitions", "Learn practice-following patterns from January-June history.<br/>Compare Black Pearl's July scores with its May and June scores.<br/>Collect improved practices once, then score practices that<br/>historically followed them.", 105),
        ("Popularity", "Count improvements across teams in January-June.<br/>August's policy uses historical popularity only.", 62),
    ]
    y=189
    for label,body,height in history_rows:
        d.text(label,60,y+12,202,size=21,bold=True,color=TEAL,max_h=height-20,leading=26)
        d.text(body,282,y+12,618,size=18,max_h=height-20,leading=20)
        d.rule(48,y+height,864)
        y+=height
    d.text("<b>Monthly policy: one shared set of settings for all teams.</b><br/>For August, test combinations across May prediction cases using their May-July outcomes.",48,445,864,size=17,color=GRAY,leading=21)
    d.end()

    d.new("Why these two practices rank highest", "§3.5 and §3.7")
    d.text("Black Pearl · August 2020 · 28 eligible practices ranked",48,105,864,size=23,color=GRAY)
    d.text("Each component: raw evidence ÷ highest raw value. Final rank: weighted total.",48,137,864,size=17,color=GRAY)
    widths=[228,212,212,212]
    d.rect(48,164,864,50,NAVY)
    x=48
    for ci,(label,width) in enumerate(zip(["Component / weight", "#1 Scrum Master", "#2 Tech debt strategy", "#3 DoD"],widths)):
        if ci in (1,2):
            d.rect(x,164,width,50,TEAL)
        d.text(label,x+12,170,width-24,size=17.5,color="FFFFFF",bold=True)
        if ci:
            d.text("Selected" if ci in (1,2) else "Ranked third",x+12,195,width-24,size=11,color="FFFFFF")
        x+=width
    score_rows=[
        (["Similarity · 25%", "<b>0.000</b><br/>(0 ÷ 0.5944)", "<b>0.513</b><br/>(0.3047 ÷ 0.5944)", "<b>1.000</b><br/>(0.5944 ÷ 0.5944)"],56),
        (["Transitions · 25%", "<b>1.000</b><br/>(1.333 ÷ 1.333)", "<b>0.525</b><br/>(0.700 ÷ 1.333)", "<b>0.000</b><br/>(0 ÷ 1.333)"],56),
        (["Popularity · 50%", "<b>1.000</b><br/>(15 ÷ 15)", "<b>0.933</b><br/>(14 ÷ 15)", "<b>0.800</b><br/>(12 ÷ 15)"],56),
        (["Weighted total", "0.750", "0.726", "0.650"],36),
    ]
    y=214
    for row,height in score_rows:
        if row[0]=="Weighted total":
            d.rect(48,y,864,height,"F2F5F7")
        x=48
        for ci,(label,width) in enumerate(zip(row,widths)):
            if ci in (1,2):
                d.rect(x,y,width,height,PALE)
            d.text(label,x+12,y+7,width-24,size=17.5,leading=21,max_h=height-14,bold=row[0]=="Weighted total",color=TEAL if ci in (1,2) else NAVY)
            x+=width
        d.rule(48,y+height,864)
        y+=height
    d.text("<b>Similarity:</b> combine how similar each peer was with how much it improved the practice.<br/><b>Transitions:</b> combine historical evidence that a practice follows Black Pearl's recent improvements.<br/><b>Popularity:</b> count how often the practice improved across teams.<br/>Each component is scaled relative to its highest raw score. Details: backup A4.",48,431,864,size=13,leading=14,max_h=56)
    d.end()

    d.new("Temporal controls prevent future-data leakage", "§3.6-3.7 and §6.5")
    d.text("Example: July baseline, August prediction",48,113,864,size=24,color=GRAY)
    # A quantitative date plot of the documented worked-example outcome window.
    dates=[date(2020,7,5),date(2020,8,3),date(2020,9,6),date(2020,10,5)]
    xs=[168+(v-dates[0]).days/(dates[-1]-dates[0]).days*654 for v in dates]
    d.rule(95,253,772,color=GRAY,thickness=1.5)
    for j,(x,label) in enumerate(zip(xs,["5 July","3 August","6 September","5 October"])):
        d.c.setFillColor(colors.HexColor('#'+(NAVY if j==0 else TEAL)))
        d.c.circle(x,H-253,5,stroke=0,fill=1)
        d.text(label,x-48,276,130,size=20,bold=True)
    d.text("Baseline",xs[0]-61,199,160,size=23,bold=True)
    d.text("Prediction",xs[1]-70,199,170,size=23,color=TEAL,bold=True)
    d.text("Why three snapshots? Allow time for practice maturity to improve.",48,331,864,size=23,color=TEAL,bold=True)
    d.text("Select weights only after earlier outcomes are complete, to avoid future-data leakage.",48,373,864,size=20)
    d.text("May-July: popularity-only bootstrap.<br/>August: May's three-snapshot outcomes are complete; policy selection can begin.",48,411,864,size=20,leading=25)
    d.caption("Three snapshots is a fixed design choice; we did not optimize the window length.",y=474,size=14)
    d.end()

    d.new("What counts as a successful ranking?", "§3.6-3.7 and §6.2-6.3")
    d.text("Conditional Hit Rate@2",48,120,864,size=26,color=TEAL,bold=True)
    d.text("At least one recommendation matches a later improvement<br/>in a case where an improvement occurred.",48,164,864,size=24,leading=33)
    d.text("Black Pearl",48,253,217,size=23,bold=True)
    d.text("Tech debt strategy later improved: this case is a hit.",274,253,638,size=23,color=TEAL)
    d.text("298 eligible prediction cases with complete follow-up",48,310,864,size=22,bold=True)
    d.text("May-September · baseline + 3 later snapshots · ≥2 eligible practices",48,345,864,size=19,color=GRAY)
    d.rect(48,378,864*120/298,24,TEAL)
    d.rect(48+864*120/298,378,864*178/298,24,"B5C4CF")
    d.text("120 cases<br/>Maturity increased",48,413,393,size=21,bold=True,color=TEAL,leading=25)
    d.text("178 cases<br/>No maturity increase recorded",447,413,465,size=21,bold=True,leading=25)
    d.caption("Hit-rate cohort: 120 improvement cases + 1 with partial follow-up = 121.",y=473,size=14)
    d.end()

    d.new("Primary historical results", "§6.2-6.3")
    d.text("Mean monthly Conditional Hit Rate@2",48,109,864,size=24,color=GRAY)
    # Horizontal quantitative chart. The full 0-100% scale avoids exaggerating the gap.
    x0,span=362,452
    for tick in [0,.25,.5,.75,1]:
        x=x0+tick*span
        d.c.setStrokeColor(colors.HexColor('#'+LINE));d.c.setLineWidth(.5)
        d.c.line(x,H-167,x,H-351)
        d.text(f"{tick:.0%}",x-16,365,80,size=14,color=GRAY)
    for y,label,value,color in [(176,"Random baseline",.306,"A9B8C3"),(240,"Time-aware popularity",.557,"607E91"),(304,"Adaptive blend",.58,TEAL)]:
        d.text(label,48,y+2,302,size=23,bold=label=="Adaptive blend")
        d.rect(x0,y,span*value,38,color)
        d.text(f"{value:.1%}",x0+span*value+12,y+3,100,size=25,bold=True)
    d.text("Popularity counts how frequently practices improved across teams, with an adjustable emphasis on recent improvements.",48,392,864,size=14,color=GRAY,leading=18,max_h=18)
    d.text("1.9× random · +2.3 percentage points over popularity",48,438,864,size=23,color=TEAL,bold=True)
    d.caption("Five primary months. 121 outcome-bearing cases. The difference is exploratory.",y=476,size=13)
    d.end()

    d.new("Capabilities, practical value and limits", "Executive summary, pp. 6-7; §7.3")
    d.text("Working decision aid",48,133,418,size=27,color=TEAL,bold=True)
    d.text("Evidence boundaries",534,133,378,size=27,bold=True)
    for y,left,right in [
        (209,"Excel input + web interface / API","One organization, short history"),
        (277,"Automatic monthly policy selection","3 of 5 months use bootstrap"),
        (345,"Consistent, evidence-based rankings","Practical benefit needs a pilot")
    ]:
        d.text(left,48,y,418,size=23,max_h=62)
        d.text(right,534,y,378,size=22,max_h=62)
    d.text("Ready for supervised pilot testing",48,431,864,size=26,color=TEAL,bold=True)
    d.caption("The prototype still needs production hardening. Estimated time savings have not been measured.",y=475,size=12)
    d.end()

    d.new("A prospective pilot can test practical benefit", "§3.6 and §8.2; proposed design")
    d.text("Recommendation-assisted<br/>coaching",48,143,408,size=30,bold=True,leading=39)
    d.text("Usual coaching",534,143,378,size=30,bold=True,leading=39)
    d.text("Compare improvement frequency and time to improvement.",48,273,864,size=27,color=TEAL,bold=True,leading=37)
    d.text("Record actual attempts, failures and recommendation use.<br/>Predefine allocation, duration and success criteria.",48,367,864,size=24,leading=34)
    d.end()

    d.new("Conclusions", "§1.2, §6.3 and §8.1-8.3")
    d.text("An empirical approach: learning from how teams improved provides evidence for what another team could consider next.",
           48,143,864,size=34,color=TEAL,bold=True,leading=44,max_h=140)
    d.text("Implemented in a working recommendation system,<br/>evaluated retrospectively, and ready for supervised pilot testing.",
           48,311,864,size=25,leading=35,max_h=80)
    d.caption("Questions and discussion",y=456,size=22,color=TEAL)
    d.end()

    d.new("A1. Results by prediction month", "§6.3",True)
    d.table(["2020","Cases","Blend","Popularity","Recommendation policy"],[
        ["3 May","21","28.6%","28.6%","Bootstrap / popularity only"],
        ["8 June","22","63.6%","63.6%","Bootstrap / popularity only"],
        ["5 July","27","66.7%","66.7%","Bootstrap / popularity only"],
        ["3 August","24","79.2%","75.0%","Adaptive blend"],
        ["6 September","27","51.9%","44.4%","Adaptive blend"],
        ["5 October","24","33.3%","20.8%","Adaptive blend*"],
        ["4 November","6","33.3%","33.3%","Adaptive blend*"]
    ],[177,100,150,170,267],y=104,row_h=36,size=18,highlight=(3,4))
    d.text("<b>Bootstrap:</b> no earlier prediction month has complete three-snapshot follow-up to select blend weights.<br/>"
           "Uses 100% popularity (50% historical + 50% recent); similarity and transitions have zero weight.<br/>"
           "Primary: 58.0% vs 55.7%. All seven months: 50.9% vs 47.5%.<br/>"
           "*October and November: incomplete follow-up; supplementary results, excluded from the primary average.",48,414,864,size=14,max_h=76)
    d.end()

    d.new("A2. Policy search grid", "§3.5 and §6.5",True)
    d.text("Select one shared policy per prediction month, using only completed outcomes from earlier predictions.",48,103,864,size=18,color=GRAY)
    widths=[220,210,434]
    d.rect(48,145,864,40,NAVY)
    for x,title,width in [(48,"Parameter",220),(268,"Candidate values",210),(478,"Meaning",434)]:
        d.text(title,x+12,153,width-24,size=19,color="FFFFFF",bold=True)
    y=185
    rows=[
        ("Peer count", "5, 10 or 19", "Maximum number of distinct peer teams<br/>used for similarity evidence.", 62),
        ("Minimum cosine<br/>similarity", "0, 0.50 or 0.75", "Keep peers at or above this threshold;<br/>higher values require closer profiles.", 62),
        ("Three component<br/>weights", "15 combinations<br/>in 25% steps", "Similarity + transitions + popularity = 100%.<br/>Example: 25% / 25% / 50%.", 72),
        ("Recent share<br/>within popularity", "0%, 25%, 50%,<br/>75% or 100%", "0% = historical only; 100% = recent only.<br/>Intermediate values mix the two scores.", 72),
    ]
    for label,values,meaning,height in rows:
        for x,text,width in [(48,label,220),(268,values,210),(478,meaning,434)]:
            d.text(text,x+12,y+10,width-24,size=18,leading=22,max_h=height-18,bold=x==48)
        d.rule(48,y+height,864)
        y+=height
    d.text("3 × 3 × 15 × 5 = 675 policies. Select the highest mean monthly hit rate on completed earlier outcomes.",48,466,864,size=14,leading=18,max_h=18)
    d.end()

    d.new("A3. One shared policy is selected each month", "§3.5, §3.7 and §6.5",True)
    d.rows([
        ("1. Gather evidence", "Use earlier prediction months whose three-snapshot<br/>outcome windows have closed before the target month."),
        ("2. Compare policies", "Replay all 675 combinations. Select the highest mean<br/>monthly Conditional Hit Rate@2 on that earlier evidence."),
        ("3. Apply the policy", "Use one set of settings for all teams in the target month.<br/>Each team's evidence still produces its own ranking."),
    ],y=119,step=65,label_w=225,body_size=20)
    d.table(["Prediction month", "Earlier predictions used", "Their outcome windows"],[
        ["August", "May", "May-July"],
        ["September", "May and June", "May-July and June-August"],
    ],[204,294,366],y=330,row_h=43,size=19)
    d.caption("No completed earlier outcomes: use default popularity. Reselect each month; settings may stay the same.",y=477,size=13)
    d.end()

    d.new("A4. How component scores are normalized", "§3.5 and §3.7",True,source_label="Source: src/ml/policy.py; source workbook; project report §3.5 and §3.7")
    d.text("Tech debt strategy · Black Pearl · August 2020",48,107,864,size=23,color=GRAY)
    d.table(["Component", "Tech debt strategy<br/>raw score", "Highest raw score<br/>and practice", "Division and result"],[
        ["Similarity", "0.3047", "0.5944<br/>(DoD)", "0.3047 ÷ 0.5944<br/>= <b>0.513</b>"],
        ["Transitions", "0.700", "1.333<br/>(Scrum Master)", "0.700 ÷ 1.333<br/>= <b>0.525</b>"],
        ["Popularity", "14 events", "15 events<br/>(Scrum Master)", "14 ÷ 15<br/>= <b>0.933</b>"],
    ],[150,216,248,250],y=140,row_h=70,size=15)
    d.text("Normalized score = raw evidence ÷ largest raw value for that component.",48,410,864,size=20,color=TEAL,bold=True)
    d.text("Similarity: sum of peer similarity × observed maturity increase.<br/>Transitions: sum of learned successor probabilities for recent improvements.<br/>Popularity counts improvement events across teams. Values shown are rounded; full precision is used.",48,443,864,size=13,color=GRAY,leading=15,max_h=45)
    d.end()

    d.new("A5. Where raw scores and divisors come from", "§3.3-3.5 and §3.7",True,source_label="Source: source workbook; src/ml/policy.py and src/ml/sequences.py")
    d.text("Black Pearl · August 2020 · the two inputs to each division in A4",48,105,864,size=21,color=GRAY)
    widths=[150,357,357]
    d.rect(48,143,864,44,NAVY)
    x=48
    for label,width in zip(["Component","Tech debt strategy's raw score","Highest raw score (divisor)"],widths):
        d.text(label,x+12,154,width-24,size=17,color="FFFFFF",bold=True)
        x+=width
    raw_rows=[
        (["Similarity", "ACM: 0.913998 × (1 ÷ 3)<br/>= <b>0.3047</b>", "DoD: ACM + Puffin<br/>0.3047 + 0.2897 = <b>0.5944</b>"],80),
        (["Transitions", "Product Owner + Scrum Master<br/>0.500 + 0.200 = <b>0.700</b>", "Scrum Master:<br/>Backlog grooming + Retro<br/>2/6 + 1/1 = <b>1.333</b>"],80),
        (["Popularity", "Tech debt strategy:<br/><b>14 improvement events</b>", "Scrum Master:<br/><b>15 improvement events</b> (maximum)"],60),
    ]
    y=187
    for row,height in raw_rows:
        x=48
        for ci,(label,width) in enumerate(zip(row,widths)):
            d.text(label,x+12,y+10,width-24,size=17.5,leading=20,max_h=height-18,bold=ci==0,color=TEAL if ci==0 else NAVY)
            x+=width
        d.rule(48,y+height,864)
        y+=height
    d.text("<b>Similarity:</b> ACM improved Tech debt strategy from level 1 to 2; the other nine selected peers contributed zero.<br/>For DoD, ACM and Puffin each improved one level. Each contribution is peer similarity × (level increase ÷ 3).<br/><b>Transitions:</b> values are learned probabilities that the candidate follows Black Pearl's recently improved practices.<br/>Scrum Master followed Backlog grooming in 2 of 6 successor links, and Retro in 1 of 1. Retro's evidence is one observation.<br/>Popularity counts events across teams before July. Values shown are rounded; calculations use full precision.",48,416,864,size=13,color=GRAY,leading=14,max_h=70)
    d.end()

    d.new("A6. Code walkthrough", "§4.2-4.3",True,source_label="Source: src/ml/policy.py · PolicyEngine._compute_components")
    d.text("PolicyEngine._compute_components",48,116,864,size=29,color=TEAL,bold=True)
    d.text('<link href="https://github.com/erezmorabia/agile-prediction-mvp/blob/main/src/ml/policy.py#L335"><u>src/ml/policy.py:335</u></link> · inputs: team + latest assessment date',48,163,864,size=20,color=TEAL)
    d.text("Collects the team's current state and raw evidence<br/>for the three recommendation components.",48,214,864,size=24,leading=31)
    d.rows([
        ("Current state", "Read maturity scores; identify practices below level 3."),
        ("Similarity", "Find earlier peer profiles and their later improvements."),
        ("Transitions", "Use recent team improvements to look up likely successors."),
        ("Popularity", "Collect historical and recent improvement counts across teams."),
    ],y=302,step=37,label_w=180,body_size=19)
    d.caption("Returns CaseComponents. score_case() later normalizes and combines the evidence.",y=466,size=17)
    d.end()

    d.finish()
    return d.titles


def make_presenter(titles):
    styles={
        'title':ParagraphStyle('title',fontName='Arial-Bold',fontSize=23,leading=29,textColor=colors.HexColor('#'+NAVY),spaceAfter=12),
        'head':ParagraphStyle('head',fontName='Arial-Bold',fontSize=14,leading=19,textColor=colors.HexColor('#'+TEAL),spaceBefore=18,spaceAfter=7,keepWithNext=True),
        'body':ParagraphStyle('body',fontName='Arial',fontSize=10.7,leading=16,textColor=colors.HexColor('#'+NAVY),spaceAfter=7),
        'source':ParagraphStyle('source',fontName='Arial',fontSize=9,leading=13,textColor=colors.HexColor('#'+GRAY),spaceAfter=8)
    }
    story=[]
    def para(text,key='body'):
        return Paragraph(clean(text),styles[key])
    story.append(para('Defense presentation<br/>Presenter notes','title'))
    story.append(para('Erez Morabia · M.Sc. Advanced Project in Computer Science · 22997'))
    story.append(para('Session: Zoom, Sunday, 10:00-11:00, as supplied by the student. The supervisor requests a clear explanation of problems in the current state of the art and how the project improves on them. No additional presentation requirements were specified. Plan approximately 20-25 minutes for the presentation within the one-hour meeting, leaving substantial time for discussion. English remains a working choice. The audience PDF contains 16 main slides and six backups with PDF outline navigation.'))
    story.append(para('Executive-summary foundation','head'))
    story.append(para('The main narrative follows the Executive Summary on pages 5-7 of PROJECT_DOCUMENTATION.pdf: the challenge, empirical organizational learning, three evidence signals, monthly adaptive blending, validation, results and pilot readiness. Architecture and the Black Pearl example come from sections 3.7 and 4. The contribution is the applied learning approach and working system. Transition evidence does not guarantee readiness. The report\'s 4-8 hours per month is a practitioner estimate, so the deck does not present it as measured savings.'))
    story.append(para('Maturity assessments identify improvement gaps. This project addresses the practical decision: which practice should an individual team consider next? It uses longitudinal team and peer histories, observed practice transitions, and organization-wide trends to rank candidates. The working system and temporally controlled evaluation are the design contributions. The measured result is 58.0% conditional historical alignment, versus 30.6% random and 55.7% time-aware popularity. The small additional gain over popularity remains exploratory. The project did not compare implementations of the cited prior systems or test whether providing advice accelerates adoption.'))
    story.append(para('Design basis','head'))
    story.append(para('The deck follows university guidance on legibility and attention: a white background, dark navy text, one teal accent, embedded Arial fonts, 34 pt headings and predominantly 24 pt body text. The agreed narrative is why (slides 1-2), what (3-4), how (5-10), evidence (11-13), and implications (14-16). Visuals show inputs and outputs, parallel recommendation signals, a shared-engine architecture, and the software request. The later example outcome appears only in the evaluation section. These are selectable vector diagrams in the PDF. Diagram detail and supporting captions use smaller type. Small source footers and page numbers are supporting metadata. Quantitative graphics use direct labels, so meaning does not depend on color. This is a custom academic design, not an official Open University template.'))
    for org,title,url in RESEARCH:
        story.append(para(f'{escape(org)}: <link href="{url}">{escape(title)}</link>','source'))
    story.append(para('Projection and rehearsal','head'))
    story.append(para('On Zoom, share the PDF application window and keep these presenter notes on a separate screen. Use presentation or full-screen mode and check that the shared view shows slides only. Stop after slide 16 for questions. The six backup pages are A1 (monthly results), A2 (policy search grid), A3 (monthly policy selection) A4 (component normalization) A5 (raw evidence calculations) and A6 (code walkthrough). For a shorter talk, shorten algorithm and example details while preserving the problem statement, project response, metric definition and limits. Precompute any optional live backtest. Review your personal contribution before the session.'))
    story.append(para('Timing','head'))
    story.append(para('Aim for 20-25 minutes before questions. The 10:00-11:00 slot describes the whole meeting, rather than a requirement to speak for an hour. The demonstration is optional and would add approximately two minutes. Rehearse the first four slides as one connected argument: practical problem, empirical learning proposal, and recommendation approach.'))
    replacements={
        1:'45 seconds. Open with the professor\'s requested framing. Existing assessment and recommendation approaches help organizations plan improvement, but this project addresses a particular operational decision: which practice should this team consider next? Explain the history-based ranking approach, the implemented decision aid and the backtest evidence. The project improves the organization\'s ability to make this decision systematically. Causal acceleration and superiority over published tools remain outside the demonstrated claims.',
        2:'75 seconds. Define the practical limitation in the existing organizational process. Assessments identify many practices below maximum maturity, but the team still needs to decide where to invest limited coaching attention. Explain the three challenges on the slide: different starting maturity profiles, useful evidence in other teams\' improvement histories, and the difficulty of comparing those histories manually at organizational scale. The goal is to turn that experience into two team-specific practices for coach review. This is the operational problem the project addresses. Avoid treating every existing maturity framework as a fixed universal roadmap. The next slide introduces the proposal directly: learning from organizational histories to guide the next-practice decision. No measured manual-analysis time savings are claimed.',
        3:'90 seconds. Acknowledge that process-improvement recommendation already exists. ReMo develops recommendations by analysing process-assessment findings. The 2022 chapter describes correlations analysis, improvement packages, review and refinement, and recommendation development, evaluated through industrial cases. WebProcessPAIR recommends improvement actions for individual developers\' performance problems and root causes, using crowdsourced actions. These are useful approaches with different targets. Our specific target is the next observed practice change in a team\'s longitudinal organizational history. Avoid saying that prior work is merely manual, that no recommender exists, or that all existing methods ignore history. The cited descriptions establish a task distinction, rather than a head-to-head performance comparison.',
        4:'90 seconds. Lead with the executive summary\'s central contribution: empirically learn how this organization improves, then use that evidence to identify likely next practices for one team. Collaborative filtering and transition modelling operationalize the approach. State the proposal before describing its implementation. Input is a team and prediction month, together with organizational history available at the earlier baseline. Output is two ranked practices that have not reached maximum maturity, when at least two candidates remain. The engine learns from prior organizational history using component-specific scoring windows. There is no fixed lookback for historical learning: each prediction uses only the history available under its baseline cutoffs. The dataset contains ten recorded months overall, not ten months of history for every prediction. The next slide notes explain the shorter component windows. The coach evaluates feasibility and context before deciding what to attempt. This slide specifies the decision aid rather than claiming a new algorithm or proven adoption acceleration. The next slide explains the recommendation idea conceptually, before the data and software architecture.',
        5:'105 seconds. Read the three evidence streams in parallel, not as sequential prerequisites. Similar teams contribute practices that comparable historical peer states later improved. Practice transitions contribute empirical successors to the target team\'s recently improved practices. Time-aware popularity contributes historical and recent organization-wide improvement counts. The arrows converge on component normalization and score blending. Monthly weights come from completed earlier outcomes. Only practices below maximum maturity enter the candidate set; the bottom ranking label does not mean candidate eligibility is decided after seeing the scores. The system returns exactly two practices when at least two candidates remain. Ranking scores are not calibrated success probabilities. Window details: collaborative filtering searches peer snapshots across all months strictly before the baseline, then measures improvements in each matched peer\'s next two recorded snapshots, stopping at the baseline. The Practice Transition Model learns patterns from all history strictly before the baseline; it identifies the target team\'s recent improvements by comparing the baseline against each of its two preceding snapshots. Time-aware popularity blends historical counts strictly before the baseline with the single latest organization-wide transition into the baseline. These shorter scoring windows do not cap the historical learning window. The three-snapshot forward window is for evaluating outcomes, not a scoring lookback. Snapshot counts need not equal calendar months. All signals remain bounded by the historical baseline.',
        12:'105 seconds. Follow the executive summary from results to practical value. The functional prototype accepts Excel data and provides recommendations through a web interface and API. Monthly policy selection reduces manual parameter tuning, and a shared ranking approach supports consistent coach-team discussions. These are delivered capabilities. They do not constitute measured time savings or evidence of faster adoption. The short single-organization history and three identical bootstrap months limit performance interpretation. The system is ready for supervised pilot testing, while access control, monitoring and automated data refresh remain future engineering work. The next slide explains what that pilot should measure.',
        7:'90 seconds. Read each row as a request and its returned result, not as independent data exports from PolicyEngine. In the top row, the user clicks Recommend; the API calls the shared recommendation engine with the selected team and prediction month. The engine returns two ranked practices, which are displayed in the browser. Both paths originate in the web interface and API: the upper branch is the Recommend action and the lower branch is the Run backtest action. In the bottom row, the API starts BacktestEngine, which loops over historical team-month cases and requests recommendations from the same engine. It then compares those results with later recorded improvements and calculates metrics. The two arrows in each row show logical call and response order; the result is returned to the caller. In the center, PolicyEngine has two responsibilities: once per prediction month it selects and caches global settings from completed earlier prediction outcomes, or uses the default popularity policy when none exist; for each team-month request it computes the evidence, applies the selected settings, ranks eligible practices and returns the top two. The 675-policy selection evaluates earlier cases and is distinct from the backtest outer loop over evaluated target months. Both live requests and historical replay consume the processed team histories introduced on the previous slides. The CLI also uses this engine but is omitted from the diagram for clarity. Backup A2 defines the grid and A3 explains monthly selection.' ,
        8:'120 seconds. Explicitly introduce this as an explanation by example using a reproducible historical request. Explicitly identify Black Pearl as the team name and August 2020 as the prediction month. The question is which two practices this team should prioritize next. Find current state means locating the latest recorded assessment before that prediction: 5 July 2020, the baseline. The workbook encodes the August snapshot as 3 August 2020. Of the 30 retained practices, 28 are below raw maturity level 3 and eligible. There are 47 distinct qualifying peer teams with cosine similarity at least 0.75; the policy selects the 10 most similar. Each peer is represented by its best-matching historical snapshot strictly before the baseline, rather than necessarily its latest state. The selected 10 have similarities approximately 0.869-0.914. Weights are 25% collaborative-filtering similarity, 25% practice transitions and 50% popularity. The recent-popularity share is zero, so popularity is historical only. Policy selection uses all earlier prediction cohorts whose three-snapshot outcome windows have closed before August, not a fixed number of months back. Here only the 3 May prediction cohort qualifies: its outcome snapshots are 3 May, 8 June and 5 July. Thus selection relies on one completed prior prediction month, three calendar months before August; June and July predictions have not yet completed their outcome windows. This cohort selects the global policy across teams, rather than tuning it just for Black Pearl. Component learning separately uses the available historical evidence under its temporal cutoffs. After normalization and blending, the returned practices are Scrum Master at 0.750 and Tech debt strategy at 0.726. Scores rank candidates; they are not probabilities. Later improvements are reserved for the evaluation discussion on slide 10. Slide 9 decomposes the scores.',
        9:'120 seconds. Walk through the July-to-October date chart. The August prediction uses the most recent earlier team baseline, 5 July. Component learning precedes the baseline, and peer follow-up ends at the baseline. The August maturity values do not enter recommendation scoring. Policy selection uses only strictly earlier prediction months with completed outcomes. After generating the recommendations, evaluate against the August, September and October snapshots. Three recorded snapshots need not equal three calendar months because team observations can be irregular. These temporal controls separate scoring and policy selection from the later evaluation. Outcome conditioning still limits interpretation, as the next slide explains.',
        10:'120 seconds. Revisit Black Pearl: Tech debt strategy improved in the August-to-October outcome window, so one of the two returned suggestions matches and the case counts as a hit. Define a hit as a nonempty intersection between the two recommendations and eligible practices that later improve. The reported rate conditions on at least one observed improvement. The stacked bar audits the stricter complete-team-window cohort: 120 improvement-bearing and 178 no-improvement cases out of 298. The primary hit rate on the next slide uses 121 outcome-bearing cases because one additional case has a partial team-level window. Do not combine the 121-case rate cohort with the 178 no-improvement cases as if they shared one completeness definition. Without records of attempted practices, the no-improvement cases cannot establish whether providing a recommendation would have changed outcomes. Average case hit indicators within each month, then average the monthly rates.',
        14:'45 seconds. Close with the takeaway: an empirical approach, learning from how teams improved, provides evidence for what another team could consider next. The approach is implemented in a working recommendation system, evaluated retrospectively, and ready for supervised pilot testing. Empirical means grounded in observed organizational improvement histories. Historical alignment does not establish faster adoption or a clear advantage over popularity alone. Stop here for questions; use the three appendix slides for monthly results, policy-search details or monthly policy selection when relevant.',
        22:'Backup. The 2022 ReMo chapter and the 2017 WebProcessPAIR abstract establish related process-improvement decision targets. The project report documents the implementation and reported results. Technical claims follow that report, not the separately developed conference manuscript. If asked about novelty, state the specific task and protocol rather than claiming no prior work exists. The cited prior systems were not implemented as evaluation arms. Primary sources: https://doi.org/10.1002/9781119821779.ch1 and https://doi.org/10.1145/3084100.3084365 .'
    }
    def shifted_refs(note):
        note=re.sub(r'\bslide (\d+)',lambda m: 'slide '+str(int(m[1])+1 if 6<=int(m[1])<=15 else int(m[1])),note,flags=re.I)
        return note.replace('Slides 7 and 12','Slides 8 and 13')
    for i,(source_index,title) in enumerate(zip(SOURCE_ORDER,titles),1):
        if source_index == -3:
            note='75 seconds. This diagram follows section 4.1 of the project report, simplified for projection. The browser interface uses HTML, CSS and JavaScript and sends requests over HTTP/REST to the API layer. The API contains routes, request/response models and a service layer. Below it are three modules: the ML engine computes evidence and owns policy selection and ranking; validation replays historical predictions and computes metrics; the data module loads Excel, validates and normalizes maturity scores, and indexes histories. The upper arrows show API access to modules. The lower arrow from validation to ML explicitly shows that backtesting requests historical recommendations from the same ML engine, rather than maintaining an independent scoring implementation. The modules collaborate: validation uses the same recommendation engine and both consume processed history. Technical terms, if asked: PolicyEngine is the central scoring and policy-selection class. It selects the monthly settings from completed earlier outcomes and combines the three signals to rank eligible practices. RecommendationEngine is a thin compatibility wrapper: it exposes the recommendation interface and delegates the work to PolicyEngine, rather than implementing another model. The diagram uses responsibilities instead of these class names. Validation is where the BacktestEngine replays historical prediction cases, compares recommendations against later observed improvements and calculates ranking metrics, using the same scoring engine as the live application. The next slide explains those data dependencies and the shared scoring engine. CLI access is covered there. This slide shows the implemented modular structure and separation of responsibilities.'
            source='PROJECT_DOCUMENTATION.pdf, page 21, section 4.1; docs/PROJECT_DOCUMENTATION.md, sections 4.1-4.3'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(shifted_refs(note))),para('Sources: '+escape(source),'source')]))
            continue

        if source_index == -6:
            note='Walk through PolicyEngine._compute_components(team, baseline_month), currently at src/ml/policy.py:335. It collects the baseline maturity levels, practices below maximum maturity, historical peer matches and per-practice improvements, target-team recent-improvement transition evidence, and historical/recent organizational popularity counts. It returns CaseComponents. Policy-specific peer selection, normalization and weighting occur later in score_case; final top-two selection occurs in top_practices. The PDF source pointer links to the repository source. Line numbers may move as the code changes.'
            source='src/ml/policy.py:335, PolicyEngine._compute_components'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(note)),para('Sources: '+escape(source),'source')]))
            continue
        if source_index == -5:
            note='Use the visible examples on A5 to explain where raw evidence comes from. Among the ten selected peers, only ACM improved Tech debt strategy in the allowed follow-up, from raw level 1 on 8 June to raw level 2 on 5 July. Its cosine similarity is 0.9139982658084418; multiply by the normalized one-level increase of one-third to obtain 0.3046660886028139, displayed as 0.3047. For transition evidence before July, Backlog grooming sprint has six recorded outgoing successor links, two to Scrum Master; Retro has one outgoing link, to Scrum Master. Because Black Pearl recently improved both practices, their 2/6 and 1/1 probabilities contribute to Scrum Master, totaling 1.3333333333333333. These are counts of practice-to-practice links between consecutive improvement-bearing steps, not necessarily distinct teams or consecutive calendar months. Popularity counts improvement events across earlier organizational histories: Scrum Master 15 and Tech debt strategy 14. A4 then divides these raw evidence values by component-specific maxima.'
            source='data/raw/combined_dataset.xlsx; src/ml/policy.py: _peer_contribution and _compute_components; src/ml/sequences.py: _learn_team_transitions and get_typical_next_practices'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(note)),para('Sources: '+escape(source),'source')]))
            continue
        if source_index == -4:
            note='105 seconds. Reproduce the values with the checked-in workbook using the standard 90-percent missingness filter, July baseline and August policy. For similarity, select the ten peers above the threshold. For each peer and practice, find the best observed normalized maturity increase in up to two follow-up snapshots, ending no later than July. Sum peer cosine similarity times that increase. Tech debt strategy has raw evidence 0.3046660886028139; the largest similarity evidence across practices is DoD at 0.5943733751712366. Division gives 0.5125836743865602, displayed as 0.513. This is not the peer cosine itself. For transitions, collect recently improved target practices once, sum their learned top-three successor probabilities into each successor practice, then divide by the largest combined transition score. Tech debt strategy has 0.7 divided by 1.3333333333333333, giving 0.525; Scrum Master provides the maximum. Popularity counts observed improvement events strictly before July: Tech debt strategy has 14 and the largest count among eligible candidates is Scrum Master at 15, giving 0.9333333333333333. The August recent share is zero. Normalization scopes differ: similarity and transitions are normalized over all evidence before masking to eligible practices; historical popularity is first restricted to eligible practices and then normalized. Thus similarity denominator DoD can be outside the candidate set. Scrum Master has zero similarity evidence, and maximum transition and historical popularity evidence, producing components 0, 1 and 1. Blend the unrounded normalized values with 25/25/50 weights to get 0.750 and 0.726. Scores rank historical evidence and are not probabilities.'
            note+=' Explain frequency versus weighted improvement using this illustrative example, not actual Black Pearl peer records: one peer with similarity 0.90 improves a practice from level 1 to level 3. Its normalized increase is two-thirds, so its contribution is 0.90 times two-thirds = 0.60. For another practice, two peers each have similarity 0.80 and each improves from level 1 to level 2. Each contributes 0.80 times one-third, about 0.267; together they contribute about 0.533. The first practice has one improvement event but a higher similarity evidence total than the second practice with two events. Thus DoD having the largest actual similarity total means its selected peers provide the strongest combined similarity-and-magnitude evidence, not necessarily the most frequent improvement events. For a peer, the implementation uses its best increase within the allowed two-snapshot follow-up, rather than counting every intermediate increase. In contrast, popularity counts recorded improvement events across all teams, ignoring peer similarity and increase size; a level 1-to-3 increase is still one event. Scrum Master has 15 such events, Tech debt strategy 14 and DoD 12 in the historical window. The popularity denominator 15 is the largest count among eligible practices, not the total across practices.'
            note+=' What is the divisor in each row? Similarity: divide by the largest combined peer-improvement evidence total across practices. Here DoD supplies that maximum, 0.5944. Transitions: divide by the largest sum of learned follow-on probabilities across practices. Here Scrum Master supplies that maximum, 1.333. Historical popularity: divide by the highest improvement-event count among eligible practices, meaning the most frequently improved eligible practice. Here Scrum Master supplies the maximum of 15 events, so Tech debt strategy is 14 divided by 15. These divisors are separate maxima, not sums across practices, not the number of teams and not the number of observations. They are calculated for this case from its available evidence, rather than being fixed constants. The maximum becomes 1; if a component has no positive evidence, all its scores are zero.'
            source='data/raw/combined_dataset.xlsx; src/ml/policy.py: _peer_contribution, _compute_components, _normalize and score_case; docs/PROJECT_DOCUMENTATION.md, sections 3.5 and 3.7'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(note)),para('Sources: '+escape(source),'source')]))
            continue
        if source_index == -2:
            note='90 seconds. One global policy is selected for each prediction month, not separately for each team. The selection uses all earlier evaluated prediction months whose full three-snapshot outcome windows have closed strictly before the target month. Replay each of the 675 configurations using each earlier case historical components and candidate set, calculate Conditional Hit Rate@2 within each earlier month on the fixed outcome-bearing cohort, then average those monthly rates. Choose the maximum with deterministic tie-breaking. For August, only May predictions qualify because their May/June/July outcome snapshots are available before August. For September, May and June predictions qualify; June outcomes close in August. July predictions require September outcomes and cannot yet inform September settings. Apply the selected policy to target-month team evidence, so settings are shared but recommendations differ by team. Re-selection can return the same settings as before. With no completed earlier outcomes, use the fixed default of 100% popularity and equal historical/recent shares. The selection is cached per prediction month by PolicyEngine; it is not independently re-optimized for every request. Component learning still uses each case available history; May-only selection evidence does not restrict August component learning to May.'
            source='docs/PROJECT_DOCUMENTATION.md, sections 3.5, 3.7 and 6.5; src/ml/policy.py: completed_prior_months and select_policy'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(shifted_refs(note))),para('Sources: '+escape(source),'source')]))
            continue
        if source_index == -1:
            note='105 seconds. Explain selection using only the evidence available for scoring, without revealing later outcomes. Both practices are eligible: Scrum Master is at raw level 2 and Tech debt strategy at raw level 1. Of 28 eligible candidates, these have the largest weighted totals. Scrum Master receives zero normalized similarity evidence, but the strongest transition and historical-popularity scores, both 1.000. Its score is 0.25 times 0 plus 0.25 times 1 plus 0.50 times 1 = 0.750. Zero similarity means no improvement contribution for this practice from the selected peers within the allowed windows; it does not mean no similar teams were found. Tech debt strategy receives support from all three components: 0.513 similarity, 0.525 transitions and 0.933 popularity. Their weighted contributions are approximately 0.128, 0.131 and 0.467, totaling 0.726 using unrounded inputs. A positive contribution from more components does not automatically yield a higher total. The model ranks numerical evidence; it does not prove suitability or predict a success probability. The component values shown are rounded and have component-specific normalization scopes. Later outcomes are discussed on slide 11.'
            note+=' The main table now shows the numerator and denominator for every normalized component score, including DoD as the third-ranked eligible practice. Similarity raw values are 0, 0.3046660886028139 and 0.5943733751712366; divide each by the maximum 0.5943733751712366. Transition raw scores are 1.3333333333333333, 0.7 and 0; divide each by 1.3333333333333333. Historical popularity counts are 15, 14 and 12 improvement events, divided by the highest eligible-practice count of 15. Raw values in the slide are rounded; calculation uses full precision. The selected August weights are 25 percent similarity, 25 percent transitions and 50 percent historical popularity. Scrum Master total is 0.25 times 0 plus 0.25 times 1 plus 0.5 times 1, equal to 0.750. Tech debt strategy is approximately 0.25 times 0.513 plus 0.25 times 0.525 plus 0.5 times 0.933, equal to 0.726 with unrounded inputs. DoD is 0.25 times 1 plus 0.25 times 0 plus 0.5 times 0.8, equal to 0.650. It has the highest similarity score but lacks transition support and has lower popularity, so its overall rank is third. Similarity raw evidence sums each selected peer cosine times its best normalized maturity increase within the allowed follow-up. Transition raw evidence sums the learned top-three successor probabilities from each deduplicated recently improved target practice. Improvement counts may include multiple events across teams and time, not just distinct teams. Backup A4 elaborates the raw evidence and normalization scopes.'
            source='docs/PROJECT_DOCUMENTATION.md, sections 3.5 and 3.7; data/raw/combined_dataset.xlsx; src/ml/policy.py: score_case and top_practices'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(shifted_refs(note))),para('Sources: '+escape(source),'source')]))
            continue
        if source_index is None:
            note='90 seconds. Separate component evidence from policy selection. For the August request, the baseline is 5 July. The transition model learns organizational patterns from all available snapshots strictly before July: January, March, April, May and June. It then identifies Black Pearl practices that improved when its July baseline is compared separately with its May and June snapshots. These are two comparisons, not two separate transition paths. A practice improved in either comparison enters one deduplicated set, and each practice contributes once as a trigger for learned successor patterns. Similarity matches the July target profile to peer states before July and observes up to two subsequent peer snapshots, never beyond July. Historical popularity also counts improvements strictly before July; the selected policy assigns zero share to the recent-popularity component. One cross-team policy is selected per prediction month and shared by all teams for that month; it is not fitted separately for Black Pearl. May only refers to selecting those global settings: replay recommendations for May across teams using the history available for those May cases, score candidate policies against May, June and July outcomes, and choose the best policy. August scoring then applies that policy to the richer history available for August. May is the first prediction cohort because the implementation starts at the fourth recorded global snapshot; January, March and April supply initial history. June and July prediction cohorts do not yet have complete outcomes before August. These are recorded-snapshot windows, not fixed calendar durations.'
            source='src/ml/policy.py: prediction_months, completed_prior_months, _peer_contribution, _month_popularity, _compute_components and select_policy; src/ml/sequences.py: learn_sequences_up_to_month'
            story.append(KeepTogether([para(f'{i:02d}. {escape(title)}','head'),para(escape(shifted_refs(note))),para('Sources: '+escape(source),'source')]))
            continue
        slide=CONTENT['slides'][source_index]
        prior_i=i if i<6 else i-1
        old_i=((prior_i if prior_i<3 else prior_i+1) if prior_i<8 else prior_i-1) if prior_i<16 else source_index+1
        note=replacements.get(old_i,slide['notes'])
        note=note.replace('Slides 8 and 11','Slides 7 and 12').replace('slide 10.', 'slide 11.')
        note=note.replace('Keep detailed cleaning and missing-value questions for backup slide E.', 'Discuss detailed cleaning and missing-value questions using the project report.').replace('backup F','the presenter demonstration instructions')
        source=slide['source']
        if old_i in (3,22):
            source='Choi et al. (2022), doi:10.1002/9781119821779.ch1; Raza et al. (2017), doi:10.1145/3084100.3084365; submission/xp2027/LITERATURE_REVIEW.md (bounded scoping review); docs/PROJECT_DOCUMENTATION.md, sections 1-3 and 6'
        if old_i==17:
            note+=' A policy is a configuration of the scoring blend, not a separate model. Peer count is a maximum: after applying the minimum cosine threshold and deduplicating by team, take up to 5, 10 or 19 peers. A zero threshold imposes no positive similarity floor; 0.75 requires cosine similarity of at least 0.75. Component weights are ordered similarity, transitions and popularity. Each is 0, 25, 50, 75 or 100 percent; exactly 15 triples sum to 100 percent. For example, 25/25/50 gives popularity half the final score. Recent share is a separate inner weight within popularity: historical share is 100 percent minus recent share. Thus 25 percent recent means 75 percent historical; it is not a fourth outer component weight. The historical and recent inputs are normalized scores, not unscaled counts. Multiply the four option counts to obtain 675 configurations. They are evaluated on the same fixed outcome-bearing cases in completed prior prediction months; the selected policy maximizes mean monthly Conditional Hit Rate@2. The 5/10/19 values are the configured search choices; do not claim that their optimality was established. The component windows remain fixed at two recorded snapshots and are not searched.'
        if old_i==4:
            source='PROJECT_DOCUMENTATION.pdf, Executive Summary, pages 5-7; docs/PROJECT_DOCUMENTATION.md, sections 1.2, 3.5 and 4.3'
        if old_i==12:
            source='PROJECT_DOCUMENTATION.pdf, Executive Summary, pages 6-7; docs/PROJECT_DOCUMENTATION.md, sections 6.3 and 7.3'
        if old_i==5:
            source='docs/PROJECT_DOCUMENTATION.md, sections 3.3-3.5 and 6.5'
        if old_i==5:
            note+=' Define popularity as the frequency of recorded practice maturity increases across teams, rather than current high maturity or the number of teams using a practice. Historical counts summarize earlier organizational improvement events; recent counts summarize the latest observed interval. Each count vector is normalized under the component-specific rules before blending. A historical/recent balance is selected using completed earlier outcomes. The balance can assign all weight to history, as in the August worked example.'
        if old_i==11:
            note+=' Explain the standalone comparison before reading the bars: time-aware popularity ranks eligible practices using only organizational improvement counts, balancing historical and recent evidence. It uses no peer similarity or practice-transition score. Its historical/recent balance is selected independently from completed prior outcomes under the same walk-forward rules as the adaptive blend. It is not necessarily the popularity component configuration chosen inside the blend. This controls for how much of the result can be achieved simply by recommending practices that commonly improved across the organization.'
        if old_i==11:
            note+=' Adjustable emphasis means that recent improvements do not automatically receive more weight. For example, a policy can combine 25% normalized historical score with 75% normalized recent score, giving recent evidence greater influence. The independent popularity comparison selects this weighting from completed earlier outcomes. In the Black Pearl August example, the popularity component inside the selected blend instead uses 100% historical and 0% recent. Avoid implying that this example necessarily shares the independently selected comparison policy. Recent refers to improvements over the latest recorded interval, not simply a practice having a recent assessment date.'
        if old_i==6:
            note+=' Distinguish units explicitly: 654 is the number of unique observed team-date snapshots, not the number of evaluated predictions. A prediction case is one team at one prediction date, supported by an earlier baseline and up to three later observations. For example, the July baseline and August, September and October outcomes support one Black Pearl August case; some of those snapshots also support other cases. The 298 cases are eligible May-September predictions with all three follow-up snapshots, not 298 different teams or 298 source rows. Source scores are 0-3 and normalized to 0-1. The observations come from one organization and do not record attempted practices.'
        if old_i==6:
            note+=' Explain the timeline: the first three recorded global snapshots, January, March and April, are reserved for initial history. Evaluation starts at the fourth snapshot, May, whose latest earlier assessment is April. This warm-up period is a design choice; we did not experimentally optimize its length. It is not a universal mathematical minimum for all components. February is absent from the source data. May through September are the five primary prediction months because their three-snapshot follow-up fits within the dataset ending in November. October and November are shown as remaining follow-up for that primary analysis; predictions for those two months are also reported separately as sensitivity cases with truncated global outcome windows. A snapshot can support multiple prediction cases.'
        if old_i==9:
            note+=' Explain the documented rationale in report section 3.6: practice maturity improvements can take time to appear, so outcomes are checked across three recorded snapshots rather than only the first follow-up. Section 6.3 explains that policy selection waits until the complete outcome window of an earlier prediction month has closed; this prevents choosing settings using future outcomes. May is the first evaluated prediction month. Its outcomes are May, June and July, so they can first inform policy selection for August. Therefore May, June and July use the default bootstrap policy, 100% popularity with a 50/50 historical/recent split. The three bootstrap prediction months follow from the outcome-window rule; they were not selected independently. Distinguish this from the initial January/March/April history warm-up. The documentation supplies a qualitative adoption-timeline rationale, not an empirical comparison proving that three snapshots is optimal. Neither the warm-up length nor the outcome-window length was optimized. Do not claim a universal three-month adoption duration; the unit is recorded snapshots.'
        if old_i==10:
            note+=' Without improvement means that no eligible practice has a recorded maturity increase above baseline in any of the three later snapshots. Scores may remain unchanged or decrease. This does not establish that the team attempted and failed a practice or that a recommendation failed; the historical teams did not receive these recommendations, and attempted practices were not recorded. The partition is 120 plus 178 equals 298. The hit-rate cohort separately adds one improvement-bearing case with partial follow-up to reach 121.'
        if old_i==6:
            source='docs/PROJECT_DOCUMENTATION.md, sections 3.2, 5.5 and 6.1'
        if old_i==7:
            source='docs/PROJECT_DOCUMENTATION.md, sections 4.1-4.3, 5.4, 6.5 and 7.3'
        if old_i==8:
            source='docs/PROJECT_DOCUMENTATION.md, section 3.7; data/raw/combined_dataset.xlsx through the standard 90% missingness filter; src/ml/policy.py (case_components, completed_prior_months, select_policy, _selected_peer_indices); src/ml/similarity.py'
        if old_i==14:
            note=note.replace('Backup slides follow and can be opened directly if a question calls for detail.','Use the PDF outline to navigate directly to the relevant backup slide.')
        block=[para(f'{i:02d}. {escape(title)}','head'),para(escape(shifted_refs(note))),para('Sources: '+escape(source),'source')]
        story.append(KeepTogether(block))
    def page_footer(c,doc):
        c.setFont('Arial',9);c.setFillColor(colors.HexColor('#'+GRAY))
        c.drawString(42,27,'Defense preparation · Erez Morabia')
        c.drawRightString(A4[0]-42,27,str(doc.page))
    doc=SimpleDocTemplate(str(OUT/'agile-project-defense-presenter-notes.pdf'),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=39,bottomMargin=44,title='Defense presenter notes',author=CONTENT['author'])
    doc.build(story,onFirstPage=page_footer,onLaterPages=page_footer)


def audit_render():
    import pymupdf
    from PIL import Image
    doc=pymupdf.open(OUT/'agile-project-defense.pdf')
    assert len(doc)==22
    alltext='\n'.join(p.get_text() for p in doc)
    for expected in ['58.0%', '55.7%', '30.6%', '120', '178', '0.726', '675']:
        assert expected in alltext,expected
    bad=[]
    font_names=set()
    for i,p in enumerate(doc,1):
        assert round(p.rect.width)==W and round(p.rect.height)==H
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    font_names.add(span['font'])
                    x0,y0,x1,y1=span['bbox']
                    if x0<0 or y0<0 or x1>W+.5 or y1>H+.5:
                        bad.append(dict(page=i,text=span['text'],bbox=span['bbox']))
        pix=p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
        pix.save(str(QA/f'slide-{i:02d}.png'))
    assert not bad,bad
    thumbs=[]
    for i in range(1,len(doc)+1):
        im=Image.open(QA/f'slide-{i:02d}.png').convert('RGB');im.thumbnail((384,216));thumbs.append(im)
    sheet=Image.new('RGB',(384*4,240*6),'#DDE3E8')
    from PIL import ImageDraw
    draw=ImageDraw.Draw(sheet)
    for i,im in enumerate(thumbs):
        x=(i%4)*384;y=(i//4)*240
        sheet.paste(im,(x,y));draw.text((x+8,y+220),str(i+1),fill='black')
    sheet.save(QA/'montage.png')
    notes=pymupdf.open(OUT/'agile-project-defense-presenter-notes.pdf')
    for i,p in enumerate(notes,1):
        p.get_pixmap(matrix=pymupdf.Matrix(1,1),alpha=False).save(str(QA/f'notes-{i:02d}.png'))
    def luminance(hexcolor):
        c=[int(hexcolor[i:i+2],16)/255 for i in (0,2,4)]
        c=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c]
        return .2126*c[0]+.7152*c[1]+.0722*c[2]
    contrast={c:round(1.05/(luminance(c)+.05),2) for c in [NAVY,TEAL,GRAY]}
    assert min(contrast.values())>=4.5
    used_font_names={span['font'] for page in doc for block in page.get_text('dict')['blocks'] for line in block.get('lines',[]) for span in line['spans']}
    embedded={font[3].split('+')[-1] for page in doc for font in page.get_fonts() if doc.extract_font(font[0])[3]}
    assert used_font_names <= embedded
    assert all(token in ' '.join(doc[3].get_text().split()) for token in ['Collaborative filtering','Practice Transition Model','popularity','Normalize'])
    assert all(token in doc[6].get_text() for token in ['Web interface / API','Recommend action','Run backtest action','PolicyEngine','For each prediction month','For each team','Display results','Evaluate results'])
    assert 'Find current state' in doc[7].get_text() and 'Returned recommendations' not in doc[7].get_text()
    assert all(token in doc[9].get_text() for token in ['0.750','0.726','0.513','Scrum Master','Tech debt strategy'])
    assert all(token in doc[8].get_text() for token in ['January-June','July scores','May and June','Monthly policy','all teams'])
    assert all(token in doc[12].get_text() for token in ['58.0%','55.7%','30.6%'])
    assert all(token in doc[21].get_text() for token in ['_compute_components','src/ml/policy.py:335','CaseComponents'])
    assert any(link.get('uri','').endswith('src/ml/policy.py#L335') for link in doc[21].get_links())
    assert all(token in doc[20].get_text() for token in ['ACM','0.913998','2/6 + 1/1','15 improvement events'])
    assert all(token in doc[19].get_text() for token in ['0.3047','0.5944','1.333','14 events','15 events'])
    assert all(token in doc[5].get_text() for token in ['Web interface','API layer','ML engine','Validation engine','Backtest past predictions','Data module'])
    report=dict(slide_pages=len(doc),notes_pages=len(notes),page_size_points=[W,H],embedded_fonts=sorted(font_names),out_of_bounds_text=bad,all_used_fonts_embedded=used_font_names <= embedded,verified_diagram_slides=[3,4,6,7],contrast_on_white=contrast,research=RESEARCH)
    (QA/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    QA.mkdir(parents=True,exist_ok=True)
    titles=make_slides()
    make_presenter(titles)
    audit_render()

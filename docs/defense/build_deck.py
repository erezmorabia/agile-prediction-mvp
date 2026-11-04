"""Build the defense deck from content.json using dependency-free Office Open XML.

The native artifact service was unavailable during authoring. This fallback keeps
text, tables, charts and notes editable without installing substitute libraries.
Run: python3 docs/defense/build_deck.py
"""

import html
import io
import json
import textwrap
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "content.json").read_text())
OUT = ROOT
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
BG, INK, TEAL, GRAY, RULE = "F7F7F2", "173740", "087F83", "52656A", "D5DEDB"
EMU = 9525


def rels(items):
    return XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(
        f'<Relationship Id="{rid}" Type="{R}/{kind}" Target="{target}"/>' for rid, kind, target in items
    ) + '</Relationships>'


def para(text, px=26, color=INK, bold=False):
    return '<a:p><a:pPr algn="l"/><a:r><a:rPr lang="en-US" sz="%s" b="%s"><a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:latin typeface="Arial"/><a:ea typeface="Arial"/><a:cs typeface="Arial"/></a:rPr><a:t xml:space="preserve">%s</a:t></a:r><a:endParaRPr lang="en-US"/></a:p>' % (round(px * 75), int(bold), color, escape(str(text)))


def text_shape(sid, text, x, y, w, h, px=26, color=INK, bold=False):
    return f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="Text {sid}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="{round(x*EMU)}" y="{round(y*EMU)}"/><a:ext cx="{round(w*EMU)}" cy="{round(h*EMU)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0" anchor="t"/><a:lstStyle/>' + ''.join(para(t, px, color, bold) for t in text.split('\n')) + '</p:txBody></p:sp>'


def group_header():
    return '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'


def native_table(sid, values, x, y, widths, row_h, px=24):
    rows = []
    for ri, row in enumerate(values):
        cells = []
        for ci, value in enumerate(row):
            color = BG if ri == 0 else INK
            fill = INK if ri == 0 else ("FFFFFF" if ri % 2 else "EDF1EC")
            cells.append('<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>' + para(value, px, color, ri == 0) + f'</a:txBody><a:tcPr marL="{12*EMU}" marR="{12*EMU}" marT="{10*EMU}" marB="{8*EMU}" anchor="ctr"><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill></a:tcPr></a:tc>')
        rows.append(f'<a:tr h="{round(row_h*EMU)}">' + ''.join(cells) + '</a:tr>')
    return f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="Evidence table"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr><p:xfrm><a:off x="{x*EMU}" y="{y*EMU}"/><a:ext cx="{sum(widths)*EMU}" cy="{round(len(values)*row_h*EMU)}"/></p:xfrm><a:graphic><a:graphicData uri="{A}/table"><a:tbl><a:tblPr firstRow="1" bandRow="1"/><a:tblGrid>' + ''.join(f'<a:gridCol w="{w*EMU}"/>' for w in widths) + '</a:tblGrid>' + ''.join(rows) + '</a:tbl></a:graphicData></a:graphic></p:graphicFrame>'


def layout(slide, index):
    """A shared layout drives both native Office objects and the browser preview."""
    objs = []

    def txt(text, x, y, w, h, px=26, color=INK, bold=False):
        objs.append(dict(type="text", text=text, x=x, y=y, w=w, h=h, px=px, color=color, bold=bold))

    if slide.get("kind") == "cover":
        txt("Identifying Likely Large-Scale\nAgile Implementation Pathways", 64, 130, 1145, 230, 57, INK, True)
        txt(slide["subtitle"], 68, 425, 1110, 180, 25, GRAY)
        return objs
    txt(slide["title"], 64, 42, 1152, 100, 44, INK, True)
    if slide.get("lead"):
        txt(slide["lead"], 66, 153, 1146, 82, 29, TEAL, True)
    start = 258 if slide.get("lead") else 183
    if slide.get("kind") == "data":
        for col, (num, label) in enumerate(slide["stats"]):
            txt(num, 66+col*385, 159, 320, 80, 66, TEAL, True)
            txt(label, 67+col*385, 237, 320, 43, 24, GRAY)
        start = 304
    if slide.get("rows"):
        gap = 73 if slide.get("kind") == "data" else 86
        if len(slide["rows"]) == 3:
            gap = 107
        for n, (label, body) in enumerate(slide["rows"]):
            txt(label, 66, start+n*gap, 279, gap-12, 25, TEAL, True)
            txt(body, 365, start+n*gap, 842, gap-12, 26, INK)
    if slide.get("table"):
        values = slide["table"]
        count = len(values[0])
        if slide.get("kind") == "example":
            widths, rh, y, px = [400, 220, 230, 302], 89, 273, 25
        elif count == 5:
            widths, rh, y, px = [230, 105, 175, 190, 452], 49, 182, 22
        elif count == 3:
            widths, rh, y, px = [220, 485, 447], 99, 193, 24
        else:
            widths, rh, y, px = [330, 822], 70 if slide.get("lead") else 77, 238 if slide.get("lead") else 191, 24
        objs.append(dict(type="table", values=values, x=64, y=y, widths=widths, rh=rh, px=px))
    if slide.get("chart"):
        objs.append(dict(type="chart", x=92, y=255, w=1090, h=333, **slide["chart"]))
    if slide.get("bottom"):
        txt(slide["bottom"], 66, 623, 1140, 61, 23, GRAY)
    txt(f'{"Backup" if slide.get("backup") else "Defense"}   {index+1:02d}', 1050, 692, 166, 20, 13, GRAY)
    return objs


def workbook_bytes(categories, values):
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
        z.writestr('_rels/.rels', rels([('rId1','officeDocument','xl/workbook.xml')]))
        z.writestr('xl/workbook.xml', XML + f'<workbook xmlns="{ns}" xmlns:r="{R}"><sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', rels([('rId1','worksheet','worksheets/sheet1.xml')]))
        rows = ['<row r="1"><c r="A1" t="inlineStr"><is><t>Method</t></is></c><c r="B1" t="inlineStr"><is><t>Conditional Hit Rate@2</t></is></c></row>']
        for i,(cat,val) in enumerate(zip(categories,values), 2):
            rows.append(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{escape(cat)}</t></is></c><c r="B{i}"><v>{val}</v></c></row>')
        z.writestr('xl/worksheets/sheet1.xml', XML+f'<worksheet xmlns="{ns}"><sheetData>'+''.join(rows)+'</sheetData></worksheet>')
    return mem.getvalue()


def chart_xml(obj):
    cats, vals = obj['categories'],obj['values']
    cat_cache = ''.join(f'<c:pt idx="{i}"><c:v>{escape(v)}</c:v></c:pt>' for i,v in enumerate(cats))
    val_cache = ''.join(f'<c:pt idx="{i}"><c:v>{v}</c:v></c:pt>' for i,v in enumerate(vals))
    points = ''.join(f'<c:dPt><c:idx val="{i}"/><c:spPr><a:solidFill><a:srgbClr val="{col}"/></a:solidFill><a:ln><a:noFill/></a:ln></c:spPr></c:dPt>' for i,col in enumerate(["A9B7B7","6B8D96",TEAL]))
    tx = f'<c:txPr><a:bodyPr/><a:lstStyle/><a:p><a:pPr><a:defRPr sz="1800"><a:solidFill><a:srgbClr val="{INK}"/></a:solidFill><a:latin typeface="Arial"/></a:defRPr></a:pPr><a:endParaRPr lang="en-US"/></a:p></c:txPr>'
    return XML+f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}" xmlns:r="{R}"><c:lang val="en-US"/><c:chart><c:autoTitleDeleted val="1"/><c:plotArea><c:layout/><c:barChart><c:barDir val="col"/><c:grouping val="clustered"/><c:varyColors val="1"/><c:ser><c:idx val="0"/><c:order val="0"/><c:tx><c:v>Conditional Hit Rate@2</c:v></c:tx>{points}<c:cat><c:strRef><c:f>Results!$A$2:$A$4</c:f><c:strCache><c:ptCount val="3"/>{cat_cache}</c:strCache></c:strRef></c:cat><c:val><c:numRef><c:f>Results!$B$2:$B$4</c:f><c:numCache><c:formatCode>0.0%</c:formatCode><c:ptCount val="3"/>{val_cache}</c:numCache></c:numRef></c:val></c:ser><c:dLbls><c:numFmt formatCode="0.0%" sourceLinked="0"/>{tx}<c:dLblPos val="outEnd"/><c:showLegendKey val="0"/><c:showVal val="1"/><c:showCatName val="0"/><c:showSerName val="0"/></c:dLbls><c:gapWidth val="95"/><c:axId val="100"/><c:axId val="200"/></c:barChart><c:catAx><c:axId val="100"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:axPos val="b"/><c:tickLblPos val="nextTo"/>{tx}<c:crossAx val="200"/><c:crosses val="autoZero"/></c:catAx><c:valAx><c:axId val="200"/><c:scaling><c:orientation val="minMax"/><c:max val="1"/><c:min val="0"/></c:scaling><c:axPos val="l"/><c:majorGridlines/><c:numFmt formatCode="0%" sourceLinked="0"/><c:tickLblPos val="nextTo"/>{tx}<c:crossAx val="100"/><c:crosses val="autoZero"/><c:majorUnit val="0.25"/></c:valAx></c:plotArea><c:plotVisOnly val="1"/></c:chart><c:spPr><a:noFill/><a:ln><a:noFill/></a:ln></c:spPr>{tx}<c:externalData r:id="rId1"><c:autoUpdate val="0"/></c:externalData></c:chartSpace>'


def build_pptx():
    parts = {}
    def put(name, payload):
        parts[name] = payload
    put('_rels/.rels', rels([('rId1','officeDocument','ppt/presentation.xml')]))
    ids = ''.join(f'<p:sldId id="{256+i}" r:id="rId{i+2}"/>' for i in range(len(DATA['slides'])))
    put('ppt/presentation.xml',XML+f'<p:presentation xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:notesMasterIdLst><p:notesMasterId r:id="rId30"/></p:notesMasterIdLst><p:sldIdLst>{ids}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>')
    put('ppt/_rels/presentation.xml.rels',rels([('rId1','slideMaster','slideMasters/slideMaster1.xml'),('rId30','notesMaster','notesMasters/notesMaster1.xml')]+[(f'rId{i+2}','slide',f'slides/slide{i+1}.xml') for i in range(len(DATA['slides']))]))
    empty_tree = '<p:spTree>'+group_header()+'</p:spTree>'
    mapping = '<p:clrMap accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" bg1="lt1" bg2="lt2" folHlink="folHlink" hlink="hlink" tx1="dk1" tx2="dk2"/>'
    put('ppt/slideMasters/slideMaster1.xml',XML+f'<p:sldMaster xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:cSld>{empty_tree}</p:cSld>{mapping}<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst><p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>')
    put('ppt/slideMasters/_rels/slideMaster1.xml.rels',rels([('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','theme','../theme/theme1.xml')]))
    put('ppt/slideLayouts/slideLayout1.xml',XML+f'<p:sldLayout xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}" type="blank" preserve="1"><p:cSld name="Blank">{empty_tree}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    put('ppt/slideLayouts/_rels/slideLayout1.xml.rels',rels([('rId1','slideMaster','../slideMasters/slideMaster1.xml')]))
    put('ppt/notesMasters/notesMaster1.xml', XML+f'<p:notesMaster xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:cSld>{empty_tree}</p:cSld>{mapping}<p:notesStyle/></p:notesMaster>')
    put('ppt/notesMasters/_rels/notesMaster1.xml.rels',rels([('rId1','theme','../theme/theme1.xml')]))
    colors = [('dk1',INK),('lt1',BG),('dk2',GRAY),('lt2','FFFFFF'),('accent1',TEAL),('accent2','6B8D96'),('accent3','A9B7B7'),('accent4','B97945'),('accent5','83A390'),('accent6','527F94'),('hlink',TEAL),('folHlink','527F94')]
    color_scheme = ''.join(f'<a:{n}><a:srgbClr val="{v}"/></a:{n}>' for n,v in colors)
    fonts = '<a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
    fills = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'*3
    lines = '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>'*3
    put('ppt/theme/theme1.xml', XML+f'<a:theme xmlns:a="{A}" name="Academic"><a:themeElements><a:clrScheme name="Academic">{color_scheme}</a:clrScheme>{fonts}<a:fmtScheme name="Academic"><a:fillStyleLst>{fills}</a:fillStyleLst><a:lnStyleLst>{lines}</a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst>{fills}</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')
    for i,slide in enumerate(DATA['slides'],1):
        objects = []
        links = [('rId1','slideLayout','../slideLayouts/slideLayout1.xml'),('rId2','notesSlide',f'../notesSlides/notesSlide{i}.xml')]
        for sid,obj in enumerate(layout(slide,i-1),2):
            if obj['type']=='text':
                objects.append(text_shape(sid,obj['text'],obj['x'],obj['y'],obj['w'],obj['h'],obj['px'],obj['color'],obj['bold']))
            elif obj['type']=='table':
                objects.append(native_table(sid,obj['values'],obj['x'],obj['y'],obj['widths'],obj['rh'],obj['px']))
            else:
                links.append(('rId3','chart','../charts/chart1.xml'))
                objects.append(f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="Primary results chart"/><p:cNvGraphicFramePr/><p:nvPr/></p:nvGraphicFramePr><p:xfrm><a:off x="{obj["x"]*EMU}" y="{obj["y"]*EMU}"/><a:ext cx="{obj["w"]*EMU}" cy="{obj["h"]*EMU}"/></p:xfrm><a:graphic><a:graphicData uri="{C}"><c:chart xmlns:c="{C}" r:id="rId3"/></a:graphicData></a:graphic></p:graphicFrame>')
                put('ppt/charts/chart1.xml',chart_xml(obj))
                put('ppt/charts/_rels/chart1.xml.rels',rels([('rId1','package','../embeddings/results.xlsx')]))
                put('ppt/embeddings/results.xlsx',workbook_bytes(obj['categories'],obj['values']))
        put(f'ppt/slides/slide{i}.xml',XML+f'<p:sld xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"'+(' show="0"' if slide.get('backup') else '')+f'><p:cSld name="{escape(slide["title"], {chr(34): "&quot;"})}"><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{BG}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg><p:spTree>'+group_header()+''.join(objects)+'</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
        put(f'ppt/slides/_rels/slide{i}.xml.rels',rels(links))
        note_text = slide['notes']+'\n\nSources: '+slide['source']
        note_shape = '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Speaker notes"/><p:cNvSpPr/><p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr><p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'+''.join(para(p,16) for p in note_text.split('\n'))+'</p:txBody></p:sp>'
        put(f'ppt/notesSlides/notesSlide{i}.xml',XML+f'<p:notes xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:cSld><p:spTree>'+group_header()+note_shape+'</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>')
        put(f'ppt/notesSlides/_rels/notesSlide{i}.xml.rels',rels([('rId1','notesMaster','../notesMasters/notesMaster1.xml'),('rId2','slide',f'../slides/slide{i}.xml')]))
    types = {'presentation':'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml','slide':'application/vnd.openxmlformats-officedocument.presentationml.slide+xml','slideMaster':'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml','slideLayout':'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml','notesSlide':'application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml','notesMaster':'application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml','theme':'application/vnd.openxmlformats-officedocument.theme+xml','chart':'application/vnd.openxmlformats-officedocument.drawingml.chart+xml'}
    overrides=[]
    for name in parts:
        if name.endswith('.xml') and not name.startswith('_rels'):
            parent=Path(name).parent.name
            kind={'slides':'slide','slideMasters':'slideMaster','slideLayouts':'slideLayout','notesSlides':'notesSlide','notesMasters':'notesMaster','charts':'chart','theme':'theme'}.get(parent,'presentation')
            overrides.append(f'<Override PartName="/{name}" ContentType="{types[kind]}"/>')
    put('[Content_Types].xml',XML+'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="xlsx" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"/>'+''.join(overrides)+'</Types>')
    with zipfile.ZipFile(OUT/'agile-project-defense.pptx','w',zipfile.ZIP_DEFLATED) as z:
        for name,payload in parts.items():
            z.writestr(name,payload)


def build_html():
    pages=[]
    for i,slide in enumerate(DATA['slides']):
        elements=[]
        for obj in layout(slide,i):
            if obj['type']=='text':
                css=f'left:{obj["x"]}px;top:{obj["y"]}px;width:{obj["w"]}px;height:{obj["h"]}px;font-size:{obj["px"]}px;color:#{obj["color"]};font-weight:{700 if obj["bold"] else 400}'
                elements.append(f'<div class="txt" style="{css}">{html.escape(obj["text"])}</div>')
            elif obj['type']=='table':
                rows=''.join('<tr>'+''.join(f'<{"th" if ri==0 else "td"}>{html.escape(str(v))}</{"th" if ri==0 else "td"}>' for v in row)+'</tr>' for ri,row in enumerate(obj['values']))
                cols=''.join(f'<col style="width:{w}px">' for w in obj['widths'])
                elements.append(f'<table style="left:{obj["x"]}px;top:{obj["y"]}px;width:{sum(obj["widths"])}px;font-size:{obj["px"]}px;--rh:{obj["rh"]}px"><colgroup>{cols}</colgroup>{rows}</table>')
            else:
                # A preview of the same native column-chart evidence in the PPTX.
                bars=''.join(f'<div class="barcol"><div class="bar" style="height:{v*240}px;background:#{col}"><b>{v:.1%}</b></div><span>{html.escape(cat)}</span></div>' for cat,v,col in zip(obj['categories'],obj['values'],['A9B7B7','6B8D96',TEAL]))
                elements.append(f'<div class="chart" style="left:{obj["x"]}px;top:{obj["y"]}px;width:{obj["w"]}px;height:{obj["h"]}px"><div class="scale">100%<br>75%<br>50%<br>25%<br>0%</div><div class="bars">{bars}</div></div>')
        pages.append(f'<section class="slide" data-backup="{str(bool(slide.get("backup"))).lower()}" id="slide-{i+1}">'+''.join(elements)+f'<aside><strong>Speaker notes</strong><p>{html.escape(slide["notes"])}</p><small>Sources: {html.escape(slide["source"])}</small></aside></section>')
    template='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Agile Project Defense</title><style>
*{box-sizing:border-box}body{margin:0;background:#173740;color:#173740;font-family:Arial,sans-serif}.slide{display:none;position:relative;width:1280px;height:720px;background:#F7F7F2;transform-origin:top left}.slide.active{display:block}.txt{position:absolute;white-space:pre-wrap;line-height:1.18}table{position:absolute;border-collapse:collapse;table-layout:fixed}tr{height:var(--rh)}th,td{text-align:left;vertical-align:middle;padding:10px 12px;line-height:1.18;overflow-wrap:normal}th{background:#173740;color:#F7F7F2;font-weight:700}td{background:#FFFFFF}tr:nth-child(odd) td{background:#EDF1EC}.chart{position:absolute;display:flex;padding:0 20px 45px 0}.scale{width:75px;font-size:20px;text-align:right;line-height:60px;margin-top:-30px;color:#52656A}.bars{display:flex;align-items:flex-end;justify-content:space-around;width:100%;height:240px;border-bottom:1px solid #A9B7B7;background:repeating-linear-gradient(to top,transparent 0,transparent 59px,#D5DEDB 59px,#D5DEDB 60px)}.barcol{width:28%;height:240px;display:flex;align-items:center;justify-content:flex-end;flex-direction:column;position:relative}.bar{width:72%;position:relative}.bar b{display:block;position:absolute;top:-35px;width:100%;text-align:center;font-size:28px}.barcol span{position:absolute;top:257px;left:-15%;width:130%;text-align:center;font-size:23px}aside{display:none;position:absolute;top:730px;left:0;width:1280px;padding:30px 64px;background:#fff;font-size:24px;line-height:1.5}body.notes aside{display:block}nav{position:fixed;bottom:8px;left:12px;color:#fff;font-size:13px;z-index:10;opacity:.85}nav button{color:white;border:1px solid #6B8D96;background:#173740;margin-right:8px;padding:6px 12px;cursor:pointer}#index{display:none;position:fixed;inset:20px;background:white;overflow:auto;z-index:20;padding:25px;columns:2}#index a{display:block;break-inside:avoid;color:#173740;margin:0 0 12px;line-height:1.4;font-size:18px}@media print{body{background:white}.slide,.slide.active{display:block!important;transform:none!important;page-break-after:always;break-after:page}aside,nav,#index{display:none!important}@page{size:1280px 720px;margin:0}}
</style><main>SLIDES</main><nav><button onclick="move(-1)">Previous</button><button onclick="move(1)">Next</button><button onclick="toggleNotes()">Notes (N)</button><button onclick="toggleIndex()">All slides (G)</button><span id="status"></span></nav><div id="index"></div><script>
const slides=[...document.querySelectorAll('.slide')];let current=0;function resize(){let s=Math.min(innerWidth/1280,(innerHeight-42)/720);slides.forEach(el=>el.style.transform=`scale(${s})`)}function show(n){current=Math.max(0,Math.min(slides.length-1,n));slides.forEach((s,i)=>s.classList.toggle('active',i===current));document.querySelector('#status').textContent=`${current+1} / ${slides.length}${slides[current].dataset.backup==='true'?' · Backup':''}`;history.replaceState(null,'',`#slide-${current+1}`);resize()}function move(d){show(current+d)}function toggleNotes(){document.body.classList.toggle('notes');resize()}function toggleIndex(){const e=document.querySelector('#index');e.style.display=e.style.display==='block'?'none':'block'}document.querySelector('#index').innerHTML=slides.map((s,i)=>`<a href="#slide-${i+1}" onclick="show(${i});toggleIndex();return false">${i+1}. ${s.querySelector('.txt').textContent}</a>`).join('');document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();move(1)}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();move(-1)}if(e.key.toLowerCase()==='n')toggleNotes();if(e.key.toLowerCase()==='g')toggleIndex();if(e.key==='Home')show(0);if(e.key==='End')show(slides.length-1)});addEventListener('resize',resize);show(Number(location.hash.replace('#slide-',''))-1||0);
</script></html>'''
    (OUT/'agile-project-defense.html').write_text(template.replace('SLIDES',''.join(pages)))


if __name__=='__main__':
    build_pptx()
    build_html()
    print(f'Built {len(DATA["slides"])} slides in {OUT}')

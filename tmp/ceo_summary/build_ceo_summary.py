from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path('/Users/sreeharshak/Dev/research-agents')
OUT = ROOT / 'output/pdf/circular_dairy_ceo_summary'
ASSETS = OUT / 'assets'
PDF = OUT / 'ceo_project_summary.pdf'
SCREENSHOT = ASSETS / 'dashboard_overview.png'
SCREENSHOT_BW = ASSETS / 'dashboard_overview_bw.png'

W, H = letter
BLACK = colors.black
DARK = colors.HexColor('#1A1A1A')
GRAY = colors.HexColor('#555555')
LIGHT = colors.HexColor('#D5D5D5')
WHITE = colors.white

REG = 'Times-Roman'
BOLD = 'Times-Bold'


def style(name: str, size: float, leading: float | None = None, font: str = REG, color=DARK) -> ParagraphStyle:
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading or size * 1.25,
                          textColor=color, spaceAfter=0, spaceBefore=0, alignment=0)


BODY = style('body', 8.8, 11.2)
SMALL = style('small', 8.1, 10.2)
CAPTION = style('caption', 7.2, 9.0)


def para(c: canvas.Canvas, text: str, x: float, y_top: float, width: float,
         st: ParagraphStyle, max_height: float = 300) -> float:
    p = Paragraph(text, st)
    _, h = p.wrap(width, max_height)
    p.drawOn(c, x, y_top - h)
    return h


def section(c: canvas.Canvas, number: int, title: str, x: float, y: float, width: float) -> float:
    c.setFont(BOLD, 11)
    c.setFillColor(BLACK)
    c.drawString(x, y, f'{number}. {title}')
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.45)
    c.line(x, y - 4, x + width, y - 4)
    return y - 14


def running_header(c: canvas.Canvas, page: int) -> None:
    c.setStrokeColor(BLACK)
    c.setLineWidth(0.45)
    c.line(42, 761, W - 42, 761)
    c.setFont(REG, 7.5)
    c.setFillColor(GRAY)
    c.drawString(42, 767, 'Strategic Analytics for Circular Dairy Bioeconomy')
    c.drawRightString(W - 42, 767, 'Executive Project Summary')
    c.setFillColor(BLACK)
    c.drawCentredString(W / 2, 23, str(page))


def two_column_section(c: canvas.Canvas, number: int, title: str, body: str,
                       x: float, y: float, width: float) -> float:
    y = section(c, number, title, x, y, width)
    h = para(c, body, x, y, width, BODY)
    return y - h - 8


def draw_framework(c: canvas.Canvas, y: float) -> None:
    boxes = [
        (52, 142, '<b>Farm Definition</b><br/>Herd, land, markets, policies, equipment and operating choices'),
        (235, 142, '<b>Virtual Dairy Farm</b><br/>Thirteen coordinated components<br/>Four circular resource loops'),
        (418, 142, '<b>Decision Evidence</b><br/>Production, resources, health, emissions, economics and assumptions'),
    ]
    for x, w, text in boxes:
        c.setFillColor(WHITE)
        c.setStrokeColor(BLACK)
        c.setLineWidth(0.7)
        c.roundRect(x, y, w, 62, 3, stroke=1, fill=1)
        para(c, text, x + 9, y + 50, w - 18, style(f'box{x}', 7.5, 9.3), 45)
    c.setStrokeColor(BLACK)
    c.setFillColor(BLACK)
    c.setLineWidth(0.8)
    for x1, x2 in [(194, 235), (377, 418)]:
        c.line(x1, y + 31, x2 - 7, y + 31)
        p = c.beginPath()
        p.moveTo(x2, y + 31)
        p.lineTo(x2 - 7, y + 35)
        p.lineTo(x2 - 7, y + 27)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def draw_page_one(c: canvas.Canvas) -> None:
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(BLACK)
    c.setFont(BOLD, 21)
    c.drawCentredString(W / 2, 735, 'Strategic Analytics for a Circular Dairy Bioeconomy')
    c.setFont(REG, 13)
    c.drawCentredString(W / 2, 712, 'A Virtual Farm for Executive Decision Support')
    c.setFont(REG, 9.5)
    c.drawCentredString(W / 2, 695, 'Two-Page Project Summary for Executive Review')
    c.setLineWidth(0.6)
    c.line(42, 684, W - 42, 684)

    abstract = ('<b>Abstract.</b> Dairy farms must evaluate production, animal health, resource use, environmental performance and operating economics as one connected system. This project provides a reproducible virtual dairy farm that allows leadership to compare strategies before field deployment. The current software coordinates thirteen biological, operational, environmental and financial components, represents four circular resource loops, and provides scenario comparison, dashboard analysis and traceable reports. The system is a decision-support foundation rather than a validated financial forecast. Farm-specific calibration and domain review are required before results are used for investment commitments.')
    para(c, abstract, 52, 670, 508, style('abstract', 8.7, 10.8), 85)

    col_w = 244
    left_x, right_x = 52, 316
    executive = ('The project converts a complex dairy operation into a controlled simulation environment. Leadership can define a farm, change operating policies or circular systems, and compare the resulting effects on milk, feed, disease, manure, water, energy, processing, emissions and financial performance. Each run retains its configuration, seed, output history and calibration metadata so that results can be reproduced and reviewed.<br/><br/>The intended business use is to improve the quality and sequence of decisions. The model helps identify interactions, operating constraints and evidence gaps before capital is committed or farm routines are disrupted. It does not assume that every circular technology creates value under every farm condition.')
    y_left = two_column_section(c, 1, 'Executive Summary', executive, left_x, 575, col_w)
    need = ('Circular dairy investments are commonly assessed as separate projects. This can hide dependencies. A manure strategy changes nutrient availability, energy feedstock and emissions. Water treatment affects irrigation and nutrient recovery. Dairy processing changes revenue streams, energy demand and residual materials. Market conditions and animal performance influence all of these outcomes.<br/><br/>A whole-farm decision model allows executives to examine these consequences within one governed scenario. The output is a comparison of modeled alternatives, not a promise of return.')
    two_column_section(c, 2, 'Business Need', need, left_x, y_left, col_w)

    product = ('The current implementation is a day-by-day agent-based model with a browser workbench. It includes cow lifecycle and production, feed and crops, sensors, disease, water, manure, energy, dairy processing, land management, markets, environmental accounting, farm management and genetics.<br/><br/><b>Implemented capabilities</b><br/>- Explicit nutrient, water, energy and dairy by-product loops.<br/>- Optional land, dairy processing and whey-processing configurations.<br/>- Static or observed market scenarios with reproducible uncertainty.<br/>- Executive overview, scenario comparison, circular-flow, cow, environment, economics, equipment and parameter views.<br/>- Daily, monthly and annual reports with exportable data and calibration provenance.')
    two_column_section(c, 3, 'Implemented Product', product, right_x, 575, col_w)

    draw_framework(c, 165)
    para(c, '<b>Figure 1.</b> A governed farm definition is evaluated by the virtual farm and returned as traceable decision evidence.', 52, 154, 508, CAPTION, 24)

    c.setStrokeColor(BLACK)
    c.setLineWidth(0.45)
    c.line(52, 100, 560, 100)
    para(c, '<b>Implementation status.</b> The calibration registry validates and the current automated test suite passes. These checks establish software behavior and reporting contracts. They do not establish scientific or financial validity.', 52, 89, 508, SMALL, 55)
    c.drawCentredString(W / 2, 23, '1')


def prepare_grayscale_screenshot() -> None:
    image = Image.open(SCREENSHOT).convert('RGB')
    image = ImageOps.grayscale(image)
    image = ImageEnhance.Contrast(image).enhance(1.12)
    image.save(SCREENSHOT_BW, optimize=True)


def draw_page_two(c: canvas.Canvas) -> None:
    c.setFillColor(WHITE)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    running_header(c, 2)
    y = section(c, 4, 'Project Deliverable', 42, 738, 528)
    intro = ('The principal deliverable is an operational decision workbench rather than a static report. Executives can configure a scenario, run the same authoritative model used by the command-line workflow, review connected outcomes, compare alternatives and export the supporting evidence.')
    para(c, intro, 42, y, 528, BODY, 45)

    image = Image.open(SCREENSHOT_BW)
    c.drawImage(ImageReader(image), 54, 408, 504, 283.5, preserveAspectRatio=True, mask='auto')
    para(c, '<b>Figure 2.</b> Current product interface showing a thirty-day, one-hundred-cow illustrative run with the four circular loops, processing and land enabled. Displayed values are simulated outputs and are not a forecast.', 54, 400, 504, CAPTION, 28)

    col_w = 250
    left_x, right_x = 42, 320
    outputs = ('<b>Configured virtual farm.</b> A governed baseline representing the partner farm\'s herd, feed, land, market, processing, manure, water and energy conditions. Data sources, assumptions and confidence are recorded.<br/><br/><b>Decision scenario library.</b> Comparable cases for circular-loop combinations, operating policies, market conditions, processing choices and equipment represented by the model.<br/><br/><b>Executive evidence package.</b> Dashboard views, scenario differences, operational and environmental histories, financial outputs, export files and an assumption-aware audit trail.<br/><br/><b>Validation and governance protocol.</b> A calibration checklist, domain-review process, acceptance thresholds and documented rules defining when model results are appropriate for business use.')
    two_column_section(c, 5, 'Required Outputs', outputs, left_x, 354, col_w)

    decisions = ('The product supports four decisions. First, it identifies combinations that merit a controlled field pilot. Second, it exposes cross-system trade-offs instead of optimizing one metric in isolation. Third, it shows where missing or weak evidence prevents a reliable conclusion. Fourth, it creates a consistent record for moving from virtual comparison to limited pilot, measured validation and governed scale-up.')
    y_right = two_column_section(c, 6, 'Executive Decisions Supported', decisions, right_x, 354, col_w)
    value = ('The workbench shortens the path from an idea to an evidence-based pilot. It gives operations, sustainability, finance and technology teams one analytical language. It reveals interactions that single-purpose calculators miss and records what was tested, what changed and why a strategy was selected.<br/><br/>Its immediate value is improved decision discipline. Its longer-term value depends on calibration quality, observed farm data and independent domain review.')
    y_right = two_column_section(c, 7, 'Business Value', value, right_x, y_right, col_w)
    gate = ('The next project gate is a partner-farm calibration exercise. High-impact biological, resource, environmental and financial parameters must be checked against observed data. The calibrated baseline can then rank a focused set of pilot scenarios. No budget is included in this summary.')
    two_column_section(c, 8, 'Decision Gate', gate, right_x, y_right, col_w)


def main() -> None:
    prepare_grayscale_screenshot()
    c = canvas.Canvas(str(PDF), pagesize=letter, pageCompression=1)
    c.setTitle('Strategic Analytics for a Circular Dairy Bioeconomy - Executive Project Summary')
    c.setAuthor('Sreeharsha Kannegundla')
    c.setSubject('Two-page executive project summary based on the current Dairy Farm ABM implementation')
    draw_page_one(c)
    c.showPage()
    draw_page_two(c)
    c.showPage()
    c.save()


if __name__ == '__main__':
    main()

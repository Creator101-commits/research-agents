from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
W, H = 5184, 4032
MAROON = "#500000"
INK = "#202020"
MUTED = "#5f5f5f"
PAPER = "#fbf7f0"
GREEN = "#3b6e5a"
BLUE = "#2f6f8f"
GOLD = "#9a741f"
RULE = "#d8d0c7"
PALE = "#efe2dc"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ITALIC = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"


def f(size: int, bold: bool = False, italic: bool = False):
    path = FONT_BOLD if bold else FONT_ITALIC if italic else FONT
    return ImageFont.truetype(path, size=size)


def wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int):
    lines = []
    for para in text.split("\n"):
        if not para:
            lines.append("")
            continue
        words = para.split()
        line = words[0]
        for word in words[1:]:
            trial = line + " " + word
            if draw.textlength(trial, font=font) <= width:
                line = trial
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def text_block(draw, xy, text, size, width, color=INK, bold=False, italic=False,
               leading=1.24, bullet=False):
    x, y = xy
    ft = f(size, bold, italic)
    line_h = int(size * leading)
    for para in text.split("\n"):
        prefix = "• " if bullet else ""
        indent = int(size * 0.9) if bullet else 0
        lines = wrap(draw, prefix + para, ft, width)
        for i, line in enumerate(lines):
            draw.text((x + (indent if bullet and i > 0 else 0), y), line, font=ft, fill=color)
            y += line_h
        y += int(size * 0.28)
    return y


def section_heading(draw, x, y, width, title, color=MAROON):
    draw.rectangle((x, y, x + width, y + 8), fill=color)
    draw.text((x, y + 26), title, font=f(48, bold=True), fill=color)
    return y + 98


def bullet_list(draw, x, y, width, items, size=31, color=INK, gap=9):
    for item in items:
        y = text_block(draw, (x, y), item, size, width, color=color, leading=1.24, bullet=True)
        y += gap
    return y


def fit_image(path: Path, target_width: int):
    im = Image.open(path).convert("RGB")
    height = round(im.height * target_width / im.width)
    return im.resize((target_width, height), Image.Resampling.LANCZOS)


def main():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)

    d.rectangle((0, 0, W, 675), fill=MAROON)
    title = ("An Agent-Based Virtual Farm Model Evaluating Operating Returns and "
             "Resource Recovery in Circular Dairy Bioeconomy Systems")
    y = text_block(d, (150, 82), title, 112, 4750, color="white", bold=True, leading=1.02)
    d.text((150, y + 12), "Megha Poyyara Saiju¹, Manogna Rayala², Karun Kaniyamattam¹",
           font=f(42, bold=True), fill="white")
    d.text((150, y + 70),
           "¹Department of Animal Science    ²Department of Statistics    Texas A&M University",
           font=f(32), fill="#f1ded7")

    d.rectangle((0, 675, W, 855), fill=PALE)
    d.rectangle((0, 850, W, 855), fill=MAROON)
    takeaway = ("ViCBio DM links cow-level biology to four circular pathways so farm-specific "
                "technology packages can be compared before investment.")
    text_block(d, (150, 716), takeaway, 43, 4800, color=MAROON, bold=True, leading=1.16)

    x1, w1 = 140, 1170
    x2, w2 = 1375, 2450
    x3, w3 = 3890, 1154
    y0 = 920

    y = section_heading(d, x1, y0, w1, "Why this matters")
    stats = [
        ("$52.8B", "U.S. milk sales in 2022"),
        ("-39%", "farms selling milk from 2017 to 2022"),
        ("$43.9B", "specialized dairy production expenses; feed was 46%"),
    ]
    for number, label in stats:
        d.text((x1, y + 8), number, font=f(60, bold=True), fill=MAROON)
        text_block(d, (x1 + 280, y + 10), label, 32, w1 - 300, color=MUTED, leading=1.16)
        d.rectangle((x1, y + 96, x1 + w1, y + 99), fill=RULE)
        y += 118
    y = text_block(d, (x1, y + 7),
                   "Source: USDA NASS, 2022 Census of Agriculture Dairy Cattle and Milk Production.",
                   24, w1, color=MUTED, leading=1.2)

    y = section_heading(d, x1, 1510, w1, "Research question", GOLD)
    question = ("Which combinations of nutrient, water, energy, and by-product pathways improve "
                "farm operating performance and reduce resource losses under the same herd and market assumptions?")
    y = text_block(d, (x1, y), question, 34, w1, bold=True, leading=1.24)
    d.rectangle((x1, y + 8, x1 + 9, y + 198), fill=GOLD)
    text_block(d, (x1 + 28, y + 8),
               "Hypothesis. Coupled pathways will change profit, emissions, and resource use differently "
               "from isolated technology evaluations.",
               32, w1 - 30, leading=1.2)

    y = section_heading(d, x1, 2240, w1, "Model and experiment", GREEN)
    method_items = [
        "Simulate cow-resolved milk, feed, water, manure, methane, health, and reproduction every day.",
        "Coordinate 12 core agents plus an optional land agent through dated data packets.",
        "Switch four circular loops on or off, creating 16 technology configurations.",
        "Hold herd, market, calibration, duration, and seed constant in paired comparisons.",
        "Report operating benefit, CapEx, payback, ROI, emissions, water, and nutrient recovery when inputs are available.",
    ]
    for i, item in enumerate(method_items, 1):
        d.ellipse((x1, y + 2, x1 + 42, y + 44), fill=MAROON)
        d.text((x1 + 21, y + 22), str(i), font=f(25, bold=True), fill="white", anchor="mm")
        y = text_block(d, (x1 + 62, y), item, 32, w1 - 62, leading=1.18)
        y += 8

    y = section_heading(d, x1, 3290, w1, "Daily execution", BLUE)
    daily = ("Market and sensors update first. Feed and management policies prepare the day. Disease, "
             "water delivery, cow production, processing, manure, energy, water accounting, environment, "
             "and farm management then update in sequence.")
    y = text_block(d, (x1, y), daily, 32, w1, leading=1.18)
    text_block(d, (x1, y + 8),
               "A fixed seed uses one seeded random-number generator for deterministic replay.",
               25, w1, color=MUTED, leading=1.2)

    fig1 = fit_image(ROOT / "vicbio_loop_framework.png", 2320)
    im.paste(fig1, (x2 + 65, y0))
    d.rectangle((x2 + 64, y0 - 1, x2 + 65 + fig1.width, y0 + fig1.height), outline=RULE, width=3)
    text_block(d, (x2 + 65, y0 + fig1.height + 17),
               "Figure 1. Each loop exchanges resources with the same virtual farm rather than operating as a stand-alone calculator.",
               24, 2320, color=MUTED, leading=1.2)

    results_y = 2420
    d.text((x2 + 65, results_y), "Illustrative results", font=f(48, bold=True), fill=MAROON)
    d.text((x2 + w2 - 65, results_y + 8), "Model output, not field validation",
           font=f(25), fill=MUTED, anchor="ra")
    fig2 = fit_image(ROOT / "vicbio_illustrative_results.png", 2320)
    fig2_y = results_y + 75
    im.paste(fig2, (x2 + 65, fig2_y))
    d.rectangle((x2 + 64, fig2_y - 1, x2 + 65 + fig2.width, fig2_y + fig2.height), outline=RULE, width=3)
    text_block(d, (x2 + 65, fig2_y + fig2.height + 16),
               "Figure 2. Deterministic 365-day comparison: 100 cows, seed 42, processor and optional land enabled, "
               "identical default market and calibration assumptions. Values are annual model totals or means.",
               23, 2320, color=MUTED, leading=1.17)

    y = section_heading(d, x3, y0, w3, "What the run shows")
    y = bullet_list(d, x3, y, w3, [
        "L3 energy reduced modeled net greenhouse gas by 10.4% and generated 68.2 MWh of electricity.",
        "L4 by-products produced most of the operating-profit change through modeled dairy processing.",
        "L1 and L2 produced no additional top-line change under these default demand conditions.",
        "The combined result equaled L3 + L4, exposing inactive or unconstrained pathways instead of hiding them.",
    ], size=32)

    y = section_heading(d, x3, 1800, w3, "Interpretation and limits", GOLD)
    d.rectangle((x3, y + 3, x3 + 10, y + 238), fill=MAROON)
    y = text_block(d, (x3 + 28, y), "Operating profit is not investment return. Equipment CapEx was not supplied, so ROI and payback are unavailable for this demonstration.",
                   32, w3 - 28, color=MAROON, bold=True, leading=1.18)
    text_block(d, (x3, y + 8),
               "Default calibration includes assumption-marked values. This run is a software demonstration, not empirical validation or a farm investment recommendation.",
               32, w3, leading=1.18)

    y = section_heading(d, x3, 2475, w3, "Conclusion", GREEN)
    text_block(d, (x3, y),
               "Coupled modeling makes cross-loop effects, timing, and unused recovery pathways visible. The framework compares technology packages without treating manure, water, energy, and processing as isolated decisions.",
               32, w3, leading=1.18)

    y = section_heading(d, x3, 2920, w3, "Future work", BLUE)
    bullet_list(d, x3, y, w3, [
        "Calibrate against farm observations.",
        "Add real installed-cost ranges.",
        "Repeat scenarios across seeds.",
        "Validate conventional, robotic, certified organic, raw-milk, and beef-on-dairy systems.",
    ], size=32, gap=2)

    y = section_heading(d, x3, 3355, w3, "References")
    refs = [
        "1. USDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024.",
        "2. Wood, P.D.P. Algebraic model of the lactation curve in cattle. Nature 216, 164-165 (1967). doi:10.1038/216164a0.",
        "3. Muell, J.D. et al. Frontiers in Environmental Science 10:880839 (2022). doi:10.3389/fenvs.2022.880839.",
    ]
    for ref in refs:
        y = text_block(d, (x3, y), ref, 24, w3, leading=1.18)
        y += 4

    d.rectangle((x3, 3865, x3 + w3, 3869), fill=RULE)
    d.text((x3, 3887), "ACKNOWLEDGMENTS", font=f(24, bold=True), fill=MUTED)
    d.text((x3, 3922), "Texas A&M University Departments of Animal Science and Statistics.",
           font=f(24), fill=INK)
    d.text((x3, 3965), "MODEL  github.com/Creator101-commits/research-agents",
           font=f(24, bold=True), fill=MAROON)

    im.save(ROOT / "vicbio_symposium_poster_full.png", quality=95)


if __name__ == "__main__":
    main()

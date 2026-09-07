from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


OUT = Path(__file__).resolve().parent
MAROON = "#500000"
INK = "#222222"
CREAM = "#FBF7F0"
GREEN = "#3B6E5A"
BLUE = "#2F6F8F"
GOLD = "#B58B36"
GRAY = "#6B6B6B"
LIGHT = "#E8E3DD"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def font(size: int, bold: bool = False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT, size=size)


def multiline(draw, xy, text, size, color=INK, bold=False, spacing=8, anchor="la", align="left"):
    draw.multiline_text(xy, text, font=font(size, bold), fill=color,
                        spacing=spacing, anchor=anchor, align=align)


def rounded_box(draw, box, outline, fill="white", radius=28, width=5):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def arrow(draw, start, end, color, width=7):
    import math
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=color, width=width)
    angle = math.atan2(y2-y1, x2-x1)
    length = 24
    points = [(x2, y2)]
    for delta in (2.55, -2.55):
        points.append((x2 + length*math.cos(angle+delta), y2 + length*math.sin(angle+delta)))
    draw.polygon(points, fill=color)


def framework_figure():
    im = Image.new("RGB", (3200, 1800), CREAM)
    d = ImageDraw.Draw(im)
    multiline(d, (110, 110), "One virtual farm, four coupled resource loops", 82, MAROON, True)
    multiline(d, (110, 220),
              "Daily agent interactions connect cow biology, recovered resources, and farm economics.",
              42, GRAY)

    center = (1250, 610, 1950, 1240)
    rounded_box(d, center, MAROON, "#F2E7E4", 45, 9)
    multiline(d, (1600, 735), "VIRTUAL DAIRY FARM", 60, MAROON, True, anchor="ma", align="center")
    multiline(d, (1600, 925),
              "cow-resolved production\n+ daily market, health, and\nmanagement decisions",
              42, INK, spacing=18, anchor="mm", align="center")
    multiline(d, (1600, 1135), "12 core agents + optional land agent", 34, GRAY,
              anchor="mm", align="center")

    boxes = [
        ((120, 520, 1040, 885), "L1  NUTRIENTS",
         "Manure -> compost/digestate\n-> soil and feed-production credits", GREEN),
        ((120, 1015, 1040, 1380), "L2  WATER",
         "Wastewater -> treatment\n-> recycled irrigation", BLUE),
        ((2160, 520, 3080, 885), "L3  ENERGY",
         "Organic feedstock -> biogas\n-> electricity and usable heat", GOLD),
        ((2160, 1015, 3080, 1380), "L4  BY-PRODUCTS",
         "Milk processing -> products,\nwhey feed, and residual recovery", MAROON),
    ]
    for box, title, body, color in boxes:
        rounded_box(d, box, color, "white", 34, 6)
        multiline(d, (box[0]+50, box[1]+72), title, 51, color, True)
        multiline(d, (box[0]+50, box[1]+185), body, 38, INK, spacing=15)

    arrow(d, (1250, 790), (1045, 720), GREEN)
    arrow(d, (1045, 795), (1250, 980), GREEN)
    arrow(d, (1250, 1060), (1045, 1180), BLUE)
    arrow(d, (1045, 1280), (1250, 1160), BLUE)
    arrow(d, (1950, 790), (2155, 720), GOLD)
    arrow(d, (2155, 795), (1950, 980), GOLD)
    arrow(d, (1950, 1060), (2155, 1180), MAROON)
    arrow(d, (2155, 1280), (1950, 1160), MAROON)

    multiline(d, (1600, 1520), "Outputs for each technology package", 45, INK, True,
              anchor="ma", align="center")
    multiline(d, (1600, 1610),
              "annual operating benefit  |  CapEx  |  payback  |  ROI  |  emissions  |  water  |  nutrient recovery",
              36, GRAY, anchor="ma", align="center")
    im.save(OUT / "vicbio_loop_framework.png")


def draw_bar_panel(d, x0, y0, w, title, unit, values, labels, colors, maxval, fmt, show_labels):
    multiline(d, (x0, y0), title, 45, INK, True)
    multiline(d, (x0, y0+62), unit, 29, GRAY)
    bar_left = x0 + (245 if show_labels else 25)
    bar_right = x0 + w - 85
    bar_w = bar_right - bar_left
    row_h = 185
    for i, (label, value, color) in enumerate(zip(labels, values, colors)):
        y = y0 + 145 + i*row_h
        if show_labels:
            multiline(d, (bar_left-28, y+40), label, 30, INK, anchor="ra")
        d.rounded_rectangle((bar_left, y, bar_left + bar_w*value/maxval, y+80),
                            radius=15, fill=color)
        multiline(d, (bar_left + bar_w*value/maxval + 18, y+40), fmt(value), 30, INK, True,
                  anchor="lm")
        d.line((bar_left, y+105, bar_right, y+105), fill=LIGHT, width=2)


def results_figure():
    im = Image.new("RGB", (3200, 1800), "white")
    d = ImageDraw.Draw(im)
    multiline(d, (100, 90), "Illustrative deterministic scenario comparison", 78, MAROON, True)
    multiline(d, (100, 198),
              "100 cows | 365 days | seed 42 | identical market and calibration assumptions",
              38, GRAY)

    labels = ["No loops", "L3 energy", "L4 by-products", "L3 + L4", "All four loops"]
    colors = ["#C8C2BC", GOLD, MAROON, GREEN, BLUE]
    draw_bar_panel(d, 100, 330, 1120, "Operating profit", "$ thousand / year",
                   [42.979, 47.359, 121.246, 125.626, 125.626], labels, colors, 145,
                   lambda v: f"{v:.1f}", True)
    draw_bar_panel(d, 1240, 330, 930, "Net greenhouse gas", "t CO2e / year",
                   [133.523, 119.653, 133.523, 119.653, 119.653], labels, colors, 150,
                   lambda v: f"{v:.1f}", False)
    draw_bar_panel(d, 2190, 330, 910, "Circularity score", "mean, 0 to 1",
                   [0.011, 0.311, 0.211, 0.511, 0.511], labels, colors, 0.60,
                   lambda v: f"{v:.3f}", False)
    multiline(d, (2160, 1385), "lower is better", 26, GRAY, anchor="ra")
    multiline(d, (100, 1480),
              "Interpretation: L3 reduced net GHG by 10.4%; L4 produced most of the operating-profit change.\n"
              "L1 and L2 generated no additional top-line change under these default demand conditions.",
              35, INK, spacing=14)
    multiline(d, (100, 1675),
              "Model output, not field validation. Equipment CapEx was not supplied; ROI and payback remain unavailable.",
              31, MAROON, True)
    im.save(OUT / "vicbio_illustrative_results.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    framework_figure()
    results_figure()

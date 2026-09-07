from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean, median

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import Normalize
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tmp" / "postdoc_poster_v2" / "data"
OUT = ROOT / "output" / "figures" / "poster_visual_revision"

INK = "#202523"
MUTED = "#626965"
GRID = "#D6DAD7"
WHITE = "#FFFFFF"
GREEN = "#347B67"
GREEN_DARK = "#1F5948"
MAROON = "#7A2636"
TEAL = "#2B7484"
GOLD = "#C28A26"
NEUTRAL = "#A8ACA9"

LOOP_COLORS = {
    "L1 nutrient": MAROON,
    "L2 water": TEAL,
    "L3 energy": GOLD,
    "L4 products": GREEN,
}

CONDITION_COLORS = {
    "No loops": NEUTRAL,
    "Nutrient + water": TEAL,
    "Energy": GOLD,
    "Products": GREEN,
    "All loops": GREEN_DARK,
}


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 15,
            "axes.titlesize": 18,
            "axes.titleweight": "bold",
            "axes.labelsize": 15,
            "axes.edgecolor": "#AEB5B1",
            "axes.linewidth": 0.9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": WHITE,
            "savefig.facecolor": WHITE,
        }
    )


def read_rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def add_tier(ax, x: float, y: float, width: float, height: float, label: str, fill: str) -> None:
    tier = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.16",
        facecolor=fill,
        edgecolor="#D4D9D6",
        linewidth=1.2,
        zorder=0,
    )
    ax.add_patch(tier)
    ax.text(x + 0.28, y + height - 0.35, label, fontsize=15, fontweight="bold", color=MUTED, va="top")


def add_node(
    ax,
    x: float,
    y: float,
    width: float,
    height: float,
    label: str,
    loops: tuple[str, ...] = (),
    label_size: float = 16,
) -> None:
    node = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.03,rounding_size=0.13",
        facecolor=WHITE,
        edgecolor="#AEB6B1",
        linewidth=1.25,
        zorder=4,
    )
    ax.add_patch(node)

    if loops:
        segment_width = width / len(loops)
        for index, loop in enumerate(loops):
            ax.add_patch(
                Rectangle(
                    (x + index * segment_width, y + height - 0.12),
                    segment_width,
                    0.12,
                    facecolor=LOOP_COLORS[loop],
                    edgecolor="none",
                    zorder=5,
                )
            )

    label_y = y + height * (0.64 if loops else 0.52)
    ax.text(
        x + width / 2,
        label_y,
        label,
        ha="center",
        va="center",
        fontsize=label_size,
        fontweight="bold",
        color=INK,
        zorder=6,
    )

    if loops:
        gap = 0.10
        chip_widths = [0.54 + 0.033 * len(loop) for loop in loops]
        total_width = sum(chip_widths) + gap * (len(loops) - 1)
        current_x = x + (width - total_width) / 2
        for loop, chip_width in zip(loops, chip_widths, strict=True):
            chip = FancyBboxPatch(
                (current_x, y + 0.15),
                chip_width,
                0.34,
                boxstyle="round,pad=0.02,rounding_size=0.10",
                facecolor=LOOP_COLORS[loop],
                edgecolor="none",
                zorder=6,
            )
            ax.add_patch(chip)
            ax.text(
                current_x + chip_width / 2,
                y + 0.32,
                loop,
                ha="center",
                va="center",
                fontsize=9.7,
                fontweight="bold",
                color=WHITE,
                zorder=7,
            )
            current_x += chip_width + gap


def add_arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = "#7F8984",
    width: float = 1.8,
    curve: float = 0.0,
    dashed: bool = False,
    zorder: int = 2,
) -> None:
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=16,
        linewidth=width,
        color=color,
        linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={curve}",
        shrinkA=3,
        shrinkB=3,
        zorder=zorder,
    )
    ax.add_patch(arrow)


def make_architecture() -> None:
    figure, ax = plt.subplots(figsize=(18, 10.8))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")

    add_tier(ax, 0.25, 0.75, 4.15, 8.55, "INPUTS", "#F5F0E7")
    add_tier(ax, 4.65, 0.75, 6.45, 8.55, "FARM SYSTEM", "#E8F1EC")
    add_tier(ax, 11.35, 0.75, 4.4, 8.55, "OUTPUTS + FEEDBACK", "#E8F1F3")

    # Flow arrows sit below the component boxes.
    add_arrow(ax, (3.95, 7.18), (5.35, 6.75), dashed=True)
    add_arrow(ax, (3.95, 4.90), (5.35, 6.28))
    add_arrow(ax, (7.95, 5.68), (7.95, 4.48))
    add_arrow(ax, (10.35, 3.78), (12.03, 7.46), curve=-0.16)
    add_arrow(ax, (7.95, 3.18), (7.95, 2.52))
    add_arrow(ax, (10.05, 1.75), (11.78, 3.55), curve=-0.12)
    add_arrow(ax, (10.58, 6.54), (12.02, 7.63))
    add_arrow(ax, (13.55, 6.88), (13.55, 6.17))
    add_arrow(ax, (13.55, 5.08), (13.55, 4.55))
    add_arrow(ax, (11.78, 3.50), (3.86, 4.03), color=GREEN, width=2.8, curve=-0.62, zorder=3)

    add_node(ax, 0.72, 6.55, 3.20, 1.28, "Market + sensors", ("L4 products",))
    add_node(ax, 0.62, 4.12, 3.38, 1.60, "Land + feed/crop", ("L1 nutrient", "L2 water"))

    add_node(ax, 5.35, 5.62, 5.22, 2.02, "Individual cows + disease", ("L1 nutrient", "L2 water"), 18)
    add_node(ax, 5.55, 3.18, 4.82, 1.58, "Processing + manure routing", ("L1 nutrient", "L3 energy", "L4 products"), 16)
    add_node(ax, 5.93, 1.08, 4.06, 1.47, "Energy + water accounting", ("L2 water", "L3 energy"), 15.5)

    add_node(ax, 12.03, 7.02, 3.02, 1.39, "Milk + products", ("L4 products",), 16)
    add_node(ax, 11.82, 5.08, 3.46, 1.15, "Profit · GHG · water\n· circularity", (), 14.5)
    add_node(ax, 11.78, 3.02, 3.54, 1.57, "Environment + farm manager", ("L1 nutrient", "L2 water", "L3 energy"), 15)

    ax.text(
        7.9,
        0.25,
        "Recovered resources and management signals return to land and feed decisions",
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=GREEN_DARK,
    )

    figure.savefig(OUT / "architecture_tiered_feedback.png", dpi=300, bbox_inches="tight", pad_inches=0.10)
    figure.savefig(OUT / "architecture_tiered_feedback.svg", bbox_inches="tight", pad_inches=0.10)
    plt.close(figure)


def matrix(records: dict[str, dict[str, str]], metric: str, mode: str) -> np.ndarray:
    baseline = float(records["0000"][metric])
    row_bits = ("00", "10", "01", "11")
    column_bits = ("00", "10", "01", "11")
    values = np.zeros((4, 4))
    for row, prefix in enumerate(row_bits):
        for column, suffix in enumerate(column_bits):
            value = float(records[prefix + suffix][metric])
            if mode == "change":
                values[row, column] = 100 * (value - baseline) / baseline
            elif mode == "reduction":
                values[row, column] = 100 * (baseline - value) / baseline
            else:
                values[row, column] = value
    return values


def annotated_heatmap(
    ax,
    values: np.ndarray,
    title: str,
    formatter,
    cmap,
    norm,
    compact: bool = False,
) -> mpl.image.AxesImage:
    image = ax.imshow(values, cmap=cmap, norm=norm, aspect="auto")
    ax.set_title(title, loc="left", pad=10, color=INK)
    ax.set_xticks(range(4), ["None", "L3", "L4", "L3 + L4"], fontsize=12.5 if compact else 14)
    ax.set_yticks(range(4), ["None", "L1", "L2", "L1 + L2"], fontsize=12.5 if compact else 14)
    ax.tick_params(length=0)
    for row in range(4):
        for column in range(4):
            value = float(values[row, column])
            red, green, blue, _ = image.cmap(image.norm(value))
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            ax.text(
                column,
                row,
                formatter(value),
                ha="center",
                va="center",
                fontsize=12.5 if compact else 14,
                fontweight="bold",
                color=INK if luminance > 0.56 else WHITE,
            )
    for boundary in np.arange(-0.5, 4.5, 1):
        ax.axhline(boundary, color=WHITE, linewidth=2.4)
        ax.axvline(boundary, color=WHITE, linewidth=2.4)
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(3.5, -0.5)
    return image


def make_effects() -> None:
    records = {row["configuration"]: row for row in read_rows("factorial_seed42.csv")}
    baseline_profit = float(records["0000"]["operating_profit"])
    prefixes = ("00", "10", "01", "11")
    suffixes = ("00", "10", "01", "11")
    labels = ["No L3 or L4", "L3 energy", "L4 products", "L3 + L4"]
    colors = [NEUTRAL, GOLD, GREEN, GREEN_DARK]

    profit_groups: list[list[float]] = []
    for suffix in suffixes:
        group = []
        for prefix in prefixes:
            value = float(records[prefix + suffix]["operating_profit"])
            group.append(100 * (value - baseline_profit) / baseline_profit)
        profit_groups.append(group)

    ghg_reduction = matrix(records, "net_kg_co2e", "reduction")
    water_reduction = matrix(records, "freshwater_withdrawal_l", "reduction")
    circularity = matrix(records, "mean_circularity_score", "level")

    figure = plt.figure(figsize=(18, 11), constrained_layout=True)
    grid = figure.add_gridspec(2, 4, width_ratios=[1.34, 1.34, 1.0, 1.0], height_ratios=[1.07, 0.93])
    ax_profit = figure.add_subplot(grid[:, :2])
    ax_ghg = figure.add_subplot(grid[0, 2:])
    ax_water = figure.add_subplot(grid[1, 2])
    ax_circularity = figure.add_subplot(grid[1, 3])

    means = [mean(group) for group in profit_groups]
    lows = [value - min(group) for value, group in zip(means, profit_groups, strict=True)]
    highs = [max(group) - value for value, group in zip(means, profit_groups, strict=True)]
    positions = np.arange(4)
    bars = ax_profit.barh(positions, means, color=colors, height=0.62, edgecolor="none")
    ax_profit.errorbar(means, positions, xerr=np.array([lows, highs]), fmt="none", ecolor=INK, elinewidth=1.7, capsize=5, zorder=4)
    for bar, value in zip(bars, means, strict=True):
        x = bar.get_width()
        value_label = f"{value:+.1f}%" if abs(value) < 1 else f"{value:+.0f}%"
        ax_profit.text(
            x + 4 if x < 180 else x - 4,
            bar.get_y() + bar.get_height() / 2,
            value_label,
            va="center",
            ha="left" if x < 180 else "right",
            fontsize=18,
            fontweight="bold",
            color=INK if x < 180 else WHITE,
        )
    ax_profit.set_yticks(positions, labels, fontsize=15)
    for tick, color in zip(ax_profit.get_yticklabels(), colors, strict=True):
        tick.set_color(color if color != NEUTRAL else MUTED)
        tick.set_fontweight("bold")
    ax_profit.invert_yaxis()
    ax_profit.set_xlim(0, 220)
    ax_profit.set_xlabel(
        "Operating profit change from the no-loop baseline (%)\n"
        "Bars show means; whiskers show the range across L1 and L2 settings."
    )
    ax_profit.set_title("A  Processing drives the profit result", loc="left", pad=12, color=INK)
    ax_profit.grid(axis="x", color=GRID, linewidth=0.9)
    ax_profit.set_axisbelow(True)
    shared_norm = Normalize(vmin=-11, vmax=11)
    shared_cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "red_white_green",
        ["#B2182B", "#FFFFFF", "#1B7837"],
    )
    heat_ghg = annotated_heatmap(
        ax_ghg,
        ghg_reduction,
        "B  Net GHG reduction",
        lambda value: f"{value:+.1f}%",
        shared_cmap,
        shared_norm,
    )
    annotated_heatmap(
        ax_water,
        water_reduction,
        "C  Freshwater reduction",
        lambda value: f"{value:+.1f}%",
        shared_cmap,
        shared_norm,
        compact=True,
    )
    sequential_norm = Normalize(vmin=0, vmax=0.8)
    sequential_cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "white_teal",
        ["#F7FBFA", "#B8DDD6", "#58AFA5", "#126A70"],
    )
    heat_circularity = annotated_heatmap(
        ax_circularity,
        circularity,
        "D  Circularity index",
        lambda value: f"{value:.2f}",
        sequential_cmap,
        sequential_norm,
        compact=True,
    )

    ax_ghg.set_ylabel("Nutrient and water-loop setting")
    ax_ghg.set_xlabel("Energy and product-loop setting")
    ax_water.set_xlabel("Energy and product loops", fontsize=12.5)
    ax_circularity.set_xlabel("Energy and product loops", fontsize=12.5)

    colorbar_change = figure.colorbar(heat_ghg, ax=[ax_ghg, ax_water], orientation="horizontal", fraction=0.055, pad=0.12)
    colorbar_change.set_label("Environmental improvement from baseline (%)     worse  ←  0  →  better", fontsize=13)
    colorbar_change.ax.tick_params(labelsize=12)
    colorbar_circularity = figure.colorbar(heat_circularity, ax=ax_circularity, orientation="horizontal", fraction=0.055, pad=0.12)
    colorbar_circularity.set_label("Index value", fontsize=13)
    colorbar_circularity.ax.tick_params(labelsize=12)

    figure.savefig(OUT / "loop_effects_revised.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    figure.savefig(OUT / "loop_effects_revised.svg", bbox_inches="tight", pad_inches=0.12)
    plt.close(figure)


def make_robustness() -> None:
    records = read_rows("robustness_12seeds.csv")
    labels = ["No loops", "Nutrient + water", "Energy", "Products", "All loops"]
    metrics = [
        ("operating_profit", 1000.0, "A  Annual operating profit", "$ thousands per year", 135, "${:.0f}k"),
        ("net_kg_co2e", 1000.0, "B  Annual net GHG emissions", "t CO2e per year", 145, "{:.0f} t"),
    ]

    figure, axes = plt.subplots(1, 2, figsize=(18, 7.6), constrained_layout=True)
    for ax, (metric, scale, title, ylabel, upper, number_format) in zip(axes, metrics, strict=True):
        groups = [[float(row[metric]) / scale for row in records if row["label"] == label] for label in labels]
        colors = [CONDITION_COLORS[label] for label in labels]
        boxplot = ax.boxplot(
            groups,
            positions=np.arange(1, 6),
            widths=0.52,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": WHITE, "linewidth": 2.4},
            whiskerprops={"color": MUTED, "linewidth": 1.2},
            capprops={"color": MUTED, "linewidth": 1.2},
        )
        for patch, color in zip(boxplot["boxes"], colors, strict=True):
            patch.set_facecolor(color)
            patch.set_edgecolor(color)
            patch.set_alpha(0.94)

        jitter = np.linspace(-0.16, 0.16, 12)
        for position, (group, color) in enumerate(zip(groups, colors, strict=True), start=1):
            ax.scatter(position + jitter, group, s=31, facecolor=WHITE, edgecolor=color, linewidth=1.35, zorder=3)
            middle = median(group)
            lift = upper * (0.047 if metric == "operating_profit" else 0.027)
            ax.annotate(
                number_format.format(middle),
                xy=(position + 0.16, middle),
                xytext=(position + 0.43, middle + lift),
                ha="left",
                va="center",
                fontsize=13.5,
                fontweight="bold",
                color=INK,
                bbox={"boxstyle": "round,pad=0.18", "facecolor": WHITE, "edgecolor": color, "linewidth": 1.1},
                arrowprops={"arrowstyle": "-", "color": color, "linewidth": 1.25, "shrinkA": 2, "shrinkB": 2},
                zorder=5,
            )

        ax.set_title(title, loc="left", color=INK, pad=12)
        ax.set_ylabel(ylabel)
        ax.set_ylim(0, upper)
        ax.set_xlim(0.55, 5.65)
        ax.set_xticks(range(1, 6), ["No\nloops", "Nutrient\n+ water", "Energy", "Products", "All\nloops"])
        for tick, color in zip(ax.get_xticklabels(), colors, strict=True):
            tick.set_color(color if color != NEUTRAL else MUTED)
            tick.set_fontweight("bold")
        ax.grid(axis="y", color=GRID, linewidth=0.9)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)

    figure.text(
        0.5,
        -0.01,
        "Both axes begin at zero. Points show seeds 1–12. Boxes show the interquartile range and median.",
        ha="center",
        fontsize=14,
        color=MUTED,
    )
    figure.savefig(OUT / "robustness_zero_axis.png", dpi=300, bbox_inches="tight", pad_inches=0.12)
    figure.savefig(OUT / "robustness_zero_axis.svg", bbox_inches="tight", pad_inches=0.12)
    plt.close(figure)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configure()
    make_architecture()
    make_effects()
    make_robustness()


if __name__ == "__main__":
    main()

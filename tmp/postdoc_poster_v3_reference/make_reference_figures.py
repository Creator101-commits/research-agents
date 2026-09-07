from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tmp" / "postdoc_poster_v2" / "data"
OUT = Path(__file__).resolve().parent / "figures"

GREEN = "#347B67"
MAROON = "#651A1A"
TEAL = "#2C7180"
GOLD = "#BF8C2C"
INK = "#1F1F1F"
MUTED = "#6A6762"
GRID = "#D8D4CE"


def read_rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 13.5,
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 13.5,
            "axes.edgecolor": "#BEB9B2",
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def matrix(records: dict[str, dict[str, str]], metric: str, relative: bool) -> np.ndarray:
    base = float(records["0000"][metric])
    row_bits = ("00", "10", "01", "11")
    col_bits = ("00", "10", "01", "11")
    values = np.zeros((4, 4))
    for row, prefix in enumerate(row_bits):
        for column, suffix in enumerate(col_bits):
            value = float(records[prefix + suffix][metric])
            values[row, column] = 100 * (value - base) / base if relative else value
    return values


def heatmap(ax, values, title, formatter, cmap, vmin, vmax, compact=False) -> None:
    image = ax.imshow(values, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_title(title, loc="left", pad=10, color=INK)
    labels = ["None", "L3", "L4", "L3 + L4"]
    ax.set_xticks(range(4), labels, fontsize=13 if compact else 13.5)
    ax.set_yticks(range(4), ["None", "L1", "L2", "L1 + L2"], fontsize=13 if compact else 13.5)
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
                fontsize=13 if compact else 14,
                fontweight="bold",
                color=INK if luminance > 0.58 else "white",
            )
    for edge in np.arange(-0.5, 4, 1):
        ax.axhline(edge, color="white", linewidth=2)
        ax.axvline(edge, color="white", linewidth=2)


def make_factorial() -> None:
    records = {row["configuration"]: row for row in read_rows("factorial_seed42.csv")}
    profit = matrix(records, "operating_profit", True)
    ghg = matrix(records, "net_kg_co2e", True)
    water = matrix(records, "freshwater_withdrawal_l", True)
    circularity = matrix(records, "mean_circularity_score", False)

    figure = plt.figure(figsize=(18, 11), constrained_layout=True)
    grid = figure.add_gridspec(2, 4, width_ratios=[1.22, 1.22, 1, 1], height_ratios=[1.06, 0.94])
    ax_profit = figure.add_subplot(grid[:, :2])
    ax_ghg = figure.add_subplot(grid[0, 2:])
    ax_water = figure.add_subplot(grid[1, 2])
    ax_circularity = figure.add_subplot(grid[1, 3])

    heatmap(ax_profit, profit, "A  Processing produces the largest profit change", lambda value: f"{value:+.0f}%", "YlGn", 0, 210)
    heatmap(ax_ghg, ghg, "B  Energy lowers net GHG emissions", lambda value: f"{value:+.0f}%", "RdYlGn_r", -12, 0)
    heatmap(ax_water, water, "C  Water effect", lambda value: f"{value:+.1f}%", "Blues_r", -0.5, 0, compact=True)
    heatmap(ax_circularity, circularity, "D  Circularity", lambda value: f"{value:.2f}", "YlOrBr", 0, 0.8, compact=True)

    ax_profit.set_ylabel("Nutrient and water-loop setting")
    ax_profit.set_xlabel("Energy and product-loop setting")
    ax_ghg.set_ylabel("Nutrient and water-loop setting")
    ax_ghg.set_xlabel("Energy and product-loop setting")
    ax_water.set_xlabel("Energy and product loops", fontsize=13)
    ax_circularity.set_xlabel("Energy and product loops", fontsize=13)
    figure.savefig(OUT / "factorial_asymmetric.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def make_robustness() -> None:
    records = read_rows("robustness_12seeds.csv")
    labels = ["No loops", "Nutrient + water", "Energy", "Products", "All loops"]
    colors = ["#B8B3AC", TEAL, GOLD, "#9A5A58", MAROON]
    metrics = [
        ("operating_profit", 1000.0, "A  Annual operating profit", "$ thousands per year", "{:.0f}"),
        ("net_kg_co2e", 1000.0, "B  Annual net GHG emissions", "t CO2e per year", "{:.0f}"),
    ]

    figure, axes = plt.subplots(1, 2, figsize=(18, 7.4), constrained_layout=True)
    for ax, (metric, scale, title, ylabel, format_value) in zip(axes, metrics, strict=True):
        groups = [[float(row[metric]) / scale for row in records if row["label"] == label] for label in labels]
        boxes = ax.boxplot(
            groups,
            positions=np.arange(1, 6),
            widths=0.52,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": "white", "linewidth": 2.3},
            whiskerprops={"color": MUTED},
            capprops={"color": MUTED},
        )
        for patch, color in zip(boxes["boxes"], colors, strict=True):
            patch.set_facecolor(color)
            patch.set_edgecolor(color)
            patch.set_alpha(0.9)
        jitter = np.linspace(-0.16, 0.16, 12)
        vertical_range = max(max(group) for group in groups) - min(min(group) for group in groups)
        for index, (group, color) in enumerate(zip(groups, colors, strict=True), start=1):
            ax.scatter(index + jitter, group, s=28, facecolor="white", edgecolor=color, linewidth=1.3, zorder=3)
            ax.text(index, max(group) + vertical_range * 0.045, format_value.format(mean(group)), ha="center", fontsize=13.5, fontweight="bold", color=INK)
        ax.set_title(title, loc="left", color=INK, pad=10)
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(1, 6), ["No\nloops", "Nutrient\n+ water", "Energy", "Products", "All\nloops"])
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)
    figure.savefig(OUT / "robustness_refined.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configure()
    make_factorial()
    make_robustness()


if __name__ == "__main__":
    main()

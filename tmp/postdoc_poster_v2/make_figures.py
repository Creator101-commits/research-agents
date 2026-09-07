from __future__ import annotations

import csv
from pathlib import Path
from statistics import mean

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from analyze_experiment import scenario
from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FIGURES = HERE / "figures"
MAROON = "#500000"
MAROON_LIGHT = "#8B4A4A"
GREEN = "#32735F"
TEAL = "#2C7180"
GOLD = "#B8872D"
INK = "#202020"
MUTED = "#666666"
GRID = "#D9D4CC"


def rows(path: str) -> list[dict[str, str]]:
    with (DATA / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def configure() -> None:
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 13,
            "axes.titlesize": 16,
            "axes.titleweight": "bold",
            "axes.labelsize": 13,
            "axes.edgecolor": "#BDB7AE",
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
        }
    )


def annotated_heatmap(ax, data, title, formatter, cmap, vmin=None, vmax=None) -> None:
    image = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_title(title, loc="left", pad=12, color=INK)
    ax.set_xticks(range(4), ["None", "L3", "L4", "L3 + L4"])
    ax.set_yticks(range(4), ["None", "L1", "L2", "L1 + L2"])
    ax.set_xlabel("Energy and product-loop configuration")
    ax.set_ylabel("Nutrient and water-loop configuration")
    ax.tick_params(length=0)
    for row in range(4):
        for column in range(4):
            value = float(data[row, column])
            red, green, blue, _ = image.cmap(image.norm(value))
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            color = INK if luminance > 0.58 else "white"
            ax.text(column, row, formatter(value), ha="center", va="center", color=color, fontsize=13, fontweight="bold")
    for edge in np.arange(-0.5, 4, 1):
        ax.axhline(edge, color="white", linewidth=2)
        ax.axvline(edge, color="white", linewidth=2)
    return image


def make_factorial_matrix() -> None:
    records = rows("factorial_seed42.csv")
    by_config = {record["configuration"]: record for record in records}
    baseline = by_config["0000"]
    row_bits = ("00", "10", "01", "11")
    col_bits = ("00", "10", "01", "11")

    def matrix(metric: str, relative: bool = False) -> np.ndarray:
        values = np.zeros((4, 4))
        base = float(baseline[metric])
        for i, prefix in enumerate(row_bits):
            for j, suffix in enumerate(col_bits):
                value = float(by_config[prefix + suffix][metric])
                values[i, j] = 100 * (value - base) / base if relative else value
        return values

    profit = matrix("operating_profit", True)
    ghg = matrix("net_kg_co2e", True)
    water = matrix("freshwater_withdrawal_l", True)
    circularity = matrix("mean_circularity_score", False)

    figure, axes = plt.subplots(2, 2, figsize=(17, 12), constrained_layout=True)
    annotated_heatmap(axes[0, 0], profit, "A  Operating profit change", lambda x: f"{x:+.1f}%", "YlGn", vmin=0, vmax=max(210, profit.max()))
    annotated_heatmap(axes[0, 1], ghg, "B  Net GHG change", lambda x: f"{x:+.1f}%", "RdYlGn_r", vmin=-12, vmax=0)
    annotated_heatmap(axes[1, 0], water, "C  Freshwater withdrawal change", lambda x: f"{x:+.2f}%", "Blues_r", vmin=-0.5, vmax=0)
    annotated_heatmap(axes[1, 1], circularity, "D  Mean circularity score", lambda x: f"{x:.2f}", "YlOrBr", vmin=0, vmax=0.8)
    figure.suptitle("Four-loop factorial experiment: each cell is one 365-day configuration", x=0.01, ha="left", fontsize=21, fontweight="bold", color=MAROON)
    figure.text(0.01, -0.01, "L1 nutrient | L2 water | L3 energy | L4 on-farm processing and byproduct routing. Changes are relative to 0000 (no loop toggles), seed 42.", fontsize=12.5, color=MUTED)
    figure.savefig(FIGURES / "factorial_matrix.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def make_robustness_plot() -> None:
    records = rows("robustness_12seeds.csv")
    labels = ["No loops", "Nutrient + water", "Energy", "Products", "All loops"]
    palette = ["#A8A29A", TEAL, GOLD, MAROON_LIGHT, MAROON]
    metrics = [
        ("operating_profit", 1000.0, "A  Annual operating profit", "$ thousands/year"),
        ("net_kg_co2e", 1000.0, "B  Annual net greenhouse gas emissions", "t CO2e/year"),
    ]
    figure, axes = plt.subplots(1, 2, figsize=(17, 7.3), constrained_layout=True)
    for ax, (metric, scale, title, ylabel) in zip(axes, metrics, strict=True):
        groups = [[float(row[metric]) / scale for row in records if row["label"] == label] for label in labels]
        boxes = ax.boxplot(groups, positions=np.arange(1, 6), widths=0.55, patch_artist=True, showfliers=False, medianprops={"color": "white", "linewidth": 2.4}, whiskerprops={"color": MUTED}, capprops={"color": MUTED})
        for patch, color in zip(boxes["boxes"], palette, strict=True):
            patch.set_facecolor(color)
            patch.set_edgecolor(color)
            patch.set_alpha(0.88)
        offsets = np.linspace(-0.17, 0.17, 12)
        for index, (group, color) in enumerate(zip(groups, palette, strict=True), start=1):
            ax.scatter(index + offsets, group, s=24, color="white", edgecolor=color, linewidth=1.2, zorder=3)
            avg = mean(group)
            ax.text(index, max(group) + (max(max(g) for g in groups) - min(min(g) for g in groups)) * 0.045, f"{avg:.1f}", ha="center", va="bottom", fontsize=11.5, color=INK, fontweight="bold")
        ax.set_title(title, loc="left", color=INK, pad=10)
        ax.set_ylabel(ylabel)
        ax.set_xticks(range(1, 6), ["No\nloops", "Nutrient\n+ water", "Energy", "Products", "All\nloops"])
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", length=0)
    figure.suptitle("Repeated-seed robustness: the route ranking is stable across 12 stochastic initializations", x=0.01, ha="left", fontsize=20, fontweight="bold", color=MAROON)
    figure.text(0.01, -0.02, "Dots show individual seeds; boxes show the interquartile range and median. Product-loop values include modeled product revenue under calibration prices.", fontsize=12.5, color=MUTED)
    figure.savefig(FIGURES / "robustness_plot.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def rolling(values: list[float], window: int = 30) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    kernel = np.ones(window) / window
    return np.convolve(array, kernel, mode="valid")


def make_annual_profile() -> None:
    full = rows("full_loop_daily_seed42.csv")
    no_loop_ctx = DairyFarmModel(scenario(42, (False, False, False, False)), load_calibration()).run()
    no_loop = no_loop_ctx.daily_records
    days = np.arange(30, 366)
    figure, axes = plt.subplots(2, 1, figsize=(17, 7.8), sharex=True, constrained_layout=True)
    panels = [
        ("profit", "A  Operating profit, 30-day moving average", "$/day"),
        ("net_kg_co2e", "B  Net GHG emissions, 30-day moving average", "kg CO2e/day"),
    ]
    for ax, (metric, title, ylabel) in zip(axes, panels, strict=True):
        full_values = rolling([float(row[metric]) for row in full])
        no_values = rolling([float(row[metric]) for row in no_loop])
        ax.plot(days, no_values, color="#9A948C", linewidth=2.4, label="No loop toggles")
        ax.plot(days, full_values, color=MAROON, linewidth=3.0, label="All four loops")
        ax.fill_between(days, no_values, full_values, color=GOLD, alpha=0.16)
        ax.set_title(title, loc="left", color=INK, pad=8)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0].legend(frameon=False, ncol=2, loc="upper right")
    axes[1].set_xlabel("Simulation day")
    figure.suptitle("Temporal behavior remains separated through the one-year run", x=0.01, ha="left", fontsize=20, fontweight="bold", color=MAROON)
    figure.savefig(FIGURES / "annual_profile.png", dpi=260, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    configure()
    make_factorial_matrix()
    make_robustness_plot()
    make_annual_profile()


if __name__ == "__main__":
    main()

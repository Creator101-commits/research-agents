import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/sreeharshak/.codex/plugins/cache/openai-primary-runtime/presentations/26.904.11930/skills/presentations";
const PROJECT_DIR = "/Users/sreeharshak/Dev/research-agents";
const WORKSPACE_DIR = "/Users/sreeharshak/Dev/research-agents/tmp/postdoc_poster_v2";
const FINAL_PPTX = "/Users/sreeharshak/Dev/research-agents/output/presentations/ViCBio_DM_Postdoc_Symposium_Poster_54x42_PRINT_READY.pptx";
const RUNTIME_PYTHON = "/Users/sreeharshak/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";
const FONT = "Arial";
const WIDTH = 5184;
const HEIGHT = 4032;
const MAROON = "#500000";
const MAROON_2 = "#7A2525";
const GREEN = "#32735F";
const TEAL = "#2C7180";
const GOLD = "#B8872D";
const INK = "#202020";
const MUTED = "#5F5B56";
const PAPER = "#F5F1EB";
const LINE = "#D7D0C7";
const WHITE = "#FFFFFF";

function addShape(slide, geometry, position, fill = WHITE, line = { style: "solid", fill: LINE, width: 1 }, name) {
  return slide.shapes.add({ geometry, position, fill, line, name, borderRadius: geometry === "roundRect" ? 18 : undefined });
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
    name: options.name,
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.fontSize ?? 32,
    bold: options.bold ?? false,
    italic: options.italic ?? false,
    color: options.color ?? INK,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: "none",
    wrap: "square",
    lineSpacing: options.lineSpacing ?? 1.04,
    insets: options.insets ?? { top: 2, right: 4, bottom: 2, left: 4 },
  };
  return shape;
}

function panel(slide, x, y, width, height, title, accent = MAROON) {
  addShape(slide, "roundRect", { left: x, top: y, width, height }, WHITE, { style: "solid", fill: LINE, width: 1.5 });
  addShape(slide, "rect", { left: x, top: y, width: 14, height }, accent, { fill: "none", width: 0 });
  addText(slide, title, { left: x + 34, top: y + 24, width: width - 64, height: 58 }, { fontSize: 40, bold: true, color: MAROON, name: `${title}-heading` });
  addShape(slide, "line", { left: x + 34, top: y + 92, width: width - 68, height: 0 }, "none", { style: "solid", fill: LINE, width: 1.5 });
  return { left: x + 36, top: y + 112, width: width - 72, height: height - 136 };
}

function kpiCard(slide, x, label, value, delta, color) {
  addShape(slide, "roundRect", { left: x, top: 524, width: 585, height: 214 }, WHITE, { style: "solid", fill: LINE, width: 1.2 });
  addShape(slide, "rect", { left: x, top: 524, width: 585, height: 12 }, color, { fill: "none", width: 0 });
  addText(slide, label, { left: x + 24, top: 552, width: 537, height: 34 }, { fontSize: 24, bold: true, color: MUTED, alignment: "center" });
  addText(slide, value, { left: x + 20, top: 588, width: 545, height: 70 }, { fontSize: 52, bold: true, color, alignment: "center", verticalAlignment: "middle" });
  addText(slide, delta, { left: x + 20, top: 665, width: 545, height: 40 }, { fontSize: 24, bold: true, color: INK, alignment: "center" });
}

function bulletText(items) {
  return items.map((item) => `• ${item}`).join("\n");
}

function addFlowNode(slide, x, y, width, label, fill, textColor = INK) {
  const node = addShape(slide, "roundRect", { left: x, top: y, width, height: 88 }, fill, { style: "solid", fill: "#C9C0B6", width: 1.4 });
  node.text = label;
  node.text.style = { typeface: FONT, fontSize: 28, bold: true, color: textColor, alignment: "center", verticalAlignment: "middle", autoFit: "none", insets: { top: 6, right: 8, bottom: 6, left: 8 } };
  return node;
}

const presentation = Presentation.create({ slideSize: { width: WIDTH, height: HEIGHT } });
const slide = presentation.slides.add();
slide.background.fill = PAPER;

addShape(slide, "rect", { left: 0, top: 0, width: WIDTH, height: 468 }, MAROON, { fill: "none", width: 0 });
addShape(slide, "rect", { left: 0, top: 468, width: WIDTH, height: 16 }, GOLD, { fill: "none", width: 0 });
addText(slide, "POSTDOCTORAL RESEARCH SYMPOSIUM  |  COMPUTATIONAL STUDY", { left: 126, top: 28, width: 3100, height: 38 }, { fontSize: 24, bold: true, color: "#E9DCCB" });
addText(slide, "54 × 42 IN", { left: 4740, top: 24, width: 300, height: 42 }, { fontSize: 24, bold: true, color: WHITE, alignment: "right" });
addText(slide, "How Four Circular Dairy Loops Change Operating Profit,\nGreenhouse Gas Emissions, and Water Use", { left: 122, top: 76, width: 4920, height: 238 }, { fontSize: 102, bold: true, color: WHITE, lineSpacing: 0.93, name: "poster-title" });
addText(slide, "A 365-day agent-based virtual farm experiment (ViCBio DM)", { left: 128, top: 322, width: 3000, height: 48 }, { fontSize: 34, bold: true, color: "#F3E7D7" });
addText(slide, "Megha Poyyara Saiju¹  ·  Manogna Rayala²  ·  Karun Kaniyamattam¹", { left: 128, top: 380, width: 3060, height: 42 }, { fontSize: 31, bold: true, color: WHITE });
addText(slide, "¹Department of Animal Science  |  ²Department of Statistics  |  Texas A&M University", { left: 3220, top: 371, width: 1820, height: 56 }, { fontSize: 27, color: WHITE, alignment: "right" });

const leftX = 120;
const leftW = 1160;
const centerX = 1320;
const centerW = 2480;
const rightX = 3840;
const rightW = 1224;

let box = panel(slide, leftX, 524, leftW, 490, "Why this matters", GOLD);
addText(slide, "The 2022 USDA Census reported $52.8B in milk sales while dairy farm numbers fell 39%. Specialized dairy production expenses reached $43.9B; feed represented 46%. Circular technologies may recover value, but their interactions must be tested under the same farm constraints.", box, { fontSize: 32, lineSpacing: 1.08 });

box = panel(slide, leftX, 1036, leftW, 570, "Objective & hypothesis", TEAL);
addText(slide, "OBJECTIVE", { left: box.left, top: box.top, width: box.width, height: 34 }, { fontSize: 24, bold: true, color: TEAL });
addText(slide, "Quantify how L1 nutrient, L2 water, L3 energy, and L4 processing/product loops change annual operating profit, net GHG emissions, freshwater withdrawal, and circularity.", { left: box.left, top: box.top + 38, width: box.width, height: 174 }, { fontSize: 32, lineSpacing: 1.05 });
addText(slide, "HYPOTHESIS", { left: box.left, top: box.top + 224, width: box.width, height: 34 }, { fontSize: 24, bold: true, color: TEAL });
addText(slide, "Adding loops will increase profit and circularity while reducing net GHG emissions and freshwater withdrawal relative to the same farm with all loop toggles off.", { left: box.left, top: box.top + 264, width: box.width, height: 170 }, { fontSize: 32, lineSpacing: 1.05 });

box = panel(slide, leftX, 1628, leftW, 1096, "ViCBio DM architecture", GREEN);
addText(slide, "13 linked components · fixed daily order · seeded stochastic replay", { left: box.left, top: box.top, width: box.width, height: 40 }, { fontSize: 25, bold: true, color: MUTED, alignment: "center" });
const nodeX = box.left + 120;
const nodeW = 670;
const nodeYs = [box.top + 64, box.top + 184, box.top + 304, box.top + 424, box.top + 544, box.top + 664];
const nodes = [
  addFlowNode(slide, nodeX, nodeYs[0], nodeW, "Market + sensors", "#F1E4D4"),
  addFlowNode(slide, nodeX, nodeYs[1], nodeW, "Land + feed/crop", "#E6EFEA"),
  addFlowNode(slide, nodeX, nodeYs[2], nodeW, "Individual cows + disease", "#F4E7E7"),
  addFlowNode(slide, nodeX, nodeYs[3], nodeW, "Processing + manure routing", "#F1E8D6"),
  addFlowNode(slide, nodeX, nodeYs[4], nodeW, "Energy + water accounting", "#E0EDF0"),
  addFlowNode(slide, nodeX, nodeYs[5], nodeW, "Environment + farm manager", "#E8E5E1"),
];
for (let index = 0; index < nodes.length - 1; index += 1) {
  slide.shapes.connect(nodes[index], nodes[index + 1], { kind: "straight", fromSide: "bottom", toSide: "top", line: { style: "solid", fill: "#9A938A", width: 2.2 }, head: { type: "triangle", width: "sm", length: "sm" } });
}
const loopLabels = [
  ["L1", MAROON_2, nodeYs[3] + 13],
  ["L2", TEAL, nodeYs[4] + 5],
  ["L3", GOLD, nodeYs[4] + 48],
  ["L4", GREEN, nodeYs[3] + 56],
];
for (const [label, color, y] of loopLabels) {
  const pill = addShape(slide, "roundRect", { left: box.left + 830, top: y, width: 110, height: 38 }, color, { fill: "none", width: 0 });
  pill.text = label;
  pill.text.style = { typeface: FONT, fontSize: 24, bold: true, color: WHITE, alignment: "center", verticalAlignment: "middle", autoFit: "none" };
}
addText(slide, "Genetics records daily intake and annual gain separately. Agents exchange dated packets carrying source, period, quality, and confidence.", { left: box.left, top: box.top + 786, width: box.width, height: 142 }, { fontSize: 27, color: MUTED, lineSpacing: 1.04 });

box = panel(slide, leftX, 2746, leftW, 1138, "Computational experiment", MAROON);
addText(slide, bulletText([
  "100 cows; 365 days; high-intensity system",
  "80 ha cropland + 40 ha pasture",
  "Full 2⁴ factorial: all 16 loop combinations",
  "Seed 42 for factorial; seeds 1–12 for robustness",
  "Processor, whey, and land components available in every run",
  "Amino-acid water savings and automatic manager responses disabled to isolate loop effects",
  "Calibration prices with configured stochastic shock",
  "Daily records aggregated to annual metrics",
]), box, { fontSize: 32, lineSpacing: 1.04 });
addShape(slide, "roundRect", { left: box.left, top: box.top + 760, width: box.width, height: 182 }, "#F8EDED", { style: "solid", fill: "#D6B4B4", width: 1.2 });
addText(slide, "No capital-cost basis was supplied. ROI and payback are intentionally not reported.", { left: box.left + 22, top: box.top + 790, width: box.width - 44, height: 116 }, { fontSize: 32, bold: true, color: MAROON, alignment: "center", verticalAlignment: "middle" });

kpiCard(slide, centerX, "OPERATING PROFIT", "$123.8k", "+206.7% vs no loops", MAROON);
kpiCard(slide, centerX + 625, "NET GHG", "121.2 t", "−10.3% vs no loops", GREEN);
kpiCard(slide, centerX + 1250, "FRESHWATER", "38.75 ML", "−159,417 L · −0.41%", TEAL);
kpiCard(slide, centerX + 1875, "CIRCULARITY", "0.71", "+0.50 on 0–1 scale", GOLD);
addText(slide, "ALL FOUR LOOPS · SEED 42 · MILK OUTPUT UNCHANGED AT 719,779 L/YEAR", { left: centerX, top: 744, width: centerW, height: 34 }, { fontSize: 24, bold: true, color: MUTED, alignment: "center" });

addShape(slide, "roundRect", { left: centerX, top: 790, width: centerW, height: 1750 }, WHITE, { style: "solid", fill: LINE, width: 1.4 });
const factorialBytes = await fs.readFile(path.join(WORKSPACE_DIR, "figures", "factorial_matrix.png"));
slide.images.add({ blob: factorialBytes, contentType: "image/png", alt: "Four-panel heatmap of profit, net greenhouse gas, freshwater, and circularity across all sixteen circular-loop configurations.", fit: "contain", position: { left: centerX + 26, top: 812, width: centerW - 52, height: 1708 } });

addShape(slide, "roundRect", { left: centerX, top: 2564, width: centerW, height: 1186 }, WHITE, { style: "solid", fill: LINE, width: 1.4 });
const robustnessBytes = await fs.readFile(path.join(WORKSPACE_DIR, "figures", "robustness_plot.png"));
slide.images.add({ blob: robustnessBytes, contentType: "image/png", alt: "Two-panel repeated-seed box and dot plot comparing annual operating profit and net greenhouse gas emissions for five loop configurations.", fit: "contain", position: { left: centerX + 26, top: 2586, width: centerW - 52, height: 1140 } });

box = panel(slide, rightX, 524, rightW, 865, "What drives the result", MAROON);
addText(slide, bulletText([
  "L4 processing/product loop: +$78,868 versus no loops; dominant profit separation under assumed product-mix prices.",
  "L3 energy loop: +$4,380 and −13.87 t CO2e; entire modeled GHG reduction.",
  "L2 water loop: 159,417 L less freshwater and about $159 higher operating profit.",
  "L1 nutrient loop: 70.9 t feed-offset credit, but no top-line change because farm-grown feed was not binding.",
]), box, { fontSize: 32, lineSpacing: 1.05 });

box = panel(slide, rightX, 1412, rightW, 520, "Conclusion", GREEN);
addText(slide, "Circular interventions do not contribute equally. In this scenario, L4 determines the economic result, L3 determines the GHG result, L2 produces a small water benefit, and L1 creates a latent material credit. ViCBio DM is defensible as a screening and experiment platform before field trials or capital planning.", box, { fontSize: 32, lineSpacing: 1.05 });

box = panel(slide, rightX, 1954, rightW, 792, "Limitations", GOLD);
addText(slide, bulletText([
  "Simulated outputs; one virtual farm-year; no field validation.",
  "No CapEx, financing, taxes, or depreciation; no ROI claim.",
  "L4 depends strongly on calibrated yields and product prices.",
  "Physical nutrient return and wastewater treatment remain active when L1/L2 toggles are off; the toggles add next-day credits.",
  "The abstract's five farm systems are not yet five comparable scenarios in this code revision.",
  "Passing tests verifies software contracts, not scientific or financial validity.",
]), box, { fontSize: 32, lineSpacing: 1.01 });

box = panel(slide, rightX, 2768, rightW, 598, "Next validation steps", TEAL);
addText(slide, "1  Calibrate loop-specific CapEx and O&M.\n2  Ingest observed market and farm data.\n3  Implement the five proposed farm-system scenarios.\n4  Run global sensitivity and uncertainty analysis.\n5  Compare against farm mass-balance and financial records before reporting ROI.", box, { fontSize: 32, lineSpacing: 1.04 });

box = panel(slide, rightX, 3388, rightW, 496, "References & acknowledgments", MAROON);
addText(slide, "1. USDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024.\n2. Wood, P.D.P. Nature 216, 164–165 (1967). doi:10.1038/216164a0.\n3. Muell, J.D. et al. Front. Environ. Sci. 10:880839 (2022). doi:10.3389/fenvs.2022.880839.\n4. ViCBio DM source: research-agents, commit 7c41c15daaf1. Outputs generated 2026-09-05.\n\nAcknowledgments: Texas A&M Departments of Animal Science and Statistics.", box, { fontSize: 24, lineSpacing: 1.02 });

addText(slide, "Interpretation boundary: modeled operating profit excludes capital investment. Values are computational experiment outputs, not farm measurements.", { left: 126, top: 3952, width: 4930, height: 44 }, { fontSize: 24, bold: true, color: MAROON, alignment: "center" });

slide.speakerNotes.textFrame.setText(`FIVE-MINUTE POSTER TALK\n\n0:00–0:40 — The problem\nThe 2022 Census of Agriculture reports 52.8 billion dollars in milk sales, but dairy farm numbers declined 39 percent. Specialized dairy production expenses reached 43.9 billion dollars and feed represented 46 percent. Circular technologies can recover nutrients, water, energy, and product value, but producers need a way to compare them inside the same farm system.\n\n0:40–1:20 — Objective and model\nOur objective was to quantify how four implemented loops change annual operating profit, net greenhouse gas emissions, freshwater withdrawal, and circularity. ViCBio DM links 13 components and preserves a fixed daily causal order. The hypothesis was that more loops would improve profit and circularity while lowering emissions and water use.\n\n1:20–2:10 — Experiment\nWe ran a one-year, 100-cow, high-intensity virtual farm with 80 hectares of cropland and 40 hectares of pasture. The experiment covered all sixteen combinations of nutrient, water, energy, and processing/product loops at seed 42. Five representative configurations were then repeated across seeds 1 through 12. The separate amino-acid water-saving policy and automatic manager responses were disabled so they would not mask the loop effects.\n\n2:10–3:20 — Factorial results\nThe heatmaps show that loop effects are not equal. L4 produces the economic separation: it raises seed-42 operating profit by 78,868 dollars relative to no loops under the model's assumed product mix and prices. L3 produces the environmental separation: it lowers net emissions 10.3 percent and adds about 4,380 dollars. L2 reduces freshwater withdrawal by 159,417 liters, or 0.41 percent. L1 creates 70.9 tonnes of feed-offset credit but no top-line benefit because farm-grown feed was not binding.\n\n3:20–4:10 — Combined and robustness results\nWith all loops active, operating profit is 123,755 dollars versus 40,348 dollars, net emissions are 121.2 versus 135.1 tonnes of CO2 equivalent, and circularity rises from 0.21 to 0.71. Milk output is unchanged at 719,779 liters, so the differences arise from routing and modeled values rather than more milk. Across twelve seeds, the ranking remains stable: all loops average 120.7 plus or minus 2.9 thousand dollars, compared with 38.4 plus or minus 1.9 thousand with no loop toggles.\n\n4:10–5:00 — Conclusion and boundary\nThe result is not a validated investment return. No capital-cost basis was supplied, so ROI and payback are intentionally absent. The correct use of this version is screening: identify which assumptions and constraints drive results, then calibrate CapEx, operating cost, observed prices, and farm mass balances before making investment claims.\n\nQ&A DEFENSE\nWhy is L4 so large? It combines modeled processing revenue with byproduct routing and therefore depends strongly on calibrated product yields and prices.\nWhy is baseline circularity already 0.21? Physical wastewater treatment and nutrient return are implemented even when L1 and L2 toggles are off; those toggles add next-day credits rather than disabling all recovery.\nWhere is ROI? The manager reports ROI only when a positive capital-cost basis is supplied. This experiment supplies none, so an ROI number would be fabricated.\nWere five farm types compared? No. The current repository exposes three feed-production-system settings, not the five proposed abstract categories. Implementing and validating those five scenarios is future work.\nWhat do the tests prove? The 229 passing tests verify software contracts and deterministic behavior. They do not validate biological calibration, prices, or investment performance.\n\nSOURCES\nUSDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024. https://data.nass.usda.gov/Publications/Highlights/2024/Census22_HL_Dairy.pdf\nWood, P.D.P. Algebraic model of the lactation curve in cattle. Nature 216, 164–165. https://doi.org/10.1038/216164a0\nMuell, J.D. et al. Farm-scale water-energy-food-waste nexus analysis for a closed-loop dairy system. Frontiers in Environmental Science 10:880839. https://doi.org/10.3389/fenvs.2022.880839\nViCBio DM repository commit 7c41c15daaf1. Computational outputs generated 2026-09-05.`);
slide.speakerNotes.setVisible(true);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const stagingDir = path.join(WORKSPACE_DIR, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const preview = await presentation.export({ slide, format: "png", scale: 0.5 });
await fs.writeFile(path.join(WORKSPACE_DIR, "draft-slide.png"), new Uint8Array(await preview.arrayBuffer()));

const result = await finalizePresentation({
  explicitTotalSlideCount: 1,
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  workspaceDir: PROJECT_DIR,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "49377600,38404800", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "ViCBio_DM_Postdoc_Symposium_Poster_54x42_PRINT_READY.pptx.validation.json"),
});

console.log(JSON.stringify({ finalPath: FINAL_PPTX, result }, null, 2));

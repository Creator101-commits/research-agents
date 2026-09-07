import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/sreeharshak/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const PROJECT_DIR = "/Users/sreeharshak/Dev/research-agents";
const WORKSPACE_DIR = path.join(PROJECT_DIR, "tmp/postdoc_poster_v3_reference");
const FINAL_PPTX = path.join(PROJECT_DIR, "output/presentations/ViCBio_DM_Postdoc_Symposium_Poster_REFERENCE_DESIGN_FINAL.pptx");
const RUNTIME_PYTHON = "/Users/sreeharshak/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";

const WIDTH = 5184;
const HEIGHT = 4032;
const FONT = "Arial";
const GREEN = "#347B67";
const MAROON = "#651B1B";
const MAROON_DARK = "#4E1111";
const TEAL = "#287281";
const GOLD = "#B98729";
const INK = "#1D1D1D";
const MUTED = "#5C5C5C";
const LIGHT = "#D7D7D7";
const WHITE = "#FFFFFF";

function addShape(slide, geometry, position, fill = WHITE, line = { fill: "none", width: 0 }, name) {
  return slide.shapes.add({ geometry, position, fill, line, name });
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
    lineSpacing: options.lineSpacing ?? 1.03,
    insets: options.insets ?? { top: 1, right: 3, bottom: 1, left: 3 },
  };
  return shape;
}

function sectionTitle(slide, title, x, y, width) {
  return addText(slide, title, { left: x, top: y, width, height: 50 }, {
    fontSize: 38,
    bold: true,
    color: MAROON,
    name: `${title}-heading`,
  });
}

function addKpi(slide, x, width, label, value, delta, color = INK) {
  addText(slide, label, { left: x, top: 556, width, height: 30 }, {
    fontSize: 24,
    bold: true,
    color: MUTED,
    alignment: "center",
  });
  addText(slide, value, { left: x, top: 590, width, height: 60 }, {
    fontSize: 48,
    bold: true,
    color,
    alignment: "center",
    verticalAlignment: "middle",
  });
  addText(slide, delta, { left: x, top: 656, width, height: 34 }, {
    fontSize: 24,
    bold: true,
    color: INK,
    alignment: "center",
  });
}

function addFlowNode(slide, x, y, width, label) {
  const node = addShape(slide, "roundRect", { left: x, top: y, width, height: 82 }, LIGHT, {
    style: "solid",
    fill: LIGHT,
    width: 0.8,
  });
  node.text = label;
  node.text.style = {
    typeface: FONT,
    fontSize: 25,
    bold: true,
    color: INK,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    insets: { top: 5, right: 8, bottom: 5, left: 8 },
  };
  return node;
}

function addLoopPill(slide, x, y, label, fill) {
  const pill = addShape(slide, "roundRect", { left: x, top: y, width: 108, height: 48 }, fill);
  pill.text = label;
  pill.text.style = {
    typeface: FONT,
    fontSize: 24,
    bold: true,
    color: WHITE,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "none",
    insets: { top: 3, right: 4, bottom: 3, left: 4 },
  };
}

const presentation = Presentation.create({ slideSize: { width: WIDTH, height: HEIGHT } });
const slide = presentation.slides.add();
slide.background.fill = WHITE;

// Header: preserve the supplied flat green band and left-aligned title hierarchy.
addShape(slide, "rect", { left: 0, top: 0, width: WIDTH, height: 468 }, GREEN);
addText(slide, "Not All Circular Loops Pay Off:\nProduct Loops Drive Profit, Energy Loops Cut Emissions", {
  left: 142,
  top: 78,
  width: 3740,
  height: 218,
}, {
  fontSize: 90,
  bold: false,
  color: WHITE,
  lineSpacing: 0.94,
  name: "poster-title",
});
addText(slide, "Evidence from a 365-day simulated dairy farm using ViCBio DM", {
  left: 146,
  top: 318,
  width: 2760,
  height: 43,
}, { fontSize: 31, bold: true, color: WHITE });
addText(slide, "Megha Poyyara Saiju¹   Manogna Rayala²   Karun Kaniyamattam¹", {
  left: 146,
  top: 375,
  width: 3020,
  height: 38,
}, { fontSize: 28, bold: true, color: WHITE });
addText(slide, "¹Department of Animal Science   ²Department of Statistics   Texas A&M University", {
  left: 3550,
  top: 374,
  width: 1485,
  height: 40,
}, { fontSize: 24, color: WHITE, alignment: "right" });

const leftX = 145;
const leftW = 1120;
const centerX = 1390;
const centerW = 2370;
const rightX = 3905;
const rightW = 1134;

// Left column.
sectionTitle(slide, "Why this matters", leftX, 558, leftW);
addText(slide,
  "Feed accounts for 46% of specialized dairy production costs, while U.S. milk sales reached $52.8 billion in 2022. Farms need to know which circular technologies recover enough value to justify further testing. Most studies evaluate nutrient, water, energy, and product recovery separately. ViCBio DM runs all four routes within the same herd and shared resource balance, using one consistent price set.",
  { left: leftX, top: 620, width: leftW, height: 390 },
  { fontSize: 31, lineSpacing: 1.04 });

sectionTitle(slide, "Research question and expectation", leftX, 1032, leftW);
addText(slide,
  "We asked which loops materially change profit or environmental performance when all four draw on the same farm resources. We expected the energy and product loops to dominate because they create priced outputs. Nutrient and water recovery would matter most when feed or freshwater became limiting.",
  { left: leftX, top: 1094, width: leftW, height: 320 },
  { fontSize: 31, lineSpacing: 1.04 });

sectionTitle(slide, "ViCBio DM architecture", leftX, 1460, leftW);
addText(slide, "13 linked components with fixed daily order and seeded stochastic replay", {
  left: leftX,
  top: 1520,
  width: leftW,
  height: 34,
}, { fontSize: 24, color: MUTED, alignment: "center" });

const nodeX = leftX + 104;
const nodeW = 690;
const nodeYs = [1582, 1700, 1818, 1936, 2054, 2172];
const nodes = [
  addFlowNode(slide, nodeX, nodeYs[0], nodeW, "Market + sensors"),
  addFlowNode(slide, nodeX, nodeYs[1], nodeW, "Land + feed/crop"),
  addFlowNode(slide, nodeX, nodeYs[2], nodeW, "Individual cows + disease"),
  addFlowNode(slide, nodeX, nodeYs[3], nodeW, "Processing + manure routing"),
  addFlowNode(slide, nodeX, nodeYs[4], nodeW, "Energy + water accounting"),
  addFlowNode(slide, nodeX, nodeYs[5], nodeW, "Environment + farm manager"),
];
for (let index = 0; index < nodes.length - 1; index += 1) {
  slide.shapes.connect(nodes[index], nodes[index + 1], {
    kind: "straight",
    fromSide: "bottom",
    toSide: "top",
    line: { style: "solid", fill: "#A8A39B", width: 2 },
    head: { type: "triangle", width: "sm", length: "sm" },
  });
}
addLoopPill(slide, leftX + 850, 1953, "L1", MAROON);
addLoopPill(slide, leftX + 850, 2011, "L4", GREEN);
addLoopPill(slide, leftX + 850, 2069, "L2", TEAL);
addLoopPill(slide, leftX + 850, 2127, "L3", GOLD);
addText(slide,
  "Genetics records daily intake and annual gain separately. Agents exchange dated packets that retain source, period, quality, and confidence.",
  { left: leftX, top: 2292, width: leftW, height: 130 },
  { fontSize: 24, color: MUTED, lineSpacing: 1.02 });

sectionTitle(slide, "Computational experiment", leftX, 2502, leftW);
addText(slide,
  "We simulated a 100-cow high-intensity farm for 365 days, with 80 ha of cropland and 40 ha of pasture. The full 2⁴ design tested all 16 loop combinations at seed 42. We repeated five representative configurations across seeds 1 through 12.\n\nProcessor, whey, and land components stayed available in every run. We turned off amino-acid water savings and automatic manager responses so we could isolate loop effects. The model applied its calibration prices and configured price shock. We aggregated daily records into annual totals.",
  { left: leftX, top: 2564, width: leftW, height: 770 },
  { fontSize: 30, lineSpacing: 1.02 });
addText(slide,
  "We did not include capital costs, so this poster does not report ROI or payback.",
  { left: leftX + 20, top: 3400, width: leftW - 40, height: 110 },
  { fontSize: 29, bold: true, color: MAROON, alignment: "center", verticalAlignment: "middle" });

// Center column: retain the reference's unboxed metric row.
const kpiW = 560;
addKpi(slide, centerX, kpiW, "OPERATING PROFIT", "$124k", "about +207%", MAROON_DARK);
addKpi(slide, centerX + 600, kpiW, "NET GHG", "121 t CO2e", "about −10%", GREEN);
addKpi(slide, centerX + 1200, kpiW, "FRESHWATER", "38.7 ML", "0.16 ML less", TEAL);
addKpi(slide, centerX + 1800, kpiW, "CIRCULARITY", "0.71", "+0.50", GOLD);
addText(slide, "All-loop run at seed 42. Milk output remained 720,000 L per year.", {
  left: centerX,
  top: 708,
  width: centerW,
  height: 34,
}, { fontSize: 24, bold: true, color: MUTED, alignment: "center" });

addText(slide, "Loop effects across all 16 configurations", {
  left: centerX,
  top: 782,
  width: centerW,
  height: 48,
}, { fontSize: 38, bold: true, color: MAROON, alignment: "center" });
const factorialBytes = await fs.readFile(path.join(WORKSPACE_DIR, "figures/factorial_asymmetric.png"));
slide.images.add({
  blob: factorialBytes,
  contentType: "image/png",
  alt: "Asymmetric four-panel heatmap. Profit occupies the dominant panel, emissions a medium panel, and water and circularity smaller supporting panels. All sixteen circular-loop configurations are shown.",
  fit: "contain",
  position: { left: centerX, top: 842, width: centerW, height: 1450 },
});
addText(slide,
  "L1 represents nutrient recovery, L2 water recovery, L3 energy recovery, and L4 on-farm processing with byproduct routing. Changes use the no-loop configuration at seed 42 as the baseline.",
  { left: centerX, top: 2300, width: centerW, height: 72 },
  { fontSize: 24, color: MUTED, alignment: "center", lineSpacing: 1.0 });

addText(slide, "Product and energy effects persist across 12 seeds", {
  left: centerX,
  top: 2438,
  width: centerW,
  height: 48,
}, { fontSize: 38, bold: true, color: MAROON, alignment: "center" });
const robustnessBytes = await fs.readFile(path.join(WORKSPACE_DIR, "figures/robustness_refined.png"));
slide.images.add({
  blob: robustnessBytes,
  contentType: "image/png",
  alt: "Repeated-seed dot and box plots for annual operating profit and net greenhouse gas emissions across five representative loop configurations.",
  fit: "contain",
  position: { left: centerX, top: 2500, width: centerW, height: 1000 },
});
addText(slide,
  "Each point shows one seed. Boxes show the interquartile range and median. Product-loop values include modeled product revenue under calibration prices.",
  { left: centerX, top: 3510, width: centerW, height: 70 },
  { fontSize: 24, color: MUTED, alignment: "center", lineSpacing: 1.0 });

// Right column: preserve section order and flat placement from the supplied design.
sectionTitle(slide, "What drives the result", rightX, 558, rightW);
addText(slide,
  "L4 created the economic result. Turning on processing and product routing raised seed-42 operating profit by about $79,000 under the modeled product mix and prices.\n\nThe energy loop added about $4,400 and reduced net emissions by 13.9 t CO2e.\n\nL2 saved about 160,000 L of freshwater and $160.\n\nThe L1 nutrient loop generated 71 t of feed-offset credit. Farm-grown feed was not a limiting input, so the credit did not change operating profit.",
  { left: rightX, top: 620, width: rightW, height: 720 },
  { fontSize: 30, lineSpacing: 1.01 });

sectionTitle(slide, "Conclusion", rightX, 1390, rightW);
addText(slide,
  "Use the model to decide which loop deserves field calibration first. For this farm setup, product prices control the economic case, while energy recovery controls the emissions result. Nutrient and water loops need scarcity scenarios before their value can be judged.",
  { left: rightX, top: 1452, width: rightW, height: 310 },
  { fontSize: 31, lineSpacing: 1.04 });

sectionTitle(slide, "Limitations", rightX, 1810, rightW);
addText(slide,
  "• Results come from one simulated farm-year and have not been compared with measured farm data.\n\n• The model omits capital costs, financing, taxes, and depreciation.\n\n• L4 results depend on calibrated processing yields and product prices.\n\n• Wastewater treatment and nutrient return stay active when L1 and L2 are off. Those toggles add next-day credits rather than removing all reuse.\n\n• Five real-world farm-system comparisons are planned but not yet implemented.\n\n• Unit tests check model logic and accounting equations. Field data have not yet tested the biological and financial estimates.",
  { left: rightX, top: 1872, width: rightW, height: 835 },
  { fontSize: 27, lineSpacing: 1.0 });

sectionTitle(slide, "Next research steps", rightX, 2758, rightW);
addText(slide, "ECONOMICS", { left: rightX, top: 2820, width: rightW, height: 30 }, {
  fontSize: 24, bold: true, color: MAROON });
addText(slide, "Add loop-specific capital and operating costs, then calculate ROI.", {
  left: rightX, top: 2853, width: rightW, height: 77 }, { fontSize: 28 });
addText(slide, "CALIBRATION", { left: rightX, top: 2946, width: rightW, height: 30 }, {
  fontSize: 24, bold: true, color: MAROON });
addText(slide, "Replace default prices and yields with observed farm and market data.", {
  left: rightX, top: 2979, width: rightW, height: 77 }, { fontSize: 28 });
addText(slide, "EXTERNAL VALIDATION", { left: rightX, top: 3072, width: rightW, height: 30 }, {
  fontSize: 24, bold: true, color: MAROON });
addText(slide, "Implement the five farm systems, run global sensitivity analysis, and compare results with farm mass-balance and financial records.", {
  left: rightX, top: 3105, width: rightW, height: 154 }, { fontSize: 28, lineSpacing: 1.02 });

sectionTitle(slide, "References and acknowledgments", rightX, 3322, rightW);
addText(slide,
  "1. USDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024.\n2. Wood, P.D.P. Algebraic Model of the Lactation Curve in Cattle. Nature 216, 164–165 (1967). doi:10.1038/216164a0.\n3. Muell, J.D. et al. Farm-Scale Water-Energy-Food-Waste Nexus Analysis for a Closed-Loop Dairy System. Frontiers in Environmental Science 10:880839 (2022). doi:10.3389/fenvs.2022.880839.\n4. ViCBio DM model code. github.com/Creator101-commits/research-agents. Version accessed September 2026.\n\nAcknowledgments: Texas A&M University Department of Animal Science and Department of Statistics.",
  { left: rightX, top: 3384, width: rightW, height: 500 },
  { fontSize: 24, lineSpacing: 1.0 });

slide.speakerNotes.textFrame.setText(`FIVE-MINUTE POSTER TALK

0:00 to 0:35. Why this matters
Feed represents 46 percent of specialized dairy production costs, while U.S. milk sales reached 52.8 billion dollars in 2022. Farms need to know which circular technologies recover enough value to justify detailed field and engineering work. Existing analyses often isolate one route. ViCBio DM places nutrient, water, energy, and processing routes inside the same herd and resource balance.

0:35 to 1:15. Question and expectation
We asked which loop materially changes economic or environmental performance when all four compete within the same farm. We expected the product and energy loops to dominate because they create priced outputs. We expected nutrient and water recovery to become valuable mainly when feed or freshwater became limiting.

1:15 to 1:55. Experiment
We simulated a 100-cow high-intensity farm for 365 days, with 80 hectares of cropland and 40 hectares of pasture. The full two-by-two-by-two-by-two design tested all sixteen loop configurations at seed 42. Five representative configurations were repeated across seeds 1 through 12. Processor, whey, and land components remained available in every run. We disabled amino-acid water savings and automatic manager responses to isolate loop effects.

1:55 to 3:15. Factorial results
The figure uses area to match importance. Profit is the largest panel because the processing and product loop produces the largest change. At seed 42, L4 raises annual operating profit by about 79,000 dollars under the modeled product mix and prices. The energy loop adds about 4,400 dollars and reduces net emissions by 13.9 tonnes of carbon dioxide equivalent. L2 saves about 160,000 liters of freshwater and about 160 dollars. L1 generates 71 tonnes of feed-offset credit. Since farm-grown feed is not limiting in this scenario, the credit does not change operating profit.

3:15 to 4:05. Combined and repeated-seed results
With all loops active, annual operating profit is about 124,000 dollars, net emissions are 121 tonnes of carbon dioxide equivalent, freshwater withdrawal is 38.7 megaliters, and circularity is 0.71. Milk output remains about 720,000 liters. Across twelve seeds, the route ranking is stable. Product configurations remain the high-profit cases, while energy configurations remain the low-emission cases.

4:05 to 5:00. Decision and boundary
The practical use is to choose the next calibration target. Product pricing controls the economic case, so L4 needs observed yields, prices, capital cost, and operating cost before investment analysis. Energy recovery controls emissions, so L3 needs equipment and methane-capture calibration. Nutrient and water routes need explicit scarcity scenarios. This poster does not report ROI or payback because the experiment contains no capital-cost basis.

Q&A NOTES
Why is L4 large? The loop combines modeled processing revenue with byproduct routing and depends on product yields and prices.
Why is baseline circularity above zero? Physical wastewater treatment and nutrient return stay active when L1 and L2 are off. Those switches add next-day credits instead of disabling all recovery.
Were five farm types compared? No. Five real-world farm-system comparisons are planned but are not implemented in this code revision.
What do the tests establish? Unit tests check model logic, deterministic replay, and accounting equations. They do not validate biology, observed prices, capital performance, or field transferability.

SOURCES
USDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024. https://data.nass.usda.gov/Publications/Highlights/2024/Census22_HL_Dairy.pdf
Wood, P.D.P. Algebraic model of the lactation curve in cattle. Nature 216, 164–165. https://doi.org/10.1038/216164a0
Muell, J.D. et al. Farm-scale water-energy-food-waste nexus analysis for a closed-loop dairy system. Frontiers in Environmental Science 10:880839. https://doi.org/10.3389/fenvs.2022.880839
ViCBio DM model code. https://github.com/Creator101-commits/research-agents. Version accessed September 2026.`);
slide.speakerNotes.setVisible(true);

const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);
const stagingDir = path.join(WORKSPACE_DIR, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(stagingDir, "candidate-reference-revision.pptx");
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
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "49377600,38404800", "--validate-heading-fit"],
  fontPolicy: { basis: "design", families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "ViCBio_DM_Postdoc_Symposium_Poster_REFERENCE_DESIGN_FINAL.pptx.validation.json"),
});

console.log(JSON.stringify({ finalPath: FINAL_PPTX, result }, null, 2));

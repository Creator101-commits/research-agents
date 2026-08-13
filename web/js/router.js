export const PAGES = Object.freeze([
  {id: "overview", label: "Overview", description: "See the latest farm outcomes and research signals."},
  {id: "simulation", label: "Simulation", description: "Run calibrated scenarios with the authoritative Python model."},
  {id: "charts", label: "Charts", description: "Inspect backend-produced time series and trends."},
  {id: "loops", label: "Circular Loops", description: "Trace nutrient, water, energy, and byproduct pathways."},
  {id: "comparison", label: "Scenario Comparison", description: "Compare independent model runs without mixing their state."},
  {id: "cows", label: "Cow Performance", description: "Review the model's per-cow records and herd signals."},
  {id: "environment", label: "Environment", description: "Audit emissions, water, soil, and sustainability outputs."},
  {id: "economics", label: "Economics", description: "Review reported revenue, cost, cash, and profit measures."},
  {id: "roi", label: "Equipment ROI", description: "Inspect backend-produced equipment benefits and payback."},
  {id: "parameters", label: "Parameters", description: "Review calibration metadata and submit validated overrides."},
  {id: "model-details", label: "Model Details", description: "Inspect run metadata, provenance, and report contracts."},
  {id: "exports", label: "Export", description: "Download official reports and presentation outputs."},
]);

export const DEFAULT_PAGE = "simulation";
const PAGE_IDS = new Set(PAGES.map(page => page.id));

export function pageFromHash(hash) {
  const value = String(hash || "").replace(/^#\/?/, "").split("?", 1)[0];
  return PAGE_IDS.has(value) ? value : DEFAULT_PAGE;
}

export function navigate(page) {
  const target = PAGE_IDS.has(page) ? page : DEFAULT_PAGE;
  if (typeof window !== "undefined") {
    const hash = `#/${target}`;
    if (window.location.hash !== hash) window.location.hash = hash;
  }
  return target;
}

export function initRouter(onChange) {
  const update = () => onChange(pageFromHash(window.location.hash));
  if (typeof window === "undefined") {
    onChange(DEFAULT_PAGE);
    return () => {};
  }
  window.addEventListener("hashchange", update);
  update();
  return () => window.removeEventListener("hashchange", update);
}

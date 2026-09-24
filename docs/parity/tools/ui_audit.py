"""Compare the target Conventional dashboard with the running app, page by page.

Usage (Playwright for Python and a Chromium build must already be available;
this is a local audit tool, not a project dependency):

    python3 webapp.py &                                   # app on http://localhost:8765
    python3 docs/parity/tools/ui_audit.py target docs/parity/conventional_dashboard_target.html
    python3 docs/parity/tools/ui_audit.py app http://localhost:8765/

Writes <out>/<which>-<page>-<theme>.png and <out>/<which>.json with every Chart.js
instance per page (type, size, dataset lengths, finite and non-zero counts) plus
console errors. The target loads Chart.js from a CDN; if that is blocked, copy the
target next to web/vendor/chart.umd.js and point its script tag at the local file.
"""

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = ["overview", "charts", "loops", "compare", "roi", "ranking", "params", "animal"]

CHART_PROBE = """
() => {
  const out = [];
  const inst = (window.Chart && Chart.instances) ? Object.values(Chart.instances) : [];
  for (const c of inst) {
    const el = c.canvas;
    const sec = el.closest('.page-section');
    const ds = (c.data.datasets || []).map(d => {
      const vals = (d.data || []).map(v => (v && typeof v === 'object') ? v.y : v);
      const nums = vals.filter(v => typeof v === 'number' && isFinite(v));
      return {label: d.label, n: vals.length, finite: nums.length,
              nonzero: nums.filter(v => v !== 0).length,
              min: nums.length ? Math.min(...nums) : null, max: nums.length ? Math.max(...nums) : null};
    });
    out.push({id: el.id, type: c.config.type, section: sec ? sec.id : null,
              w: el.clientWidth, h: el.clientHeight, labels: (c.data.labels || []).length, datasets: ds});
  }
  return out;
}
"""


def run(which: str, url: str, out: Path) -> None:
    log = {"console": [], "pageerror": [], "pages": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda m: log["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: log["pageerror"].append(str(e)))
        page.goto(url, wait_until="load")
        if which == "target":
            page.evaluate("() => launchFarm('conventional')")
        page.wait_for_function(
            "() => document.querySelector('#kpiGrid .kpi-card') && "
            "document.getElementById('statusBadge').textContent.trim() === 'Ready'",
            timeout=240000,
        )
        page.wait_for_timeout(800)
        for theme in ("light", "dark"):
            if theme == "dark":
                page.click("[data-theme-toggle]")
                page.wait_for_timeout(500)
            for name in PAGES:
                page.evaluate(f"() => navigate('{name}')")
                page.wait_for_timeout(700)
                if name == "compare" and theme == "light":
                    page.click("#loopCmpBtn")
                    page.wait_for_function(
                        "() => document.getElementById('loopCmpResults').style.display !== 'none' "
                        "&& !document.getElementById('loopCmpBtn').disabled",
                        timeout=600000,
                    )
                    page.wait_for_timeout(1500)
                if name == "ranking" and theme == "light":
                    page.click("#rankBtn")
                    page.wait_for_function("() => document.getElementById('rankResults').style.display !== 'none'", timeout=120000)
                    page.wait_for_timeout(1000)
                page.screenshot(path=str(out / f"{which}-{name}-{theme}.png"), full_page=True)
                charts = page.evaluate(CHART_PROBE)
                log["pages"][f"{name}-{theme}"] = [c for c in charts if c["section"] == f"section-{name}"]
        browser.close()
    (out / f"{which}.json").write_text(json.dumps(log, indent=1))


if __name__ == "__main__":
    which, location = sys.argv[1], sys.argv[2]
    out = Path(sys.argv[3] if len(sys.argv) > 3 else "/tmp/uiaudit")
    out.mkdir(parents=True, exist_ok=True)
    url = location if location.startswith("http") else Path(os.path.abspath(location)).as_uri()
    run(which, url, out)
    print("done", which, out)

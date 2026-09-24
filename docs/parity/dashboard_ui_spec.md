# Dairy Bioeconomy Simulator v5.1: Conventional Farm dashboard spec and gap map

Source: `6e308933-Dairy_bioeconomy_dashboard.html` (4,537 lines, about 258 KB, one file with inline CSS and JS).
Scope: the **Conventional Farm** dashboard only. The farm-type landing screen (`#farmLanding`) and the other four presets (Robotic, Organic, Raw Milk, Beef-on-Dairy) are out of scope. Any logic that branches on `activeFarmType !== 'conventional'` is ignored below.

Existing app: `~/mnt/research-agents` (`web/index.html`, `web/js/*.js`, `web/styles/*.css`, `webapp.py`, `dairy_abm/dashboard.py`). I only read the repository. One side effect: importing `dairy_abm` once created git-ignored `__pycache__/` folders (see section 12).

---

## 0. Libraries and fonts

| Item | Value |
|---|---|
| Chart library | **Chart.js 4.4.2**, loaded from `https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js` (UMD, global `Chart`). No plugins. The comparison chart registers one inline plugin (`baselineLine`) that draws a dashed zero rule. |
| Fonts | Google Fonts: `Inter` (weights 300 to 700), `JetBrains Mono` (400 and 600). |
| Icons | Inline SVG strokes (Feather-style, 16px, `stroke-width 2`) in the nav and KPI tiles, plus emoji in headings and cards. The app replaces every target emoji with a small inline SVG in the same box (no emojis in the repository). |
| Other | No framework. Global functions, `onclick=` attributes, and `innerHTML` templates. |

Existing app: hand-written SVG charts (`web/js/charts.js: svgChart`), a system font stack, no icons and no emoji. **The chart library and fonts would need to be added.** The `webapp.py` static server only serves `/assets/*` from `web/`. You can either use the CDN (as the target does) or vendor `chart.umd.min.js` into `web/`.

---

## 1. Design tokens

### 1.1 Colors (light is the default `:root,[data-theme="light"]`; dark is `[data-theme="dark"]`)

| Token | Light | Dark |
|---|---|---|
| `--color-bg` | `#f7f6f2` | `#171614` |
| `--color-surface` | `#f9f8f5` | `#1c1b19` |
| `--color-surface-2` | `#fbfbf9` | `#201f1d` |
| `--color-surface-offset` | `#f3f0ec` | `#1d1c1a` |
| `--color-surface-dynamic` | `#e6e4df` | `#2d2c2a` |
| `--color-divider` | `#dcd9d5` | `#262523` |
| `--color-border` | `#d4d1ca` | `#393836` |
| `--color-text` | `#28251d` | `#cdccca` |
| `--color-text-muted` | `#7a7974` | `#797876` |
| `--color-text-faint` | `#bab9b4` | `#5a5957` |
| `--color-text-inverse` | `#f9f8f4` | `#2b2a28` |
| `--color-primary` (teal) | `#01696f` | `#4f98a3` |
| `--color-primary-hover` | `#0c4e54` | `#227f8b` |
| `--color-primary-active` | `#0f3638` | `#1a626b` |
| `--color-primary-highlight` | `#cedcd8` | `#313b3b` |
| `--color-success` (green) | `#437a22` | `#6daa45` |
| `--color-success-hover` | `#2e5c10` | `#4d8f25` |
| `--color-success-highlight` | `#d4dfcc` | `#3a4435` |
| `--color-warning` | `#964219` | `#bb653b` |
| `--color-warning-highlight` | `#ddcfc6` | `#564942` |
| `--color-error` (magenta) | `#a12c7b` | `#d163a7` |
| `--color-error-highlight` | `#e0ced7` | `#4c3d46` |
| `--color-gold` | `#d19900` | `#e8af34` |
| `--color-gold-highlight` | `#e9e0c6` | `#4d4332` |
| `--color-blue` | `#006494` | `#5591c7` |
| `--color-blue-highlight` | `#c6d8e4` | `#3a4550` |
| `--color-purple` | `#7a39bb` | `#a86fdf` |
| `--color-purple-highlight` | `#dacfde` | `#4e4652` |
| `--color-orange` | `#da7101` | `#fdab43` |
| `--color-orange-highlight` | `#e7d7c4` | `#564b3e` |
| Farm accent (Conventional) | `#01696f`: topbar border-bottom 2px, farm pill, subtitle, banner left border | same |

Loop color mapping, used everywhere: **L1 = success/green, L2 = blue, L3 = orange, L4 = purple**. Revenue stream mapping: **Milk = primary teal, Energy = orange, Heat = gold, Compost = success green, Costs = error**.

The chart palette (`getChartColors()`) is hard-coded per theme: grid `rgba(0,0,0,.06)` (dark `rgba(255,255,255,.06)`), tick `#7a7974` (dark `#797876`), plus primary, success, gold, blue, orange, error, bg and text as in the table. Chart fills use the line color plus hex alpha `22`, `18` or `28`. Donut fills use `cc`.

Undefined tokens the source refers to anyway, so they silently fall back: `--text-2xl` (loop hero value), `--color-notification` (negative deltas), `--transition-interactive`, `--color-surface-offset-2` (falls back to `#edeae5`), and `co.muted` in JS (undefined, so Chart.js uses its default grey).

### 1.2 Radii, shadows, motion, type, spacing

- Radius: `sm .375rem`, `md .5rem`, `lg .75rem`, `xl 1rem`, `full 9999px`. Cards use `lg`. Loop and equipment hero cards use `xl`.
- Shadow: `sm 0 1px 2px oklch(.2 .01 80/.06)`, `md 0 4px 12px …/.08`, `lg 0 12px 32px …/.12`. Dark values are `/.2`, `/.3` and `/.4` on black.
- Transition: `180ms cubic-bezier(0.16,1,0.3,1)`.
- Font sizes (fluid clamp): `xs clamp(.75rem,.7rem+.25vw,.875rem)`, `sm clamp(.875rem,.8rem+.35vw,1rem)` (body), `base clamp(1rem,.95rem+.25vw,1.125rem)`, `lg clamp(1.125rem,1rem+.75vw,1.5rem)`, `xl clamp(1.5rem,1.2rem+1.25vw,2.25rem)`.
- Spacing scale: `1 .25rem`, `2 .5rem`, `3 .75rem`, `4 1rem`, `5 1.25rem`, `6 1.5rem`, `8 2rem`, `10 2.5rem`, `12 3rem`, `16 4rem`.
- `--sidebar-w: 260px`.
- Numbers use `font-variant-numeric: tabular-nums lining-nums`. Parameter values and loop-table values use JetBrains Mono.
- Focus ring: `2px solid primary`, offset 3px.
- Animations: KPI `numPop` (.35s scale pop on update); `pulse-dirty` (gold ring, 1.5s, on the Run button when parameters changed); `spin` (.6s spinner); `equip-slide-in` (.35s, staggered .05s per card); payback bar width animation (.8s); hover lift `translateY(-2px)` with `shadow-lg` on loop and equipment cards.

### 1.3 Theme

`<html data-theme>` starts from `prefers-color-scheme`. The topbar sun/moon button toggles it and swaps the icon (sun shown in light, moon in dark). On toggle, the Overview charts are rebuilt, plus Time Series and Loops if those pages are visible. Nothing is persisted.

### 1.4 Responsive

At 768px or narrower: the app becomes one column, **the sidebar is hidden (no replacement navigation)**, the charts grid is one column, KPIs are two columns and parameters are one column. At 900px or narrower, the ROI portfolio grid and equipment grid are one column.

Existing app tokens (`web/styles/tokens.css`) are completely different: white paper `#ffffff`, ink `#111827`, **red accent `#b42318`**, sage `#3f6b4f`, line `#e5e7eb`, square 2 to 3px radii, system font and no dark mode. Every token has to be replaced.

---

## 2. App shell

```
.app  grid: [260px sidebar | 1fr main], rows [56px topbar | 1fr]
┌───────────────────────────── topbar (sticky, z100, 56px) ─────────────────────────────┐
│ ◎ Dairy Bioeconomy Simulator ᵛ⁵     [Conventional] (Ready) [▶ Run Simulation] [] │
├────────────┬──────────────────────────────────────────────────────────────────────────┤
│ DASHBOARD  │ main (padding 1.5rem, flex column, gap 1.5rem)                           │
│ ▦ Overview │   page-header: h1 (text-xl 700) + p (muted, max 65ch)                    │
│ ∿ Time …   │   …page content…                                                         │
│ ⟳ Circular │                                                                          │
│ ▮ Compar…  │                                                                          │
│ $ ROI Just │                                                                          │
│ ▮ Cow Rank │                                                                          │
│ ────────── │                                                                          │
│ SETTINGS   │                                                                          │
│  Params   │                                                                          │
│ ⬭ Animal B │                                                                          │
└────────────┴──────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Topbar
- **Logo**: a 28px SVG (circle and cow face) in primary, then the text "Dairy Bioeconomy Simulator" with `<sup>v5</sup>` at .6em and opacity .6. The page `<title>` is "Dairy Bioeconomy Simulator v5.1".
- **Farm pill** `#farmPill`: "Conventional". Background `#01696f`, white text, radius 20px, 12px/700. Clicking it goes back to the landing screen, which is out of scope, so render it static or non-interactive.
- **Status chip** `#statusBadge`: a pill (`radius-full`, text-xs 500). States: `ready` (success-highlight background, success text, "Ready"), `running` (gold-highlight and gold, "Running"), `error` (error-highlight and error, "Error"). After a run its tooltip reads "Individual cow model: Wood's lactation curve + calving cycles + illness + culling".
- **Run Simulation** `#runBtn`: primary background, inverse text, radius md, padding .5rem 1.25rem, 600 weight, play-triangle icon.
  - While running: `.running` (opacity .7, the spinner replaces the icon, disabled).
  - After any parameter edit: `.dirty` (gold background, pulsing gold ring, title "Parameters changed — click to re-run simulation").
  - A successful run clears both.
- **Theme toggle**: 36×36 icon button.

### 2.2 Sidebar (nav only; it holds no parameter controls)
- The section label style is text-xs, 600 weight, uppercase, tracking .06em, faint color.
- The **DASHBOARD** group has Overview, Time Series Charts, Circular Loops, Comparison, ROI Justification and Cow Ranking. A divider (1px, divider color) follows, then the **SETTINGS** group with Parameters and Animal Biology.
- Nav item: padding .5rem 1rem, muted text, 16px icon at opacity .7. Hover uses the surface-offset background. Active uses the primary-highlight background, primary text, 600 weight and icon opacity 1.
- `navigate(id)` toggles `.page-section.active` and rebuilds the charts for the page it opens: charts, loops, the overview charts and revenue summary, or ROI. It then resizes all Chart.js instances. There is no URL routing.

> Note: the Overview copy says "Adjust parameters in the sidebar first". In fact the parameters live on the Parameters page.

### 2.3 Shared components
- `.card`: surface background, 1px border, radius lg, shadow sm. `.card-header` has padding 1rem 1.25rem and a bottom divider; its title is text-sm 600 and its subtitle text-xs muted. `.card-body` has padding 1.25rem. `.chart-wrap` is 260px tall.
- `.kpi-card`: a 32px tinted icon tile (green, teal, gold, blue, orange or red, each a highlight background with a solid foreground), then the label (text-xs muted), then the value (text-lg 700) followed by the unit (text-xs muted). Grid: `repeat(auto-fill,minmax(200px,1fr))`, gap 1rem.
- `.charts-grid`: `repeat(auto-fill,minmax(400px,1fr))`, gap 1.25rem.
- `.empty-state`: centered 48px faint icon, h3 and p (max 36ch).
- Tables: `.data-table`, `.loop-cmp-table` (sticky header and sticky first column) and `.rank-table` (sortable).
- Pills and tabs: `.rank-filter-btn` (full-radius outline; active is primary fill with white text), `.sc-pill` (scenario toggle; selected is primary-highlight), `.cmp-mode-tab`, and `.cmp-chart-tab` (active is primary fill).
- Stale banner `.stale-banner` (Time Series page only): gold-tinted, "Parameters changed — click Run Simulation to update charts".

---

## 3. Page: Overview (`#section-overview`)

1. **Header**: h1 "Farm Overview". p "Run the simulation from the top bar to see results. Adjust parameters in the sidebar first." Farm subtitle (12px, 600, `#01696f`): "Conventional Farm — Standard high-output dairy farm. All 4 circular loops active. TMR feeding, industry-standard inputs."
2. **Farm summary card** `#farmSummaryCard`: surface background, a 1.5px border in `#01696f40`, a 4px left border in `#01696f` and radius lg.
   - Title: "Conventional Farm — Parameters Loaded" (15px, 700, farm color), with the description beneath it.
   - Right-hand chip: "Running simulation…", which becomes "Simulation complete" in success color after the run.
   - For Conventional there are **no** parameter-diff rows or notes.
3. **KPI grid** `#kpiGrid` has 11 cards. Each value is the **daily average over the whole run** (`avg[key]`). Formatting: currency keys use `$x.xx`, `$x.xK` or `$x.xxM`; everything else uses `x.x`, `x.xK` (≥1e4) or `x.xxM`; FCR is shown to 3 decimals.

| # | Label | Unit | Source key | Icon tint |
|---|---|---|---|---|
| 1 | Avg. Daily Milk | L/day | `milk` (herd L/day) | green |
| 2 | Milk Revenue | $/day | `milkRev` | teal |
| 3 | Energy Revenue | $/day | `energyVal` | orange |
| 4 | Heat Value | $/day | `heatVal` | gold |
| 5 | Compost Revenue | $/day | `compostRev` | green |
| 6 | Net GHG/day | kgCO₂e | `netGHG` | teal |
| 7 | Daily Electricity | kWh/day | `totalElec` (biogas and solar) | orange |
| 8 | Daily Biogas | m³/day | `biogasM3` | blue |
| 9 | Net Feed/day | kg/day | `netFeed` | teal |
| 10 | Daily Compost | kg/day | `compost` | green |
| 11 | Feed Conv. Ratio | kg/kg | `netFCR` (mean of daily netFeed/milkKg) | blue |

   Before the first run, the grid shows an empty state: "No simulation data yet · Click Run Simulation in the top bar to generate results."
4. **Revenue Summary card** `#revSummaryWrap`:
   - **Header band** (primary background, white text):
     - Title "Revenue Summary — Simulation Period".
     - Period label: "{n} cows · {years.toFixed(1)} yr ({days} days)".
     - Right side, "GROSS REVENUE": `fmtCurrency(milk+energy+heat+compost)`, subline "before input costs".
     - A vertical divider, then "NET PROFIT" at text-xl 900: `totals.profit`, subline "revenue − feed & water".
   - **Body** is a grid of `1fr auto`:
     - Left side: a 2×2 grid of stream cards, each with a 2px border in its stream color. Each card shows the emoji, the uppercase title in stream color, the total (text-xl 800), "{pct}% of gross" and "$x/day avg".
       - Milk Revenue (primary), Energy Revenue (orange), Heat Value (gold), Compost Revenue (success).
     - Beneath the streams: the "Input Costs Deducted" card (error border), split in two:
       - Feed Cost: "−$x" total and "−$x/day avg".
       - Water Cost: same layout.
     - Right side: a **doughnut chart** (200×200, `responsive:false`, `cutout:'65%'`, 4 segments with fills `color+'cc'` and borders in the solid color, borderWidth 2, hoverOffset 10, legend hidden).
       - The center text reads "GROSS / Revenue".
       - A custom legend below lists Milk, Energy, Heat and Compost, each with its %.
       - Tooltip: "$x (y%)".
5. **Overview charts** `#overviewCharts`, 4 line charts in `.charts-grid`. X axis labels are "Day N" for every simulated day (up to 8 ticks). `pointRadius 0`, tension .3.

| Card title | Subtitle | Datasets |
|---|---|---|
| Daily Milk Production | Litres per day over simulation period | Milk (L/day), primary, filled |
| Daily Revenue | Milk, energy, heat & compost — separate streams | Milk Revenue ($/day) primary; Energy Revenue orange; Heat Value gold; Compost Revenue success (all unfilled) |
| GHG Emissions | Gross vs Net kg CO₂e per day | Gross GHG (kgCO₂e) error; Net GHG success, filled |
| Energy Generation | Biogas + solar electricity kWh/day | Total Electricity (kWh/day) orange, filled |

The page auto-runs on load. `init` calls `runSimulation()`.

---

## 4. Page: Time Series Charts (`#section-charts`)

- Header: "Time Series Charts", with "Daily trends across all major flow and stock metrics."
- Stale banner, shown when parameters are dirty.
- Empty card "No data · Run simulation to see charts."
- Content: `#allChartsGrid` holds **15 single-series filled line charts**, one card each (title only, no subtitle, legend shows the title). The x axis is "Day N" daily.

| id | Title | Series key | Color |
|---|---|---|---|
| ts_milk | Milk Production (L/day) | milk | primary |
| ts_feed | Net Feed Consumed (kg/day) | netFeed | gold |
| ts_water | Net Water Use (L/day) | netWater | blue |
| ts_manure | Manure Output (kg/day) | manure | orange |
| ts_biogas | Biogas Production (m³/day) | biogasM3 | success |
| ts_elec | Total Electricity (kWh/day) | totalElec | orange |
| ts_heat | Heat Recovered (kWh/day) | heat | error |
| ts_compost | Compost Produced (kg/day) | compost | success |
| ts_nrec | Nitrogen Recovered (kg/day) | nRec (compost N only) | primary |
| ts_ghg | Net GHG (kgCO₂e/day) | netGHG | error |
| ts_rev_milk | Milk Revenue ($/day) | milkRev | primary |
| ts_rev_energy | Energy Revenue ($/day) | energyVal | orange |
| ts_rev_heat | Heat Value ($/day) | heatVal | gold |
| ts_rev_compost | Compost Revenue ($/day) | compostRev | success |
| ts_fcr | Feed Conversion Ratio (kg/kg) | netFCR | blue |

There is no period switcher (daily only) and no grouping.

---

## 5. Page: Circular Loops (`#section-loops`)

- Header: "Circular Bioeconomy Loops", with "Average daily resource flows through the four circular loops of the dairy bioeconomy system."
- Before the first run: an empty card.
- **Loop hero cards** `.loops-hero-grid` (`minmax(260px,1fr)`). Each `.lhc` card contains:
  - a 44px emoji icon tile in the loop highlight color;
  - a badge ("Loop N", uppercase, loop color), a title and a subtitle;
  - a 3px gradient accent bar;
  - the hero stat (value at weight 900 in loop color, unit and label);
  - metric rows (name on the left, value on the right, 700 weight).

  All values are daily averages.

| Loop | Title / subtitle | Hero (value · unit · label) | Rows |
|---|---|---|---|
| L1 green | Manure Separator / "Solid fraction → compost + N/P/K → cropland → feed offset" | compost+digestate+sludgeFertilizer · kg/day · "Total organic fertilizer to cropland" (1 dp) | Feed offset from nutrients (kg/day, 1dp); Nitrogen recovered, Phosphorus recovered, Potassium recovered (kg/day, 2dp; compost path only); Digestate applied (kg/day) |
| L2 blue | Water Cycle / "Wastewater treatment → irrigation → fresh-water offset" | recycledIrrig · L/day · "Recycled irrigation water" (integer, locale) | Wastewater treated; Fresh water offset; Net water draw (L/day) |
| L3 orange | Energy / Biogas / "Manure → anaerobic digester → electricity + heat" | totalElec · kWh/day · "Total electricity (biogas + solar)" | Biogas produced (m³/day); Heat recovered (kWh/day); Digestate → fertilizer (kg/day) |
| L4 purple | Dairy Byproduct / "Whey + waste milk → animal feed + functional foods" | feedReturn · kg/day · "Feed return from byproducts" | Whey → functional foods (L/day) = avg.whey × 0.5; Sludge → fertilizer (kg/day) |

- **Nutrient Pool Over Time** card. Subtitle: "Soil nutrient pool builds over 90-day lag, then depletes seasonally — high uptake in summer, near-zero in winter".
  - Line chart, downsampled to 1 point per 7 days. X labels are "Yr N" at the start of each year and blank otherwise.
  - Datasets:
    - Soil Nutrient Pool (kg): success, filled, tension .4, left `y` axis titled "Nutrient Pool (kg)", ticks shown as `k`.
    - Daily Organic Input (kg): orange, dash `[5,4]`, right `y1` axis titled "Daily kg".
    - Feed Offset / day (kg): primary, dash `[2,3]`, `y1`.
  - Interaction `index`, not intersecting. The tooltip title reads "Year N, ~Mon (Day d)".

---

## 6. Page: Comparison (`#section-compare`)

- Header: "Circular Loop Comparison", with "Simulate all 16 loop combinations and compare their economic and environmental outcomes."
- **Loop key bar** `.cmp-loop-key` shows four 26px chips: L1 Manure Separator (green), L2 Water Cycle (blue), L3 Energy / Biogas (orange), L4 Dairy Byproduct (purple). A **Run Analysis** button (a `.run-btn` with spinner) is pushed to the right.
- **Run Analysis** runs **16 full simulations** with the same seed and herd, toggling `activeLoops` for each:
  - Baseline, with no loops (Reference group);
  - L1, L2, L3 and L4 (Individual);
  - L1+L2, L1+L3, L1+L4, L2+L3, L2+L4 and L3+L4 (2-Loop Combo);
  - L1+L2+L3, L1+L2+L4, L1+L3+L4 and L2+L3+L4 (3-Loop Combo);
  - All 4 (All 4 Loops, "Full circular economy").

  Each scenario has a short description (for example "Nutrient+Water").
- **Summary strip** (3 `.cmp-stat` tiles):
  - "All-4 Net Profit Change": ±$ vs Baseline over the period, green when ≥0.
  - "Best Profit Scenario": the scenario label, with "+$x vs Baseline".
  - "All-4 GHG Change": −x kg CO₂e ("net emissions over simulation period").
- **Table card**:
  - Mode tabs: **A "Baseline + Selected"** (default) and **B "Pairwise A vs B"**.
  - Mode A controls: "Scenarios:" pills for the 15 non-baseline scenarios, each with chips and label. The default selection is L1, L2, L3 and L4; clicking toggles a pill. Then "Show:" All, Gains or Savings (filters rows by whether they contain a positive or negative delta).
  - Mode B controls: two `<select>`s. The options are grouped with optgroups, defaulting to Baseline vs All 4.
  - Table title and subtitle: Mode A reads "Baseline + Selected Scenarios · Baseline always pinned · Δ = change vs Baseline · tick scenarios above to add/remove". Mode B reads "{A} vs {B} · Side-by-side · Δ = B minus A (absolute + %)".
  - Columns:
    - Mode A: Metric, Baseline ("— reference"), then one column per selected scenario showing the value and a Δ line (abs and %, green when favourable, magenta when not). The All 4 column is highlighted with the primary tint.
    - Mode B: Metric, A, B, then "Δ (B − A)" with abs and %.
  - Header cells carry the loop chips and the loop-colored header background (`col-l1` to `col-l4`, `col-combo2` gold-tint, `col-combo3` warning-tint, `col-all4` primary).
  - **Rows**, grouped by section rows. Values are period totals unless marked *avg*. `$` values have no decimals, and kg, L, m³ and kWh are integers.
    - REVENUE: Milk Revenue ($), Energy Revenue ($), Heat Revenue ($), Compost Revenue ($), **Total Revenue ($)**, Feed Cost ($, lower is good), Water Cost ($, lower is good), **Net Profit ($)**.
    - LOOP 2 — WATER CYCLE: Water Credit Applied (L), Fresh-Water Offset Queued (L), Recycled Irrigation (L), Net Water Draw (L, lower is good).
    - LOOP 1 & 4 — FEED SAVINGS: Net Feed Input (kg, lower is good), Nutrient Feed Offset (kg), Byproduct Feed Return (kg).
    - CIRCULAR LOOP OUTPUT: Organic Fertilizer (kg), Compost Produced (kg), Biogas Produced (m³), Total Electricity (kWh), Heat Generated (kWh).
    - WASTE & NUTRIENT RECOVERY: Nitrogen Recovered, Phosphorus Recovered and Potassium Recovered (kg; compost plus wastewater).
    - ENVIRONMENTAL: Net GHG (kg CO₂e, lower is good), Gross GHG (lower is good), Grid GHG Avoided.
    - DAILY AVERAGES: Avg Daily Milk (L) *avg*, Avg Net FCR (kg/kg, 3dp, lower is good) *avg*, Avg Gross FCR *avg*.
- **Chart card** "Net Profit vs Baseline" with tabs Profit, Revenue, Feed Savings, Water Savings and GHG.
  - A bar chart (280px) of the **Δ vs reference** for each selected scenario (Mode A) or for A and B (Mode B).
  - Bar colors by group: Individual teal, 2-combo gold, 3-combo orange, All-4 green. Mode B uses teal and orange. `borderRadius 4`.
  - A dashed zero rule labelled "Baseline", drawn by the plugin in Mode A only.
  - Y axis formats: `$Nk` for profit and revenue, `$` for feed and water, `N.Nt` for GHG.
  - Titles: Net Profit vs Baseline, Total Revenue vs Baseline, Feed Cost Savings vs Baseline, Water Cost Savings vs Baseline, GHG Reduction vs Baseline.
- **Two side-by-side cards**:
  - "Performance Radar · Normalised across 5 dimensions": a radar (300px) with axes Net Profit, Revenue, Feed Savings (Δ netFeed kg), Water Savings (Δ waterCost), GHG Reduction. Each axis is normalised to 0 to 100 against the maximum across the 15 non-baseline scenarios. Palette `['#01696f','#da7101','#27ae60','#2980b9','#8e44ad','#c0392b','#e67e22','#16a085']`, legend on the right.
  - "Avg Profit Gain by Group · Mean gain vs Baseline per loop group": a horizontal bar chart of Individual, 2-Loop, 3-Loop and All 4, colored teal, gold, orange and green, `borderRadius 6`.

> Important semantics: for Conventional, the normal Overview run uses **all 4 loops on**. "Baseline" exists only here, as a separate **no-loop** scenario.

---

## 7. Page: ROI Justification (`#section-roi`)

- Header: "Equipment ROI Justification". p: "Per-equipment financial defence for every capital addition…". The farm banner (a 4px `#01696f` left border on surface-offset) reads "**Conventional Farm** · Standard high-output dairy farm. All 4 circular loops active. TMR feeding, industry-standard inputs."
- **Assumption inputs bar** (surface-offset panel). Number inputs with `oninput` trigger a live recalculation:
  - Discount Rate (%): 7 (range 0 to 30, step .5).
  - Equipment Lifespan (yrs): 15 (1 to 40, step 1).
  - Install & Commissioning (%): 15 (0 to 50, step 1).
  - Annual Maintenance (%): 2 (0 to 10, step .5).
  - A "↻ Recalculate" button.
- Before the first run: an empty card.
- **Portfolio banner** (primary background, radius xl):
  - Title "Total Equipment Portfolio", subline "{8} equipment items · {5}-year simulation · herd of {100}".
  - KPIs, separated by dividers:
    - Total CapEx ("incl. install");
    - Total Annual Benefit ("$/year across all equipment", which is actually the sum of **annual net**);
    - Blended Payback ("N.N yrs", "simple recovery");
    - Portfolio NPV ("at 7.0% · 15yr").
- **Two charts** (grid `1.4fr 1fr`, 280px):
  - "Payback Timeline by Equipment · Cumulative net benefit vs capital cost over lifespan": a line chart with one line per equipment item, `−capex + annualNet×year` for years 0 to L (labels Y0 to YL), plus a dashed "Break-even" line at 0. Palette `#01696f, #437a22, #006494, #da7101, #7a39bb, #d19900`, which cycles.
  - "Annual Benefit Breakdown · $/year contribution per equipment item": grouped bars, "Annual Benefit" (colored) and "Annual Maint." (negative, magenta at .35). Labels are the first 2 words of each name.
- **Equipment cards** `.equip-roi-grid` (`minmax(340px,1fr)`). Each card has:
  - a header (48px emoji tile, badge "{Lx} — {Energy Loop | Water Loop | Dairy Loop | Nutrient Loop | Precision Tech}", name and description);
  - an accent bar;
  - a 3-cell KPI row (Total CapEx; Annual Net, green or red; {L}yr NPV, green or red);
  - metric rows specific to the item, followed by "Annual ROI" (+x.x%) and "Lifetime ROI ({L}yr)" (+x%);
  - a payback bar ("Payback: N.N yrs" or "> lifespan", with "{L}yr lifespan"; fill = min(100, L/payback×100)%);
  - a verdict strip: good (green), warn (warning) or bad (error), with text chosen by payback.

  The 8 items are listed in section 10.4.
- Methodology note (surface-offset box): "How values are calculated: … ROI = (Lifetime Benefit − Total CapEx) / Total CapEx × 100. NPV discounts annual net benefit … Payback = Total CapEx ÷ Annual Net Benefit."

---

## 8. Page: Cow Ranking (`#section-ranking`)

- Header: "Cow Efficiency Ranking". The p for Conventional is: "Every cow in the herd ranked by Feed Conversion Ratio (FCR) — kg of feed per **kg** of milk produced. Lower FCR = more efficient cow. Efficiency % is scored within the herd's actual FCR spread (1–99%). Tiers: Elite ≥ 80% · Good 60–79% · Average 35–59% · Poor < 35%."
- **Control card**:
  - "Generate Individual Cow Rankings", with a subtitle. After generation it reads "{N} active cows ranked ({k} replaced cows hidden · {m} never-milked excluded) · {n} herd · {days} days · Wood's curve + calving cycles".
  - A checkbox, "Show all lifetime cows (including replaced)".
  - A **Generate Rankings** button (`.run-btn` with spinner).
  - For Conventional, the ranking reuses the herd from the last main run when herd size and days match; otherwise it re-simulates the herd.
- **KPI row** (4 `.kpi-card`s, value text-lg 800 in color):
  - Best FCR Cow: the cow ID, subline "0.xxx kg/kg" (primary).
  - Herd Avg FCR: "0.xxx", subline "kg feed per kg milk" (gold).
  - Avg Milk / Cow: "xx.x L", subline "per cow per milking day" (success).
  - Elite Cows: the count, subline "x% of all cows" (orange).
- **Tier filter**: "Filter by tier:" then All Cows, Elite, Good, Average, Poor. A right-hand hint reads "Click column headers to sort".
- **Rank table** (click a header to sort; the first click is ascending for rank and FCR and descending for everything else; icons ⇅, ▲ and ▼):
  - Columns: Rank (a 28px round badge: gold `#FFD700`, silver `#C0C0C0`, bronze `#CD7F32`, otherwise surface-offset) · Cow ID (e.g. `C00001`, bold) · Parity · Body Wt (kg) · Avg Milk L/day (per milking day, primary bold, 2dp) · Avg Feed (kg/day, 2dp) · Avg Water (L/day, 1dp) · Avg Manure (kg/day, 2dp) · FCR (kg/kg, 3dp; primary when elite, error when poor) · Dairy Rev ($/day, success) · GHG (kgCO₂e/day) · Efficiency (1–99%) · Tier.
  - The Efficiency cell is a 6px bar whose width is the efficiency % (primary when ≥80, gold when ≥60, error otherwise) followed by the % text.
  - The Tier cell is a pill: elite uses primary-highlight, good success-highlight, avg gold-highlight and poor error-highlight.
- **Two charts**:
  - "FCR vs Milk Yield per Cow · Lower FCR + higher milk = top performer": a scatter with x = Avg Milk (L/milking day) and y = FCR (kg/kg). Points are colored by tier (elite primary, good success, avg gold, poor error); radius = clamp(120/N, 3, 7). The legend shows the tier labels. Tooltip: "C0xxxx · tier" and "Milk … | FCR …".
  - "Top 20 — Daily Milk Revenue · Highest revenue cows, coloured by tier": bars labelled by cow ID, y titled "Milk Revenue ($/day)".

---

## 9. Pages: Parameters and Animal Biology

### 9.1 Parameters (`#section-params`)
- Header: "Simulation Parameters", with "Adjust all bioeconomy model parameters. Changes take effect on the next simulation run."
- A "JUMP TO SECTION" pill navigator (smooth-scrolls to each group).
- `.params-layout` is `repeat(auto-fill,minmax(320px,1fr))`. Each `.param-group` has an uppercase header (surface-offset) with an emoji and title.
- Controls:
  - **Slider**: the label, with a monospace primary value on the right, then a range input (accent primary), then an optional hint.
  - **Number**: a text input.
  - **Toggle**: a 40×22 switch.
- Value display (`formatParamVal`): keys containing `fraction` or `cull`, plus `methane_reduction_factor`, show as `NN%` when between 0 and 1; `probability` shows as `N.NN%`; integers as integers; values below .01 to 4dp, below .1 to 3dp, below 10 to 2dp, otherwise 1dp.
- Any change marks the dashboard dirty (Run button pulse and stale banner). Setting `separator_solid_fraction` also sets `liquid = 1 − solid`.
- Buttons: "▶ Run with These Parameters" and "Reset to Defaults" (outline).

Conventional defaults (preset `overrides: {}`, so these are the `DEFAULTS` values):

| Group | Key · label | Type | Default | Min to max (step) |
|---|---|---|---|---|
| Herd & Simulation Setup | number_of_cows · Number of Cows | number | 100 | 1 to 5000 (10) |
| | simulation_years · Simulation Years | number | 5 | 1 to 30 (1) |
| | random_seed · Random Seed | number | 42 | 0 to 99999 (1) |
| | enable_random_daily_variation · Random Daily Variation | toggle | on | |
| | enable_seasonal_profile · Seasonal Profile | toggle | on | |
| | enable_dynamic_loop_feedback · Dynamic Loop Feedback | toggle | on | |
| Per-Cow Daily Rates (all "▸ Reference", which do not drive output) | milk_yield_L_per_cow_per_day | slider | 28 | 10 to 80 (1) |
| | feed_intake_kg_per_cow_per_day | slider | 22 | 10 to 50 (.5) |
| | water_use_L_per_cow_per_day | slider | 120 | 50 to 250 (5) |
| | manure_output_kg_per_cow_per_day | slider | 55 | 20 to 100 (1) |
| Smart Technology | smart_tech_feed_efficiency_factor | slider | 1.0 | 0.5 to 2 (.05) |
| | smart_tech_water_efficiency_factor | slider | 1.0 | 0.5 to 2 (.05) |
| | smart_tech_milk_yield_factor | slider | 1.0 | 0.5 to 2 (.05) |
| | health_feed_efficiency_factor · Health Feed Factor | slider | 1.0 | 0.5 to 2 (.05) |
| | health_milk_yield_factor · Health Milk Factor | slider | 1.0 | 0.5 to 2 (.05) |
| | methane_reduction_factor | slider | 1.0 | 0.1 to 1.5 (.05) |
| Manure Management | manure_to_treatment_fraction · Fraction to Treatment | slider | 1.0 | 0 to 1 (.05) |
| | separator_solid_fraction · Solid Fraction (→ Compost) | slider | 0.35 | 0.1 to 0.9 (.05) |
| | biogas_m3_per_kg_manure_to_digester · Biogas Yield | slider | 0.025 | 0.005 to 0.08 (.005) |
| | compost_kg_per_kg_manure_to_compost · Compost Yield | slider | 0.40 | 0.1 to 0.8 (.05) |
| Energy | electricity_kWh_per_m3_biogas | slider | 2.0 | 0.5 to 4 (.1) |
| | heat_kWh_per_m3_biogas | slider | 2.5 | 0.5 to 5 (.1) |
| | solar_electricity_kWh_per_cow_per_day | slider | 0.5 | 0 to 5 (.1) |
| Milk Processing | fraction_milk_to_processor | slider | 1.0 | 0 to 1 (.05) |
| | fraction_dairy_products_of_milk | slider | 0.85 | 0.5 to 1 (.05) |
| | fraction_whey_of_milk · Whey Fraction (Legacy) | slider | 0.10 | 0 to 0.3 (.01) |
| | fraction_whey_to_animal_feed_loop · Whey → Feed Loop | slider | 0.50 | 0 to 1 (.05) |
| Milk Market & Pricing | fraction_milk_to_cheese | slider | 0.40 | 0 to 1 (.05) |
| | fraction_milk_to_butter | slider | 0.20 | 0 to 1 (.05) |
| | fraction_milk_to_yogurt | slider | 0.15 | 0 to 1 (.05) |
| | fraction_milk_to_fresh | slider | 0.15 | 0 to 1 (.05) |
| | fraction_milk_to_functional | slider | 0.10 | 0 to 1 (.05) |
| | price_per_L_milk_cheese | number | 0.90 | 0.1 to 5 (.05) |
| | price_per_L_milk_butter | number | 0.60 | 0.1 to 5 (.05) |
| | price_per_L_milk_yogurt | number | 0.75 | 0.1 to 5 (.05) |
| | price_per_L_milk_fresh | number | 0.45 | 0.1 to 3 (.05) |
| | price_per_L_milk_functional | number | 1.20 | 0.1 to 10 (.1) |
| Economics | feed_cost_per_kg | slider | 0.22 | 0.05 to 0.8 (.01) |
| | water_cost_per_L | slider | 0.0008 | 0.0001 to 0.005 (.0001) |
| | milk_price_currency_per_L (**unused by revenue**) | slider | 0.45 | 0.1 to 3 (.01) |
| | electricity_price_currency_per_kWh | slider | 0.16 | 0.01 to 0.5 (.01) |
| | compost_value_currency_per_kg | slider | 0.05 | 0 to 0.2 (.005) |
| | heat_value_currency_per_kWh | slider | 0.06 | 0 to 0.2 (.005) |
| GHG & Climate | enteric_methane_kg_co2e_per_cow_per_day | slider | 5.0 | 1 to 15 (.5) |
| | manure_n2o_kg_co2e_per_kg_manure | slider | 0.008 | 0 to 0.05 (.001) |
| | grid_avoided_kg_co2e_per_kWh | slider | 0.40 | 0.1 to 1 (.05) |
| | biogas_methane_displacement_kg_co2e_per_m3 | slider | 1.5 | 0.5 to 3 (.1) |
| Land Resources (not used in the math) | land_cropland_ha | slider | 80 | 0 to 500 (5) |
| | land_pasture_ha | slider | 40 | 0 to 500 (5) |
| | soil_carbon_sequestration_index | slider | 1.0 | 0.5 to 2 (.1) |
| | land_silvopastoral_tree_cover_fraction | slider | 0.05 | 0 to 0.5 (.01) |
| Variability | daily_variation_std_fraction | slider | 0.08 | 0 to 0.3 (.01) |
| | seasonal_amplitude_fraction | slider | 0.12 | 0 to 0.4 (.01) |
| | milk_manure_correlation | slider | 0.65 | 0 to 1 (.05) |
| Animal Biology (Wood's Curve) | wood_b | slider | 0.20 | 0.05 to 0.5 (.01) |
| | wood_c | slider | 0.0055 | 0.001 to 0.02 (.0005) |
| | mature_parity | number | 3 | 2 to 6 (1) |
| | cow_peak_std_fraction | slider | 0.12 | 0 to 0.3 (.01) |
| Health & Culling | illness_duration_days_mean | slider | 4.0 | 1 to 14 (.5) |
| | illness_feed_penalty_fraction | slider | 0.15 | 0 to 0.5 (.05) |
| Body Weight & Intake | maintenance_dmi_fraction_of_bw | slider | 0.020 | 0.01 to 0.04 (.001) |
| | dmi_kg_per_L_milk | slider | 0.30 | 0.1 to 0.6 (.01) |
| | manure_kg_per_kg_dmi | slider | 2.0 | 0.5 to 4 (.1) |
| | water_base_L | slider | 15 | 5 to 40 (1) |
| | water_L_per_kg_dmi | slider | 3.5 | 1 to 8 (.5) |
| | water_L_per_L_milk | slider | 1.0 | 0.2 to 3 (.1) |
| | water_seasonal_amplitude | slider | 0.15 | 0 to 0.4 (.01) |

Hidden defaults that exist but have no control: `days_per_year 365`, `daily_variation_min/max_multiplier 0.70/1.30`, `seasonal_peak_day_of_year 120`, `nutrient_pool_daily_use_fraction 0.03`, `nutrient_pool_max_kg 250000`, `fraction_forage_silage_of_feed 0.70`, `fraction_alternative_byproduct_feed 0.15`, `separator_liquid_fraction 0.65`, `digestate_kg_per_kg_manure_to_digester 0.90`, `nitrogen/phosphorus/potassium_kg_per_kg_manure_to_compost 0.005/0.002/0.006`, `fraction_whey_to_functional_foods_bioproducts 0.50`, `whey_volume_L_per_L_cheese_milk 0.85`, `whey_volume_L_per_L_yogurt_milk 0.75`, `fraction_sludge_of_milk 0.02`, `fraction_waste_milk_of_milk 0.03`, `fraction_waste_milk_to_animal_feed_loop 0.70`, `fraction_waste_milk_to_biogas 0.30`, `fraction_sludge_to_biogas 0.50`, `fraction_sludge_to_fertilizer 0.50`, `fraction_water_to_wastewater 0.80`, `fraction_wastewater_recycled_to_irrigation 0.70`, `wastewater_n/p/k_recovery_kg_per_L 0.0001/0.00005/0.00008`, `nutrient_loop_feed_substitution_fraction 0.10`, `water_loop_fresh_water_offset_fraction 0.70`, `energy_loop_external_energy_offset_fraction 0.20`, `byproduct_loop_feed_substitution_kg_per_kg 0.80`, `milk_density_kg_per_L 1.03`, `water_peak_day_of_year 200`, `gestation_days 283`.

### 9.2 Animal Biology (`#section-animal`)
- Header: "Animal Biology Parameters", with "Configure individual cow lactation, health, reproduction, and body-weight assumptions (Wood's curve model)."
- Same control styles as 9.1. Some keys also appear on the Parameters page, and both controls write the same `cfg` key.
- Button: "▶ Run with These Parameters".

| Group | Key · label | Type | Default | Range (step) |
|---|---|---|---|---|
| Lactation — Wood's Curve | peak_milk_L_first_parity · Peak Milk 1st Parity (L/day) | slider | 38 | 15 to 70 (1) |
| | peak_milk_L_mature · Peak Milk Mature Cow (L/day) | slider | 50 | 20 to 80 (1) |
| | lactation_length_days | slider | 305 | 200 to 400 (5) |
| | dry_period_days | slider | 60 | 30 to 120 (5) |
| | wood_b · Wood's b (rise to peak) | slider | 0.20 | 0.05 to 0.5 (.01) |
| | wood_c · Wood's c (post-peak decline) | slider | 0.0055 | 0.001 to 0.02 (.0005) |
| | mature_parity | number | 3 | 2 to 6 (1) |
| | max_parity · Max Parity (cull threshold) | number | 6 | 2 to 12 (1) |
| | cow_peak_std_fraction · Cow-to-Cow Peak Variation (σ) | slider | 0.12 | 0 to 0.3 (.01) |
| Health & Disease | daily_illness_probability | slider | 0.004 | 0 to 0.05 (.001) |
| | illness_duration_days_mean | slider | 4.0 | 1 to 14 (.5) |
| | illness_milk_penalty_fraction | slider | 0.35 | 0 to 0.8 (.05) |
| | illness_feed_penalty_fraction | slider | 0.15 | 0 to 0.5 (.05) |
| Reproduction & Culling | annual_involuntary_cull_fraction | slider | 0.12 | 0.01 to 0.40 (.01) |
| Body Weight & Intake | bodyweight_first_parity_kg · Heifer Body Weight | slider | 540 | 300 to 800 (10) |
| | bodyweight_mature_kg | slider | 680 | 400 to 1000 (10) |
| | maintenance_dmi_fraction_of_bw, dmi_kg_per_L_milk, manure_kg_per_kg_dmi, water_base_L, water_L_per_kg_dmi, water_L_per_L_milk, water_seasonal_amplitude | slider | as 9.1 | as 9.1 |

---

## 10. Simulation math (what the backend must match or replace)

All of this runs in the browser for every day `d = 1..round(years×365)` (1,825 days by default). The random generator is xorshift32 seeded with `random_seed`. Normal draws use Box-Muller. Daily multipliers use an Irwin-Hall approximation, `z = (Σ4 U − 2)/√2`.

### 10.1 Herd model (per cow, per day)
- **Initialisation**: n cows. Parity is sampled with weights [.33, .25, .18, .12, .08, .04] (truncated at max_parity). `cycleDay ~ U{1..(305+60)}`. `peakFactor = max(0.4, N(1, 0.12))`. IDs run `C00001` upward.
- **Cycle**: `cycleDay++`. When the cycle passes `lactation+dry` (365 days), `parity++` and `cycleDay = 1`. Parity above `max_parity` is culled (`max_parity`). Otherwise the cow is culled at daily probability `1 − (1−0.12)^(1/365)` (involuntary). A culled cow is replaced by a new heifer: parity 1, cycleDay 1 and a new peakFactor.
- **Milking** when `cycleDay ≤ 305` and the cow is not culled.
- **Illness**: a healthy cow falls ill at `p = 0.004`/day. Duration is `max(1, round(−4·ln U))` days.
- **Wood's curve**: `shape = dim^b · e^(−c·dim)`, normalised by `(b/c)^b · e^(−b)`.
  - `peak(parity)` is 38 at parity ≤1 and 50 at parity ≥3; parity 2 is linear between them.
  - `milk = peak·peakFactor·shape/norm × (1−0.35 if sick) × smartMilk × healthMilk × herdMilkScale(=28/28=1) × seasonMilk × dailyMult`.
  - `seasonMilk = 1 + 0.12·cos(2π(doy−120)/365)` and `seasonManure = 1 + 0.06·cos(…)`.
  - `dailyMult = clip(1 + z·0.08, 0.7, 1.3)`.
- **Body weight**: 540 at parity 1 and 680 at parity ≥3, linear in between.
- **DMI**: `(BW·0.020 + 0.30·milk)·(1 − 0.15 if sick) / (smartFeed·healthFeed)`.
- **Water**: `(15 + 3.5·DMI + 1.0·milk)·(1 + 0.15·cos(2π(doy−200)/365)) / smartWater`.
- **Manure**: `DMI·2.0·seasonManure·dailyMult^0.65`.
- **Herd totals**: the sums of milkL, feedKg (= DMI), waterL and manureKg.

### 10.2 Daily bioeconomy flows (`simulateDay`, all 4 loops on for Conventional, feedback on)

Notation: `mix` is the product fractions normalised to sum to 1 (0.40, 0.20, 0.15, 0.15, 0.10).

- **Processing**:
  - `proc = milk·1.0`, `processed = proc·0.85`.
  - `whey = processed·(0.40·0.85 + 0.15·0.75)`, falling back to `proc·0.10`.
  - `sludge = proc·0.02` L and `wasteMilk = proc·0.03` L. Their kg values are the litres ×1.03.
- **Manure**: `treated = manure·1.0`, `solid = treated·0.35`, `liquid = treated·0.65`.
- **L4**:
  - `wheyToFeed = whey·0.5` and `wasteToFeed = wasteMilk·0.70`.
  - `feedReturn = (wheyToFeed + wasteToFeed)·1.03·0.80` kg. This is **queued as a feed credit for later days**.
  - `sludgeBiogas = sludgeKg·0.5`, `wasteMilkBiogas = wasteKg·0.3`, `sludgeFertilizer = sludgeKg·0.5`.
- **L1 compost**: `compost = solid·0.40`, `nRec = solid·0.005`, `pRec = solid·0.002`, `kRec = solid·0.006`.
- **L3**:
  - `biogasM3 = liquid·0.025` and `digestate = liquid·0.90`.
  - `totalBiogas = biogasM3 + (sludgeBiogas + wasteMilkBiogas)·0.025`.
  - `elec = totalBiogas·2.0`, `heat = totalBiogas·2.5` kWh.
  - `solar = 0.5·n` (**always on, whatever the loop state**), `totalElec = elec + solar`.
  - The energy credit queue (20% of totalElec) is tracked but **never used in the economics**.
- **L2 water**:
  - `wastewater = waterBase·0.80`, `recycledIrrig = wastewater·0.70`, `freshOffset = recycledIrrig·0.70`. freshOffset is queued, so the credit applies the next day.
  - `wN/wP/wK = wastewater·(1e−4, 5e−5, 8e−5)`.
- **L1 nutrient pool**:
  - `organicFert = compost + sludgeFertilizer + digestate`.
  - organicFert enters a **90-slot ring buffer**. The value leaving it (from 90 days earlier) is added to `pool` (capped at 250,000 kg).
  - `season = max(0.05, 0.5 + 0.5·sin(2π(doy−80)/365))`.
  - `feedOffset = min(pool·0.03·season, feedDemand·0.10)`, and `pool −= feedOffset`.
- **Credits applied today**: `feedCredit = min(byproductQueue, feedDemand)` and `waterCredit = min(waterQueue, waterBase)`.
- **Net inputs**: `netFeed = max(0, feedDemand − feedCredit − feedOffset)` and `netWater = max(0, waterBase − waterCredit)`.
- **Recovered nutrients**: `nRecTotal = nRec + wN`, and likewise for P and K.
- **GHG**:
  - `enteric = n·5.0·methaneReduction`, `manureGHG = manure·0.008`, `grossGHG = enteric + manureGHG`.
  - `avoidedGrid = totalElec·0.40`, `biogasDispl = totalBiogas·1.5`.
  - `netGHG = max(0, gross − avoidedGrid − biogasDispl)`.
- **Economics**:
  - `blendPrice = Σ mix_i·price_i` = 0.40·0.90 + 0.20·0.60 + 0.15·0.75 + 0.15·0.45 + 0.10·1.20 = **$0.78/L**. (The `milk_price_currency_per_L` 0.45 control is ignored.)
  - `milkRev = milk·blendPrice` (on **all** milk, not only the processed fraction).
  - `energyVal = totalElec·0.16`, `heatVal = heat·0.06`, `compostRev = compost·0.05`.
  - `feedCost = netFeed·0.22`, `waterCost = netWater·0.0008`.
  - `totalRevenue = milkRev + energyVal + heatVal + compostRev`.
  - `profit = totalRevenue − feedCost − waterCost`. **There are no labour, fixed, vet or energy-use costs.**
- **FCR**: `netFCR = netFeed/(milk·1.03)` and `grossFCR = feedDemand/(milk·1.03)`, both in kg/kg.
- **Aggregation**: `totals[k] = Σ daily`, `avg[k] = totals/days`. KPI aliases: `feed = netFeed`, `biogas = biogasM3`, `fcr = netFCR`, `water = netWater`, `wheyFoods = avg.whey·0.5`.

### 10.3 Comparison
The same `runSim` runs with `activeLoops` per scenario. With a loop off, its branch values are 0:
- L1 off: no compost, NPK, organicFert, pool or feedOffset.
- L2 off: no wastewater, credits or offsets.
- L3 off: no biogas, elec or heat (solar remains).
- L4 off: no feedReturn or sludge flows.

Each Δ is `scenario − baseline` (or `B − A`).
- Δ % is `diff/|base|·100`.
- The favourable direction per metric is set by `sign` (higher-good or lower-good), as listed in section 6.
- Summary best scenario = the `argmax(totals.profit − base.totals.profit)` over the 15 non-baseline scenarios.
- Group average = the mean profit gain within each group.
- Radar normalisation: `max(0, v / max_over_15 · 100)`.

### 10.4 Equipment ROI (Conventional branch; `T` = totals, `Y` = simulation years, `n` = herd)

For each item:
- `capex = capitalFn(n)·(1 + install%)`
- `annualNet = annualBenefit − capex·maint%`
- `payback = capex/annualNet` (999 when ≤0)
- `NPV = −capex + Σ_{t=1..L} annualNet/(1+r)^t`
- `lifetimeROI = (annualNet·L − capex)/capex·100`
- `annualROI = annualNet/capex·100`

Portfolio values:
- Total CapEx = Σ capex.
- "Total Annual Benefit" = Σ annualNet.
- Blended payback = Σcapex/ΣannualNet.
- Portfolio NPV = Σ NPV.

| Item (loop, icon) | capitalFn(n) | Annual benefit ($/yr) | Card metric rows | Verdict (ROI thresholds) |
|---|---|---|---|---|
| Anaerobic Biodigester (L3 ) | 700·n | digestate/Y·(0.005·1.20 + 0.002·2.50) + (biogasM3/Y/0.025/1000)·3 + (biogasM3/Y·1.5/1000)·30 | Biogas Produced/yr; Avg Biogas Output m³/day; Digestate N+P Value/yr; Digestate Produced/day; Manure Disposal Saved/yr; Carbon Credits/yr | good >80, warn >20 |
| Biogas CHP Engine (L3 ) | max(50000, (n·55·0.65·0.025·2/24)·3500)·1.15 (**install applied twice**) | E·p_e + H·p_h + 0.25·E·p_e + (avoidedGrid/Y/1000)·30 + 0.05·E·p_e, with E = elec/Y and H = heat/Y | Electricity Generated/yr; Heat Generated/yr; Avg Electrical Capacity kWe; Avoided Grid Cost/yr; Heat Value/yr; Grid CO₂e Avoided/yr; Carbon Credits/yr; Combined Efficiency "~75%" | good >60, warn >15 |
| Manure Separator (L1 ) | max(15000, 180·n) | compostRev/Y + (N+P+K totals)/Y·0.80 + feedCost/Y·0.08 + organicFert/Y·0.015 | Compost Revenue/yr; N+P+K Fertilizer Value/yr; Feed Cost Offset/yr; Compost Produced kg/day; N/P/K Recovered/yr | good >150, warn >40 |
| Solar PV Array (L3 ) | max(30000, 350·n) | S·p_e + S·0.40/1000·30 + 0.05·S·p_e, with S = solar/Y | Solar kWh/yr; Avoided Grid Cost/yr; Carbon Credits/yr; Grid CO₂e Avoided/yr; Avg Solar Output/day | good >50, warn >10 |
| Whey Processing Unit (L4 ) | max(40000, 280·n) | feedReturn/Y·0.22 + (wheyToFeed + wasteToFeed)/Y/1000·40 + whey/Y·0.5·0.08 | Feed Return Value/yr; Whey to Feed/yr L; Waste Milk to Feed/yr L; Waste Disposal Saved/yr; Whey Processed/day | good >60, warn >15 |
| Water Recycling System (L2 ) | max(25000, 220·n) | recycledIrrig/Y·p_w·2.5 + freshOffset/Y·p_w + recycledIrrig/Y/1000·0.5 + (wN+wP+wK)/Y·0.80 | Irrigation Water Value/yr; Fresh Water Avoided/yr L; Treatment Cost Saved/yr; Nutrient Recovery Value/yr; Water Recycled/day | good >60, warn >10 |
| Smart Feed & Health Sensors (L1 , "Precision Tech") | max(20000, 120·n) | milkRev/Y·max(0, smartMilk−1) + feedCost/Y·max(0, 1−smartFeed) + 50·n + milkRev/Y·0.015 | Milk Uplift/yr; Feed Savings/yr; Vet Cost Savings/yr; Reduced Culling Benefit/yr; Milk Revenue (simulated)/yr | good >150, warn >50 |
| Beef-on-Dairy Program (L4 ) | max(3000, 35·n) | 0 on Conventional (card still shown: "Switch to Beef-on-Dairy farm type") | Cross-breed fraction; Bull calves sold/yr; Value per weaner; Gross calf revenue/yr; Active on this farm | good >200, warn >50 |

The verdict text is chosen by payback bands, for example the digester: ≤6 "Excellent…", ≤12 "Strong…", otherwise "Good…".

### 10.5 Cow ranking

Per cow, over its lifetime in the simulation:
- `milkKg = totalMilk·1.03` and **`FCR = totalFeed/milkKg`** (kg/kg).
- `avgMilk = totalMilk/daysMilking`.
- `feed`, `water` and `manure` are averages per active day.
- `milkRev = avgMilk·blendPrice`.
- `ghg = 5.0·methaneReduction`, a constant that is **the same for every cow**.
- `bw = BW(parity)`.

Cows are filtered to active cows that milked at least one day (or all cows that ever milked when the toggle is on), then sorted by FCR ascending to get the rank.
- `eff = clamp(round(97 − (FCR − min)/(max − min)·94), 1, 99)`.
- Tier: elite ≥80, good ≥60, avg ≥35, otherwise poor.
- KPIs: the best cow is `displayCows[0]`; the averages cover active and founder cows; the elite count is taken over all ranked cows.

### 10.6 Reference output from the target JS (defaults, seed 42, 100 cows, 1,825 days; I ran it headless)

| Metric | avg/day | 5-yr total |
|---|---|---|
| Milk | 2,651 L (26.5 L/cow) | |
| Milk revenue | $2,068 | $3,774,318 |
| Energy revenue | $29.87 | $54,516 |
| Heat value | $10.25 | $18,711 |
| Compost revenue | $28.88 | $52,713 |
| Gross revenue | $2,137 | $3,900,258 |
| Feed cost | $307.87 | $561,859 |
| Water cost | $5.52 | $10,070 |
| **Net profit** | $1,824 | **$3,328,329** |
| Net / Gross GHG | 355.8 / 533.0 kg CO₂e | 649,347 net |
| Electricity / Biogas | 186.7 kWh / 68.3 m³ | |
| Net feed / Compost | 1,399 kg / 577.7 kg | |
| Net FCR | 0.516 kg/kg | |
| Recycled irrigation / Net water | 6,351 L / 6,897 L | |
| Baseline (no loops) totals | | revenue $3,788,918 · feed $827,484 · water $16,558 · profit $2,944,876 · net GHG 936,244 |
| ROI portfolio (7%, 15 yr, 15% install, 2% maintenance) | | CapEx $309,350 · annual net $152,592 · blended payback 2.0 yr · NPV $1,080,442 |
| ROI by item: capex / annualNet / payback / NPV | | digester 80,500 / 12,198 / 6.6 / 30,599 · CHP 66,125 / 13,616 / 4.9 / 57,884 · separator 20,700 / 41,738 / 0.5 / 359,448 · solar 40,250 / 2,480 / 16.2 / −17,662 · whey 46,000 / 59,650 / 0.8 / 497,286 · water 28,750 / 7,128 / 4.0 / 36,167 · sensors 23,000 / 15,863 / 1.4 / 121,478 · beef-on-dairy 4,025 / −80 / n/a / −4,758 |

For comparison, the Python model (`baseline.json` at 365 days with processor and whey on, run with `-B` so no files were written) gave:
- milk 711,699 L/yr (19.8 L/cow/day);
- total revenue $388,109 and total cost $263,395, so **profit $124,714**;
- **feed_cost 0.0**;
- freshwater 37.9 M L;
- heat_value 0 and solar 0;
- all equipment CapEx = 0, so ROI and payback are unavailable.

It ran in about 1.8 s per simulated year. **The numbers will not match the target without calibration and structural changes.**

---

## 11. Element map: target vs existing app vs backend field

Legend: [match] exists and matches · [different] exists but different · [missing] missing in the UI. The backend column says whether `serialize_dashboard_run` (in `dairy_abm/dashboard.py`) can feed the element:
- **OK**: already in the payload.
- **ADD**: the value exists in `ctx` (daily_records, state histories or packets) but is not serialized.
- **NONE**: the Python model has no such quantity.

### 11.1 Shell

| Target element | Existing UI | Backend source |
|---|---|---|
| Topbar with logo "Dairy Bioeconomy Simulator v5" | [different] brand "Dairy Farm ABM" sits in the rail; the topbar holds the page title, description and eyebrow | static |
| Farm pill "Conventional" | [missing] (a scenario chip exists, `#header-scenario`) | OK: `meta.farm_system` and `meta.farm_system_label` |
| Status chip Ready/Running/Error | [different] `#run-status`: READY/RUNNING/SIMULATED/COMPARED/ERROR, square style | client state |
| Global Run button with spinner and dirty pulse | [different] `button#go` lives inside the Simulation page form; no dirty state | POST `/api/run` |
| Theme toggle and dark mode | [missing] | n/a |
| Sidebar 2 groups (6 + 2 items) | [different] 12 flat items: Overview, Simulation, Charts, Circular Loops, Scenario Comparison, Cow Performance, Environment, Economics, Equipment ROI, Parameters, Model Details, Export. There is no Animal Biology page, and there are extra pages (Simulation, Environment, Economics, Model Details, Export) that the target lacks. | n/a |
| Hash routing | Existing has `#/page` routing (target has none), which is better to keep | n/a |
| Run inputs (herd, years, seed) | [different] the Simulation page form has scenario, days (1 to 3650), start date, seed, herd and 7 system toggles. The target has cows, years and seed on the Parameters page. | scenario overrides `days`, `seed`, `herd_size`, loop flags |
| Stale banner | [missing] | client state |
| Hide-navigation toggle, research report, footer | extra in existing (not in target) | n/a |

### 11.2 Overview

| Target element | Existing UI | Backend source |
|---|---|---|
| Farm subtitle and summary card | [missing] | static, plus `meta.farm_system_label` |
| KPI Avg Daily Milk (L/day) | [different] "Total milk" and "Average milk / cow / day" | OK: `summary.milk.value / meta.days` (or mean of `series.daily[].milk_l`) |
| KPI Milk Revenue ($/day) | [missing] (total revenue only) | OK: `economics.metrics.milk_revenue / days`. Semantics: this is processor revenue when the processor is on; the target uses blended contract prices on all milk. |
| KPI Energy Revenue ($/day) | [missing] | OK: `economics.metrics.energy_value`. Python combines electricity savings and heat savings. |
| KPI Heat Value ($/day) | [missing] | ADD: `ctx.state["energy_history"][].heat_value` (default 0: it only counts displaced `farm_heat_demand_mj_per_day`) |
| KPI Compost Revenue ($/day) | [missing] | **NONE**: there is no compost price or compost sales in the model |
| KPI Net GHG/day | [different] total "Net GHG" | OK: `summary.net_co2e / days` |
| KPI Daily Electricity | [different] "Energy self-sufficiency %" | OK: mean of `series.daily[].electricity_generated_kwh` (net of parasitic, includes solar) |
| KPI Daily Biogas m³ | [missing] | OK: `series.daily[].biogas_volume_m3` |
| KPI Net Feed/day | [missing] | OK (approximate): `series.daily[].purchased_feed_kg_dm`, in kg DM rather than as-fed. It was 0 in my test run. |
| KPI Daily Compost kg | [missing] | [different] ADD or approximate: `loops.l1.metrics.compost_kg` is **manure routed to compost**, not compost product; daily `compost_kg` is in daily_records but not in `DASHBOARD_DAILY_FIELDS` |
| KPI Feed Conv. Ratio (kg/kg) | [different] "Feed conversion ratio" in kg DM/L | OK: `summary.fcr` (gross DMI/L, ratio of sums). A net kg/kg version needs a /1.03 conversion and a net feed figure. |
| Extra existing KPIs (total cost, freshwater, circularity, sustainability, disease, ending herd, GHG intensity) | extra | OK |
| Revenue Summary banner (Gross, Net Profit, period label) | [missing] | OK: `economics.metrics.total_revenue`, `.profit`, `meta.herd_size`, `meta.days`. The definitions differ: Python total_revenue also includes byproduct and carbon credit, and profit subtracts all 9 cost categories rather than only feed and water. |
| 4 stream cards and donut | [missing] | Milk OK, Energy OK, Heat ADD, Compost **NONE**. Python has additional streams (byproduct_revenue, carbon_credit_value) that the target lacks. |
| Input costs (Feed, Water) | [missing] | OK: `economics.metrics.feed_cost`, `.water_cost` |
| Chart Daily Milk | [different] "Milk production" (SVG) | OK: `series.daily[].milk_l` |
| Chart Daily Revenue (4 streams) | [different] "Economics": revenue, cost and profit | Milk and energy OK via `economics.daily[]`; heat ADD; compost NONE |
| Chart GHG gross vs net | [different] gross, avoided and net | OK: `gross_kg_co2e`, `net_kg_co2e` |
| Chart Energy Generation | [missing] (existing 4th chart is freshwater) | OK: `electricity_generated_kwh` |

### 11.3 Time Series (15 charts)

The existing Charts page has 25 SVG charts in 5 groups plus a Daily/Monthly/Annual switch, so it is [different].

| Target chart | Backend |
|---|---|
| Milk | OK `milk_l` |
| Net Feed | OK approx. `purchased_feed_kg_dm` |
| Net Water | OK `freshwater_withdrawal_l` (or ADD `net_water_l`) |
| Manure Output | ADD `manure_kg` (in daily_records, not in DASHBOARD_DAILY_FIELDS) |
| Biogas | OK `biogas_volume_m3` |
| Total Electricity | OK `electricity_generated_kwh` |
| Heat Recovered (kWh) | OK `heat_generated_mj / 3.6` (can be null) |
| Compost Produced | ADD `compost_kg` (routed manure) |
| Nitrogen Recovered | ADD a daily series from `manure_flow_history` compost_n_kg + digestate_n_kg (+ water_history recovered_n_kg); only totals are serialized now |
| Net GHG | OK `net_kg_co2e` |
| Milk Revenue | OK `economics.daily[].milk_revenue` |
| Energy Revenue | OK `economics.daily[].energy_value` |
| Heat Value $ | ADD `energy_history[].heat_value` |
| Compost Revenue $ | **NONE** |
| FCR | OK derived `dmi_kg / milk_l` (kg DM/L) |

### 11.4 Circular Loops

Existing: 4 text "loop sections" with raw metric lists, state badges and provenance, plus a node/edge topology list. That is structurally [different]: there are no hero cards and no chart.

| Target | Backend |
|---|---|
| L1 hero "Total organic fertilizer" kg/day | [different] partial: `loops.l1.metrics.compost_kg + digester_kg` are manure masses routed. No digestate mass and no sludge fertilizer. |
| L1 Feed offset | OK `loops.l1.metrics.feed_loop_offset_kg` (÷ days) |
| L1 N/P/K recovered | OK `compost_n/p/k_kg` (+ `digestate_n/p/k_kg`) ÷ days |
| L1 Digestate applied | NONE as mass (N/P/K only) |
| L2 hero Recycled irrigation | OK `loops.l2.metrics.recycled_irrigation_l` |
| L2 Wastewater treated | ADD `water_history[].wastewater_volume_l` (in the packet, not serialized) |
| L2 Fresh water offset | OK approx. `loops.l2.metrics.water_saving_l` |
| L2 Net water draw | OK `loops.l2.metrics.net_water_l` / `freshwater_withdrawal_l` |
| L3 hero Total electricity | OK `loops.l3.metrics.electricity_generated_kwh` |
| L3 Biogas / Heat | OK `biogas_volume_m3`, `heat_generated_mj/3.6` |
| L3 Digestate → fertilizer | NONE (mass) |
| L4 hero Feed return kg/day | [different] `loops.l4.metrics.feed_eligible_kg_dm` is **latest-day only**. A run total would need an ADD of daily `l4_feed_offset_kg`. |
| L4 Whey → functional foods | [different] `whey_l` total minus `whey_feed_l` (latest only). ADD a history. |
| L4 Sludge → fertilizer | [different] `sludge_l` latest only; no fertilizer route |
| L4 availability | `l4_enabled` requires `enable_processor`, and `baseline.json` has `enable_processor: false`, so L4 shows **inactive by default**, unlike the target's "all 4 loops active" |
| Nutrient Pool Over Time chart (pool, organic input, feed offset) | **NONE**: the model has no soil nutrient pool or 90-day lag. The closest proxies are `soil_carbon_delta_kg`, `synthetic_fertilizer_saved_kg`, `nutrient_return_kg` and `feed_loop_offset_kg`, and only feed_loop_offset has a daily series (ADD). |

### 11.5 Comparison

| Target | Existing | Backend |
|---|---|---|
| 16-combination loop matrix | [different] "Full L1-L4 matrix" mode already posts 16 real runs to `/api/compare`; other modes: baseline vs current, single loop off, and two scenarios | OK `serialize_comparison` returns the full run payloads and deltas. Cost: about 1.8 s per simulated year per run, so 16 × 5 years is roughly 2.5 min, synchronous and in a single request. |
| Summary strip (All-4 profit Δ, best scenario, GHG Δ) | [missing] | OK derivable from `runs[i].summary.profit`, `.net_co2e` |
| Mode A pills and Mode B selectors | [missing] (mode buttons and 1 metric chart) | client |
| 30-row sectioned table with Δ and % | [different] table of 14 summary deltas | `deltas[].metrics` covers only `_SUMMARY_DEFINITIONS` (14 keys). The rest can be computed on the client from `runs[i].economics.metrics` and `runs[i].loops.*.metrics`. Missing: compost revenue (NONE), heat revenue (ADD), water credit and fresh offset queued (use `water_saving_l`), feed return total (ADD), organic fertilizer (NONE), grid avoided (use `avoided_kg_co2e`), net and gross FCR (derive). |
| Tabbed Δ bar chart (Profit, Revenue, Feed Savings, Water Savings, GHG) with baseline rule | [different] one SVG delta bar chart | OK derivable |
| Radar and group-average bar chart | [missing] | OK derivable |

### 11.6 ROI Justification

| Target | Existing | Backend |
|---|---|---|
| Assumption inputs (discount, lifespan, install %, maintenance %) and live recalculation | [missing] (discount rate is fixed at `DEFAULT_DISCOUNT_RATE`) | client-side, or a new API param |
| Portfolio banner (CapEx, annual benefit, blended payback, NPV) | [missing] | [different] `equipment.assets[]` exist, but **every CapEx defaults to 0.0** (`scenario.equipment_capex` is absent), so ROI and payback are null and the status is `zero_capex` |
| Payback timeline and benefit breakdown charts | [missing] | derivable once capex > 0 |
| 8 equipment cards (digester, CHP, separator, solar, whey unit, water recycling, sensors, beef-on-dairy) | [different] 4 plain cards: milking parlour/bulk tank, dairy processor, whey processor, manure system | **Catalogue mismatch.** Python benefits are `raw_milk×365`, `(processor−raw)×365`, `byproduct×365` and `(energy+carbon)×365`. There is no digester, CHP, separator, solar, water recycling or sensor asset, and the target's capital formulas (700·n and so on) are not in the model. They would have to be added to `farm_manager_agent._equipment_roi`, to the serializer as a presentation catalogue, or computed on the client from the section 10.4 formulas using ADD fields (digestate, solar kWh, heat, avoided grid, wastewater N/P/K). |
| Per-item NPV over lifespan | [different] `equipment_npvs` = `npv([annual_benefit])`, a single-year cash flow | needs a lifespan-based NPV |
| Methodology note | [missing] | static |

### 11.7 Cow Ranking

| Target | Existing | Backend |
|---|---|---|
| Generate Rankings button and "all lifetime cows" toggle | [missing] (the Cow Performance page renders automatically) | n/a. Python keeps only the current herd; culled cows are not retained, so the toggle has no data. |
| KPI row (best FCR cow, herd avg FCR, avg milk/cow, elite count) | [missing] (health-state bars instead) | derivable from `cows.records` |
| Rank table with badge, tier chips and efficiency bars | [different] 11-column latest-day table (ID, milk, DMI, FCR, DIM, health, rumen pH, SARA, BCS, weight, pregnant) plus 4 sort buttons | `cows.records` has `milk_l`, `dmi_kg`, `fcr_kg_dm_per_l`, `parity`, `body_weight_kg` and `enteric_ch4_kg` for the **latest day only**. Lifetime averages (avg milk per milking day, avg feed, avg manure) need an ADD aggregating `ctx.state["cows"][].milk_history`, `dmi_history` and `manure_history`, which do exist (365 entries in a 1-year run). **Per-cow water: NONE.** Dairy Rev $/day: derive milk × price (`economics.market.milk_price_per_l`). GHG per cow: OK `enteric_ch4_kg` (kg CH₄, needs a CO₂e factor). Efficiency and tier: derive on the client from the FCR spread. |
| Scatter FCR vs milk (tier-colored) | [different] "Milk vs FCR" SVG scatter, no tiers | OK |
| Top-20 revenue bars | [missing] (existing has a DMI vs milk scatter) | derivable |
| Genetic traits disclosure and health counts | extra in existing | OK |

### 11.8 Parameters and Animal Biology

| Target | Existing | Backend |
|---|---|---|
| 13 curated groups of sliders, numbers and toggles with live value readouts, jump nav, dirty state, "Run with These Parameters", "Reset to Defaults" | [different] the Parameters page is generated from `/api/calibration` (209 rows grouped by agent: cow, dairy_processor, disease, energy, …) with search, group, assumption and changed-only filters, number inputs only, per-field and per-group reset, and validation | OK `/api/calibration?scenario=` (uncommitted change). **The key sets differ entirely.** The target's JS keys (`feed_cost_per_kg`, `wood_b`, …) have no 1:1 Python keys. Examples of the Python equivalents: `market.milk_price_per_l 0.42`, `market.feed_cost_per_kg_dm 0.32`, `water.water_cost_per_l 0.001`, `energy.electricity_price_per_kwh 0.12`, `energy.heat_value_per_kwh 0.04`, `energy.solar_kw_per_cow 0.1`, `cow.base_milk_l_per_cow_day 30`, `cow.base_dmi_kg_per_cow_day 22`, `cow.base_manure_kg_per_cow_day 60`, `cow.lactation_peak_days 60`, `manure.compost_route_fraction 0.35`. A curated slider layout needs a mapping table from the target labels to calibration keys, and `valid_range` supplies min and max. There are no step values or hints in the inventory beyond `description`. |
| Herd, years and seed controls | on the Simulation page | scenario overrides |
| Animal Biology page (Wood's curve peak by parity, lactation and dry days, max parity, illness probability and penalties, cull rate, body weights) | [missing] | Mostly **NONE** as named parameters. The Python cow agent uses its own lactation factor (`cow.lactation_peak_days`), NRC DMI (Eq 2.1) and a disease agent (`disease.mastitis_daily_probability`, `milk_loss_sick_fraction`, …). Show the matching `cow.*`, `disease.*` and `genetics.*` calibration rows instead. |

### 11.9 Existing pages with no target counterpart
Simulation (run form, ledger/graphs, CSV zip), Environment audit, Economics audit, Model Details, Export, and the research report overlay. Choose between hiding them, folding them into Settings, or keeping them as extra nav items. The target has no export feature.

---

## 12. Uncommitted changes in the existing repo (`git diff`)

The changes touch 7 files (+76 / −18). Together they make the **Parameters page scenario-aware**:
- **`webapp.py`**: pulls scenario file loading out into `_load_scenario(filename)`, with the same path-traversal guard and a file-exists check. `_run_simulation` now uses it. `GET /api/calibration` now accepts `?scenario=<file>`: it loads that scenario, resolves its `reference_calibration` profile through `_scenario_calibration`, and returns that inventory. Previously it always returned the global `CALIBRATION`. It returns 400 on a bad file name.
- **`web/js/api.js`**: `loadCalibration(scenario)` appends `?scenario=` with `encodeURIComponent`.
- **`web/js/state.js`**: adds `calibrationScenario: null`.
- **`web/js/app.js`**:
  1. `applyScenarioDefaults` now also clears the cached `state.calibration`, `calibrationScenario` and `parameterLoading`, so switching scenario reloads the inventory.
  2. `renderParameters` passes the selected scenario and ignores stale responses if the dropdown changed mid-fetch.
  3. On the Economics page, policy conflicts render as a structured list (objectives, reason, resolution) instead of a JSON dump.
  4. On the Equipment ROI page, duplicate warnings are collapsed with "(N occurrences)".
- **`web/styles/pages.css`**: adds `.economics-conflicts` list styles.
- **Tests**: `test_webapp.py` checks that `/api/calibration?scenario=cdairy_airand_reference.json` returns `cow.base_milk_l_per_cow_day ≈ 50.8197`; `test_dashboard_parameters.py` checks strings in the JS.
- There is also an untracked file, `Cdairy_mc_kk_current_PS_CM_Strategies.xlsm`.

Side effects of my read-only inspection:
- Importing `dairy_abm` once, to list the calibration inventory, created git-ignored `__pycache__/` folders (`dairy_abm/`, `dairy_abm/agents/`, `dairy_abm/analysis/`). That was the only write. Later runs used `python3 -B`.
- A plain `git status` tried to create `.git/index.lock` and was blocked. Later git calls used `--no-optional-locks`.

---

## 13. Known quirks in the target worth deciding on, not copying blindly
- `milk_price_currency_per_L` is shown but unused. The "$0.78/L" figure is the blended contract price.
- The "▸ Reference" per-cow sliders do nothing, and `_herdMilkScale` is only recomputed on launch or reset.
- Solar is counted in "Energy / Biogas" and in avoided grid GHG even in the no-loop Baseline.
- The energy credit queue is never used. Cow GHG is a constant for every cow.
- CHP capex applies the install factor twice. The Beef-on-Dairy card shows a negative NPV on Conventional.
- The payback palette has 6 colors for 8 lines.
- Undefined CSS vars and `co.muted` fall back to defaults.
- On mobile the nav disappears.
- The ROI page renders only when visible (`buildEquipROI` is called on navigate or when already active).

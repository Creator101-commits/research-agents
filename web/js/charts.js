import { esc, fmt, periodLabel } from "./format.js";

const ALL_PERIODS = Object.freeze(["daily", "monthly", "annual"]);

export const CHART_REGISTRY = Object.freeze([
  {id: "milk", title: "Milk production", field: "milk_l", unit: "L", group: "Production", kind: "area", color: "#b42318", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "purchased-feed", title: "Purchased feed", field: "purchased_feed_kg_dm", unit: "kg DM", group: "Production", kind: "bar", color: "#8b5e3c", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "irrigation", title: "Irrigation", field: "irrigation_l", unit: "L", group: "Resources", kind: "bar", color: "#527a61", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "net-energy", title: "Net energy", field: "net_kwh", unit: "kWh", group: "Energy", kind: "area", color: "#b7791f", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "feedstock", title: "Feedstock", field: "feedstock_tons", unit: "tonnes", group: "Energy", kind: "bar", color: "#8b5e3c", dec: 3, ydec: 3, periods: ALL_PERIODS},
  {id: "electricity", title: "Electricity generated", field: "electricity_generated_kwh", unit: "kWh", group: "Energy", kind: "area", color: "#3f6b4f", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "biogas-volume", title: "Biogas volume", field: "biogas_volume_m3", unit: "m3", group: "Energy", kind: "area", color: "#527a61", dec: 2, ydec: 2, periods: ALL_PERIODS},
  {id: "biogas-energy", title: "Biogas gross energy", field: "biogas_gross_kwh", unit: "kWh", group: "Energy", kind: "area", color: "#4f7d5c", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "heat", title: "Heat generated", field: "heat_generated_mj", unit: "MJ", group: "Energy", kind: "area", color: "#c2412d", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "energy-self-sufficiency", title: "Energy self-sufficiency", field: "energy_self_sufficiency_pct", unit: "%", group: "Energy", kind: "area", color: "#4f7d5c", dec: 1, ydec: 0, periods: ALL_PERIODS},
  {id: "freshwater", title: "Freshwater withdrawal", field: "freshwater_withdrawal_l", unit: "L", group: "Resources", kind: "bar", color: "#527a61", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "recycled-irrigation", title: "Recycled irrigation", field: "recycled_irrigation_l", unit: "L", group: "Resources", kind: "bar", color: "#3f6b4f", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "gross-ghg", title: "Gross GHG", field: "gross_kg_co2e", unit: "kg CO2e", group: "Environment", kind: "area", color: "#b7791f", dec: 1, ydec: 1, floor: false, periods: ALL_PERIODS},
  {id: "avoided-ghg", title: "Avoided GHG", field: "avoided_kg_co2e", unit: "kg CO2e", group: "Environment", kind: "area", color: "#3f6b4f", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "net-ghg", title: "Net GHG", field: "net_kg_co2e", unit: "kg CO2e", group: "Environment", kind: "area", color: "#b42318", dec: 1, ydec: 1, floor: false, periods: ALL_PERIODS},
  {id: "ghg-intensity", title: "GHG intensity", field: "kg_co2e_per_l_milk", unit: "kg CO2e/L milk", group: "Environment", kind: "area", color: "#c2412d", dec: 3, ydec: 3, floor: false, periods: ALL_PERIODS},
  {id: "input-circularity", title: "Input circularity", field: "input_circularity", unit: "fraction", group: "Environment", kind: "area", color: "#b42318", dec: 3, ydec: 2, floor: false, periods: ALL_PERIODS},
  {id: "output-circularity", title: "Output circularity", field: "output_circularity", unit: "fraction", group: "Environment", kind: "area", color: "#3f6b4f", dec: 3, ydec: 2, floor: false, periods: ALL_PERIODS},
  {id: "circularity-score", title: "Circularity score", field: "circularity_score", unit: "fraction", group: "Environment", kind: "area", color: "#4f7d5c", dec: 3, ydec: 2, floor: false, periods: ALL_PERIODS},
  {id: "nue", title: "Nitrogen-use efficiency", field: "environment_nue", unit: "fraction", group: "Environment", kind: "area", color: "#527a61", dec: 3, ydec: 2, floor: false, periods: ALL_PERIODS},
  {id: "soil-carbon", title: "Soil carbon change", field: "soil_carbon_delta_kg", unit: "kg C", group: "Environment", kind: "area", color: "#8b5e3c", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "fertilizer-saved", title: "Synthetic fertilizer saved", field: "synthetic_fertilizer_saved_kg", unit: "kg N", group: "Environment", kind: "bar", color: "#3f6b4f", dec: 1, ydec: 1, periods: ALL_PERIODS},
  {id: "sustainability", title: "Sustainability score", field: "sustainability_score_0_100", unit: "score / 100", group: "Environment", kind: "area", color: "#2f6f4e", dec: 1, ydec: 0, periods: ALL_PERIODS},
  {id: "disease-cost", title: "Disease economic cost", field: "disease_economic_cost", unit: "currency", group: "Economics", kind: "bar", color: "#b42318", dec: 0, ydec: 0, periods: ALL_PERIODS},
  {id: "profit", title: "Profit", field: "profit", unit: "currency", group: "Economics", kind: "area", color: "#3f6b4f", dec: 0, ydec: 0, floor: false, periods: ALL_PERIODS},
]);

export const CH = { W:520, H:244, L:76, R:18, T:48, B:40 };

export function svgChart(o) {
  const rows = o.rows, W=CH.W, H=CH.H, L=CH.L, R=CH.R, T=CH.T, B=CH.B;
  const plotW = W-L-R, plotH = H-T-B, n = rows.length || 1;
  const gx = i => L + (n===1 ? plotW/2 : (i/(n-1))*plotW);
  const barX = i => L + ((i + 0.5)/n)*plotW;
  const valueOf = (row, key) => {
    if (row[key] === null || row[key] === undefined || row[key] === "") return null;
    const value = Number(row[key]);
    return Number.isFinite(value) ? value : null;
  };
  const all = [];
  o.series.forEach(s => rows.forEach(r => {
    const value = valueOf(r, s.key);
    if (value !== null) all.push(value);
  }));
  let min = o.floor === false && all.length ? Math.min(...all) : 0;
  let max = all.length ? Math.max(...all) : 1;
  if (o.floor === false && min > 0) min = 0;
  if (max <= min) max = min + 1;
  const span = max - min;
  const gy = v => T + (1 - (v-min)/span)*plotH;
  const ydec = (o.ydec != null) ? o.ydec : (span < 10 ? 2 : 0);
  const valTxt = v => fmt(v, ydec);
  const xText = day => periodLabel(day, o.period);

  let grid = "", yLabels = "";
  const ticks = 4;
  for (let i=0; i<=ticks; i++) {
    const v = min + span*i/ticks, y = gy(v);
    grid += `<line x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}" class="ax"/>`;
    yLabels += `<text x="${L-10}" y="${(y+3).toFixed(1)}" class="axislabel" text-anchor="end">${valTxt(v)}</text>`;
  }
  const xIndexes = [...new Set(n<=1 ? [0] : [0, Math.floor((n-1)/2), n-1])];
  const xLabels = rows.length ? xIndexes.map(i =>
    `<text x="${gx(i).toFixed(1)}" y="${H-12}" class="axislabel" text-anchor="middle">${xText(rows[i].day)}</text>`).join("") : "";
  const axes = `<line x1="${L}" y1="${T+plotH}" x2="${W-R}" y2="${T+plotH}" class="baseline"/>`;

  let body = "";
  o.series.forEach((s, si) => {
    const col = s.color;
    if (o.kind === "bar") {
      const bw = Math.min(48, Math.max(2, plotW/n*0.62));
      const base = gy(0);
      rows.forEach((r, i) => {
        const v = valueOf(r, s.key);
        if (v === null) return;
        const top = gy(v), hi = Math.abs(top-base);
        body += `<rect x="${(barX(i)-bw/2).toFixed(1)}" y="${Math.min(top,base).toFixed(1)}" width="${bw.toFixed(1)}" height="${hi.toFixed(1)}" fill="${col}" opacity="0.85"><title>${esc(r.day)} - ${fmt(v,o.dec||0)} ${esc(o.unit||"")}</title></rect>`;
      });
    } else {
      const segments = [];
      let segment = [];
      rows.forEach((r, i) => {
        const v = valueOf(r, s.key);
        if (v === null) {
          if (segment.length) segments.push(segment);
          segment = [];
          return;
        }
        segment.push({x: gx(i), y: gy(v)});
      });
      if (segment.length) segments.push(segment);
      segments.forEach(points => {
        const pts = points.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
        if (o.area !== false) body += `<polygon points="${pts} ${points[points.length-1].x.toFixed(1)},${gy(0).toFixed(1)} ${points[0].x.toFixed(1)},${gy(0).toFixed(1)}" fill="${col}" opacity="${si===1?0.08:0.12}"/>`;
        body += `<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
      });
      rows.forEach((r, i) => {
        const v = valueOf(r, s.key);
        if (v === null) return;
        const point = `<circle cx="${gx(i).toFixed(1)}" cy="${gy(v).toFixed(1)}" r="14" fill="transparent"><title>${esc(r.day)} ${esc(s.label)}: ${fmt(v,o.dec||0)} ${esc(o.unit||"")}</title></circle>`;
        body += point;
      });
    }
  });

  const ns = o.series.length;
  const legend = o.series.map((s,i) =>
    `<rect x="${W-R-14-ns*86+i*86}" y="11" width="8" height="8" fill="${s.color}"/>` +
    `<text x="${W-R-14-ns*86+i*86+12}" class="lg" y="19">${s.label}</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg" class="gsv" role="img" aria-label="${esc(`${o.title}; unit ${o.unit || "reported value"}; ${rows.length} ${o.period || "daily"} points`)}">
      <style>
        .gsv .ax { stroke: #e5e7eb; stroke-width: 1; }
        .gsv .baseline { stroke: #9ca3af; stroke-width: 1.2; }
        .gsv text { fill: #667085; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 11px; }
        .gsv .axislabel { fill: #667085; font-size: 11px; }
        .gsv .ttl { fill: #111827; font-size: 13px; font-weight: 700; }
        .gsv .lg { fill: #667085; font-size: 10.5px; }
      </style>
      <rect width="${W}" height="${H}" fill="#fff"/>
      <text x="10" y="21" class="ttl">${esc(o.title)}</text>
      ${legend}${grid}${yLabels}${xLabels}${axes}${body}
    </svg>`;
}



export function buildCharts(rows, period) {
  const D = (over) => Object.assign({rows, period}, over);
  return [
    { s: svgChart(D({title:"Milk produced", kind:"area", unit:"L", dec:0, ydec:0, series:[{key:"milk_l",color:"#b42318",label:"Milk"}]})) },
    { s: svgChart(D({title:"Net CO2e", kind:"bar", unit:"kg", dec:0, ydec:0, series:[{key:"net_kg_co2e",color:"#c2412d",label:"CO2e"}]})) },
    { s: svgChart(D({title:"Profit", kind:"area", unit:"", dec:0, ydec:0, floor:false, series:[{key:"profit",color:"#3f6b4f",label:"Profit"}]})) },
    { s: svgChart(D({title:"Energy self-sufficiency (%)", kind:"area", unit:"%", dec:1, ydec:0, series:[{key:"energy_self_sufficiency_pct",color:"#4f7d5c",label:"Self-suff"}]})) },
    { s: svgChart(D({title:"Freshwater drawn", kind:"bar", unit:"L", dec:0, ydec:0, series:[{key:"freshwater_withdrawal_l",color:"#527a61",label:"Water"}]})) },
    { s: svgChart(D({title:"Circularity (input / output)", kind:"area", unit:"", dec:3, ydec:2, floor:false, series:[{key:"input_circularity",color:"#b42318",label:"Input"},{key:"output_circularity",color:"#3f6b4f",label:"Output"}]})) },
    { s: svgChart(D({title:"Sustainability score", kind:"area", unit:"/100", dec:1, ydec:0, series:[{key:"sustainability_score_0_100",color:"#2f6f4e",label:"Score"}]})) },
    { s: svgChart(D({title:"Disease cases", kind:"bar", unit:"", dec:0, ydec:0, series:[{key:"active_disease_cases",color:"#b42318",label:"Cases"}]})) },
  ];
}

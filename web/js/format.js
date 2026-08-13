export const esc = (s) => String(s).replace(/[&<>\"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));

export const fmt = (n, d = 0) => (n === null || n === undefined || isNaN(n)) ? "-" :
  Number(n).toLocaleString("en-US", {minimumFractionDigits: d, maximumFractionDigits: d});

const AGG = {
  milk_l: 1,
  profit: 1,
  net_kg_co2e: 1,
  freshwater_withdrawal_l: 1,
  active_disease_cases: 1,
  energy_self_sufficiency_pct: 0,
  input_circularity: 0,
  output_circularity: 0,
  cow_count: 0,
  sustainability_score_0_100: 0,
};

export function aggregate(rows, period) {
  if (period === "daily") return rows.slice();
  const groups = new Map();
  rows.forEach(row => {
    const id = period === "monthly" ? row.day.slice(0, 7) : row.day.slice(0, 4);
    if (!groups.has(id)) groups.set(id, {sum: {}, n: 0});
    const group = groups.get(id);
    group.n++;
    for (const key in AGG) {
      if (row[key] != null) group.sum[key] = (group.sum[key] || 0) + Number(row[key]);
    }
  });
  return Array.from(groups.keys()).sort().map(id => {
    const group = groups.get(id);
    const row = {day: id};
    for (const key in AGG) {
      if (group.sum[key] != null) row[key] = AGG[key] ? group.sum[key] : group.sum[key] / group.n;
    }
    row.kg_co2e_per_l_milk = row.milk_l > 0 && row.net_kg_co2e != null
      ? row.net_kg_co2e / row.milk_l : null;
    return row;
  });
}

export function periodLabel(day, period) {
  if (period === "annual" || period === "yearly") return day;
  return period === "monthly" ? day.slice(2) : day.slice(5);
}

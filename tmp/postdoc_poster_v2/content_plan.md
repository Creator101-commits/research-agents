# Poster content plan

## Title

How Four Circular Dairy Loops Change Operating Profit, Greenhouse Gas Emissions, and Water Use

Subtitle: A 365-day agent-based virtual farm experiment (ViCBio DM)

Authors: Megha Poyyara Saiju¹, Manogna Rayala², Karun Kaniyamattam¹

Affiliations: ¹Department of Animal Science; ²Department of Statistics; Texas A&M University

## Why this matters

The 2022 USDA Census of Agriculture reports $52.8 billion in U.S. milk sales, a 39% decline in dairy farm numbers, and $43.9 billion in specialized dairy production expenses; feed represented 46% of those expenses. Circular technologies may recover nutrients, water, energy, and product value, but producers need a common system model to expose interactions and tradeoffs before committing capital.

## Objective and hypothesis

Objective: Quantify how four implemented circular loops—nutrient (L1), water (L2), energy (L3), and on-farm processing/byproduct routing (L4)—change annual operating profit, net greenhouse gas emissions, freshwater withdrawal, and circularity in one virtual dairy farm.

Hypothesis: Adding circular loops will increase operating profit and circularity while decreasing net greenhouse gas emissions and freshwater withdrawal relative to the same farm with all four loop toggles off.

## Model architecture

ViCBio DM links 13 components through dated packets: market and sensors; optional land; feed/crop; farm-manager policy; disease; water delivery; individual cows; dairy processor; manure; energy; water accounting; environment; and genetics intake. The daily scheduler preserves a fixed causal order, and all stochastic behavior uses the scenario seed.

Four material pathways are represented:

- L1 nutrient: manure-derived nutrients and compost create a next-day feed-offset credit.
- L2 water: treated parlor wastewater creates a next-day freshwater irrigation credit.
- L3 energy: manure and processor residuals produce electricity/heat and avoided grid emissions.
- L4 products: half of modeled milk is processed using a calibrated product mix; whey and other residuals are routed to feed, energy, or materials.

## Computational experiment

One-year runs used a 100-cow, high-intensity virtual farm with 80 ha cropland and 40 ha pasture. Processor, whey-processing, and land components were available in every run. The separate amino-acid water-saving policy and automatic manager responses were disabled so loop effects were not masked. A full 2⁴ factorial evaluated all 16 loop combinations at seed 42. Five representative configurations were repeated with seeds 1–12. Prices used the model's static calibration with its configured stochastic price shock. Metrics were aggregated from daily records. No capital cost was supplied; ROI and payback were therefore not calculated.

## Results

All four loops versus no loop toggles, seed 42:

- Operating profit: $123,755 versus $40,348 per year (+206.7%).
- Net GHG emissions: 121.2 versus 135.1 t CO2e per year (-10.3%).
- Freshwater withdrawal: 38.75 versus 38.91 million L per year (-0.41%; 159,417 L avoided).
- Mean circularity score: 0.71 versus 0.21 (+0.50 on a 0–1 scale).
- Recovered outputs: 70.0 MWh electricity, 177.1 t feed-offset credits, and 266.0 thousand L whey.
- Milk production was identical: 719,779 L per year, isolating the reported differences to loop routing and modeled values rather than milk yield.

Factor attribution:

- L3 produced the entire 10.3% net-GHG reduction and raised annual operating profit by about $4,380 at seed 42.
- L4 produced the dominant profit separation (+$78,868 versus no loops) under assumed product-mix prices; this includes processing revenue, not only byproduct value.
- L2 reduced freshwater withdrawal by 159,417 L and increased operating profit by about $159.
- L1 generated 70.9 t of feed-offset credits but did not change top-line profit, emissions, or water because farm-grown feed was not binding in this scenario.

Across seeds 1–12, mean annual operating profit was $38.4 ± $1.9 thousand with no loop toggles and $120.7 ± $2.9 thousand with all loops. Mean net GHG emissions were 133.9 ± 1.1 versus 120.1 ± 1.1 t CO2e. The route ranking remained stable.

## Conclusion

Circular interventions did not contribute equally. In this computational scenario, L4 determined the economic result, L3 determined the greenhouse-gas result, L2 produced a small water benefit, and L1 created a material credit without a realized top-line benefit. ViCBio DM is most defensible as a screening and experiment platform: it can identify which assumptions and resource constraints drive outcomes before field trials or capital planning.

## Limitations

Outputs are simulated, not field measurements. This is one virtual farm-year with calibration-based prices and no observed farm data, audited capital costs, financing, taxes, or equipment depreciation. The L4 estimate depends strongly on calibrated processing yields and prices. Physical wastewater treatment and nutrient return remain active in the model even when L1/L2 toggles are off; those toggles add next-day credits rather than removing all reuse. The five farm systems described in the abstract are not yet implemented as five directly comparable scenarios in the current repository revision. Software tests verify contracts, not scientific or financial validity.

## Next steps

Calibrate loop-specific CapEx and O&M; ingest observed milk, feed, electricity, and product prices; implement and validate the five proposed farm-system scenarios; run global sensitivity and uncertainty analysis; compare predictions with farm mass-balance and financial records; then report ROI and payback only with a documented cost basis.

## References

1. USDA NASS. 2022 Census of Agriculture: Dairy Cattle and Milk Production. 2024.
2. Wood, P.D.P. Algebraic model of the lactation curve in cattle. Nature 216, 164–165 (1967). doi:10.1038/216164a0.
3. Muell, J.D. et al. Farm-scale water-energy-food-waste nexus analysis for a closed-loop dairy system. Frontiers in Environmental Science 10:880839 (2022). doi:10.3389/fenvs.2022.880839.
4. ViCBio DM source: Creator101-commits/research-agents, commit 7c41c15daaf1; model outputs generated 2026-09-05.

## Acknowledgments

Department of Animal Science and Department of Statistics, Texas A&M University.

## Five-minute talk track

0:00–0:40 — Define the decision problem using the USDA context and identify the four loops.

0:40–1:20 — State the objective and hypothesis; explain the fixed daily agent order and the 2⁴ factorial design.

1:20–2:30 — Walk through the factorial heatmap: L4 shifts modeled profit, L3 shifts net GHG, L2 shifts water, and L1 records material substitution without a binding economic effect.

2:30–3:20 — Use the repeated-seed plot to show that the route ranking persists across 12 initializations.

3:20–4:15 — Report the all-loops totals and explain that milk yield is unchanged; the differences arise from resource routing and calibrated values.

4:15–5:00 — State the limitation: these are screening results without CapEx or field validation. End with the calibration and validation steps required before ROI claims.

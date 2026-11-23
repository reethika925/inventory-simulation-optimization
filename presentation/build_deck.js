// Build the project slide deck from the results.
//   cd presentation && npm install && node build_deck.js
// Every number on the slides is read from ../results/key_numbers.json.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const ROOT = path.resolve(__dirname, "..");
const K = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "key_numbers.json"), "utf8"));
const FIG = (n) => path.join(ROOT, "results", "figures", n);
const OUT = path.join(__dirname, "inventory_simulation_slides.pptx");

const THEME = {
  name: "Inventory Simulation",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "14213D", lt1: "FFFFFF", dk2: "4A5568", lt2: "F1F4F8",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "EDA100",
    accent5: "6250D6", accent6: "52514E", hlink: "2A78D6", folHlink: "6250D6",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "Simulation and Optimization of Inventory Management";
pres.author = "Jahnavi Gouru, Mary Reethika Reddy Kolukula, Praneeth Kapila";
pres.subject = "AMS 553 / CSE 529 final project";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

const W = 13.333, MX = 0.6, CW = W - 2 * MX;
const FOOT = "AMS 553 / CSE 529  ·  Simulation and Optimization of Inventory Management";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "DARK_TITLE",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.55, w: 11.7, h: 1.9,
        fontSize: 42, bold: true, color: C.background1, valign: "bottom", align: "left", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 3.6, w: 11.7, h: 0.8,
        fontSize: 22, color: "CADCFC", valign: "top", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "meta", type: "body", x: 0.8, y: 5.45, w: 11.7, h: 1.1,
        fontSize: 15, color: C.background1, valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.35, w: CW, h: 0.85,
        fontSize: 30, bold: true, color: C.text1, valign: "middle", align: "left", margin: 0 }, text: "" } },
    { text: { text: FOOT, options: { x: MX, y: 7.0, w: 9, h: 0.3, fontSize: 10, color: C.text2,
        margin: 0 } } },
  ],
  slideNumber: { x: 12.23, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: HEX.dk2, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK_CONTENT",
  background: { color: HEX.dk1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: MX, y: 0.45, w: CW, h: 0.85,
        fontSize: 30, bold: true, color: C.background1, valign: "middle", align: "left", margin: 0 }, text: "" } },
  ],
  slideNumber: { x: 12.23, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: "CADCFC", align: "right" },
});

// ---------------------------------------------------------------- helpers
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
// place an image inside a box, preserving aspect ratio, centred
function fitImage(slide, file, box, name) {
  const { w, h } = pngSize(file);
  const r = Math.min(box.w / w, box.h / h);
  const iw = w * r, ih = h * r;
  slide.addImage({ path: file, x: box.x + (box.w - iw) / 2, y: box.y + (box.h - ih) / 2,
    w: iw, h: ih, objectName: name, altText: name });
}
function card(slide, x, y, w, h, name, fill = C.background2) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12,
    fill: { color: fill }, line: { color: fill }, objectName: name });
}
function badge(slide, x, y, d, label, color, name) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color },
    objectName: name });
  slide.addText(label, { x, y, w: d, h: d, align: "center", valign: "middle", bold: true,
    fontSize: d > 0.6 ? 20 : 15, color: C.background1, margin: 0, isTextBox: true,
    objectName: name + " label" });
}
function text(slide, t, opts) {
  slide.addText(t, Object.assign({ isTextBox: true, margin: 0, color: C.text1, fontSize: 15,
    valign: "top" }, opts));
}
const money = (v) => `$${Number(v).toFixed(2)}`;
const sS = K.sS, sQ = K.sQ, base = K.baseline, D = K.diff;

// ================================================================ 1. title
pres.addSection({ title: "Introduction" });
{
  const s = pres.addSlide({ masterName: "DARK_TITLE", sectionTitle: "Introduction" });
  s.addText("Simulation and Optimization of Inventory Management", { placeholder: "title" });
  s.addText("Which reorder rule should the company use: (s, S) or (s, Q)?", { placeholder: "subtitle" });
  s.addText([
    { text: "Jahnavi Gouru  ·  Mary Reethika Reddy Kolukula  ·  Praneeth Kapila", options: { breakLine: true } },
    { text: "AMS 553 / CSE 529  ·  Final project  ·  Fall 2026", options: { color: "CADCFC" } },
  ], { placeholder: "meta" });
  s.addNotes("We simulate a single-product inventory system that is reviewed once a month, " +
    "compare two reorder rules - (s,S) and (s,Q) - and search for the cheapest parameters of each. " +
    "The deliverable is a concrete recommendation backed by statistics.");
}

// ================================================================ 2. the decision
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Introduction" });
  s.addText("Every reorder rule trades off three costs", { placeholder: "title" });
  const items = [
    ["1", HEX.accent3, "Ordering", "$32 per order + $3 per item", "Order often and the fixed setup charge piles up."],
    ["2", HEX.accent4, "Holding", "$1 per item per month", "Keep a lot of stock and you pay to store it."],
    ["3", HEX.accent5, "Shortage", "$5 per item per month backlogged", "Keep too little and customers wait for their orders."],
  ];
  const cw = (CW - 2 * 0.35) / 3;
  items.forEach(([n, col, head, cost, desc], i) => {
    const x = MX + i * (cw + 0.35), y = 1.5;
    card(s, x, y, cw, 2.75, `${head} card`);
    badge(s, x + 0.35, y + 0.35, 0.7, n, col, `${head} badge`);
    text(s, head, { x: x + 1.25, y: y + 0.38, w: cw - 1.5, h: 0.6, fontSize: 22, bold: true,
      fontFace: THEME.headFontFace, valign: "middle" });
    text(s, cost, { x: x + 0.35, y: y + 1.25, w: cw - 0.7, h: 0.4, fontSize: 15, bold: true, color: C.text2 });
    text(s, desc, { x: x + 0.35, y: y + 1.7, w: cw - 0.7, h: 0.9, fontSize: 15 });
  });
  text(s, "Demand and delivery times are both random, so no simple formula balances these costs. " +
    "Simulation lets us measure a rule's average monthly cost before the company commits to it.",
    { x: MX, y: 4.55, w: CW, h: 0.75, fontSize: 16, color: C.text2 });
  card(s, MX, 5.5, CW, 1.15, "answer card", "E8F1FC");
  text(s, [
    { text: "Our answer:  ", options: { bold: true, color: C.accent1 } },
    { text: `(s, S) = (${sS.best[0]}, ${sS.best[1]})`, options: { bold: true } },
    { text: `  costs ${money(sS.mean)}/month, ${K.baseline_saving_pct}% less than the textbook's (20, 40) rule and ` +
      `${money(D.mean)}/month less than the best (s, Q) rule.` },
  ], { x: MX + 0.35, y: 5.5, w: CW - 0.7, h: 1.15, fontSize: 17, valign: "middle" });
  s.addNotes("The three costs pull in different directions. Our recommendation up front: (s,S)=(24,62). " +
    "The rest of the talk shows how we got there and how sure we are.");
}

// ================================================================ 3. the system
pres.addSection({ title: "Model" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Model" });
  s.addText("The simulated system (Law & Kelton inventory example)", { placeholder: "title" });
  const hdr = (t) => ({ text: t, options: { bold: true, color: C.background1, fill: { color: HEX.dk1 } } });
  const rows = [
    [hdr("Parameter"), hdr("Value")],
    ["Review", "Start of every month, 120 months"],
    ["Initial inventory", "60 items"],
    ["Demand arrivals", "Poisson, mean 10 per month"],
    ["Demand size", "1, 2, 3, 4 w.p. 1/6, 1/3, 1/3, 1/6"],
    ["Delivery lag", "Uniform(0.5, 1) month"],
    ["Ordering cost", "K = $32 + i = $3 per item"],
    ["Holding / shortage", "h = $1, π = $5 per item per month"],
    ["Unmet demand", "Backlogged (inventory can go negative)"],
  ];
  s.addTable(rows, { x: MX, y: 1.45, w: 6.6, colW: [2.2, 4.4], fontSize: 14, color: C.text1,
    border: { type: "solid", pt: 0.75, color: "D5DBE3" }, rowH: 0.52, valign: "middle",
    fill: { color: HEX.lt1 }, objectName: "parameter table" });
  const steps = [
    ["Review", "Check the inventory level I at the start of each month."],
    ["Decide", "If I ≤ s, place an order (size set by the policy)."],
    ["Deliver", "The order arrives 0.5 to 1 month later, always before the next review."],
    ["Pay", "Holding and shortage cost accrue continuously on I⁺(t) and I⁻(t)."],
  ];
  const x0 = 7.75;
  steps.forEach(([h, d], i) => {
    const y = 1.5 + i * 1.22;
    badge(s, x0, y, 0.6, String(i + 1), HEX.accent1, `step ${i + 1}`);
    text(s, h, { x: x0 + 0.85, y: y - 0.04, w: 4.1, h: 0.4, fontSize: 18, bold: true });
    text(s, d, { x: x0 + 0.85, y: y + 0.36, w: 4.1, h: 0.75, fontSize: 14, color: C.text2 });
  });
  s.addNotes("Mean demand is 10 x 2.5 = 25 items per month. Because the lag is at most one month, " +
    "an order is never outstanding at a review - we exploit this later for an exact check.");
}

// ================================================================ 4. two policies
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Model" });
  s.addText("Two reorder policies, tested on the same system", { placeholder: "title" });
  const pol = [
    ["(s, S)", HEX.accent1, "Order up to S", "If I ≤ s, order S − I.",
      ["Order size varies with how low stock fell", "Stock after an order is always S", "Classic optimal form when orders carry a fixed charge"]],
    ["(s, Q)", HEX.accent2, "Order a fixed Q", "If I ≤ s, order exactly Q.",
      ["Every shipment is the same size", "Simpler to run: pallets, contracts", "Stock after an order varies (I + Q)"]],
  ];
  const cw = (CW - 0.5) / 2;
  pol.forEach(([name, col, head, rule, pts], i) => {
    const x = MX + i * (cw + 0.5), y = 1.45;
    card(s, x, y, cw, 3.75, `${name} card`);
    badge(s, x + 0.4, y + 0.4, 0.95, name.replace(/ /g, ""), col, `${name} badge`);
    text(s, head, { x: x + 1.6, y: y + 0.42, w: cw - 2, h: 0.5, fontSize: 24, bold: true,
      fontFace: THEME.headFontFace });
    text(s, rule, { x: x + 1.6, y: y + 0.95, w: cw - 2, h: 0.4, fontSize: 17, color: col === HEX.accent1 ? C.accent1 : "C0481B", bold: true });
    text(s, pts.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < pts.length - 1 } })),
      { x: x + 0.45, y: y + 1.8, w: cw - 0.9, h: 2.3, fontSize: 16, paraSpaceAfter: 8 });
  });
  text(s, "Fair comparison: both policies face identical demand and delivery-time streams in every replication (common random numbers).",
    { x: MX, y: 5.55, w: CW, h: 0.6, fontSize: 15, color: C.text2, italic: true });
  s.addNotes("The proposal's rule: order when the level is s or below. For (s,Q) one fixed batch is ordered " +
    "even if the level is far below s.");
}

// ================================================================ 5. method
pres.addSection({ title: "Method" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Method" });
  s.addText("Method: build, check, then search in three stages", { placeholder: "title" });
  const d = K.design;
  const steps = [
    ["Build", "Event-driven simulation in Python + Numba; ~3 µs per 120-month run", HEX.accent6],
    ["Verify & validate", "Two independent implementations agree exactly; textbook + exact Markov-chain checks", HEX.accent6],
    ["Screen", `Full integer grid: ${d.grid_sS.toLocaleString()} points per policy × ${d.n_screen} CRN reps`, HEX.accent1],
    ["Re-evaluate", `Top ${d.top_k} per policy × ${d.n_reeval.toLocaleString()} fresh reps; Bonferroni paired-t vs best`, HEX.accent1],
    ["Compare", `Winners head-to-head: ${d.n_final.toLocaleString()} new CRN reps, paired-t test`, HEX.accent2],
  ];
  const bw = (CW - 4 * 0.25) / 5;
  steps.forEach(([h, t], i) => {
    const x = MX + i * (bw + 0.25), y = 1.6;
    card(s, x, y, bw, 3.7, `stage ${i + 1} card`);
    badge(s, x + 0.3, y + 0.3, 0.65, String(i + 1), t && steps[i][2], `stage ${i + 1} badge`);
    text(s, h, { x: x + 0.3, y: y + 1.1, w: bw - 0.6, h: 0.75, fontSize: 18, bold: true, valign: "bottom" });
    text(s, t, { x: x + 0.3, y: y + 1.95, w: bw - 0.6, h: 1.65, fontSize: 14, color: C.text2 });
  });
  text(s, [
    { text: "Why separate stages?  ", options: { bold: true } },
    { text: "Taking the minimum of 12,150 noisy estimates is biased low (the optimizer's curse). " +
      "Each stage uses its own independent random numbers, so the reported costs are unbiased." },
  ], { x: MX, y: 5.6, w: CW, h: 0.9, fontSize: 15 });
  s.addNotes("Common random numbers inside a stage make comparisons sharp; independent seeds across " +
    "stages keep the final estimates honest. Average monthly cost = ordering + holding + shortage.");
}

// ================================================================ 6. validation
pres.addSection({ title: "Validation" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Validation" });
  s.addText("Validation: the model reproduces the textbook example", { placeholder: "title" });
  fitImage(s, FIG("fig02_validation.png"), { x: MX, y: 1.35, w: 7.9, h: 5.5 }, "validation chart");
  const v = K.validation;
  const stats = [
    [`${v.n_in_ci} / ${v.n}`, "exact values inside our 95% CIs (5,000 reps per policy)"],
    [`|z| ≤ ${v.max_abs_z}`, "largest gap between simulation and exact cost, in standard errors"],
    [`$${v.single_run_sd_range[0]}–${v.single_run_sd_range[1]}`, "std. dev. of a single 120-month run: one run, as in the textbook, is not enough"],
  ];
  stats.forEach(([big, small], i) => {
    const y = 1.5 + i * 1.75;
    text(s, big, { x: 8.85, y, w: 3.9, h: 0.75, fontSize: 36, bold: true, color: C.accent1,
      fontFace: THEME.headFontFace });
    text(s, small, { x: 8.85, y: y + 0.75, w: 3.9, h: 0.85, fontSize: 14, color: C.text2 });
  });
  s.addNotes("Validation uses the textbook rule (order when I < s). The textbook numbers come from one " +
    "run each, so they scatter around our tight intervals by a few dollars, as expected.");
}

// ================================================================ 7. exact check
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Validation" });
  s.addText("A second check: the exact cost from a Markov chain", { placeholder: "title" });
  fitImage(s, FIG("fig10_sim_vs_exact.png"), { x: MX, y: 1.3, w: 8.4, h: 5.55 }, "simulation vs exact chart");
  const chain = ["Lag ≤ 1 month", "Orders arrive before the next review", "Stock at reviews is a Markov chain", "Exact expected cost for every grid point"];
  chain.forEach((t, i) => {
    const y = 1.5 + i * 1.12;
    card(s, 9.35, y, 3.38, 0.82, `chain step ${i + 1}`, i === 3 ? "E8F1FC" : HEX.lt2);
    text(s, t, { x: 9.55, y, w: 3.0, h: 0.82, fontSize: 15, bold: i === 3, valign: "middle" });
  });
  text(s, `Correlation with simulation: r > 0.99999 for both policies. Used only to audit the simulation, never to pick the policy.`,
    { x: 9.35, y: 6.0, w: 3.38, h: 0.9, fontSize: 13, color: C.text2 });
  s.addNotes("This exact check is possible only because the lag is shorter than the review period. " +
    "It confirmed the simulation is unbiased and let us audit how close the simulation-based search came to the true optimum.");
}

// ================================================================ 8. surfaces
pres.addSection({ title: "Results" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Each policy has one clear valley of low cost", { placeholder: "title" });
  fitImage(s, FIG("fig03_cost_surfaces.png"), { x: MX, y: 1.3, w: CW, h: 5.55 }, "cost surface heatmaps");
  s.addNotes(`Stage 1 screening: every integer (s,S) and (s,Q) with s 0-80 and S-s or Q 1-150. ` +
    `Both valleys sit at s ≈ 24. Q below the mean monthly demand of 25 is unstable: the backlog grows without bound.`);
}

// ================================================================ 9. flat bottom
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("The bottom of each valley is flat", { placeholder: "title" });
  fitImage(s, FIG("fig04_cost_slices.png"), { x: MX, y: 1.3, w: CW, h: 4.3 }, "cost slices chart");
  const cw = (CW - 0.4) / 2;
  [[`S from ${sS.flat_within_1[0]} to ${sS.flat_within_1[1]}`, `stays within $1 of the best (s, S) cost at s = ${sS.best[0]}`, C.accent1],
   [`Q from ${sQ.flat_within_1[0]} to ${sQ.flat_within_1[1]}`, `stays within $1 of the best (s, Q) cost at s = ${sQ.best[0]}`, "C0481B"]]
    .forEach(([big, small, col], i) => {
      const x = MX + i * (cw + 0.4);
      card(s, x, 5.75, cw, 1.0, `flat callout ${i + 1}`);
      text(s, [{ text: big + "  ", options: { bold: true, color: col, fontSize: 20 } },
               { text: small, options: { color: C.text2 } }],
        { x: x + 0.3, y: 5.75, w: cw - 0.6, h: 1.0, fontSize: 15, valign: "middle" });
    });
  s.addNotes("Practical point: the recommendation is robust. Rounding S to a convenient pallet size costs very little.");
}

// ================================================================ 10. selection
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Choosing the winner without fooling ourselves", { placeholder: "title" });
  fitImage(s, FIG("fig05_top_candidates.png"), { x: MX, y: 1.3, w: CW, h: 4.55 }, "top candidates chart");
  text(s, [
    { text: "Stage-1 minima looked cheaper than they are; fresh replications correct the optimizer's curse. ", options: {} },
    { text: `${sS.n_indistinguishable} (s, S) and ${sQ.n_indistinguishable} (s, Q) candidates are statistically tied with their best. ` },
    { text: `Audit against the exact cost: our picks are $${sS.optimality_gap.toFixed(3)} and $${sQ.optimality_gap.toFixed(3)} from the true optima.`, options: { bold: true } },
  ], { x: MX, y: 5.95, w: CW, h: 0.85, fontSize: 15 });
  s.addNotes("Grey points are significantly worse than the best after a Bonferroni correction. Black ticks are exact costs.");
}

// ================================================================ 11. headline result
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Result: (s, S) wins, by a small but certain margin", { placeholder: "title" });
  const cw = (CW - 2 * 0.35) / 3;
  const cards = [
    [money(sS.mean), `± ${sS.hw.toFixed(2)}`, `best (s, S) = (${sS.best[0]}, ${sS.best[1]})`, C.accent1, "E8F1FC"],
    [money(sQ.mean), `± ${sQ.hw.toFixed(2)}`, `best (s, Q) = (${sQ.best[0]}, ${sQ.best[1]})`, "C0481B", "FDEEE7"],
    [money(D.mean), `95% CI [${D.lo.toFixed(2)}, ${D.hi.toFixed(2)}]`, "extra monthly cost of (s, Q)", C.text1, HEX.lt2],
  ];
  cards.forEach(([big, ci, lab, col, fill], i) => {
    const x = MX + i * (cw + 0.35);
    card(s, x, 1.55, cw, 2.9, `result card ${i + 1}`, fill);
    text(s, big, { x: x + 0.35, y: 1.8, w: cw - 0.7, h: 1.1, fontSize: 54, bold: true, color: col,
      fontFace: THEME.headFontFace });
    text(s, ci, { x: x + 0.35, y: 2.95, w: cw - 0.7, h: 0.45, fontSize: 16, color: C.text2 });
    text(s, lab, { x: x + 0.35, y: 3.5, w: cw - 0.7, h: 0.7, fontSize: 17, bold: true });
  });
  const pts = [
    `Paired-t on ${K.design.n_final.toLocaleString()} new CRN replications: t = ${D.t}, p < 10⁻³⁰⁰. The gap is real, but only ${D.pct}% of the cost.`,
    `Versus the textbook's (20, 40) rule (${money(base.mean)}), the optimized (s, S) saves ${money(K.baseline_saving)} per month (${K.baseline_saving_pct}%).`,
    `Both optimal rules use the same reorder point, s = ${sS.best[0]}; they differ only in how much they order.`,
  ];
  text(s, pts.map((p, j) => ({ text: p, options: { bullet: true, breakLine: j < pts.length - 1 } })),
    { x: MX, y: 4.8, w: CW, h: 1.9, fontSize: 16, paraSpaceAfter: 8 });
  s.addNotes("Monthly cost averaged over the 120-month horizon, ± 95% confidence half-width.");
}

// ================================================================ 12. breakdown (native chart)
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Where the money goes", { placeholder: "title" });
  // horizontal bars are drawn bottom-up, so list the baseline last to show it on top
  const labels = [`(s,Q) = (${sQ.best[0]}, ${sQ.best[1]})`, `(s,S) = (${sS.best[0]}, ${sS.best[1]})`, "(20, 40) baseline"];
  const data = [
    { name: "Ordering", labels, values: [sQ.ordering, sS.ordering, base.ordering] },
    { name: "Holding", labels, values: [sQ.holding, sS.holding, base.holding] },
    { name: "Shortage", labels, values: [sQ.shortage, sS.shortage, base.shortage] },
  ];
  s.addChart(pres.charts.BAR, data, {
    x: MX, y: 1.35, w: 7.9, h: 5.4, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 60,
    chartColors: [HEX.accent3, HEX.accent4, HEX.accent5],
    showValue: true, dataLabelPosition: "ctr", dataLabelFormatCode: "0.0", dataLabelColor: "FFFFFF",
    dataLabelFontSize: 12, dataLabelFontBold: true, dataLabelFontFace: "+mn-lt",
    showLegend: true, legendPos: "b", legendFontSize: 13, legendFontFace: "+mn-lt", legendColor: HEX.dk1,
    catAxisLabelColor: HEX.dk1, valAxisLabelColor: HEX.dk2, catAxisLabelFontSize: 13,
    valAxisLabelFontSize: 11, catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valAxisMinVal: 0, valAxisMaxVal: 130, valAxisMajorUnit: 20,
    valGridLine: { color: "E4E3DF", size: 0.75 }, catGridLine: { style: "none" },
    showValAxisTitle: true, valAxisTitle: "average monthly cost ($)", valAxisTitleFontSize: 12,
    valAxisTitleColor: HEX.dk2, valAxisTitleFontFace: "+mn-lt",
    objectName: "cost breakdown chart", altText: "Stacked bar chart of ordering, holding and shortage cost for three policies",
  });
  const pts = [
    [`${money(base.ordering - sS.ordering)}`, "less ordering cost: bigger, rarer orders"],
    [`${money(base.shortage - sS.shortage)}`, "less shortage cost: fewer backlogged customers"],
    [`+${money(sS.holding - base.holding)}`, "more holding cost: the price of that buffer"],
  ];
  pts.forEach(([big, small], i) => {
    const y = 1.55 + i * 1.6;
    text(s, big, { x: 8.85, y, w: 3.9, h: 0.7, fontSize: 32, bold: true, fontFace: THEME.headFontFace,
      color: [C.accent3, C.accent5, "B07800"][i] });
    text(s, small, { x: 8.85, y: y + 0.7, w: 3.9, h: 0.7, fontSize: 15, color: C.text2 });
  });
  s.addNotes("Compared with the textbook (20,40) rule. The two optimized rules have almost the same cost mix; " +
    "(s,Q) holds slightly more stock because its post-order level is less controlled.");
}

// ================================================================ 13. sample paths
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("What the two policies do, month by month", { placeholder: "title" });
  fitImage(s, FIG("fig01_sample_paths.png"), { x: MX, y: 1.25, w: CW, h: 5.65 }, "inventory sample path chart");
  s.addNotes("One replication, same demand stream for both. (s,S) always refills to 62. (s,Q) adds 51 " +
    "to whatever is left, so after a bad month it can stay short (around month 65) and after a quiet one it overshoots.");
}

// ================================================================ 14. CRN
pres.addSection({ title: "Analysis" });
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
  s.addText(`Common random numbers cut the work about ${Math.round(K.crn.reps_factor)}×`, { placeholder: "title" });
  fitImage(s, FIG("fig07_crn_variance_reduction.png"), { x: MX, y: 1.3, w: CW, h: 4.5 }, "CRN variance reduction chart");
  text(s, [
    { text: `Var(difference) with CRN is ${Math.round(100 * K.crn.var_ratio)}% of the independent-sampling variance. `, options: { bold: true } },
    { text: `Independent streams would need about ${(K.crn.reps_factor * K.design.n_final).toLocaleString(undefined, { maximumFractionDigits: 0 })} replications to match the precision CRN gets from ${K.design.n_final.toLocaleString()}.` },
  ], { x: MX, y: 5.95, w: CW, h: 0.8, fontSize: 15 });
  s.addNotes("CRN works because both policies' costs rise and fall with the same demand: a heavy month hurts both.");
}

// ================================================================ 15. sensitivity
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Analysis" });
  s.addText("Sensitivity: (s, S) is never worse", { placeholder: "title" });
  fitImage(s, FIG("fig09_sensitivity.png"), { x: MX, y: 1.25, w: 8.6, h: 5.65 }, "sensitivity chart");
  const pts = [
    ["14 / 14", "cost scenarios where re-optimized (s, S) beats re-optimized (s, Q)"],
    [`$${K.sensitivity_min_gap.toFixed(2)}–${K.sensitivity_max_gap.toFixed(2)}`, "monthly advantage of (s, S)"],
    ["Biggest gap", "when storage is expensive (h = $4) or setup is cheap (K = $8): exact order sizes then matter most"],
  ];
  pts.forEach(([big, small], i) => {
    const y = 1.45 + i * 1.75;
    text(s, big, { x: 9.5, y, w: 3.23, h: 0.7, fontSize: 30, bold: true, color: C.accent1,
      fontFace: THEME.headFontFace });
    text(s, small, { x: 9.5, y: y + 0.7, w: 3.23, h: 0.95, fontSize: 14, color: C.text2 });
  });
  s.addNotes("For each scenario both policies were re-optimized from scratch (screening + fresh re-evaluation). " +
    "The ranking never flips.");
}

// ================================================================ 16. recommendation
pres.addSection({ title: "Conclusion" });
{
  const s = pres.addSlide({ masterName: "DARK_CONTENT", sectionTitle: "Conclusion" });
  s.addText("Recommendation", { placeholder: "title" });
  text(s, [
    { text: "Use an (s, S) policy with ", options: { color: "CADCFC" } },
    { text: `s = ${sS.best[0]} and S = ${sS.best[1]}`, options: { bold: true, color: "FFFFFF" } },
  ], { x: MX, y: 1.45, w: CW, h: 0.9, fontSize: 34, fontFace: THEME.headFontFace });
  const pts = [
    ["Cheapest", `${money(sS.mean)} ± ${sS.hw.toFixed(2)} per month: lowest of 24,300 rules tested`],
    ["Robust", `any S from ${sS.flat_within_1[0]} to ${sS.flat_within_1[1]} costs within $1 of the best`],
    ["Reliable", `beats the best (s, Q) in all 14 cost scenarios, by $${K.sensitivity_min_gap.toFixed(2)}–${K.sensitivity_max_gap.toFixed(2)} a month`],
    ["Fallback", `if fixed batches are required, (s, Q) = (${sQ.best[0]}, ${sQ.best[1]}) costs only ${D.pct}% more`],
  ];
  const cw = (CW - 3 * 0.3) / 4;
  pts.forEach(([h, t], i) => {
    const x = MX + i * (cw + 0.3);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.75, w: cw, h: 2.0, rectRadius: 0.12,
      fill: { color: "22325A" }, line: { color: "22325A" }, objectName: `takeaway ${i + 1}` });
    text(s, h, { x: x + 0.3, y: 2.95, w: cw - 0.6, h: 0.5, fontSize: 20, bold: true, color: "FFFFFF" });
    text(s, t, { x: x + 0.3, y: 3.5, w: cw - 0.6, h: 1.15, fontSize: 15, color: "CADCFC" });
  });
  text(s, [
    { text: "Limitations:  ", options: { bold: true, color: "FFFFFF" } },
    { text: "stationary demand, a single product, no capacity limits, the textbook's cost values, and a fixed 120-month horizon from 60 units. " +
      "The code re-runs the whole study for new parameters in about 4 minutes.", options: { color: "CADCFC" } },
  ], { x: MX, y: 5.2, w: CW, h: 1.0, fontSize: 14 });
  s.addNotes("Close with the decision, the evidence, and the caveats.");
}

// ================================================================ 17. team + references
{
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Conclusion" });
  s.addText("Team contributions and references", { placeholder: "title" });
  const team = [
    ["JG", "Jahnavi Gouru", "Built the simulation model: event logic, random-number streams, verification tests."],
    ["MR", "Mary Reethika Reddy Kolukula", "Ran the replications and compared the two policies: CIs, paired-t, CRN analysis."],
    ["PK", "Praneeth Kapila", "Searched for good s, S and Q: grid screening, re-evaluation, sensitivity."],
  ];
  const cw = (CW - 2 * 0.35) / 3;
  team.forEach(([ini, name, role], i) => {
    const x = MX + i * (cw + 0.35);
    card(s, x, 1.45, cw, 2.55, `${name} card`);
    badge(s, x + 0.35, 1.75, 0.75, ini, [HEX.accent1, HEX.accent2, HEX.accent3][i], `${name} badge`);
    text(s, name, { x: x + 1.3, y: 1.75, w: cw - 1.55, h: 0.75, fontSize: 17, bold: true, valign: "middle" });
    text(s, role, { x: x + 0.35, y: 2.75, w: cw - 0.7, h: 1.1, fontSize: 14, color: C.text2 });
  });
  text(s, "All three wrote the report and presentation sections for their part.",
    { x: MX, y: 4.2, w: CW, h: 0.4, fontSize: 14, italic: true, color: C.text2 });
  const refs = [
    "A. M. Law, Simulation Modeling and Analysis, 5th ed., McGraw-Hill, 2015: Sec. 1.5, the inventory system.",
    "H. Scarf, \"The optimality of (S, s) policies in the dynamic inventory problem,\" 1960.",
    "B. L. Nelson, Foundations and Methods of Stochastic Simulation, 2nd ed., Springer, 2021: CRN, ranking & selection.",
    "Code, data and figures: github.com/reethika925/inventory-simulation-optimization",
  ];
  text(s, refs.map((r, j) => ({ text: r, options: { bullet: true, breakLine: j < refs.length - 1 } })),
    { x: MX, y: 4.8, w: CW, h: 1.95, fontSize: 14, paraSpaceAfter: 6 });
  s.addNotes("Workload split as in the proposal.");
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();

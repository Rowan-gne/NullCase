// sandbox README: the battery finds out why a test is flaky.
// Replays a real run on eval/demo-repo (2026-09-28); local paths in the repro
// command are shortened, everything else is the tool's own output.
import { COLORS, MONO_ADVANCE, Scene, rect, spans, text, windowFrame } from "./svg.mjs";

export default function build() {
  const size = 12.5;
  const lh = 19;
  const x = 40;
  const ch = size * MONO_ADVANCE;
  const s = new Scene({
    width: 880,
    height: 530,
    loop: 17,
    title: "nullcase-battery diagnoses an order-dependent test",
    desc:
      "nullcase-battery re-runs tests/test_order.py::test_first_user_gets_id_1 10 times with every factor pinned " +
      "and 10 times with the test order shuffled. The pinned runs fail 0 of 10 and the shuffled runs 7 of 10. " +
      "Their 95% Wilson intervals, [0.00, 0.28] and [0.40, 0.89], don't overlap, so the diagnosis is order_dependent, " +
      "with a repro command that failed 3 of 3 replays. Recorded on eval/demo-repo on 2026-09-28; paths shortened.",
  });
  s.add(windowFrame(20, 16, 840, 332, "NullCase"));

  let y = 72;
  s.add(spans(x, y, [["$", COLORS.sky]], { size }));
  let t = s.type(x + 2 * ch, y, "nullcase-battery --project eval/demo-repo --only order \\", 0.8, { size, cps: 42 });
  y += lh;
  t = s.type(x + 6 * ch, y, "--baseline-runs 10 --runs 10 tests/test_order.py::test_first_user_gets_id_1", t + 0.1, {
    size,
    cps: 42,
  });

  t += 0.5;
  for (const line of ["… baseline", "… order", "… confirming --randomly-seed=3626764237"]) {
    y += lh;
    s.show(text(x, y, line, { size, cls: "mono muted" }), t);
    t += 0.75;
  }
  y += lh + 6;
  s.show(spans(x, y, [["target: ", COLORS.muted], ["tests/test_order.py::test_first_user_gets_id_1", COLORS.amber]], { size }), t);
  t += 0.6;

  y += lh + 6;
  s.show(text(x, y, "              runs  fails   rate  95% Wilson CI", { size, cls: "mono muted" }), t);
  y += lh;
  const baselineAt = t + 0.4;
  s.show(text(x, y, "baseline        10      0   0.00  [0.00, 0.28]", { size, cls: "mono" }), baselineAt);
  y += lh;
  const orderAt = baselineAt + 0.8;
  s.show(
    rect(x - 8, y - size - 2, 69 * ch + 16, lh, { fill: COLORS.amber, opacity: 0.12, rx: 4 }) +
      spans(x, y, [["order           10      7   0.70  [0.40, 0.89]  ", COLORS.text, 700], ["differs from baseline", COLORS.amber, 700]], { size }),
    orderAt,
  );

  y += lh + 6;
  t = orderAt + 1.9;
  s.show(spans(x, y, [["diagnosis: ", COLORS.muted], ["order_dependent", COLORS.green, 700], [" (wilson interval)", COLORS.muted]], { size }), t);
  y += lh;
  s.show(text(x, y, "repro (--randomly-seed=3626764237, failed 3/3 replays):", { size, cls: "mono muted" }), t + 0.5);
  y += lh;
  s.show(
    text(x, y, "  cd eval/demo-repo && PYTHONHASHSEED=0 TZ=UTC python -m pytest -p no:cacheprovider -q \\", { size, cls: "mono" }) +
      text(x, y + lh, "      --randomly-seed=3626764237 tests/test_order.py", { size, cls: "mono" }),
    t + 0.9,
  );

  // Below the terminal: what the two intervals look like on one axis.
  const top = 366;
  s.add(rect(20, top, 840, 148, { fill: COLORS.card, stroke: COLORS.line, rx: 12 }));
  s.add(text(40, top + 28, "Why it's order_dependent: the 95% Wilson intervals for the failure rate don't overlap", { size: 13.5, cls: "b" }));
  const ax0 = 170;
  const ax1 = 750;
  const scale = (v) => ax0 + v * (ax1 - ax0);
  const axisY = top + 124;
  let axis = `<path d="M${ax0} ${axisY}H${ax1}" stroke="${COLORS.line2}"/>`;
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    axis += `<path d="M${scale(v)} ${axisY - 4}v8" stroke="${COLORS.line2}"/>`;
    axis += text(scale(v), axisY + 17, v.toFixed(2), { size: 10.5, cls: "muted", anchor: "middle" });
  }
  s.add(axis);

  const rows = [
    { label: "baseline  0/10", lo: 0, hi: 0.28, point: 0, color: COLORS.green, at: baselineAt, y: top + 60 },
    { label: "order  7/10", lo: 0.4, hi: 0.89, point: 0.7, color: COLORS.red, at: orderAt, y: top + 94 },
  ];
  for (const r of rows) {
    s.show(text(40, r.y + 5, r.label, { size: 12.5, cls: "mono" }), r.at);
    const bar = rect(scale(r.lo), r.y - 7, scale(r.hi) - scale(r.lo), 14, { fill: r.color, opacity: 0.35, rx: 7 });
    s.show(s.grow(bar, r.at + 0.1), r.at);
    s.show(
      `<circle cx="${scale(r.point)}" cy="${r.y}" r="5" fill="${r.color}"/>` +
        text(772, r.y + 4, `[${r.lo.toFixed(2)}, ${r.hi.toFixed(2)}]`, { size: 11.5, cls: "mono", fill: r.color }),
      r.at + 0.8,
    );
  }
  const gapAt = orderAt + 1.2;
  s.show(
    `<rect x="${scale(0.28)}" y="${top + 42}" width="${scale(0.4) - scale(0.28)}" height="66" fill="${COLORS.amber}" fill-opacity="0.12" stroke="${COLORS.amber}" stroke-dasharray="4 3"/>` +
      text(scale(0.34), top + 56, "gap", { size: 10.5, fill: COLORS.amber, anchor: "middle" }),
    gapAt,
  );
  return { file: "battery.svg", svg: s.render() };
}

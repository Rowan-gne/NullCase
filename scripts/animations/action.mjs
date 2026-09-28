// upload-action README: the Action diagnoses a failing test in CI.
// Replays github.com/Rowan-gne/nullcase-demo/actions/runs/36477779154
// (2026-09-28): step names, the log group title and the annotations are the
// run's own; the timing is compressed.
import { COLORS, Scene, check, cross, rect, spans, text, warning, windowFrame } from "./svg.mjs";

const STEPS = [
  ["Set up job", 0.6, 1.1, true],
  ["Run actions/checkout", 1.1, 1.5, true],
  ["Run actions/setup-python", 1.5, 2.0, true],
  ["Install test dependencies", 2.0, 3.2, true],
  ["Run tests and diagnose failures", 3.2, 7.4, false],
  ["Keep the results and diagnoses", 7.4, 7.9, true],
];

export default function build() {
  const s = new Scene({
    width: 880,
    height: 564,
    loop: 16,
    title: "The NullCase Action diagnoses a failing test in CI",
    desc:
      "A GitHub Actions job named 'pytest with NullCase diagnosis' runs on Rowan-gne/nullcase-demo. " +
      "tests/test_registry.py::test_first_user_gets_id_1 fails, the Action re-runs it under controlled perturbations, " +
      "and the run gets a warning annotation titled 'NullCase: order_dependent': the test fails when the test order " +
      "changes; it depends on state other tests leave. Replay of run 36477779154 from 2026-09-28, time compressed.",
  });
  s.add(windowFrame(20, 16, 840, 496, "github.com/Rowan-gne/nullcase-demo/actions"));

  // Run header: running, then failed.
  s.show(s.spinner(46, 64), 0.2, { until: 7.9, fade: 0.1 });
  s.show(cross(46, 64), 7.9);
  s.add(text(64, 69, "CI", { size: 16, cls: "b" }));
  s.add(text(92, 69, "Rowan-gne/nullcase-demo · workflow_dispatch · c9ce2f9", { size: 12.5, cls: "muted" }));
  s.show(text(836, 69, "failure", { size: 12.5, fill: COLORS.red, anchor: "end", weight: 700 }), 7.9);

  // Steps.
  s.add(rect(36, 88, 276, 250, { fill: COLORS.card, stroke: COLORS.line, rx: 10 }));
  s.add(text(52, 112, "pytest with NullCase diagnosis", { size: 13, cls: "b" }));
  STEPS.forEach(([name, start, end, ok], i) => {
    const y = 140 + i * 26;
    s.show(`<circle cx="60" cy="${y - 4}" r="7" fill="none" stroke="${COLORS.line2}" stroke-width="2"/>`, 0, {
      until: start,
      fade: 0.05,
    });
    s.show(rect(44, y - 17, 260, 25, { fill: COLORS.sky, opacity: 0.1, rx: 6 }) + s.spinner(60, y - 4), start, {
      until: end,
      fade: 0.1,
    });
    s.show(ok ? check(60, y - 4) : cross(60, y - 4), end, { fade: 0.15 });
    s.add(text(76, y, name, { size: 12.5 }));
  });

  // The failing step's log.
  s.add(rect(326, 88, 518, 250, { fill: "#0b1120", stroke: COLORS.line, rx: 10 }));
  s.add(text(342, 112, "Run tests and diagnose failures", { size: 13, cls: "b" }));
  const lx = 342;
  s.show(spans(lx, 142, [["FAILED ", COLORS.red, 700], ["tests/test_registry.py::test_first_user_gets_id_1", COLORS.text]], { size: 11.5 }), 4.0);
  s.show(
    spans(lx, 166, [["▾ ", COLORS.sky], ["NullCase: diagnosing ", COLORS.sky, 700], ["tests/test_registry.py::test_first_user_gets_id_1", COLORS.muted]], {
      size: 11.5,
    }),
    4.6,
  );
  // The battery's own progress lines, which the Action prints inside the group.
  ["baseline", "order", "hash_seed", "network_off", "timezone", "parallel"].forEach((step, i) => {
    s.show(text(lx + 16, 186 + i * 16, `… ${step}`, { size: 11.5, cls: "mono muted" }), 5.0 + i * 0.35);
  });
  s.show(spans(lx, 310, [["Error: ", COLORS.red, 700], ["Process completed with exit code 1.", COLORS.text]], { size: 11.5 }), 7.3);

  // Annotations.
  s.add(rect(36, 352, 808, 146, { fill: COLORS.card, stroke: COLORS.line, rx: 10 }));
  s.add(text(52, 376, "Annotations", { size: 13, cls: "b" }));
  s.show(text(160, 376, "1 error · 1 warning · 1 notice", { size: 12.5, cls: "muted" }), 8.2);
  s.show(
    rect(44, 390, 792, 62, { fill: COLORS.amber, opacity: 0.08, rx: 8 }) +
      warning(62, 410) +
      text(80, 415, "NullCase: order_dependent", { size: 13.5, fill: COLORS.amber, weight: 700 }) +
      text(828, 415, "tests/test_registry.py", { size: 12, cls: "mono muted", anchor: "end" }) +
      text(80, 439, "tests/test_registry.py::test_first_user_gets_id_1 fails when the test order changes; it depends on state other tests leave", {
        size: 12,
      }),
    8.5,
  );
  s.show(cross(62, 474) + text(80, 479, "Process completed with exit code 1.", { size: 12.5, cls: "muted" }), 9.1);

  s.show(
    text(440, 534, "Replay of a real run: Rowan-gne/nullcase-demo, run 36477779154, 2026-09-28 (time compressed).", {
      size: 12,
      cls: "muted",
      anchor: "middle",
    }) +
      text(440, 552, "The job fails because pytest failed; the Action adds the diagnosis as an annotation.", {
        size: 12,
        cls: "muted",
        anchor: "middle",
      }),
    9.4,
  );
  return { file: "ci-annotation.svg", svg: s.render() };
}

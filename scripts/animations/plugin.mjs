// pytest-plugin README: pytest writes one JSON line per test.
// Replays a real run on eval/demo-repo (2026-09-28); the output is copied, not invented.
import { COLORS, MONO_ADVANCE, Scene, spans, text, windowFrame } from "./svg.mjs";

const RECORDS = [
  ["0.000135", "tests/test_order.py", "tests/test_order.py::test_first_user_gets_id_1", "passed"],
  ["0.0001", "tests/test_order.py", "tests/test_order.py::test_register_another_user", "passed"],
  ["0.000194", "tests/test_hash.py", "tests/test_hash.py::test_unique_tags_keeps_first_seen_order", "failed"],
];

export default function build() {
  const size = 12.5;
  const lh = 19;
  const x = 40;
  const s = new Scene({
    width: 880,
    height: 360,
    loop: 14,
    title: "nullcase-pytest writes one JSON line per test",
    desc:
      "A terminal runs pytest with --nullcase-results=results.jsonl on three demo tests: two pass and one fails. " +
      "cat results.jsonl then shows one JSON record per test with its duration, file path, node ID and outcome. " +
      "Recorded on eval/demo-repo on 2026-09-28.",
  });
  s.add(windowFrame(20, 16, 840, 300, "eval/demo-repo"));
  let y = 72;
  s.add(spans(x, y, [["$", COLORS.sky]], { size }));
  const cmd = "pytest -p no:randomly tests/test_order.py tests/test_hash.py --nullcase-results=results.jsonl";
  let t = s.type(x + 2 * size * MONO_ADVANCE, y, cmd, 0.8, { size, cps: 40 });

  y += lh;
  t += 0.5;
  s.show(
    spans(x, y, [[".", COLORS.green], [".", COLORS.green], ["F", COLORS.red]], { size }) +
      text(826, y, "[100%]", { size, cls: "mono muted", anchor: "end" }),
    t,
  );
  y += lh;
  s.show(text(x, y, "⋮  failure details for test_hash.py", { size, cls: "mono muted" }), t + 0.4);
  y += lh;
  s.show(
    spans(x, y, [["FAILED ", COLORS.red], ["tests/test_hash.py::test_unique_tags_keeps_first_seen_order - Assertio...", COLORS.text]], { size }),
    t + 0.8,
  );
  y += lh;
  s.show(
    spans(x, y, [["1 failed", COLORS.red, 700], [", ", COLORS.muted], ["2 passed", COLORS.green, 700], [" in 0.13s", COLORS.muted]], { size }),
    t + 1.2,
  );

  y += lh + 6;
  t += 2.2;
  s.show(spans(x, y, [["$", COLORS.sky]], { size }), t - 0.3);
  t = s.type(x + 2 * size * MONO_ADVANCE, y, "cat results.jsonl", t, { size, cps: 30 });

  t += 0.4;
  for (const [dur, file, nodeid, outcome] of RECORDS) {
    y += lh;
    const first = spans(
      x,
      y,
      [
        ['{"duration_s": ', COLORS.muted],
        [dur, COLORS.amber],
        [', "file_path": ', COLORS.muted],
        [`"${file}"`, COLORS.text],
        [",", COLORS.muted],
      ],
      { size },
    );
    const second = spans(
      x + 2 * size * MONO_ADVANCE,
      y + lh,
      [
        ['"nodeid": ', COLORS.muted],
        [`"${nodeid}"`, COLORS.text],
        [', "outcome": ', COLORS.muted],
        [`"${outcome}"`, outcome === "passed" ? COLORS.green : COLORS.red, 700],
        ["}", COLORS.muted],
      ],
      { size },
    );
    s.show(first + second, t);
    y += lh;
    t += 0.55;
  }

  s.show(
    text(440, 342, "One record per test: outcome, duration, file and node ID. Recorded on eval/demo-repo, 2026-09-28.", {
      size: 12.5,
      cls: "muted",
      anchor: "middle",
    }),
    t + 0.2,
  );
  return { file: "plugin.svg", svg: s.render() };
}

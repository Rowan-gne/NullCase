// README: a live experiment, one fix attempt per seeded flaky test in nullcase-demo.
// From the private service's eval/fix-experiment-results.json (2026-09-28, commit
// 00faab8, claude-sonnet-5-5); targets were declared before the runs. Counts,
// attempts and costs are the runs' own; the timing is compressed.
import { COLORS, Scene, check, cross, rect, rich, text, warning, windowFrame } from "./svg.mjs";

// [test, diagnosis, attempts ("x" rejected, "v" accepted, "f" accepted with a
// review flag), gate experiment, failures before, what the model changed, cost]
const ROWS = [
  ["test_registry.py::test_first_user_gets_id_1", "order_dependent", "v", "order", 13, "an autouse fixture clears the shared registry before and after every test", "$0.0098"],
  ["test_hash.py::test_unique_tags_keeps_first_seen_order", "hash_order", "v", "hash_seed", 15, "list(set(tags)) becomes list(dict.fromkeys(tags)), which keeps first-seen order", "$0.0047"],
  [
    "test_timezone.py::test_invoice_is_dated_today",
    "timezone",
    "xxf",
    "timezone",
    10,
    "1: edited the assertion (policy) · 2: broke a healthy billing test · 3: made the test's today() UTC; flagged for review",
    "$0.0335",
  ],
  ["test_concurrency.py::test_export_report[acme]", "concurrency", "v", "parallel", 15, "each export writes its own temp file instead of one shared file", "$0.0084"],
  ["test_timing.py::test_cache_warmup_finishes_quickly", "timing", "v", "baseline", 9, "waits on the thread's event instead of a fixed 20 ms sleep", "$0.0048"],
  ["test_network.py::test_example_dot_com_is_up", "fails_consistently", "", "baseline", 20, "not attempted: the sandbox is offline, so it fails every run and counts as broken", "—"],
];

export default function build() {
  const s = new Scene({
    width: 880,
    height: 548,
    loop: 22,
    title: "Live experiment: a model fixes every seeded flaky test, checked by the gate",
    desc:
      "claude-sonnet-5-5 was given each seeded flaky test in Rowan-gne/nullcase-demo once, live, on 2026-09-28. " +
      "Order-dependent: fixed on attempt 1, order failures 13 of 20 to 0 of 20. Hash order: fixed on attempt 1, 15 of 20 " +
      "to 0 of 20. Timezone: attempt 1 changed the assertion and was rejected by the policy, attempt 2 broke a healthy " +
      "billing test and was rejected by the suite check, attempt 3 was accepted with a review flag, 10 of 20 to 0 of 20. " +
      "Concurrency: fixed on attempt 1, parallel failures 15 of 20 to 0 of 20. Timing: fixed on attempt 1, 9 of 20 to 0 " +
      "of 20. Network: not attempted, because the offline sandbox makes it fail every run. In total 5 of 5 fixable tests " +
      "fixed, 4 on the first attempt, 7 model calls, $0.061.",
  });
  s.add(windowFrame(20, 16, 840, 462, "Live fix experiment · Rowan-gne/nullcase-demo @ 00faab8 · claude-sonnet-5-5"));
  s.add(
    text(40, 70, "Each seeded flaky test, once, with a live model call. The gate decides; nothing was re-run for a better result.", {
      size: 13,
      cls: "muted",
    }),
  );
  const head = 98;
  s.add(
    text(40, head, "TEST", { size: 10.5, cls: "muted b" }) +
      text(404, head, "DIAGNOSIS", { size: 10.5, cls: "muted b" }) +
      text(522, head, "TRIES", { size: 10.5, cls: "muted b" }) +
      text(588, head, "FAILURES, BEFORE → AFTER", { size: 10.5, cls: "muted b" }) +
      text(840, head, "COST", { size: 10.5, cls: "muted b", anchor: "end" }) +
      rect(32, head + 8, 816, 1, { fill: COLORS.line }),
  );

  let t = 0.8;
  ROWS.forEach(([test, diagnosis, attempts, experiment, before, change, cost], i) => {
    const y = 128 + i * 50;
    const fixable = attempts !== "";
    const tries = [...attempts];
    const done = t + 0.9 + (tries.length - 1) * 0.6;
    s.show(text(40, y, test, { size: 11, cls: "mono" }), t);
    s.show(text(404, y, diagnosis, { size: 11, cls: "mono", fill: fixable ? COLORS.sky : COLORS.muted }), t + 0.3);

    // Failures before, as a bar out of 20, then after.
    const barX = 652;
    s.show(
      text(588, y, experiment, { size: 11, cls: "muted" }) +
        rect(barX, y - 9, 40, 8, { fill: COLORS.line, rx: 3 }) +
        s.grow(rect(barX, y - 9, (before / 20) * 40, 8, { fill: COLORS.red, rx: 3 }), t + 0.35, { dur: 0.5 }) +
        text(698, y, `${before}/20`, { size: 11, fill: COLORS.red, cls: "mono" }),
      t + 0.3,
    );

    // Each attempt: a spinner, then its verdict.
    tries.forEach((kind, k) => {
      const cx = 530 + k * 20;
      const at = t + 0.5 + k * 0.6;
      s.show(s.spinner(cx, y - 4), at, { until: at + 0.4, fade: 0.08 });
      const mark = kind === "x" ? cross(cx, y - 4) : kind === "f" ? check(cx, y - 4, COLORS.amber) : check(cx, y - 4);
      s.show(mark, at + 0.4, { fade: 0.1 });
    });

    if (fixable) {
      s.show(text(740, y, "→ 0/20", { size: 11, fill: COLORS.green, cls: "mono b" }) + text(840, y, cost, { size: 11, anchor: "end", cls: "mono" }), done);
      const flagged = attempts.endsWith("f");
      s.show(
        (flagged ? warning(48, y + 13, COLORS.amber) : "") +
          text(flagged ? 62 : 40, y + 18, change, {
            size: 11.5,
            fill: flagged ? COLORS.amber : COLORS.muted,
          }),
        done + 0.1,
      );
    } else {
      s.show(text(740, y, "no fix", { size: 11, cls: "mono muted" }) + text(840, y, cost, { size: 11, anchor: "end", cls: "muted" }), done);
      s.show(text(40, y + 18, change, { size: 11.5, cls: "muted" }), done + 0.1);
    }
    t = done + 0.6;
  });

  s.show(
    rect(32, 426, 816, 36, { fill: COLORS.green, opacity: 0.1, stroke: COLORS.line, rx: 8 }) +
      rich(
        440,
        449,
        [
          ["5 of 5 fixable tests fixed", { weight: 700, fill: COLORS.green }],
          ["  ·  4 on the first attempt  ·  7 model calls  ·  $0.061 in total  ·  1 flagged for review", {}],
        ],
        { size: 13.5, anchor: "middle" },
      ),
    t + 0.2,
  );
  s.show(
    text(440, 504, "Measured 2026-09-28 in the Docker sandbox; the targets were declared before the runs. The tests were seeded by NullCase's author,", {
      size: 12,
      cls: "muted",
      anchor: "middle",
    }) +
      text(440, 521, "so this shows the fix loop working on known kinds of flakiness, not a success rate on real-world tests.", {
        size: 12,
        cls: "muted",
        anchor: "middle",
      }),
    t + 0.6,
  );
  return { file: "fix-experiment.svg", svg: s.render() };
}

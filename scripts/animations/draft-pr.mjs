// README: the draft pull request NullCase opened for the demo's flaky test.
// Shows github.com/Rowan-gne/nullcase-demo/pull/1 (2026-09-28): the title,
// branches, evidence table, checks, provenance and CI result are the PR's own;
// the body is an excerpt and the timing is compressed.
import { COLORS, Scene, check, rect, rich, text, windowFrame } from "./svg.mjs";

const ROWS = [
  ["baseline (every factor pinned)", 0, 0],
  ["hash_seed", 0, 0],
  ["network_off", 0, 0],
  ["order", 13, 0],
  ["parallel", 0, 0],
  ["timezone", 0, 0],
];

const CHECKS = [
  "only Python source changed; no config, CI or dependency files",
  "experiments stay on: no fixed seeds, timezone, network or re-runs",
  "target test kept, not skipped, assertions unchanged, nothing swallowed",
];

function tick(x, y) {
  return (
    rect(x, y - 11, 13, 13, { fill: COLORS.sky, rx: 3 }) +
    `<path d="M${x + 3} ${y - 4.5}l2.5 2.6 4.5-5" fill="none" stroke="${COLORS.bg}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
  );
}

export default function build() {
  const s = new Scene({
    width: 880,
    height: 816,
    loop: 18,
    title: "The draft pull request NullCase opened for a flaky test",
    desc:
      "Draft pull request #1 on Rowan-gne/nullcase-demo, 'Fix flaky test_first_user_gets_id_1 (order dependent)', " +
      "from the branch nullcase-fix/test_first_user_gets_id_1 into main. The body shows the evidence: the same " +
      "experiments re-run on the patched code, with order failures dropping from 13 of 20 to 0 of 20 and every other " +
      "experiment at 0 of 20; the repro failed 3 of 3 before and passed 5 of 5 after; 0 failures in 120 runs. Three " +
      "anti-cheat checks are ticked. Provenance: patch proposed by claude-sonnet-5-5 in a live call, attempt 1 of 3, " +
      "2,549 input and 337 output tokens, $0.0095, accepted by the NullCase battery, not by the model. The pull " +
      "request's CI check passes. Opened on 2026-09-28; time compressed.",
  });
  s.add(windowFrame(20, 16, 840, 752, "github.com/Rowan-gne/nullcase-demo/pull/1"));

  // Title and branch line.
  s.add(
    rich(40, 80, [["Fix flaky test_first_user_gets_id_1 (order dependent) ", { weight: 700 }], ["#1", { fill: COLORS.muted }]], {
      size: 20,
    }),
  );
  s.add(rect(40, 96, 62, 24, { fill: COLORS.line2, rx: 12 }) + text(71, 112.5, "Draft", { size: 12.5, anchor: "middle", weight: 700 }));
  s.add(
    rich(
      114,
      112.5,
      [
        ["Rowan-gne", { weight: 700 }],
        [" wants to merge 1 commit into ", { fill: COLORS.muted }],
        ["main", { mono: true, fill: COLORS.sky }],
        [" from ", { fill: COLORS.muted }],
        ["nullcase-fix/test_first_user_gets_id_1", { mono: true, fill: COLORS.sky }],
      ],
      { size: 13 },
    ),
  );

  // The PR description.
  const left = 56;
  const head = "#172033";
  s.add(rect(36, 136, 808, 34, { fill: head, stroke: COLORS.line, rx: 8 }) + rect(36, 156, 808, 556, { fill: COLORS.bg, stroke: COLORS.line }));
  s.add(rect(37, 157, 806, 14, { fill: head }));
  s.add(rich(52, 158, [["Rowan-gne", { weight: 700 }], [" opened this pull request", { fill: COLORS.muted }]], { size: 12.5 }));
  s.show(text(left, 198, "NullCase: fix for a flaky test", { size: 17, weight: 700 }) + rect(left, 208, 772, 1, { fill: COLORS.line }), 0.5);
  s.show(
    rich(left, 232, [["Test: ", { weight: 700 }], ["tests/test_registry.py::test_first_user_gets_id_1", { mono: true }]], { size: 13 }) +
      rich(left, 252, [["Diagnosis: ", { weight: 700 }], ["order_dependent", { mono: true }], [", decided by non-overlapping 95% Wilson intervals.", {}]], {
        size: 13,
      }),
    0.9,
  );

  // Evidence table: the "after" column arrives once the gate has re-run each experiment.
  s.show(text(left, 282, "Evidence", { size: 15, weight: 700 }), 1.6);
  const cols = [left + 12, 330, 430];
  const tableTop = 294;
  const rowH = 22;
  s.show(
    rect(left, tableTop, 460, rowH, { fill: head, stroke: COLORS.line }) +
      text(cols[0], tableTop + 15.5, "Experiment", { size: 12.5, weight: 700 }) +
      text(cols[1], tableTop + 15.5, "Before", { size: 12.5, weight: 700 }) +
      text(cols[2], tableTop + 15.5, "After", { size: 12.5, weight: 700 }),
    1.9,
  );
  ROWS.forEach(([name, before, after], i) => {
    const y = tableTop + rowH * (i + 1);
    const sig = before > 0;
    const weight = sig ? 700 : undefined;
    s.show(
      rect(left, y, 460, rowH, { fill: sig ? COLORS.red : COLORS.bg, opacity: sig ? 0.1 : 1, stroke: COLORS.line }) +
        text(cols[0], y + 15.5, name, { size: 12.5, weight }) +
        text(cols[1], y + 15.5, `${before}/20`, { size: 12.5, fill: sig ? COLORS.red : COLORS.text, weight }),
      2.2 + i * 0.18,
    );
    s.show(text(cols[2], y + 15.5, `${after}/20`, { size: 12.5, fill: sig ? COLORS.green : COLORS.text, weight }), 3.6 + i * 0.3);
  });
  s.show(text(534, tableTop + rowH * 4 + 15.5, "← only test order mattered: 13/20 → 0/20", { size: 12.5, fill: COLORS.green }), 5.6);

  const below = tableTop + rowH * (ROWS.length + 1);
  s.show(
    rich(left, below + 24, [["Reproduction", { weight: 700 }], [" (", {}], ["--randomly-seed=1806341205", { mono: true }], ["): failed 3/3 replays before the fix; passed 5/5 after.", {}]], {
      size: 13,
    }) +
      rich(left, below + 44, [["Rest of the suite:", { weight: 700 }], [" 3 full runs; newly failing tests: none.", {}]], { size: 13 }) +
      rich(left, below + 64, [["After the fix:", { weight: 700 }], [" 0 failures in 120 runs; the 95% Wilson upper bound on the failure rate is 0.031.", {}]], {
        size: 13,
      }),
    6.0,
  );

  // Checks and provenance.
  const checksTop = below + 96;
  s.show(text(left, checksTop, "Checks", { size: 15, weight: 700 }), 6.6);
  CHECKS.forEach((line, i) => {
    const y = checksTop + 22 + i * 20;
    s.show(tick(left + 2, y) + text(left + 24, y, line, { size: 13 }), 6.9 + i * 0.3);
  });
  const provTop = checksTop + 94;
  s.show(
    text(left, provTop, "Provenance", { size: 15, weight: 700 }) +
      rich(
        left,
        provTop + 22,
        [["Patch proposed by ", {}], ["claude-sonnet-5-5", { mono: true }], [" (live call to claude-sonnet-5-5), attempt 1 of 3; 2,549 input", {}]],
        { size: 13 },
      ) +
      text(left, provTop + 41, "tokens (2,110 written to the prompt cache, 0 read from it) and 337 output tokens, $0.0095.", { size: 13 }) +
      text(left, provTop + 60, "Accepted by the NullCase battery, not by the model.", { size: 13, weight: 700 }),
    8.0,
  );

  // The PR's CI check: running, then passed.
  const ciTop = 722;
  s.add(rect(36, ciTop, 808, 30, { fill: COLORS.card, stroke: COLORS.line, rx: 8 }));
  const job = ["  ·  CI / pytest with NullCase diagnosis (pull_request)", { fill: COLORS.muted }];
  s.show(
    s.spinner(56, ciTop + 15, COLORS.amber) + rich(72, ciTop + 19.5, [["Some checks haven't completed yet", { weight: 700 }], job], { size: 12.5 }),
    0.3,
    { until: 9.4, fade: 0.15 },
  );
  s.show(
    check(56, ciTop + 15) +
      rich(72, ciTop + 19.5, [["All checks have passed", { weight: 700, fill: COLORS.green }], job], { size: 12.5 }) +
      text(828, ciTop + 19.5, "Successful in 16s", { size: 12.5, fill: COLORS.muted, anchor: "end" }),
    9.4,
  );

  s.show(
    text(440, 790, "Draft PR opened by NullCase on 2026-09-28: Rowan-gne/nullcase-demo#1 (an excerpt of its description; time compressed).", {
      size: 12,
      cls: "muted",
      anchor: "middle",
    }) +
      text(440, 807, "A green CI run alone proves little (the unfixed test passes whenever it runs first); the evidence is the table.", {
        size: 12,
        cls: "muted",
        anchor: "middle",
      }),
    9.8,
  );
  return { file: "draft-pr.svg", svg: s.render() };
}

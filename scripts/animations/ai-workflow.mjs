// README: one recorded run, from a flaky test to a proposed fix, showing the one
// step where a model is used. From the private service's
// eval/fix-showcase-results.json (run 20260929-024232-4893ff on
// Rowan-gne/nullcase-demo at 8e625d7, 2026-09-29). Every number, the model's
// words and the patch are the run's own; the timing is compressed.
import { COLORS, Scene, check, rect, rich, text, windowFrame } from "./svg.mjs";

const VIOLET = "#a78bfa";
const VIOLET_FILL = "#7c3aed";
const RAIL_X = 60;
const X = 92; // section content
const RIGHT = 836;

// Detection: each of the 10 suite runs, as recorded ("F" failed, "." passed).
const TARGET_RUNS = "FFF..FF.FF";
const REGISTRY_RUNS = "..F.FF.FFF";

// Diagnosis: failures out of 20 per condition.
const DIAGNOSIS = [
  ["pinned (test alone)", 0],
  ["test order", 17],
  ["hash seed", 0],
  ["network off", 0],
  ["timezone", 0],
  ["parallel", 0],
];

// The model's root cause, verbatim, wrapped to fit.
const ROOT_CAUSE = [
  "currency() is memoized with functools.cache. The parametrized tests set DEMO_CURRENCY and clear the",
  "cache before running, but they never clear it afterwards. monkeypatch restores the environment, yet the",
  "cached 'GBP' or 'EUR' value stays, so test_prices_default_to_usd fails when it runs after them.",
];

// The patch, verbatim: a new tests/conftest.py.
const PATCH = [
  "import pytest",
  "",
  "from demo_service.settings import currency",
  "",
  "",
  "@pytest.fixture(autouse=True)",
  "def _reset_currency_cache():",
  '    """Clear the cached currency setting before and after every test."""',
  "    currency.cache_clear()",
  "    yield",
  "    currency.cache_clear()",
];

function pill(x, y, label, { fill, ink, mono = false, size = 11.5 }) {
  const w = label.length * size * (mono ? 0.6 : 0.56) + 18;
  return {
    w,
    svg:
      rect(x, y - size - 3, w, size + 9, { fill, rx: (size + 9) / 2, opacity: 0.22 }) +
      text(x + w / 2, y + 0.5, label, { size, fill: ink, anchor: "middle", cls: mono ? "mono" : "", weight: 600 }),
  };
}

function dot(cx, cy, failed) {
  const color = failed ? COLORS.red : COLORS.green;
  return `<circle cx="${cx}" cy="${cy}" r="5.5" fill="${color}" fill-opacity="${failed ? 0.95 : 0.35}" stroke="${color}"/>`;
}

export default function build() {
  const s = new Scene({
    width: 880,
    height: 1134,
    loop: 30,
    title: "From a flaky test to a proposed fix: where the AI comes in",
    desc:
      "One recorded NullCase run on Rowan-gne/nullcase-demo (commit 8e625d7, 2026-09-29), in five steps. " +
      "1 Detect, no AI: the whole suite ran 10 times in the sandbox with shuffled order and varied hash seed, timezone " +
      "and parallelism; tests/test_pricing.py::test_prices_default_to_usd failed 7 of 10 runs and another test 6 of 10, " +
      "so both are flaky; 8 other tests passed every run. 2 Diagnose, no AI: 20 runs per condition, one factor at a " +
      "time; only test order changes the failure rate (17 of 20 against 0 of 20 pinned; 95% Wilson intervals 0.64 to " +
      "0.95 against 0 to 0.16), so the diagnosis is order_dependent, with a repro command that failed 3 of 3. " +
      "3 Fix, the only AI step: claude-sonnet-5-5 is given the test file, the code it imports, the evidence and the " +
      "rules, with no tools. It returns the root cause (currency() is cached with functools.cache and the currency " +
      "tests clear the cache before but not after) and a patch: a new tests/conftest.py with an autouse fixture that " +
      "clears the cache before and after every test. One live call: 2,801 input and 480 output tokens, $0.0116. " +
      "4 Gate, no AI: the same experiments on the patched code; test order failures drop from 17 of 20 to 0 of 20, " +
      "the repro passes 5 of 5, nothing else newly fails, 0 failures in 120 runs. 5 Pull request: NullCase prepares " +
      "a draft PR with the evidence and the model's name; a person decides. 77 seconds end to end.",
  });
  s.add(windowFrame(20, 16, 840, 1066, "NullCase: one recorded run, from a flaky test to a proposed fix"));

  // Header and legend.
  s.add(text(44, 76, "From a flaky test to a proposed fix: where the AI comes in", { size: 18, weight: 700 }));
  s.add(
    text(44, 97, "A recorded run on Rowan-gne/nullcase-demo (commit 8e625d7, 2026-09-29). Only step 3 uses a model; the rest is measurement.", {
      size: 12,
      cls: "muted",
    }),
  );
  let lx = 44;
  for (const [label, fill, ink] of [
    ["measured · no AI", COLORS.line2, COLORS.text],
    ["AI · a model writes the patch", VIOLET_FILL, VIOLET],
    ["a person decides", COLORS.green, COLORS.green],
  ]) {
    const p = pill(lx, 122, label, { fill, ink });
    s.add(p.svg);
    lx += p.w + 10;
  }

  const tops = [134, 268, 450, 832, 992];
  const heights = [124, 172, 372, 150, 74];
  s.add(`<line x1="${RAIL_X}" y1="${tops[0] + 20}" x2="${RAIL_X}" y2="${tops[4] + 20}" stroke="${COLORS.line}" stroke-width="2"/>`);

  // A step's card, rail marker and title.
  function step(i, at, title, tag, kind) {
    const top = tops[i];
    const ai = kind === "ai";
    const human = kind === "human";
    const stroke = ai ? VIOLET : human ? COLORS.green : COLORS.line;
    const accent = ai ? VIOLET : human ? COLORS.green : COLORS.sky;
    let svg =
      rect(76, top, 764, heights[i], { fill: ai ? VIOLET_FILL : COLORS.card, opacity: ai ? 0.13 : 0.55, rx: 10 }) +
      `<rect x="76" y="${top}" width="764" height="${heights[i]}" rx="10" fill="none" stroke="${stroke}" stroke-width="${ai ? 1.6 : 1}"/>` +
      `<circle cx="${RAIL_X}" cy="${top + 20}" r="12" fill="${accent}" fill-opacity="0.25" stroke="${accent}"/>` +
      text(RAIL_X, top + 24.5, String(i + 1), { size: 12, anchor: "middle", weight: 700, fill: accent }) +
      text(X, top + 25, title, { size: 15.5, weight: 700, fill: ai ? VIOLET : COLORS.text });
    const p = pill(X + title.length * 9.2 + 14, top + 24, tag, {
      fill: ai ? VIOLET_FILL : human ? COLORS.green : COLORS.line2,
      ink: ai ? VIOLET : human ? COLORS.green : COLORS.muted,
      size: 11,
    });
    svg += p.svg;
    s.show(svg, at);
    return top;
  }

  // 1. Detect.
  let top = step(0, 0.3, "Detect", "no AI · 10 runs · 3.6 s", "measured");
  s.show(
    text(X, top + 48, "The whole suite ran 10 times in the sandbox, shuffling test order and varying hash seed, timezone and parallelism.", {
      size: 12,
      cls: "muted",
    }),
    0.5,
  );
  const rows = [
    ["test_prices_default_to_usd", TARGET_RUNS, "failed 7 of 10: flaky", COLORS.red, true],
    ["test_first_user_gets_id_1", REGISTRY_RUNS, "failed 6 of 10: flaky (the older incident)", COLORS.muted, false],
    ["8 other tests", "..........", "passed every run", COLORS.muted, false],
  ];
  rows.forEach(([name, runs, verdict, ink, main], r) => {
    const y = top + 74 + r * 20;
    s.show(text(X, y + 4, name, { size: 11.5, cls: main ? "mono b" : "mono muted" }), 0.7 + r * 0.1);
    [...runs].forEach((c, k) => s.show(dot(318 + k * 20, y, c === "F"), 0.8 + r * 0.1 + k * 0.12, { fade: 0.08 }));
    s.show(text(532, y + 4, verdict, { size: 12, fill: ink, weight: main ? 700 : undefined }), 2.2 + r * 0.1);
  });

  // 2. Diagnose.
  top = step(1, 3.0, "Diagnose", "no AI · 20 runs per condition · 31 s", "measured");
  s.show(text(X, top + 48, "Re-run with one factor changed at a time, to find the one that makes it fail:", { size: 12, cls: "muted" }), 3.2);
  DIAGNOSIS.forEach(([label, failures], k) => {
    const col = k < 3 ? 0 : 1;
    const x = X + col * 380;
    const y = top + 74 + (k % 3) * 22;
    const hit = failures > 0;
    const at = 3.5 + k * 0.12;
    s.show(
      text(x, y + 4, label, { size: 12, fill: hit ? COLORS.red : COLORS.text, weight: hit ? 700 : undefined }) +
        rect(x + 132, y - 5, 120, 9, { fill: COLORS.line, rx: 4 }) +
        (hit ? s.grow(rect(x + 132, y - 5, (failures / 20) * 120, 9, { fill: COLORS.red, rx: 4 }), at + 0.2) : "") +
        text(x + 262, y + 4, `${failures}/20`, { size: 12, cls: "mono", fill: hit ? COLORS.red : COLORS.muted }),
      at,
    );
  });
  s.show(text(X + 302, top + 100, "← differs", { size: 12, fill: COLORS.red, weight: 700 }), 4.6);
  s.show(
    rich(
      X,
      top + 142,
      [
        ["Verdict: ", { weight: 700 }],
        ["order_dependent", { mono: true, fill: COLORS.amber }],
        [". Only test order changes the failure rate.", {}],
      ],
      { size: 12 },
    ) +
      rich(
        X,
        top + 160,
        [
          ["The 95% Wilson intervals (0.64–0.95 and 0–0.16) don't overlap. Repro ", {}],
          ["--randomly-seed=3626764237", { mono: true }],
          [" failed 3 of 3.", {}],
        ],
        { size: 12 },
      ),
    5.2,
  );

  // 3. Fix: the one AI step.
  top = step(2, 6.2, "Fix", "AI · one live call to claude-sonnet-5-5", "ai");
  let cx = X + 50;
  s.show(text(X, top + 52, "Given", { size: 12.5, weight: 700, fill: VIOLET }), 6.5);
  [
    ["tests/test_pricing.py", true],
    ["pricing.py", true],
    ["settings.py", true],
    ["the evidence from step 2", false],
    ["the failure output", false],
  ].forEach(([label, mono], k) => {
    const p = pill(cx, top + 52, label, { fill: VIOLET_FILL, ink: COLORS.text, mono, size: 11 });
    s.show(p.svg, 6.7 + k * 0.18);
    cx += p.w + 8;
  });
  s.show(
    text(X, top + 76, "No tools: it can't run code, read other files or see secrets. The rules: fix the cause; no skips, no edited assertions.", {
      size: 11.5,
      cls: "muted",
    }),
    7.9,
  );
  s.show(s.spinner(X + 8, top + 101, VIOLET) + text(X + 24, top + 105, "asking claude-sonnet-5-5…", { size: 12, fill: VIOLET }), 8.3, {
    until: 9.5,
    fade: 0.15,
  });
  s.show(
    rich(X, top + 105, [["Returns", { weight: 700, fill: VIOLET }], ["  the root cause, in its own words:", { fill: COLORS.muted }]], { size: 12.5 }),
    9.5,
  );
  s.show(rect(X, top + 113, 3, 54, { fill: VIOLET, rx: 1.5 }), 9.6);
  ROOT_CAUSE.forEach((line, k) => s.show(text(X + 12, top + 126 + k * 18, line, { size: 12 }), 9.7 + k * 0.35));
  s.show(
    rich(X, top + 192, [["and a patch", { weight: 700, fill: VIOLET }], ["  (a new ", { fill: COLORS.muted }], ["tests/conftest.py", { mono: true }], [")", { fill: COLORS.muted }]], {
      size: 12.5,
    }),
    11.0,
  );
  const codeTop = top + 202;
  s.show(rect(X, codeTop, 516, PATCH.length * 13.5 + 14, { fill: "#0b1120", stroke: COLORS.line, rx: 8 }), 11.1);
  PATCH.forEach((line, k) => {
    s.show(text(X + 10, codeTop + 18 + k * 13.5, `+${line}`, { size: 10.5, cls: "mono", fill: COLORS.green }), 11.3 + k * 0.1, { fade: 0.08 });
  });
  const nx = X + 534;
  s.show(
    text(nx, codeTop + 16, "Not trusted yet", { size: 12, weight: 700 }) +
      text(nx, codeTop + 34, "step 4 decides whether", { size: 12, cls: "muted" }) +
      text(nx, codeTop + 50, "the patch works", { size: 12, cls: "muted" }),
    12.6,
  );
  s.show(
    text(nx, codeTop + 84, "This call", { size: 12, weight: 700 }) +
      text(nx, codeTop + 102, "2,801 input tokens", { size: 12, cls: "muted" }) +
      text(nx, codeTop + 118, "480 output tokens", { size: 12, cls: "muted" }) +
      text(nx, codeTop + 142, "$0.0116", { size: 18, weight: 700, fill: VIOLET }),
    13.0,
  );

  // 4. Gate.
  top = step(3, 14.2, "Gate", "no AI · the model doesn't grade its own patch", "measured");
  s.show(text(X, top + 48, "The same experiments, re-run on the patched code:", { size: 12, cls: "muted" }), 14.4);
  s.show(
    text(X, top + 76, "test order", { size: 12, weight: 700 }) +
      rect(X + 90, top + 67, 120, 9, { fill: COLORS.line, rx: 4 }) +
      rect(X + 90, top + 67, 102, 9, { fill: COLORS.red, rx: 4 }) +
      text(X + 218, top + 76, "17/20", { size: 12, cls: "mono", fill: COLORS.red }) +
      text(X + 266, top + 76, "→", { size: 13, cls: "muted" }) +
      rect(X + 290, top + 67, 120, 9, { fill: COLORS.line, rx: 4 }),
    14.7,
  );
  s.show(text(X + 418, top + 76, "0/20", { size: 12, cls: "mono b", fill: COLORS.green }), 15.5);
  s.show(text(X + 470, top + 76, "every other condition: 0/20 before and after", { size: 12, cls: "muted" }), 15.7);
  [
    ["repro --randomly-seed=3626764237 passes 5 of 5", 0],
    ["rest of the suite: 3 runs, nothing newly failing", 1],
    ["0 failures in 120 runs (95% upper bound 0.031)", 2],
    ["policy: no skips, assertions unchanged, no config edits", 3],
  ].forEach(([label, k]) => {
    const x = X + (k % 2) * 380;
    const y = top + 104 + Math.floor(k / 2) * 22;
    s.show(check(x + 7, y - 4) + text(x + 22, y, label, { size: 12 }), 16.0 + k * 0.3);
  });
  s.show(text(RIGHT - 12, top + 25, "accepted", { size: 13, weight: 700, fill: COLORS.green, anchor: "end" }), 17.4);

  // 5. Pull request.
  top = step(4, 18.2, "Pull request", "a person decides", "human");
  s.show(
    text(X, top + 48, "NullCase prepares a draft PR with the diagnosis, the before/after table and the model's name.", { size: 12 }) +
      text(X, top + 64, "Opening it takes a click, and merging it is a person's call, as with any other change.", { size: 12, cls: "muted" }),
    18.5,
  );

  s.show(
    text(440, 1106, "Replay of run 20260929-024232-4893ff: 77 s end to end in the Docker sandbox (detect 3.6 s, diagnose 31 s, fix and gate 41 s),", {
      size: 11.5,
      cls: "muted",
      anchor: "middle",
    }) +
      text(440, 1123, "time compressed. The test was seeded by NullCase's author: this is one recorded run, not a success rate.", {
        size: 11.5,
        cls: "muted",
        anchor: "middle",
      }),
    19.2,
  );
  return { file: "ai-workflow.svg", svg: s.render() };
}

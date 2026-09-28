// Regenerates the README animations in assets/:  node scripts/animations/build.mjs
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import action from "./action.mjs";
import battery from "./battery.mjs";
import plugin from "./plugin.mjs";

const assets = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "assets");
for (const build of [plugin, battery, action]) {
  const { file, svg } = build();
  writeFileSync(join(assets, file), svg);
  console.log(`assets/${file}  ${(svg.length / 1024).toFixed(1)} KB`);
}

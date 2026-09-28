// Builds looping animated SVGs that GitHub and PyPI can display.
//
// README images can't run JavaScript, so this runs at build time instead: it
// lays out a scene and writes CSS keyframe animations into a plain SVG. Every
// element's resting style is its final state, so with animations off
// (prefers-reduced-motion) the image shows the finished frame.

export const COLORS = {
  bg: "#0f172a",
  card: "#1e293b",
  line: "#334155",
  line2: "#475569",
  text: "#e2e8f0",
  muted: "#94a3b8",
  green: "#22c55e",
  red: "#f43f5e",
  amber: "#fbbf24",
  sky: "#38bdf8",
};

const FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace";
export const MONO_ADVANCE = 0.6; // monospace glyph width as a fraction of font size

export function esc(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function text(x, y, content, { size = 13, fill, cls = "", anchor = "start", weight } = {}) {
  const style = fill ? ` style="fill:${fill}"` : "";
  const bold = weight ? ` font-weight="${weight}"` : "";
  const klass = cls ? ` class="${cls}"` : "";
  return `<text x="${x}" y="${y}" font-size="${size}"${klass}${bold} text-anchor="${anchor}"${style} xml:space="preserve">${esc(content)}</text>`;
}

// A line of differently coloured runs: [[text, fill], ...], laid out in monospace.
export function spans(x, y, runs, { size = 12.5 } = {}) {
  let cursor = x;
  const out = [];
  for (const [content, fill, weight] of runs) {
    out.push(text(cursor, y, content, { size, fill, cls: "mono", weight }));
    cursor += content.length * size * MONO_ADVANCE;
  }
  return out.join("");
}

export function rect(x, y, w, h, { fill = COLORS.card, stroke, rx = 0, opacity } = {}) {
  const s = stroke ? ` stroke="${stroke}"` : "";
  const o = opacity !== undefined ? ` fill-opacity="${opacity}"` : "";
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}"${o}${s}/>`;
}

export function windowFrame(x, y, w, h, title, { bar = "#111827", body = COLORS.bg } = {}) {
  const dots = [COLORS.red, COLORS.amber, COLORS.green]
    .map((c, i) => `<circle cx="${x + 18 + i * 16}" cy="${y + 15}" r="5" fill="${c}" fill-opacity="0.85"/>`)
    .join("");
  return (
    rect(x, y, w, h, { fill: body, stroke: COLORS.line, rx: 12 }) +
    `<path d="M${x + 12} ${y}h${w - 24}a12 12 0 0 1 12 12v18h-${w}v-18a12 12 0 0 1 12-12z" fill="${bar}"/>` +
    dots +
    text(x + w / 2, y + 19.5, title, { size: 12, cls: "muted", anchor: "middle" })
  );
}

export function check(cx, cy, color = COLORS.green) {
  return (
    `<circle cx="${cx}" cy="${cy}" r="8" fill="${color}" fill-opacity="0.18" stroke="${color}"/>` +
    `<path d="M${cx - 3.5} ${cy}l2.5 2.6 5-5.4" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`
  );
}

export function cross(cx, cy, color = COLORS.red) {
  return (
    `<circle cx="${cx}" cy="${cy}" r="8" fill="${color}" fill-opacity="0.18" stroke="${color}"/>` +
    `<path d="M${cx - 3} ${cy - 3}l6 6m0-6l-6 6" stroke="${color}" stroke-width="2" stroke-linecap="round"/>`
  );
}

export function warning(cx, cy, color = COLORS.amber) {
  return (
    `<path d="M${cx} ${cy - 8}l8.5 15h-17z" fill="${color}" fill-opacity="0.18" stroke="${color}" stroke-linejoin="round"/>` +
    `<path d="M${cx} ${cy - 3}v5" stroke="${color}" stroke-width="2" stroke-linecap="round"/>` +
    `<circle cx="${cx}" cy="${cy + 4.6}" r="1.2" fill="${color}"/>`
  );
}

export class Scene {
  constructor({ width, height, loop, title, desc, ink = COLORS.text, mutedInk = COLORS.muted }) {
    Object.assign(this, { width, height, loop, title, desc, ink, mutedInk });
    this.fadeOutAt = loop - 1.2; // everything fades out, then a short blank before the loop
    this.parts = [];
    this.styles = [];
    this.defs = [];
    this.n = 0;
  }

  p(t) {
    return Math.max(0, Math.min(100, (t / this.loop) * 100)).toFixed(2);
  }

  id(prefix) {
    this.n += 1;
    return `${prefix}${this.n}`;
  }

  add(svg) {
    this.parts.push(svg);
  }

  // Show `svg` from `at` to the end of the loop, or only until `until`.
  show(svg, at, { until = null, fade = 0.3 } = {}) {
    const k = this.id("k");
    const end = until ?? this.fadeOutAt;
    const out = until === null ? 0.6 : fade;
    const rest = until === null ? "" : "opacity:0;";
    this.styles.push(
      `@keyframes ${k}{0%,${this.p(at)}%{opacity:0}${this.p(at + fade)}%,${this.p(end)}%{opacity:1}` +
        `${this.p(end + out)}%,100%{opacity:0}}.${k}{${rest}animation:${k} ${this.loop}s linear infinite}`,
    );
    this.parts.push(`<g class="a ${k}">${svg}</g>`);
    return k;
  }

  // Type `content` one character at a time with a cursor; returns when it finishes.
  type(x, y, content, at, { size = 12.5, fill = COLORS.text, cps = 32, cover = COLORS.bg } = {}) {
    const advance = size * MONO_ADVANCE;
    const width = content.length * advance;
    const dur = content.length / cps;
    const clip = this.id("c");
    const move = this.id("m");
    const caret = this.id("u");
    const gone = this.id("h");
    this.defs.push(
      `<clipPath id="${clip}"><rect x="${x - 1}" y="${y - size}" width="${(width * 1.04 + advance + 2).toFixed(1)}" height="${size * 1.45}"/></clipPath>`,
    );
    this.styles.push(
      `@keyframes ${move}{0%,${this.p(at)}%{transform:translateX(0);animation-timing-function:steps(${content.length},end)}` +
        `${this.p(at + dur)}%,100%{transform:translateX(${width.toFixed(1)}px)}}` +
        `.${move}{transform:translateX(${width.toFixed(1)}px);animation:${move} ${this.loop}s linear infinite}`,
      `@keyframes ${caret}{0%,${this.p(at + dur + 0.35)}%{opacity:1}${this.p(at + dur + 0.4)}%,100%{opacity:0}}` +
        `.${caret}{opacity:0;animation:${caret} ${this.loop}s linear infinite}`,
      // Real monospace fonts run slightly wider than MONO_ADVANCE, so the cover is
      // removed once typing ends rather than left where it might clip the last letter.
      `@keyframes ${gone}{0%,${this.p(at + dur)}%{opacity:1}${this.p(at + dur + 0.02)}%,100%{opacity:0}}` +
        `.${gone}{opacity:0;animation:${gone} ${this.loop}s linear infinite}`,
    );
    const body =
      `<g clip-path="url(#${clip})">${text(x, y, content, { size, fill, cls: "mono" })}` +
      `<g class="a ${move}"><g class="a ${gone}">${rect(x, y - size, width + advance + 4, size * 1.45, { fill: cover })}</g>` +
      `<rect class="a ${caret}" x="${x}" y="${y - size + 1.5}" width="${advance.toFixed(1)}" height="${size * 1.15}" fill="${COLORS.sky}"/></g></g>`;
    this.show(body, at - 0.05, { fade: 0.05 });
    return at + dur;
  }

  // A bar that grows from its left edge.
  grow(svg, at, { dur = 0.9 } = {}) {
    const k = this.id("g");
    this.styles.push(
      `@keyframes ${k}{0%,${this.p(at)}%{transform:scaleX(0);animation-timing-function:cubic-bezier(.2,.8,.2,1)}` +
        `${this.p(at + dur)}%,100%{transform:scaleX(1)}}` +
        `.${k}{transform-box:fill-box;transform-origin:0 50%;animation:${k} ${this.loop}s linear infinite}`,
    );
    return `<g class="a ${k}">${svg}</g>`;
  }

  // A spinning ring, as CI pages show for a running step.
  spinner(cx, cy, color = COLORS.sky) {
    if (!this.spinStyle) {
      this.spinStyle = true;
      this.styles.push(
        "@keyframes spin{to{transform:rotate(360deg)}}" +
          ".spin{transform-box:fill-box;transform-origin:center;animation:spin .9s linear infinite}",
      );
    }
    return `<circle class="spin" cx="${cx}" cy="${cy}" r="7" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="30 14" stroke-linecap="round"/>`;
  }

  // An indeterminate progress strip, visible between `at` and `until`.
  busy(x, y, w, at, until, color = COLORS.sky) {
    const k = this.id("s");
    this.styles.push(
      `@keyframes ${k}{0%{transform:translateX(0)}100%{transform:translateX(${w - 60}px)}}` +
        `.${k}{animation:${k} 1.1s ease-in-out infinite alternate}`,
    );
    const strip =
      rect(x, y, w, 4, { fill: COLORS.line, rx: 2 }) +
      `<g class="${k}">${rect(x, y, 60, 4, { fill: color, rx: 2 })}</g>`;
    this.show(strip, at, { until, fade: 0.2 });
  }

  render() {
    return (
      `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${this.width} ${this.height}" ` +
      `width="${this.width}" height="${this.height}" role="img" aria-labelledby="title desc" xml:space="preserve">\n` +
      `<title id="title">${esc(this.title)}</title>\n<desc id="desc">${esc(this.desc)}</desc>\n` +
      `<style>text{font-family:${FONT};fill:${this.ink};white-space:pre}.mono{font-family:${MONO}}` +
      `.muted{fill:${this.mutedInk}}.b{font-weight:700}${this.styles.join("")}` +
      `@media (prefers-reduced-motion:reduce){.a{animation:none!important}}</style>\n` +
      `<defs>${this.defs.join("")}</defs>\n${this.parts.join("\n")}\n</svg>\n`
    );
  }
}

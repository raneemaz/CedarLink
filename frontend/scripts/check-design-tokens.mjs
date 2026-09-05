#!/usr/bin/env node
/**
 * Fail if a raw Tailwind colour utility reappears in frontend/src.
 *
 * The token layer in src/index.css is only worth having if it stays the
 * only way colour is expressed. One `bg-white` merged on a Friday is not
 * a problem; twenty of them over a quarter are a second, undocumented
 * palette, and by then nobody can tell which of the two is correct. So
 * the rule is enforced rather than agreed.
 *
 * This is a text scan, not an AST pass, because Tailwind classes are not
 * syntax: they turn up in string literals, in template chunks, in ternary
 * branches and in plain lookup objects like `STATUS_TONE`. A regex over
 * the file catches all of those; an AST rule would have to re-find them.
 *
 * Run: npm run lint:tokens        (CI runs it as its own step)
 *
 * When it fails, the fix is to use the role token, not to widen this
 * file: see docs/decisions/0028-design-tokens.md for the role list.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("../src", import.meta.url).pathname.replace(/^\/(\w:)/, "$1");

const EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".css"];

// Utility prefixes that take a colour. Longest first so `border-t` wins
// over `border` in the alternation.
const PREFIX = [
  "bg", "text",
  "border-t", "border-b", "border-l", "border-r",
  "border-s", "border-e", "border-x", "border-y", "border",
  "ring-offset", "ring", "outline", "divide",
  "placeholder", "accent", "caret", "decoration",
  "from", "via", "to", "fill", "stroke",
].join("|");

// Every family in Tailwind's default palette.
const FAMILY = [
  "slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber",
  "yellow", "lime", "green", "emerald", "teal", "cyan", "sky", "blue",
  "indigo", "violet", "purple", "fuchsia", "pink", "rose",
].join("|");

// Any number of variants in front (hover:, focus:, disabled:, sm:, rtl:,
// group-hover:, peer-checked:, ...).
const VARIANT = "(?:[a-z0-9-]+:)*";

const RULES = [
  {
    name: "palette shade",
    // hover:bg-emerald-700, text-gray-500/80
    re: new RegExp(
      `(?<![\\w-])!?${VARIANT}(?:${PREFIX})-(?:${FAMILY})-\\d{2,3}(?:/\\d{1,3})?(?![\\w-])`,
      "g",
    ),
  },
  {
    name: "bare white/black",
    // bg-white, text-white/70. `transparent`, `current` and `inherit` are
    // keywords meaning "no colour of my own" and are deliberately allowed.
    re: new RegExp(
      `(?<![\\w-])!?${VARIANT}(?:${PREFIX})-(?:white|black)(?:/\\d{1,3})?(?![\\w-])`,
      "g",
    ),
  },
  {
    name: "arbitrary colour",
    // bg-[#0f766e], text-[rgb(1,2,3)]
    re: new RegExp(
      `(?<![\\w-])!?${VARIANT}(?:${PREFIX})-\\[(?:#|rgba?\\(|hsla?\\(|oklch\\()[^\\]]*\\]`,
      "g",
    ),
  },
];

// index.css is where the palette values legitimately live — it is the one
// file allowed to name a colour, because it is the file that maps colours
// onto roles.
const ALLOWED = new Set(["index.css"]);

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...walk(full));
    } else if (EXTENSIONS.some((ext) => entry.endsWith(ext))) {
      out.push(full);
    }
  }
  return out;
}

const findings = [];

for (const file of walk(ROOT)) {
  const rel = relative(ROOT, file).replace(/\\/g, "/");
  if (ALLOWED.has(rel)) continue;

  const lines = readFileSync(file, "utf8").split(/\r?\n/);

  lines.forEach((line, index) => {
    for (const rule of RULES) {
      rule.re.lastIndex = 0;
      let match;
      while ((match = rule.re.exec(line)) !== null) {
        findings.push({
          file: `src/${rel}`,
          line: index + 1,
          utility: match[0],
          rule: rule.name,
        });
      }
    }
  });
}

if (findings.length === 0) {
  console.log("Design tokens: no raw colour utilities in frontend/src.");
  process.exit(0);
}

console.error(
  `Design tokens: ${findings.length} raw colour ` +
    `${findings.length === 1 ? "utility" : "utilities"} found.\n`,
);

for (const f of findings) {
  console.error(`  ${f.file}:${f.line}  ${f.utility}  (${f.rule})`);
}

console.error(
  "\nColour belongs to a role, not to a call site. Use a token from " +
    "src/index.css\n(bg-surface, text-text-muted, border-border-strong, " +
    "text-brand, bg-danger-subtle, ...).\nIf no role fits, add one to " +
    "@theme and record why in docs/decisions/0028-design-tokens.md —\n" +
    "do not widen this check.",
);

process.exit(1);

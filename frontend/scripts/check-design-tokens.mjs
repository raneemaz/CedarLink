#!/usr/bin/env node
/**
 * Fail if colour is expressed anywhere in the frontend except as a role
 * token from src/index.css.
 *
 * The token layer is only worth having if it stays the only way colour is
 * written down. One `bg-white` merged on a Friday is not a problem; twenty
 * of them over a quarter are a second, undocumented palette, and by then
 * nobody can tell which of the two is correct. So the rule is enforced
 * rather than agreed.
 *
 * Three shapes are caught:
 *
 *   1. Tailwind palette utilities  — bg-white, hover:text-gray-500
 *   2. Arbitrary Tailwind values   — bg-[#0f766e]
 *   3. Inline styles               — style="color:#333"  /  style={{ ... }}
 *
 * (3) exists ahead of need. A mockup transcribed from a design tool
 * arrives as inline styles, and a colour hidden in `style={{ color:
 * "#1f2937" }}` is exactly as invisible to a theme switch as `bg-white`
 * is — more so, because no linter reads it. Adding the rule after the
 * transcription would mean auditing it; adding it before means the
 * transcription cannot introduce the problem.
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

const HERE = new URL(".", import.meta.url).pathname.replace(/^\/(\w:)/, "$1");
const SRC = join(HERE, "..", "src");
const FRONTEND = join(HERE, "..");

const EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".css", ".html"];

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

// A colour literal in any notation a designer's export might use.
const COLOUR_LITERAL =
  "#[0-9a-fA-F]{3,8}\\b|\\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color)\\s*\\(";

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
    name: "arbitrary utility value",
    // bg-[#0f766e], text-[rgb(1,2,3)]
    re: new RegExp(
      `(?<![\\w-])!?${VARIANT}(?:${PREFIX})-\\[(?:#|rgba?\\(|hsla?\\(|oklch\\()[^\\]]*\\]`,
      "g",
    ),
  },
  {
    name: "inline style attribute",
    // style="color: #333"  — HTML, and JSX string-valued style
    re: new RegExp(`style\\s*=\\s*"[^"]*(?:${COLOUR_LITERAL})[^"]*"`, "g"),
  },
  {
    name: "inline style object",
    // style={{ background: "#fff" }} — the shape a transcribed mockup
    // arrives in. Matched non-greedily to the first closing brace pair so
    // one offending object does not swallow the rest of the line.
    re: new RegExp(`style\\s*=\\s*\\{\\{[^}]*(?:${COLOUR_LITERAL})[^}]*\\}\\}`, "g"),
  },
  {
    name: "css colour literal",
    // A raw colour in a stylesheet other than index.css.
    re: new RegExp(`(?:${COLOUR_LITERAL})`, "g"),
    onlyIn: (rel) => rel.endsWith(".css"),
  },
];

// index.css is where the palette values legitimately live — it is the one
// file allowed to name a colour, because it is the file that maps colours
// onto roles.
const ALLOWED = new Set(["src/index.css"]);

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === "dist") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...walk(full));
    } else if (EXTENSIONS.some((ext) => entry.endsWith(ext))) {
      out.push(full);
    }
  }
  return out;
}

// src/, plus index.html — the entry document is markup like any other and
// is exactly where a hand-written `style="background:#fff"` would land.
const TARGETS = [
  ...walk(SRC).map((f) => ["src/" + relative(SRC, f).replace(/\\/g, "/"), f]),
  ["index.html", join(FRONTEND, "index.html")],
];

const findings = [];

for (const [rel, file] of TARGETS) {
  if (ALLOWED.has(rel)) continue;

  let contents;
  try {
    contents = readFileSync(file, "utf8");
  } catch {
    continue; // index.html is the only optional target.
  }

  contents.split(/\r?\n/).forEach((line, index) => {
    for (const rule of RULES) {
      if (rule.onlyIn && !rule.onlyIn(rel)) continue;
      rule.re.lastIndex = 0;
      let match;
      while ((match = rule.re.exec(line)) !== null) {
        findings.push({
          file: rel,
          line: index + 1,
          snippet: match[0].length > 60
            ? `${match[0].slice(0, 57)}...`
            : match[0],
          rule: rule.name,
        });
      }
    }
  });
}

if (findings.length === 0) {
  console.log(
    "Design tokens: no raw colour in frontend/src or index.html.",
  );
  process.exit(0);
}

console.error(
  `Design tokens: ${findings.length} raw ` +
    `${findings.length === 1 ? "colour" : "colours"} found.\n`,
);

for (const f of findings) {
  console.error(`  ${f.file}:${f.line}  ${f.snippet}  (${f.rule})`);
}

console.error(
  "\nColour belongs to a role, not to a call site. Use a token from " +
    "src/index.css\n(bg-paper, text-ink-muted, border-line-strong, " +
    "text-cedar, bg-danger-subtle, fill-rating, ...).\nAn inline style " +
    "cannot be themed at all — move it to a class.\nIf no role fits, add " +
    "one to @theme and record why in docs/decisions/0028-design-tokens.md" +
    " —\ndo not widen this check.",
);

process.exit(1);

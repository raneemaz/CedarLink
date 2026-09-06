"""WCAG contrast ratios for the CedarLink token sets.

Kept in the repository rather than run once and pasted into a document,
so the figures in ADR 0029 can be reproduced after any change to the
palette. Reads the real values out of index.css, so it cannot report a
set that is not the one shipping.

Reads the real values out of frontend/src/index.css so the report can
never drift from what ships, converts oklch -> sRGB, and computes the
WCAG 2.1 relative-luminance ratio for every text-on-surface pair.
"""
import io
import math
import re
import sys

# Run from the repository root: python frontend/scripts/check-contrast.py
CSS = "frontend/src/index.css"


# ---- colour conversion ------------------------------------------------- #

def _oklab_to_linear_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (
        +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )


def oklch_to_linear(L, C, H):
    h = math.radians(H)
    return _oklab_to_linear_srgb(L, C * math.cos(h), C * math.sin(h))


def parse(value):
    """A CSS colour literal -> linear-light sRGB triple."""
    value = value.strip().rstrip(";").strip()

    m = re.match(
        r"oklch\(\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)\s*\)", value
    )
    if m:
        L, C, H = float(m.group(1)) / 100, float(m.group(2)), float(m.group(3))
        return oklch_to_linear(L, C, H)

    m = re.match(r"#([0-9a-fA-F]{6})$", value) or re.match(
        r"#([0-9a-fA-F]{3})$", value
    )
    if m:
        hexd = m.group(1)
        if len(hexd) == 3:
            hexd = "".join(c * 2 for c in hexd)
        srgb = [int(hexd[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        return tuple(
            c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
            for c in srgb
        )

    raise ValueError(f"cannot parse {value!r}")


def luminance(linear):
    r, g, b = (max(0.0, min(1.0, c)) for c in linear)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


# ---- read the token sets out of index.css ------------------------------ #

def read_sets():
    text = io.open(CSS, encoding="utf-8").read()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)

    sets = {}

    theme = re.search(r"@theme\s*\{(.*?)\n\}", text, re.S)
    sets["light"] = dict(
        re.findall(r"--color-([\w-]+):\s*([^;]+);", theme.group(1))
    )

    dark = re.search(
        r'\[data-theme="dark"\]\s*\{(.*?)\n\s*\}', text, re.S
    )
    if dark:
        overrides = dict(
            re.findall(r"--color-([\w-]+):\s*([^;]+);", dark.group(1))
        )
        sets["dark"] = {**sets["light"], **overrides}

    return sets


# ---- what must pass, and what is exempt -------------------------------- #

# Body text. Every one of these must clear 4.5:1 on every surface below.
BODY_ROLES = [
    "ink", "ink-emphasis", "ink-body", "ink-secondary", "ink-muted",
    "cedar", "danger", "warning", "info", "success",
    "warning-muted", "danger-strong", "cedar-strong",
]

# Not body text: icons and secondary metadata. Large-text bar, 3:1.
LARGE_ROLES = ["ink-faint"]

# Exempt, and the exemption is narrower than it looks — see
# docs/decisions/0029-theme-setting.md. WCAG 2.1 SC 1.4.3 excludes text in
# *inactive* user-interface components, which covers five of the nine
# `ink-disabled` call sites (all `disabled:` variants). The other four are
# decorative icons and one star-rating track; none is body text, and none
# is measured here. Listed rather than silently skipped.
EXEMPT_ROLES = ["ink-disabled"]

SURFACES = ["paper", "paper-raised", "paper-sunken"]

# Foreground-on-fill pairs, where the fill is the background. All body.
ON_FILL = [
    ("on-cedar", "cedar"),
    ("on-danger", "danger"),
    ("on-danger", "danger-accent"),
    ("on-danger", "danger-strong"),
    ("on-warning", "warning-muted"),
    ("ink", "control"),
    ("ink-body", "control"),
    ("cedar", "cedar-tint"),
    ("cedar-strong", "cedar-tint"),
    ("success", "success-subtle"),
    ("success-strong", "success-subtle"),
    ("danger", "danger-subtle"),
    ("danger-strong", "danger-subtle"),
    ("warning", "warning-subtle"),
    ("warning", "warning-tint"),
    ("info", "info-subtle"),
]

AA_BODY = 4.5
AA_LARGE = 3.0

# Pairs that fail today, in the light theme only, recorded so the gate can
# fail on anything NEW without pretending these are fine.
#
# Every one of them predates the theme work: they are the original R1
# palette, which was lifted from the pre-existing hard-coded colours and
# never measured. The dark set introduced in R2 passes clean, which is why
# this list has no dark entries.
#
# R3 replaces all 42 values against the redesign palette and is required
# to clear this list. An entry that starts passing is reported as stale, so
# the list cannot quietly outlive the problem.
KNOWN_FAILURES = {
    ("light", "ink-faint", "paper"),
    ("light", "ink-faint", "paper-raised"),
    ("light", "ink-faint", "paper-sunken"),
    ("light", "ink-muted", "paper-sunken"),
    ("light", "danger", "paper-sunken"),
    ("light", "danger", "danger-subtle"),
    ("light", "on-danger", "danger-accent"),
}


def check(name, tokens, verbose):
    """Every required pair for one theme. Returns the list of failures."""
    failures = []
    rows = []

    def measure(fg, bg, floor, kind):
        if fg not in tokens or bg not in tokens:
            return
        r = ratio(parse(tokens[fg]), parse(tokens[bg]))
        ok = r >= floor
        rows.append((fg, bg, r, floor, kind, ok))
        if not ok:
            failures.append((fg, bg, r, floor))

    for surface in SURFACES:
        for role in BODY_ROLES:
            measure(role, surface, AA_BODY, "body")
        for role in LARGE_ROLES:
            measure(role, surface, AA_LARGE, "large")

    for fg, bg in ON_FILL:
        measure(fg, bg, AA_BODY, "body")

    if verbose:
        print()
        print(f"=== {name.upper()} ===")
        print(f"{'foreground':<16}{'background':<16}{'ratio':>7} {'floor':>6}  ")
        for fg, bg, r, floor, kind, ok in rows:
            print(f"{fg:<16}{bg:<16}{r:>6.2f} {floor:>6.1f}  "
                  f"{'pass' if ok else 'FAIL'} ({kind})")
        for role in EXEMPT_ROLES:
            for surface in SURFACES:
                if role in tokens and surface in tokens:
                    r = ratio(parse(tokens[role]), parse(tokens[surface]))
                    print(f"{role:<16}{surface:<16}{r:>6.2f} {'--':>6}  "
                          f"exempt (SC 1.4.3, inactive control)")

    return failures


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    quiet = "--quiet" in sys.argv
    only = args[0] if args else None

    sets = read_sets()
    new_failures = []
    still_failing = []
    seen = set()

    for name, tokens in sets.items():
        if only and name != only:
            continue
        for fg, bg, r, floor in check(name, tokens, verbose=not quiet):
            key = (name, fg, bg)
            seen.add(key)
            (still_failing if key in KNOWN_FAILURES else new_failures).append(
                (name, fg, bg, r, floor)
            )

    stale = sorted(KNOWN_FAILURES - seen) if not only else []

    print()
    for name, fg, bg, r, floor in still_failing:
        print(f"  known   {name:<6} {fg} on {bg}: {r:.2f}:1 "
              f"(needs {floor}:1) — pre-existing, R3 must clear it")
    for name, fg, bg in stale:
        print(f"  stale   {name:<6} {fg} on {bg} now passes — "
              f"remove it from KNOWN_FAILURES")

    if stale:
        print()
        print("Contrast: the known-failure list is out of date.")
        return 1

    if not new_failures:
        themes = ", ".join(n for n in sets if not only or n == only)
        print(f"Contrast: no new AA failures ({themes}; "
              f"{len(still_failing)} known).")
        return 0

    all_failures = {}
    for name, fg, bg, r, floor in new_failures:
        all_failures.setdefault(name, []).append((fg, bg, r, floor))

    total = sum(len(v) for v in all_failures.values())
    print(f"Contrast: {total} NEW pair(s) below the WCAG AA floor.")
    print()
    for name, failures in all_failures.items():
        for fg, bg, r, floor in failures:
            print(f"  {name:<6} {fg} on {bg}: {r:.2f}:1, needs {floor}:1")
    print()
    print(
        "A theme that fails contrast is a worse accessibility outcome "
        "than no theme."
    )
    print("Adjust the value in src/index.css — do not lower the floor.")
    return 1


sys.exit(main())

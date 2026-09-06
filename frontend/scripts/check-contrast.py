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


# Body text roles, and the surfaces they are allowed to sit on.
TEXT_ROLES = [
    "ink", "ink-emphasis", "ink-body", "ink-secondary", "ink-muted",
    "ink-faint", "ink-disabled", "cedar", "danger", "warning", "info",
    "success", "warning-muted", "danger-strong", "cedar-strong",
]
SURFACES = ["paper", "paper-raised", "paper-sunken"]

# Foreground-on-fill pairs, where the fill is the background.
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

sets = read_sets()
failures = 0
which = sys.argv[1] if len(sys.argv) > 1 else None

for name, tokens in sets.items():
    if which and name != which:
        continue
    print(f"\n=== {name.upper()} ===")
    print(f"{'foreground':<16}{'background':<16}{'ratio':>7}  AA")

    for surface in SURFACES:
        for role in TEXT_ROLES:
            if role not in tokens or surface not in tokens:
                continue
            r = ratio(parse(tokens[role]), parse(tokens[surface]))
            ok = "pass" if r >= AA_BODY else (
                "LARGE-ONLY" if r >= AA_LARGE else "FAIL"
            )
            if r < AA_LARGE:
                failures += 1
            if which or r < AA_BODY or surface == "paper-raised":
                print(f"{role:<16}{surface:<16}{r:>6.2f}  {ok}")

    print(f"{'--- fills ---':<32}")
    for fg, bg in ON_FILL:
        if fg not in tokens or bg not in tokens:
            continue
        r = ratio(parse(tokens[fg]), parse(tokens[bg]))
        ok = "pass" if r >= AA_BODY else (
            "LARGE-ONLY" if r >= AA_LARGE else "FAIL"
        )
        if r < AA_LARGE:
            failures += 1
        print(f"{fg:<16}{bg:<16}{r:>6.2f}  {ok}")

print(f"\nbelow 3:1 (fails even for large text): {failures}")

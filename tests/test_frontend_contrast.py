"""The contrast of the design system's own colours.

The accessibility gate opens the pages and asks axe; this test asks the
tokens. It is the earlier of the two, and the cheaper: a pair of colours that
does not reach the ratio here would fail there too, on every page, in every
run — and here it says which pair, and in which skin.

Every pair the system puts on screen is declared below, in one of three
classes, because the three answer to three different questions.

**Text** (4.5:1). Words on a ground. The reader has to be able to read them.
WCAG 2.2 SC 1.4.3, and no exception is claimed.

**Non-text** (3:1). A line, a border, a mark that identifies a control or a
state. WCAG 2.2 SC 1.4.11. This is why the system has two border registers:
`--border-control` is the resting edge of a control and `--border-strong` is
its active edge, and both are gated here. `--border-default` is a separator
between things that are already told apart by something else, so it is
structure and not identity, and it is not gated.

**Graphics** (2:1). A data mark: a series, an axis. WCAG 2.2 exempts the
graphics that carry information, and the series register is one of them. The
floor here is not a compliance floor but a legibility floor: below 2:1 a mark
stops being visible at reading distance on a typical monitor. What the system
does instead of a contrast ratio is the redundant channel — every series
carries a symbol and a dash pattern, and the legend carries a mark — and,
above all, colour is never the only way a series is identified. The
separability of the register under colour-vision deficiency is gated
separately, in `test_frontend_series_palette.py`, where it is measured.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "frontend" / "src" / "styles" / "tokens.css"

TEXT_RATIO = 4.5
NON_TEXT_RATIO = 3.0
GRAPHICS_RATIO = 2.0

#: Text on a ground. Every ground a text can sit on.
TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("--content-primary", "--surface-canvas"),
    ("--content-primary", "--surface-raised"),
    ("--content-primary", "--surface-inset"),
    ("--content-primary", "--surface-overlay"),
    ("--content-primary", "--surface-sunken"),
    ("--content-secondary", "--surface-canvas"),
    ("--content-secondary", "--surface-raised"),
    ("--content-secondary", "--surface-inset"),
    ("--content-secondary", "--surface-overlay"),
    ("--content-tertiary", "--surface-canvas"),
    ("--content-tertiary", "--surface-raised"),
    ("--content-tertiary", "--surface-inset"),
    ("--content-tertiary", "--surface-overlay"),
    ("--content-tertiary", "--surface-sunken"),
    ("--accent", "--surface-canvas"),
    ("--accent", "--surface-raised"),
    ("--accent", "--surface-inset"),
    ("--accent-ink", "--accent"),
    ("--content-inverse", "--surface-inverse"),
    ("--semantic-info-ink", "--semantic-info-subtle"),
    ("--semantic-success-ink", "--semantic-success-subtle"),
    ("--semantic-warning-ink", "--semantic-warning-subtle"),
    ("--semantic-danger-ink", "--semantic-danger-subtle"),
    ("--semantic-neutral-ink", "--semantic-neutral-subtle"),
    ("--science-status-0-ink", "--science-status-0"),
    ("--science-status-1-ink", "--science-status-1"),
    ("--science-status-2-ink", "--science-status-2"),
    ("--science-status-3-ink", "--science-status-3"),
    ("--science-status-4-ink", "--science-status-4"),
    ("--chart-label", "--chart-well"),
    ("--chart-label", "--surface-raised"),
    ("--chart-reference", "--chart-well"),
)

#: A line, a border, a mark: something a reader must be able to see.
NON_TEXT_PAIRS: tuple[tuple[str, str], ...] = (
    ("--border-control", "--surface-canvas"),
    ("--border-control", "--surface-raised"),
    ("--border-control", "--surface-inset"),
    ("--border-strong", "--surface-canvas"),
    ("--border-strong", "--surface-raised"),
    ("--map-boundary", "--map-land"),
    ("--map-marker", "--map-land"),
    ("--map-marker-selected", "--map-land"),
)

#: A data mark. Exempt from SC 1.4.11, but it still has to be visible.
GRAPHICS_PAIRS: tuple[tuple[str, str], ...] = (
    ("--chart-axis", "--chart-well"),
    ("--series-1", "--chart-well"),
    ("--series-2", "--chart-well"),
    ("--series-3", "--chart-well"),
    ("--series-4", "--chart-well"),
    ("--series-5", "--chart-well"),
    ("--series-6", "--chart-well"),
    ("--series-7", "--chart-well"),
    ("--series-8", "--chart-well"),
)


def read_tokens() -> dict[str, tuple[str, str]]:
    """Every colour token, with its light and its dark value."""
    text = TOKENS.read_text(encoding="utf-8")
    found: dict[str, tuple[str, str]] = {}
    for name, light, dark in re.findall(
        r"(--[a-z0-9-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})\s*\)",
        text,
    ):
        found[name] = (light, dark)
    for name, value in re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6});", text):
        found.setdefault(name, (value, value))
    return found


def read_declared_names() -> set[str]:
    """Every token the file declares, whatever its value.

    The colours that carry an alpha are written in `rgb()` and never take
    part in a ratio; they are still declared, and the inventory has to see
    them.
    """
    text = TOKENS.read_text(encoding="utf-8")
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", text))


def luminance(colour: str) -> float:
    value = colour.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def linear(channel: float) -> float:
        return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linear(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(foreground: str, background: str) -> float:
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _failures(tokens: dict[str, tuple[str, str]]) -> list[str]:
    failures: list[str] = []
    for pairs, needed, kind in (
        (TEXT_PAIRS, TEXT_RATIO, "text"),
        (NON_TEXT_PAIRS, NON_TEXT_RATIO, "non-text"),
        (GRAPHICS_PAIRS, GRAPHICS_RATIO, "graphics"),
    ):
        for foreground, background in pairs:
            if foreground not in tokens or background not in tokens:
                failures.append(f"{foreground} on {background}: the token is not declared")
                break
            for skin, index in (("light", 0), ("dark", 1)):
                value = ratio(tokens[foreground][index], tokens[background][index])
                if value < needed:
                    failures.append(
                        f"{kind} {foreground} {tokens[foreground][index]} on "
                        f"{background} {tokens[background][index]} in the {skin} skin: "
                        f"{value:.2f}, under {needed}"
                    )
    return failures


def test_every_declared_pair_reaches_its_ratio() -> None:
    failures = _failures(read_tokens())
    assert not failures, (
        "the design system puts colours together that a reader cannot read:\n" + "\n".join(failures)
    )


def test_every_token_of_a_pair_is_declared() -> None:
    """A pair that names a token that does not exist checks nothing."""
    tokens = read_tokens()
    missing = sorted(
        {
            name
            for pair in TEXT_PAIRS + NON_TEXT_PAIRS + GRAPHICS_PAIRS
            for name in pair
            if name not in tokens
        }
    )
    assert not missing, f"these tokens are named by a pair but are not declared: {missing}"


def test_the_registers_do_not_cross() -> None:
    """Three registers, three meanings. A token used in one must not leak.

    The system separates the ordinal status ramp, the categorical series and
    the interactive accent. This test cannot prove they are never crossed in
    the components — that is a review, not a test — but it holds the tokens
    apart, which is where a crossing starts.
    """
    tokens = read_declared_names()
    registers = {
        "status": {f"--science-status-{index}" for index in range(5)},
        "series": {f"--series-{index}" for index in range(1, 9)},
        "accent": {
            "--accent",
            "--accent-hover",
            "--accent-active",
            "--accent-subtle",
            "--accent-ink",
            "--accent-ring",
        },
    }
    for name, register in registers.items():
        for token in register:
            assert token in tokens, f"the {name} register declares {token}, which does not exist"
    assert not registers["status"] & registers["series"]
    assert not registers["status"] & registers["accent"]
    assert not registers["series"] & registers["accent"]

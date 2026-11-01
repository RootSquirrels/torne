"""The colour-vision separability of the series register.

The categorical register is the one place in the system where colour carries
meaning, so it is the one place where colour has to be checked against the
reader's eye rather than against a surface.

Okabe-Ito is the base: eight hues that stay apart for a reader with normal
colour vision. It does not promise they stay apart for a reader with a
dichromacy, and measurement says they do not. In the register as it was, the
ochre `#A6761D` and the vermillion `#D55E00` converged under protanopia: a
CIE dE of 2.8, which is the same colour twice for that reader.

This test measures the register as it stands and holds it to a floor, in both
skins, under the three dichromacies. It also measures the order in which the
register is handed out, and holds *every prefix* of that order to the same
floor — which is the property that matters, because a chart never shows all
eight series at once, and a reader meets a prefix.

The simulation is Machado et al. 2009 at full severity, applied in linear
RGB, which is the model the palette literature uses.
"""

from __future__ import annotations

import itertools
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "frontend" / "src" / "styles" / "tokens.css"
CHART_THEME = ROOT / "frontend" / "src" / "components" / "visualization" / "chartTheme.ts"

#: The floor. A CIE76 dE below 2 is imperceptible, above 10 the two colours
#: are clearly different to a reader with normal vision; a dichromatic reader
#: needs the margin, because the separation they have is the one that was
#: taken away from them.
MINIMUM_SEPARABILITY = 10.0

SERIES = tuple(f"--series-{index}" for index in range(1, 9))

#: Machado, Oliveira and Fernandes (2009), severity 1.0, linear RGB.
MACHADO: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def read_tokens() -> dict[str, tuple[str, str]]:
    text = TOKENS.read_text(encoding="utf-8")
    found: dict[str, tuple[str, str]] = {}
    for name, light, dark in re.findall(
        r"(--[a-z0-9-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})\s*\)",
        text,
    ):
        found[name] = (light, dark)
    return found


def read_order() -> tuple[str, ...]:
    """The order in which the register is handed out, as the code declares it."""
    text = CHART_THEME.read_text(encoding="utf-8")
    block = re.search(r"const SERIES_VARS\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert block is not None, "chartTheme.ts does not declare SERIES_VARS"
    return tuple(re.findall(r"'(--series-\d+)'", block.group(1)))


def to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def to_srgb(channel: float) -> float:
    if channel <= 0.0031308:
        return channel * 12.92
    return 1.055 * (channel ** (1 / 2.4)) - 0.055


def hex_to_rgb(colour: str) -> tuple[float, float, float]:
    value = colour.lstrip("#")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def simulate(colour: str, kind: str) -> tuple[float, float, float]:
    """What the colour looks like to a reader with that dichromacy."""
    linear = [to_linear(channel) for channel in hex_to_rgb(colour)]
    matrix = MACHADO[kind]
    out = [sum(row[index] * linear[index] for index in range(3)) for row in matrix]
    return tuple(to_srgb(min(max(channel, 0.0), 1.0)) for channel in out)


def to_lab(colour: tuple[float, float, float]) -> tuple[float, float, float]:
    red, green, blue = (to_linear(channel) for channel in colour)
    x = 0.4124564 * red + 0.3575761 * green + 0.1804375 * blue
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = 0.0193339 * red + 0.1191920 * green + 0.9503041 * blue
    white = (0.95047, 1.00000, 1.08883)

    def pivot(value: float) -> float:
        if value > 216 / 24389:
            return value ** (1 / 3)
        return (841 / 108) * value + 4 / 29

    fx, fy, fz = pivot(x / white[0]), pivot(y / white[1]), pivot(z / white[2])
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(first, second, strict=True)))


def separation(first: str, second: str, tokens: dict[str, tuple[str, str]]) -> tuple[float, str]:
    """The worst distance between two slots, over both skins and the three
    dichromacies, with the case that produced it."""
    worst = (math.inf, "")
    for index, skin in enumerate(("light", "dark")):
        for kind in MACHADO:
            left = simulate(tokens[first][index], kind)
            right = simulate(tokens[second][index], kind)
            value = delta_e(to_lab(left), to_lab(right))
            if value < worst[0]:
                worst = (value, f"{skin} skin, {kind}")
    return worst


def test_every_pair_of_the_register_stays_apart() -> None:
    tokens = read_tokens()
    failures: list[str] = []
    for first, second in itertools.combinations(SERIES, 2):
        value, where = separation(first, second, tokens)
        if value < MINIMUM_SEPARABILITY:
            failures.append(
                f"{first} {tokens[first][0]}/{tokens[first][1]} and "
                f"{second} {tokens[second][0]}/{tokens[second][1]} "
                f"are {value:.2f} apart in the {where}, under {MINIMUM_SEPARABILITY}"
            )
    assert not failures, (
        "two series cannot be told apart by a reader with a dichromacy:\n" + "\n".join(failures)
    )


def test_every_prefix_of_the_order_stays_apart() -> None:
    """A chart shows a prefix of the register, never the whole of it.

    This is the property that matters in practice: whatever the reader is
    looking at — two series, four series, eight — every pair on screen has to
    stay apart.
    """
    tokens = read_tokens()
    order = read_order()
    failures: list[str] = []
    for length in range(2, len(order) + 1):
        prefix = order[:length]
        for first, second in itertools.combinations(prefix, 2):
            value, where = separation(first, second, tokens)
            if value < MINIMUM_SEPARABILITY:
                failures.append(
                    f"in a chart of {length} series, {first} and {second} "
                    f"are {value:.2f} apart in the {where}, under {MINIMUM_SEPARABILITY}"
                )
    assert not failures, "the order in which the register is handed out is not safe:\n" + "\n".join(
        failures
    )


def test_the_order_deals_every_slot_out_exactly_once() -> None:
    order = read_order()
    assert sorted(order) == sorted(SERIES), (
        f"the order deals out {order}, which is not the eight slots of the register"
    )


def test_the_order_is_the_measured_one() -> None:
    """The order is not free: it was measured, and it is recorded here.

    Changing it is allowed — but then it has to be measured again, and this
    test is where that is written down.
    """
    assert read_order() == (
        "--series-1",
        "--series-2",
        "--series-8",
        "--series-6",
        "--series-3",
        "--series-4",
        "--series-7",
        "--series-5",
    ), "the order of the register changed without being measured again"

"""Hand-rolled SVG sparkline rendering.

No charting library, no CDN dependency -- consistent with the rest of this
portfolio's self-contained discipline. Pure function: a list of numbers in,
an inline <svg> string out.
"""

from __future__ import annotations


def sparkline_svg(
    values: list[float | None], width: int = 200, height: int = 40, color: str = "#059669"
) -> str:
    """Renders a simple line sparkline from a list of numeric values, oldest
    first. Returns an empty string if fewer than two usable points exist."""
    points = [v for v in values if v is not None]
    if len(points) < 2:
        return ""

    min_v, max_v = min(points), max(points)
    span = max_v - min_v or 1.0
    step = width / (len(points) - 1)

    coords = []
    for i, v in enumerate(points):
        x = round(i * step, 1)
        y = round(height - ((v - min_v) / span) * height, 1)
        coords.append(f"{x},{y}")

    polyline = " ".join(coords)
    last_x, last_y = coords[-1].split(",")

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'class="sparkline" preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{last_x}" cy="{last_y}" r="2.5" fill="{color}"/>'
        f"</svg>"
    )

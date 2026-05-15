from __future__ import annotations

from html import escape
from pathlib import Path

from .analysis import sweep_frequency_offsets
from .loop import LoopTrace


def _text(
    x: float,
    y: float,
    text: str,
    *,
    size: int = 16,
    anchor: str = "start",
    fill: str = "#111827",
    weight: str = "normal",
    transform: str | None = None,
) -> str:
    transform_attr = f' transform="{transform}"' if transform else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}"{transform_attr}>{escape(text)}</text>'


def _paragraph(
    x: float,
    y: float,
    lines: list[str],
    *,
    size: int = 16,
    anchor: str = "start",
    fill: str = "#111827",
    weight: str = "normal",
    line_height: int = 18,
) -> str:
    tspans = [f'<tspan x="{x:.1f}" dy="0">{escape(lines[0])}</tspan>']
    tspans.extend(f'<tspan x="{x:.1f}" dy="{line_height}">{escape(line)}</tspan>' for line in lines[1:])
    return f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-family="Inter, Arial, sans-serif" text-anchor="{anchor}" font-weight="{weight}">{"".join(tspans)}</text>'


def _line(x1: float, y1: float, x2: float, y2: float, *, stroke: str = "#374151", width: float = 1.0, dash: str | None = None) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{width:.1f}"{dash_attr}/>'


def _circle(x: float, y: float, r: float, *, fill: str, opacity: float = 1.0) -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" fill-opacity="{opacity:.3f}"/>'


def render_costas_demo_svg(trace: LoopTrace, *, output: str | Path, title: str = "QPSK carrier recovery: coarse estimate, then Costas tracking") -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    width = 1200
    height = 900
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _text(width / 2, 70, "Timing is assumed solved here. The job is to stop the constellation from spinning and keep it settled.", size=16, anchor="middle", fill="#475569"),
    ]

    scatters = [
        ("received", trace.received[:240], 60.0, 110.0, 320.0, 250.0, "#ef4444", ["raw symbols still spin"]),
        ("coarse", trace.coarse_corrected[:240], 440.0, 110.0, 320.0, 250.0, "#f59e0b", ["4th-power phase estimate", "gets close"]),
        ("tracked", trace.tracked[-240:], 820.0, 110.0, 320.0, 250.0, "#2563eb", ["Costas loop keeps the cloud", "near the four corners"]),
    ]

    for _, points, left, top, panel_w, panel_h, color, subtitle_lines in scatters:
        cx = left + panel_w / 2
        cy = top + panel_h / 2
        scale = 88.0
        parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
        parts.append(_paragraph(cx, top + 24, subtitle_lines, size=15, anchor="middle", fill="#334155", weight="700", line_height=16))
        parts.append(_line(left + 26, cy, left + panel_w - 26, cy, stroke="#cbd5e1"))
        parts.append(_line(cx, top + 48, cx, top + panel_h - 22, stroke="#cbd5e1"))
        for point in points:
            x = cx + point.real * scale
            y = cy - point.imag * scale
            parts.append(_circle(x, y, 3.2, fill=color, opacity=0.45))

    series_panels = [
        (trace.phase_estimates, 90.0, 430.0, 1020.0, 150.0, "phase estimate (rad)", -3.2, 3.2, "#2563eb"),
        (trace.freq_estimates, 90.0, 610.0, 1020.0, 150.0, "frequency estimate (rad/sample)", min(trace.freq_estimates) * 1.2 - 1e-6, max(trace.freq_estimates) * 1.2 + 1e-6, "#059669"),
    ]

    for values, left, top, panel_w, panel_h, label, y_lo, y_hi, color in series_panels:
        parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
        parts.append(_text(left + 18, top + 26, label, size=15, weight="700", fill="#334155"))
        if y_hi <= y_lo:
            y_hi = y_lo + 1.0
        pts = []
        for idx, value in enumerate(values):
            x = left + 30 + idx / max(len(values) - 1, 1) * (panel_w - 50)
            y = top + panel_h - 24 - (value - y_lo) / (y_hi - y_lo) * (panel_h - 48)
            pts.append((x, y))
        parts.append(_line(left + 30, top + panel_h - 24, left + panel_w - 20, top + panel_h - 24, stroke="#94a3b8"))
        parts.append(_line(left + 30, top + 36, left + 30, top + panel_h - 24, stroke="#94a3b8"))
        payload = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.5" points="{payload}"/>')

    parts.append(_text(90, 842, f"coarse phase estimate from first 64 symbols: {trace.coarse_phase:+.3f} rad", size=14, fill="#475569"))
    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n")


def render_offset_sweep_svg(rows: list[dict[str, float]], *, output: str | Path, title: str = "Costas loop offset sweep") -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    width = 1100
    height = 720
    left = 90
    right = width - 40
    top = 90
    bottom = height - 116
    x_lo = min(row["freq_offset"] for row in rows)
    x_hi = max(row["freq_offset"] for row in rows)
    y_lo = 0.0
    y_hi = max(row["raw_rms_error"] for row in rows) * 1.1

    def map_x(v: float) -> float:
        return left + (v - x_lo) / (x_hi - x_lo) * (right - left)

    def map_y(v: float) -> float:
        return bottom - (v - y_lo) / (y_hi - y_lo) * (bottom - top)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _text(width / 2, 70, "Same QPSK setup, same loop gains. Only the carrier offset changes.", size=16, anchor="middle", fill="#475569"),
        _line(left, top, left, bottom, stroke="#334155", width=2),
        _line(left, bottom, right, bottom, stroke="#334155", width=2),
    ]

    for step in range(6):
        frac = step / 5
        y = top + frac * (bottom - top)
        val = y_hi - frac * (y_hi - y_lo)
        parts.append(_line(left, y, right, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(left - 14, y + 5, f"{val:.2f}", anchor="end", size=13, fill="#64748b"))

    for step in range(9):
        frac = step / 8
        x = left + frac * (right - left)
        val = x_lo + frac * (x_hi - x_lo)
        parts.append(_line(x, top, x, bottom, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, bottom + 26, f"{val:+.03f}", anchor="middle", size=13, fill="#64748b"))

    def polyline(key: str, stroke: str) -> str:
        payload = " ".join(f"{map_x(row['freq_offset']):.1f},{map_y(row[key]):.1f}" for row in rows)
        return f'<polyline fill="none" stroke="{stroke}" stroke-width="3" points="{payload}"/>'

    parts.append(polyline("raw_rms_error", "#ef4444"))
    parts.append(polyline("coarse_rms_error", "#f59e0b"))
    parts.append(polyline("tracked_rms_error", "#2563eb"))
    legend_x = right - 208
    legend_y = top + 18
    parts.append(f'<rect x="{legend_x:.1f}" y="{legend_y:.1f}" width="190" height="76" rx="14" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(legend_x + 18, legend_y + 24, "raw", size=14, fill="#ef4444", weight="700"))
    parts.append(_text(legend_x + 18, legend_y + 46, "after coarse phase", size=14, fill="#f59e0b", weight="700"))
    parts.append(_text(legend_x + 18, legend_y + 68, "after Costas tracking", size=14, fill="#2563eb", weight="700"))
    parts.append(_text((left + right) / 2, height - 34, "carrier offset (rad/sample)", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(34, (top + bottom) / 2, "RMS distance to nearest QPSK corner", anchor="middle", size=16, fill="#374151", weight="500", transform=f'rotate(-90 34 {(top + bottom) / 2:.1f})'))
    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n")

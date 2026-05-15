from __future__ import annotations

from html import escape
from pathlib import Path
import shutil
import subprocess
import tempfile

from .analysis import AcquisitionSweepRow, quality_band, sweep_frequency_offsets
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


def export_png_from_svg(svg_path: str | Path, png_path: str | Path, *, size: int = 1800, dpi: int = 300) -> bool:
    svg_file = Path(svg_path).resolve()
    png_file = Path(png_path).resolve()
    qlmanage = shutil.which("qlmanage")
    if qlmanage is None:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(
            [qlmanage, "-t", "-s", str(size), "-o", tmpdir, str(svg_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        generated = Path(tmpdir) / f"{svg_file.name}.png"
        if not generated.exists():
            raise FileNotFoundError(f"Quick Look did not generate {generated}")
        png_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(generated, png_file)

    sips = shutil.which("sips")
    if sips is not None:
        subprocess.run(
            [sips, "--setProperty", "dpiWidth", str(dpi), "--setProperty", "dpiHeight", str(dpi), str(png_file)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return True


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


def render_acquisition_range_svg(
    rows: list[AcquisitionSweepRow],
    *,
    output: str | Path,
    title: str = "QPSK carrier acquisition: phase-only versus 4th-power frequency help",
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    width = 1280
    height = 980
    top_left, top_right = 90.0, 1230.0
    top_top, top_bottom = 120.0, 440.0
    lower_left, lower_right = 90.0, 640.0
    lower_top, lower_bottom = 560.0, 900.0
    band_left, band_right = 710.0, 1230.0
    band_top, band_bottom = 560.0, 900.0

    x_lo = min(row.freq_offset for row in rows)
    x_hi = max(row.freq_offset for row in rows)
    top_y_lo = 0.0
    top_y_hi = max(row.raw_rms_error for row in rows) * 1.08
    lower_y_lo = x_lo
    lower_y_hi = x_hi

    def map_x(value: float, left: float, right: float) -> float:
        return left + (value - x_lo) / (x_hi - x_lo) * (right - left)

    def map_top_y(value: float) -> float:
        return top_bottom - (value - top_y_lo) / (top_y_hi - top_y_lo) * (top_bottom - top_top)

    def map_lower_y(value: float) -> float:
        return lower_bottom - (value - lower_y_lo) / (lower_y_hi - lower_y_lo) * (lower_bottom - lower_top)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _paragraph(width / 2, 68, ["The Costas loop can only clean up what the front end hands it.", "A 4th-power frequency estimate widens that handoff range."], size=16, anchor="middle", fill="#475569", line_height=18),
    ]

    # Top panel: RMS curves.
    parts.append(f'<rect x="{top_left:.1f}" y="{top_top:.1f}" width="{top_right - top_left:.1f}" height="{top_bottom - top_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(top_left + 18, top_top + 28, "Tracked RMS error across carrier offset", size=16, weight="700", fill="#334155"))
    for step in range(7):
        frac = step / 6
        y = top_top + frac * (top_bottom - top_top)
        value = top_y_hi - frac * (top_y_hi - top_y_lo)
        parts.append(_line(top_left + 48, y, top_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(top_left + 40, y + 5, f"{value:.2f}", anchor="end", size=13, fill="#64748b"))
    for step in range(9):
        frac = step / 8
        x = top_left + 48 + frac * ((top_right - 24) - (top_left + 48))
        value = x_lo + frac * (x_hi - x_lo)
        parts.append(_line(x, top_top + 32, x, top_bottom, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, top_bottom + 24, f"{value:+.02f}", anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(top_left + 48, top_top + 32, top_left + 48, top_bottom, stroke="#334155", width=2))
    parts.append(_line(top_left + 48, top_bottom, top_right - 24, top_bottom, stroke="#334155", width=2))

    def top_polyline(key: str, stroke: str, width: float = 3.0) -> str:
        payload = " ".join(
            f"{map_x(row.freq_offset, top_left + 48, top_right - 24):.1f},{map_top_y(getattr(row, key)):.1f}" for row in rows
        )
        return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width:.1f}" points="{payload}"/>'

    parts.append(top_polyline("raw_rms_error", "#cbd5e1", 2.5))
    parts.append(top_polyline("phase_only_tracked_rms_error", "#ef4444", 3.2))
    parts.append(top_polyline("freq_acquired_tracked_rms_error", "#1d4ed8", 3.6))
    legend_x = 810
    legend_y = 468
    parts.append(f'<rect x="{legend_x:.1f}" y="{legend_y:.1f}" width="340" height="82" rx="14" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(legend_x + 16, legend_y + 24, "raw received cloud", size=14, fill="#94a3b8", weight="700"))
    parts.append(_text(legend_x + 16, legend_y + 46, "phase-only coarse + Costas", size=14, fill="#ef4444", weight="700"))
    parts.append(_text(legend_x + 16, legend_y + 68, "freq + phase coarse + Costas", size=14, fill="#1d4ed8", weight="700"))
    parts.append(_text((top_left + top_right) / 2, top_bottom + 54, "carrier offset (rad/sample)", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(30, (top_top + top_bottom) / 2, "RMS distance to nearest QPSK corner", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 30 {(top_top + top_bottom) / 2:.1f})'))

    # Lower-left panel: coarse frequency estimate.
    parts.append(f'<rect x="{lower_left:.1f}" y="{lower_top:.1f}" width="{lower_right - lower_left:.1f}" height="{lower_bottom - lower_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(lower_left + 18, lower_top + 28, "4th-power coarse frequency estimate", size=16, weight="700", fill="#334155"))
    for step in range(7):
        frac = step / 6
        y = lower_top + 32 + frac * ((lower_bottom - 24) - (lower_top + 32))
        value = lower_y_hi - frac * (lower_y_hi - lower_y_lo)
        parts.append(_line(lower_left + 48, y, lower_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(lower_left + 40, y + 5, f"{value:+.02f}", anchor="end", size=13, fill="#64748b"))
    for step in range(7):
        frac = step / 6
        x = lower_left + 48 + frac * ((lower_right - 24) - (lower_left + 48))
        value = x_lo + frac * (x_hi - x_lo)
        parts.append(_line(x, lower_top + 32, x, lower_bottom - 24, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, lower_bottom + 24, f"{value:+.02f}", anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(lower_left + 48, lower_top + 32, lower_left + 48, lower_bottom - 24, stroke="#334155", width=2))
    parts.append(_line(lower_left + 48, lower_bottom - 24, lower_right - 24, lower_bottom - 24, stroke="#334155", width=2))
    diag = " ".join(
        f"{map_x(v, lower_left + 48, lower_right - 24):.1f},{map_lower_y(v):.1f}" for v in [x_lo, x_hi]
    )
    parts.append(f'<polyline fill="none" stroke="#94a3b8" stroke-width="2.0" stroke-dasharray="8 8" points="{diag}"/>')
    for row in rows:
        x = map_x(row.freq_offset, lower_left + 48, lower_right - 24)
        y = map_lower_y(row.coarse_frequency_estimate)
        parts.append(_circle(x, y, 4.0, fill="#2563eb", opacity=0.70))
    parts.append(_text((lower_left + lower_right) / 2, lower_bottom + 54, "true carrier offset (rad/sample)", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(34, (lower_top + lower_bottom) / 2, "estimated offset", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 34 {(lower_top + lower_bottom) / 2:.1f})'))
    parts.append(_paragraph(lower_left + 70, lower_bottom - 4, ["dashed line = perfect estimate", "scatter = what the 4th-power front end hands the loop"], size=14, fill="#475569", line_height=17))

    # Lower-right panel: regime bars.
    parts.append(f'<rect x="{band_left:.1f}" y="{band_top:.1f}" width="{band_right - band_left:.1f}" height="{band_bottom - band_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(band_left + 18, band_top + 28, "Acquisition regime map", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(band_left + 18, band_top + 52, ["clean < 0.10 RMS", "marginal < 0.24 RMS", "failed otherwise"], size=13, fill="#64748b", line_height=16))
    band_rows = [
        ("phase-only + Costas", 0, "phase_only_tracked_rms_error"),
        ("freq + phase + Costas", 1, "freq_acquired_tracked_rms_error"),
    ]
    band_colors = {"clean": "#10b981", "marginal": "#f59e0b", "failed": "#ef4444"}
    bar_height = 74
    for label, row_idx, key in band_rows:
        y = band_top + 120 + row_idx * 122
        parts.append(_text(band_left + 18, y - 18, label, size=14, weight="700", fill="#334155"))
        for row in rows:
            x0 = map_x(row.freq_offset, band_left + 24, band_right - 24)
            next_offset = row.freq_offset + (rows[1].freq_offset - rows[0].freq_offset if len(rows) > 1 else 0.02)
            x1 = map_x(min(next_offset, x_hi), band_left + 24, band_right - 24)
            width_seg = max(4.0, x1 - x0)
            band = quality_band(getattr(row, key))
            parts.append(f'<rect x="{x0:.1f}" y="{y:.1f}" width="{width_seg:.1f}" height="{bar_height:.1f}" fill="{band_colors[band]}" fill-opacity="0.82"/>')
        parts.append(f'<rect x="{band_left + 24:.1f}" y="{y:.1f}" width="{(band_right - 24) - (band_left + 24):.1f}" height="{bar_height:.1f}" fill="none" stroke="#cbd5e1"/>')
    for step in range(7):
        frac = step / 6
        x = band_left + 24 + frac * ((band_right - 24) - (band_left + 24))
        value = x_lo + frac * (x_hi - x_lo)
        parts.append(_line(x, band_top + 108, x, band_bottom - 34, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, band_bottom - 8, f"{value:+.02f}", anchor="middle", size=13, fill="#64748b"))
    parts.append(_text((band_left + band_right) / 2, band_bottom + 10, "offset", anchor="middle", size=15, fill="#374151"))
    parts.append(_text(band_left + 24, band_bottom - 48, "green = clean", size=13, fill="#10b981", weight="700"))
    parts.append(_text(band_left + 146, band_bottom - 48, "amber = marginal", size=13, fill="#f59e0b", weight="700"))
    parts.append(_text(band_left + 304, band_bottom - 48, "red = failed", size=13, fill="#ef4444", weight="700"))

    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n")

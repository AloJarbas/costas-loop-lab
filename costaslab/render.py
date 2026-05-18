from __future__ import annotations

from html import escape
from pathlib import Path
import shutil
import subprocess
import tempfile

from .analysis import CoarsePrefixBudgetRow, AcquisitionSweepRow, LoopGainStudy, decision_error_series, moving_average, quality_band, sweep_frequency_offsets
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


def render_loop_gain_tradeoff_svg(
    studies: list[LoopGainStudy],
    *,
    output: str | Path,
    title: str = "Costas loop gain tradeoff: faster pull-in costs steady-state calm",
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    width = 1600
    height = 980
    top_left, top_right = 80.0, 1520.0
    top_top, top_bottom = 118.0, 470.0
    lower_left, lower_right = 80.0, 780.0
    lower_top, lower_bottom = 560.0, 900.0
    summary_left, summary_right = 860.0, 1520.0
    summary_top, summary_bottom = 560.0, 900.0
    top_plot_top = top_top + 86.0
    top_plot_bottom = top_bottom - 26.0
    lower_plot_top = lower_top + 86.0
    lower_plot_bottom = lower_bottom - 26.0

    fallback = ["#0f766e", "#2563eb", "#dc2626", "#a855f7"]
    colors: dict[str, str] = {}
    for idx, study in enumerate(studies):
        colors.setdefault(study.label, fallback[idx % len(fallback)])

    top_series = {
        study.label: moving_average(decision_error_series(study.acquisition_trace.tracked), 24)
        for study in studies
    }
    top_y_lo = 0.0
    top_y_hi = max(max(values) for values in top_series.values()) * 1.08
    tail_len = min(260, min(len(study.tracking_trace.freq_estimates) for study in studies))
    lower_series = {study.label: study.tracking_trace.freq_estimates[-tail_len:] for study in studies}
    lower_y_extent = max(abs(value) for values in lower_series.values() for value in values) * 1000.0
    lower_y_extent = max(lower_y_extent, 1.0)

    def map_top_x(idx: int, count: int) -> float:
        return top_left + 56 + idx / max(count - 1, 1) * ((top_right - 24) - (top_left + 56))

    def map_top_y(value: float) -> float:
        return top_bottom - 26 - (value - top_y_lo) / (top_y_hi - top_y_lo) * ((top_bottom - 26) - (top_top + 36))

    def map_lower_x(idx: int, count: int) -> float:
        return lower_left + 56 + idx / max(count - 1, 1) * ((lower_right - 24) - (lower_left + 56))

    def map_lower_y(value: float) -> float:
        milli = value * 1000.0
        return lower_bottom - 26 - ((milli + lower_y_extent) / (2.0 * lower_y_extent)) * ((lower_bottom - 26) - (lower_top + 36))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _paragraph(
            width / 2,
            68,
            [
                "A gentler loop is calmer after lock. A hotter loop gets there faster if the coarse handoff is rough.",
                "The front end stays fixed here. Only the loop gains change.",
            ],
            size=16,
            anchor="middle",
            fill="#475569",
            line_height=18,
        ),
    ]

    # Top panel: acquisition speed in a phase-only stress case.
    parts.append(f'<rect x="{top_left:.1f}" y="{top_top:.1f}" width="{top_right - top_left:.1f}" height="{top_bottom - top_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(top_left + 18, top_top + 28, "Phase-only coarse acquisition under a harder residual ramp", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(top_left + 18, top_top + 52, ["carrier offset = +0.35 rad/sample, noise std = 0.04", "24-symbol moving average of decision error after coarse phase only"], size=14, fill="#526274", line_height=17))
    for step in range(7):
        frac = step / 6
        y = top_top + 36 + frac * ((top_bottom - 26) - (top_top + 36))
        value = top_y_hi - frac * (top_y_hi - top_y_lo)
        parts.append(_line(top_left + 56, y, top_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(top_left + 48, y + 5, f"{value:.1f}", anchor="end", size=13, fill="#64748b"))
    count = len(next(iter(top_series.values())))
    for step in range(9):
        frac = step / 8
        x = top_left + 56 + frac * ((top_right - 24) - (top_left + 56))
        value = frac * (count - 1)
        parts.append(_line(x, top_top + 36, x, top_bottom - 26, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, top_bottom + 24, f"{int(round(value))}", anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(top_left + 56, top_top + 36, top_left + 56, top_bottom - 26, stroke="#334155", width=2))
    parts.append(_line(top_left + 56, top_bottom - 26, top_right - 24, top_bottom - 26, stroke="#334155", width=2))
    for study in studies:
        series = top_series[study.label]
        payload = " ".join(f"{map_top_x(idx, len(series)):.1f},{map_top_y(value):.1f}" for idx, value in enumerate(series))
        parts.append(f'<polyline fill="none" stroke="{colors[study.label]}" stroke-width="3.0" points="{payload}"/>')
        if study.acquisition_settle_index is not None:
            settle_x = map_top_x(study.acquisition_settle_index, len(series))
            parts.append(_line(settle_x, top_top + 36, settle_x, top_bottom - 26, stroke=colors[study.label], width=2.0, dash="8 6"))
            parts.append(_text(settle_x + 6, top_top + 100 + 22 * list(top_series).index(study.label), f"{study.label}: settles ~{study.acquisition_settle_index}", size=13, fill=colors[study.label], weight="700"))
        else:
            parts.append(_text(top_right - 300, top_top + 126 + 22 * list(top_series).index(study.label), f"{study.label}: no clean settle in window", size=13, fill=colors[study.label], weight="700"))
    parts.append(_text((top_left + top_right) / 2, top_bottom + 54, "symbol index", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(28, (top_top + top_bottom) / 2, "decision error", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 28 {(top_top + top_bottom) / 2:.1f})'))

    legend_x = top_right - 282
    legend_y = top_top + 28
    parts.append(f'<rect x="{legend_x:.1f}" y="{legend_y:.1f}" width="250" height="92" rx="14" fill="#ffffff" stroke="#e2e8f0"/>')
    for idx, study in enumerate(studies):
        y = legend_y + 24 + idx * 22
        parts.append(_line(legend_x + 16, y - 5, legend_x + 44, y - 5, stroke=colors[study.label], width=4))
        parts.append(_text(legend_x + 56, y, f"{study.label}  α={study.alpha:.2f} β={study.beta:.4f}", size=13, fill="#334155", weight="700"))

    # Lower-left panel: tracking jitter after freq+phase acquisition.
    parts.append(f'<rect x="{lower_left:.1f}" y="{lower_top:.1f}" width="{lower_right - lower_left:.1f}" height="{lower_bottom - lower_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(lower_left + 18, lower_top + 28, "Tracking-mode frequency jitter after coarse frequency help", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(lower_left + 18, lower_top + 52, ["carrier offset = +0.35 rad/sample, noise std = 0.08", "the coarse front end already landed near lock; now the loop just has to stay quiet"], size=14, fill="#526274", line_height=17))
    for step in range(7):
        frac = step / 6
        y = lower_top + 36 + frac * ((lower_bottom - 26) - (lower_top + 36))
        value = lower_y_extent - frac * (2.0 * lower_y_extent)
        parts.append(_line(lower_left + 56, y, lower_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(lower_left + 48, y + 5, f"{value:+.1f}", anchor="end", size=13, fill="#64748b"))
    for step in range(6):
        frac = step / 5
        x = lower_left + 56 + frac * ((lower_right - 24) - (lower_left + 56))
        value = int(round(frac * (tail_len - 1)))
        parts.append(_line(x, lower_top + 36, x, lower_bottom - 26, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, lower_bottom + 24, f"{value}", anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(lower_left + 56, lower_top + 36, lower_left + 56, lower_bottom - 26, stroke="#334155", width=2))
    parts.append(_line(lower_left + 56, lower_bottom - 26, lower_right - 24, lower_bottom - 26, stroke="#334155", width=2))
    parts.append(_line(lower_left + 56, map_lower_y(0.0), lower_right - 24, map_lower_y(0.0), stroke="#94a3b8", width=1.8, dash="8 8"))
    for study in studies:
        series = lower_series[study.label]
        payload = " ".join(f"{map_lower_x(idx, len(series)):.1f},{map_lower_y(value):.1f}" for idx, value in enumerate(series))
        parts.append(f'<polyline fill="none" stroke="{colors[study.label]}" stroke-width="2.6" points="{payload}"/>')
    parts.append(_text((lower_left + lower_right) / 2, lower_bottom + 54, "symbol index within the last 260-symbol window", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(28, (lower_top + lower_bottom) / 2, "freq estimate residual (mrad/sample)", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 28 {(lower_top + lower_bottom) / 2:.1f})'))

    # Summary panel: settle time and jitter bars.
    parts.append(f'<rect x="{summary_left:.1f}" y="{summary_top:.1f}" width="{summary_right - summary_left:.1f}" height="{summary_bottom - summary_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(summary_left + 18, summary_top + 28, "Speed versus calm, side by side", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(summary_left + 18, summary_top + 52, ["left bars: phase-only settle time in the harder case", "right bars: tracking jitter after freq+phase acquisition"], size=14, fill="#526274", line_height=17))

    settle_max = max((study.acquisition_settle_index or 1500) for study in studies)
    jitter_max = max(study.tracking_freq_jitter for study in studies) * 1000.0 * 1.1
    row_top = summary_top + 114
    row_gap = 72
    for idx, study in enumerate(studies):
        y = row_top + idx * row_gap
        parts.append(_text(summary_left + 18, y + 6, study.label, size=14, fill=colors[study.label], weight="700"))
        settle_value = float(study.acquisition_settle_index if study.acquisition_settle_index is not None else settle_max)
        settle_w = 152.0 * settle_value / max(settle_max, 1.0)
        jitter_value = study.tracking_freq_jitter * 1000.0
        jitter_w = 148.0 * jitter_value / max(jitter_max, 1e-9)
        parts.append(f'<rect x="{summary_left + 120:.1f}" y="{y - 12:.1f}" width="152.0" height="18" rx="9" fill="#e2e8f0"/>')
        parts.append(f'<rect x="{summary_left + 120:.1f}" y="{y - 12:.1f}" width="{settle_w:.1f}" height="18" rx="9" fill="{colors[study.label]}" fill-opacity="0.85"/>')
        settle_label = f"{study.acquisition_settle_index} sym" if study.acquisition_settle_index is not None else "no settle"
        parts.append(_text(summary_left + 282, y + 2, settle_label, size=13, fill="#334155", weight="700"))

        parts.append(f'<rect x="{summary_left + 346:.1f}" y="{y - 12:.1f}" width="148.0" height="18" rx="9" fill="#e2e8f0"/>')
        parts.append(f'<rect x="{summary_left + 346:.1f}" y="{y - 12:.1f}" width="{jitter_w:.1f}" height="18" rx="9" fill="{colors[study.label]}" fill-opacity="0.55"/>')
        parts.append(_text(summary_left + 558, y + 2, f"{jitter_value:.2f} mrad/sample", size=12, anchor="end", fill="#334155", weight="700"))
        parts.append(_text(summary_left + 346, y + 24, f"tail RMS {study.tracking_tail_rms_error:.3f} · |Costas err| {study.tracking_mean_abs_costas_error:.3f}", size=12, fill="#64748b"))

    parts.append(_text(summary_left + 196, summary_bottom - 30, "settle time", anchor="middle", size=14, fill="#374151", weight="700"))
    parts.append(_text(summary_left + 420, summary_bottom - 30, "frequency jitter", anchor="middle", size=14, fill="#374151", weight="700"))
    parts.append(_paragraph(summary_left + 18, summary_bottom - 86, ["No single loop gain wins everywhere.", "Rough handoffs reward aggression.", "Good handoffs reward calm."], size=12, fill="#475569", line_height=15))

    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n")


def render_coarse_prefix_budget_svg(
    rows: list[CoarsePrefixBudgetRow],
    *,
    output: str | Path,
    title: str = "QPSK coarse-prefix budget: when the loop stops caring",
) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("rows must not be empty")

    width = 1660
    height = 1020
    top_left, top_right = 80.0, 1520.0
    top_top, top_bottom = 118.0, 456.0
    lower_left, lower_right = 80.0, 900.0
    lower_top, lower_bottom = 560.0, 900.0
    summary_left, summary_right = 940.0, 1520.0
    summary_top, summary_bottom = 560.0, 900.0
    top_plot_top = top_top + 86.0
    top_plot_bottom = top_bottom - 26.0
    lower_plot_top = lower_top + 86.0
    lower_plot_bottom = lower_bottom - 26.0

    prefixes = sorted({row.coarse_prefix for row in rows})
    noises = sorted({row.noise_std for row in rows})
    rows_by_noise = {
        noise: sorted((row for row in rows if row.noise_std == noise), key=lambda row: row.coarse_prefix)
        for noise in noises
    }

    palette = ["#0f766e", "#2563eb", "#7c3aed", "#ea580c", "#dc2626", "#0891b2"]
    colors = {noise: palette[idx % len(palette)] for idx, noise in enumerate(noises)}

    top_y_hi = max(row.mean_abs_coarse_frequency_error for row in rows) * 1000.0 * 1.08
    lower_y_lo = 0.0
    lower_y_hi = max(row.mean_tracked_rms_error for row in rows) * 1.12

    def map_x(prefix: int, left: float, right: float) -> float:
        idx = prefixes.index(prefix)
        return left + idx / max(len(prefixes) - 1, 1) * (right - left)

    def map_top_y(value: float) -> float:
        milli = value * 1000.0
        return top_plot_bottom - (milli / max(top_y_hi, 1e-9)) * (top_plot_bottom - top_plot_top)

    def map_lower_y(value: float) -> float:
        return lower_plot_bottom - ((value - lower_y_lo) / max(lower_y_hi - lower_y_lo, 1e-9)) * (lower_plot_bottom - lower_plot_top)

    def threshold_prefix(noise: float, *, target_milli: float) -> int | None:
        for row in rows_by_noise[noise]:
            if row.mean_abs_coarse_frequency_error * 1000.0 <= target_milli:
                return row.coarse_prefix
        return None

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        _text(width / 2, 42, title, size=28, anchor="middle", weight="700"),
        _paragraph(
            width / 2,
            68,
            [
                "Same outer-band carrier offset, same loop gains, same symbol-rate model.",
                "Only the front-end sample budget changes, and the post-lock output flattens early.",
            ],
            size=16,
            anchor="middle",
            fill="#475569",
            line_height=18,
        ),
    ]

    # Top panel.
    parts.append(f'<rect x="{top_left:.1f}" y="{top_top:.1f}" width="{top_right - top_left:.1f}" height="{top_bottom - top_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(top_left + 18, top_top + 28, "Mean absolute coarse-frequency error at +0.62 rad/sample", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(top_left + 18, top_top + 52, ["24 Monte Carlo trials per point", "lower is better; units are mrad/sample"], size=14, fill="#526274", line_height=16))
    for step in range(7):
        frac = step / 6
        y = top_plot_top + frac * (top_plot_bottom - top_plot_top)
        value = top_y_hi - frac * top_y_hi
        parts.append(_line(top_left + 56, y, top_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(top_left + 48, y + 5, f"{value:.1f}", anchor="end", size=13, fill="#64748b"))
    for prefix in prefixes:
        x = map_x(prefix, top_left + 56, top_right - 24)
        parts.append(_line(x, top_plot_top, x, top_plot_bottom, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, top_bottom + 24, str(prefix), anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(top_left + 56, top_plot_top, top_left + 56, top_plot_bottom, stroke="#334155", width=2))
    parts.append(_line(top_left + 56, top_plot_bottom, top_right - 24, top_plot_bottom, stroke="#334155", width=2))
    for noise in noises:
        series = rows_by_noise[noise]
        payload = " ".join(
            f"{map_x(row.coarse_prefix, top_left + 56, top_right - 24):.1f},{map_top_y(row.mean_abs_coarse_frequency_error):.1f}"
            for row in series
        )
        parts.append(f'<polyline fill="none" stroke="{colors[noise]}" stroke-width="3.2" points="{payload}"/>')
        for row in series:
            x = map_x(row.coarse_prefix, top_left + 56, top_right - 24)
            y = map_top_y(row.mean_abs_coarse_frequency_error)
            parts.append(_circle(x, y, 4.4, fill=colors[noise], opacity=0.85))
    parts.append(_text((top_left + top_right) / 2, top_bottom + 54, "coarse-prefix length (symbols)", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(28, (top_top + top_bottom) / 2, "mean |freq error| (mrad/sample)", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 28 {(top_top + top_bottom) / 2:.1f})'))

    legend_x = top_right - 190
    legend_y = top_top + 28
    parts.append(f'<rect x="{legend_x:.1f}" y="{legend_y:.1f}" width="160" height="{34 + 22 * len(noises):.1f}" rx="14" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(legend_x + 18, legend_y + 22, "noise std", size=13, fill="#334155", weight="700"))
    for idx, noise in enumerate(noises):
        y = legend_y + 44 + idx * 22
        parts.append(_line(legend_x + 18, y - 5, legend_x + 44, y - 5, stroke=colors[noise], width=4))
        parts.append(_text(legend_x + 56, y, f"{noise:.2f}", size=13, fill="#334155", weight="700"))

    # Lower-left panel.
    parts.append(f'<rect x="{lower_left:.1f}" y="{lower_top:.1f}" width="{lower_right - lower_left:.1f}" height="{lower_bottom - lower_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(lower_left + 18, lower_top + 28, "Tracked tail RMS after the Costas loop", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(lower_left + 18, lower_top + 52, ["same trials, same outer-band offset", "this is the part that flattens once the handoff is already good enough"], size=14, fill="#526274", line_height=16))
    for step in range(7):
        frac = step / 6
        y = lower_plot_top + frac * (lower_plot_bottom - lower_plot_top)
        value = lower_y_hi - frac * (lower_y_hi - lower_y_lo)
        parts.append(_line(lower_left + 56, y, lower_right - 24, y, stroke="#e2e8f0", dash="4 6"))
        parts.append(_text(lower_left + 48, y + 5, f"{value:.3f}", anchor="end", size=13, fill="#64748b"))
    for prefix in prefixes:
        x = map_x(prefix, lower_left + 56, lower_right - 24)
        parts.append(_line(x, lower_plot_top, x, lower_plot_bottom, stroke="#eef2f7", dash="4 6"))
        parts.append(_text(x, lower_bottom + 24, str(prefix), anchor="middle", size=13, fill="#64748b"))
    parts.append(_line(lower_left + 56, lower_plot_top, lower_left + 56, lower_plot_bottom, stroke="#334155", width=2))
    parts.append(_line(lower_left + 56, lower_plot_bottom, lower_right - 24, lower_plot_bottom, stroke="#334155", width=2))
    for noise in noises:
        series = rows_by_noise[noise]
        payload = " ".join(
            f"{map_x(row.coarse_prefix, lower_left + 56, lower_right - 24):.1f},{map_lower_y(row.mean_tracked_rms_error):.1f}"
            for row in series
        )
        parts.append(f'<polyline fill="none" stroke="{colors[noise]}" stroke-width="3.0" points="{payload}"/>')
        for row in series:
            x = map_x(row.coarse_prefix, lower_left + 56, lower_right - 24)
            y = map_lower_y(row.mean_tracked_rms_error)
            parts.append(_circle(x, y, 4.1, fill=colors[noise], opacity=0.82))
    parts.append(_text((lower_left + lower_right) / 2, lower_bottom + 54, "coarse-prefix length (symbols)", anchor="middle", size=16, fill="#374151"))
    parts.append(_text(28, (lower_top + lower_bottom) / 2, "tracked RMS error", anchor="middle", size=16, fill="#374151", transform=f'rotate(-90 28 {(lower_top + lower_bottom) / 2:.1f})'))

    # Summary panel.
    parts.append(f'<rect x="{summary_left:.1f}" y="{summary_top:.1f}" width="{summary_right - summary_left:.1f}" height="{summary_bottom - summary_top:.1f}" rx="18" fill="#ffffff" stroke="#e2e8f0"/>')
    parts.append(_text(summary_left + 18, summary_top + 28, "Where the diminishing returns start", size=16, weight="700", fill="#334155"))
    parts.append(_paragraph(summary_left + 18, summary_top + 52, ["threshold = first prefix whose mean coarse-frequency error drops below 5 mrad/sample", "the loop panel shows why this is mostly a front-end honesty story"], size=13, fill="#526274", line_height=16))

    row_top = summary_top + 122
    row_gap = 42
    for idx, noise in enumerate(noises):
        y = row_top + idx * row_gap
        series = rows_by_noise[noise]
        threshold = threshold_prefix(noise, target_milli=5.0)
        baseline = series[0].mean_abs_coarse_frequency_error * 1000.0
        best = series[-1].mean_abs_coarse_frequency_error * 1000.0
        tracked_delta = (series[0].mean_tracked_rms_error - series[-1].mean_tracked_rms_error)
        parts.append(_text(summary_left + 18, y + 4, f"noise {noise:.2f}", size=14, fill=colors[noise], weight="700"))
        parts.append(_text(summary_left + 126, y + 4, f"8→128: mean coarse error {baseline:.1f} → {best:.1f} mrad", size=13, fill="#334155"))
        threshold_text = f"crosses 5 mrad by prefix {threshold}" if threshold is not None else "still above 5 mrad at prefix 128"
        parts.append(_text(summary_left + 126, y + 24, threshold_text, size=12, fill="#526274"))
        parts.append(_text(summary_right - 24, y + 4, f"tracked RMS Δ {tracked_delta:+.4f}", anchor="end", size=12, fill="#526274"))

    parts.append('</svg>')
    output.write_text("\n".join(parts) + "\n")

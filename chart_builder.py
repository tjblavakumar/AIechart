"""
MCP Client for Chart Generation
Builds ECharts JSON using AI-extracted styling — no hardcoded values.
"""

import json
from typing import Dict, Any, List
import pandas as pd


def build_perfect_echarts(description: str, data: Dict) -> Dict:
    """Build ECharts config using ALL values from AI vision analysis."""
    x_data = data.get('x_data', [])
    series_data = data.get('series', [])
    annotations = data.get('annotations', {})
    y_cfg = data.get('y_axis', {})
    x_cfg = data.get('x_axis', {})
    layout = data.get('layout', {})
    data_table_config = data.get('data_table', {})

    # X-axis labels: years only, append next year if missing
    x_labels = [str(d)[:4] for d in x_data]
    if x_labels:
        last_year = int(x_labels[-1])
        next_year = str(last_year + 1)
        if x_labels[-1] != next_year:
            x_labels.append(next_year)
            for s in series_data:
                s['data'].append(None)

    total_points = len(x_labels)

    # Build series — use AI-extracted values for everything
    echarts_series = []
    for i, s in enumerate(series_data):
        color = s.get('color', '#000')
        placement = s.get('label_placement', 'none')
        label_font_size = s.get('label_font_size', 14)
        label_font_weight = s.get('label_font_weight', 'bold')
        label_x_pct = s.get('label_x_percent', 35)
        smooth = s.get('smooth', False)

        # Label index from AI-provided x percentage
        label_idx = int(total_points * label_x_pct / 100)
        label_idx = min(label_idx, len(s['data']) - 1)

        # Build data array with inline label at one point
        # Accept any placement that isn't explicitly "none" or "legend_box"
        raw_data = s['data']
        show_label = placement not in ('none', 'legend_box', '')
        label_position = "top"  # default
        if placement in ('below', 'inline_below'):
            label_position = "bottom"

        formatted_data = []
        for idx, val in enumerate(raw_data):
            if show_label and idx == label_idx and val is not None:
                formatted_data.append({
                    "value": val,
                    "symbol": "circle",
                    "symbolSize": 0.1,
                    "label": {
                        "show": True,
                        "formatter": s['name'],
                        "fontSize": label_font_size,
                        "fontWeight": label_font_weight,
                        "fontFamily": layout.get('font_family', 'Arial, sans-serif'),
                        "color": color,
                        "position": label_position,
                        "distance": 15,
                        "backgroundColor": "transparent",
                    },
                })
            else:
                formatted_data.append(val)

        series_obj = {
            "name": s['name'],
            "type": "line",
            "data": formatted_data,
            "smooth": smooth,
            "symbol": "none",
            "lineStyle": {
                "width": s.get('line_width', 2.5),
                "color": color,
                "type": s.get('line_style', 'solid'),
            },
            "itemStyle": {"color": color},
            "connectNulls": True,
        }

        if i == 0:
            _add_annotations(series_obj, annotations, x_data)

        echarts_series.append(series_obj)

    # Build option using AI-extracted axis/layout config
    option = {
        "backgroundColor": layout.get('background_color', '#ffffff'),
        "animation": False,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "line"}},
        "grid": {
            "left": layout.get('grid_left', 55),
            "right": layout.get('grid_right', 40),
            "top": layout.get('grid_top', 25),
            "bottom": layout.get('grid_bottom', 45),
        },
        "xAxis": {
            "type": "category",
            "data": x_labels,
            "boundaryGap": False,
            "axisLine": {
                "show": x_cfg.get('axis_line_show', True),
                "lineStyle": {
                    "color": x_cfg.get('axis_line_color', '#333'),
                    "width": x_cfg.get('axis_line_width', 1),
                },
            },
            "axisTick": {"show": x_cfg.get('tick_show', False)},
            "axisLabel": {
                "fontSize": x_cfg.get('label_font_size', 13),
                "color": x_cfg.get('label_color', '#333'),
                "interval": 11,
            },
            "splitLine": {
                "show": x_cfg.get('grid_lines', False),
                "lineStyle": {"color": x_cfg.get('grid_color', '#e0e0e0')},
            },
        },
        "yAxis": {
            "type": "value",
            "min": y_cfg.get('min', 0),
            "max": y_cfg.get('max', 8),
            "interval": y_cfg.get('interval', 1),
            "axisLine": {
                "show": y_cfg.get('axis_line_show', False),
                "lineStyle": {
                    "color": y_cfg.get('axis_line_color', '#333'),
                    "width": y_cfg.get('axis_line_width', 1),
                },
            },
            "axisTick": {"show": y_cfg.get('tick_show', False)},
            "axisLabel": {
                "fontSize": y_cfg.get('label_font_size', 13),
                "color": y_cfg.get('label_color', '#333'),
                "formatter": "{value}" + y_cfg.get('suffix', '%'),
            },
            "splitLine": {
                "show": y_cfg.get('grid_lines', False),
                "lineStyle": {"color": y_cfg.get('grid_color', '#e0e0e0')},
            },
        },
        "series": echarts_series,
        "graphic": [],
    }

    if data_table_config.get('visible', False):
        _add_data_table_graphic(option, series_data, x_data, data_table_config, layout)

    return option


def _add_annotations(series_obj, annotations, x_data):
    """Horizontal dashed lines + vertical shaded bands."""
    mark_line_data = []
    mark_area_data = []

    for hline in annotations.get('horizontal_lines', []):
        mark_line_data.append({
            "yAxis": hline['value'],
            "lineStyle": {
                "type": hline.get('style', 'dashed'),
                "color": hline.get('color', '#000'),
                "width": hline.get('width', 1.5),
            },
            "label": {"show": False},
        })

    # Vertical bands (new format from updated AI prompt)
    for vband in annotations.get('vertical_bands', []):
        target_year = str(vband.get('year', ''))[:4]
        band_months = vband.get('width_months', 3)
        indices = [i for i, d in enumerate(x_data) if str(d).startswith(target_year)]
        if indices:
            mid = indices[len(indices) // 2]
            half = max(1, band_months // 2)
            band_start = max(indices[0], mid - half)
            band_end = min(indices[-1], mid + half)
            band_color = vband.get('color', 'rgba(200,200,200,0.4)')
            mark_area_data.append([
                {"xAxis": band_start, "itemStyle": {"color": band_color}},
                {"xAxis": band_end},
            ])

    # Legacy format support (vertical_lines → convert to bands)
    for vline in annotations.get('vertical_lines', []):
        target_year = str(vline.get('value', ''))[:4]
        indices = [i for i, d in enumerate(x_data) if str(d).startswith(target_year)]
        if indices:
            mid = indices[len(indices) // 2]
            band_start = max(indices[0], mid - 1)
            band_end = min(indices[-1], mid + 1)
            mark_area_data.append([
                {"xAxis": band_start, "itemStyle": {"color": "rgba(200,200,200,0.4)"}},
                {"xAxis": band_end},
            ])

    if mark_line_data:
        series_obj['markLine'] = {
            "silent": True, "symbol": ["none", "none"], "data": mark_line_data,
        }
    if mark_area_data:
        series_obj['markArea'] = {"silent": True, "data": mark_area_data}


def _add_data_table_graphic(option, series_data, x_data, dt_cfg, layout):
    """Data table box using AI-extracted styling."""
    if not series_data:
        return

    def _fmt(d):
        try:
            parts = str(d).split('-')
            months = ['','Jan','Feb','Mar','Apr','May','Jun',
                      'Jul','Aug','Sep','Oct','Nov','Dec']
            return f"{months[int(parts[1])]} {parts[0]}"
        except Exception:
            return str(d)[-7:]

    prev_lbl = _fmt(x_data[-2]) if len(x_data) >= 2 else "Prev"
    curr_lbl = _fmt(x_data[-1]) if len(x_data) >= 1 else "Curr"

    # Styling from AI
    font_size = dt_cfg.get('font_size', 11)
    font_family = dt_cfg.get('font_family', layout.get('font_family', 'Arial, sans-serif'))
    header_weight = dt_cfg.get('header_font_weight', 'bold')
    header_color = dt_cfg.get('header_color', '#333')
    if header_color == 'same_as_series':
        header_color = '#333'
    value_weight = dt_cfg.get('value_font_weight', 'bold')
    border_color = dt_cfg.get('border_color', '#999')
    if border_color in ('same_as_series', 'none'):
        border_color = '#999'
    border_width = dt_cfg.get('border_width', 0.5)
    bg_color = dt_cfg.get('background', '#ffffff')
    if bg_color in ('same_as_series', 'none', 'transparent'):
        bg_color = '#ffffff'

    row_h = 20
    col_w = [75, 80, 80, 55]
    pad = 10
    table_w = sum(col_w) + pad * 2
    table_h = pad + row_h * (1 + len(series_data)) + pad

    children = []

    # Background
    children.append({
        "type": "rect",
        "shape": {"width": table_w, "height": table_h, "r": 0},
        "style": {"fill": bg_color, "stroke": border_color, "lineWidth": border_width},
    })

    # Header
    headers = ["", prev_lbl, curr_lbl, "Chg."]
    for ci, hdr in enumerate(headers):
        children.append({
            "type": "text",
            "style": {
                "text": hdr, "x": pad + sum(col_w[:ci]), "y": pad,
                "fontSize": font_size, "fontWeight": header_weight,
                "fontFamily": font_family, "fill": header_color,
            },
        })

    # Data rows
    for ri, s in enumerate(series_data):
        real_vals = [v for v in s['data'] if v is not None]
        if len(real_vals) < 2:
            continue
        prev_v, curr_v = real_vals[-2], real_vals[-1]
        chg_bp = abs(round((curr_v - prev_v) * 100))
        y = pad + row_h * (ri + 1)
        sc = s.get('color', '#333')

        cells = [s['name'], f"{prev_v:.2f}%", f"{curr_v:.2f}%", f"{chg_bp} b.p."]
        # Resolve "same_as_series" → use series color; otherwise use specified color
        raw_val_color = dt_cfg.get('value_color', '#333')
        val_color = sc if raw_val_color == 'same_as_series' else raw_val_color
        colors = [sc, val_color, val_color, header_color]
        weights = [value_weight, value_weight, value_weight, "normal"]

        for ci, cell in enumerate(cells):
            children.append({
                "type": "text",
                "style": {
                    "text": cell, "x": pad + sum(col_w[:ci]), "y": y,
                    "fontSize": font_size, "fontWeight": weights[ci],
                    "fontFamily": font_family, "fill": colors[ci],
                },
            })

    option['graphic'].append({
        "type": "group", "right": 30, "bottom": 55, "z": 100,
        "children": children,
    })



def generate_chart_from_analysis(analysis: Dict, csv_data: pd.DataFrame) -> Dict:
    """Generate ECharts JSON from AI analysis and CSV data."""
    if 'key' in csv_data.columns and 'value' in csv_data.columns:
        csv_data = csv_data.pivot(index='date', columns='key', values='value').reset_index()

    columns = list(csv_data.columns)
    x_data = csv_data[columns[0]].astype(str).tolist()

    series_data = []
    for sc in analysis.get('series', []):
        config_name = sc.get('name', '').lower()
        matched_col = None
        for col in columns[1:]:
            if config_name in col.lower() or col.lower().replace('_', ' ') in config_name:
                matched_col = col
                break
        if matched_col and pd.api.types.is_numeric_dtype(csv_data[matched_col]):
            series_data.append({
                'name': sc.get('name', matched_col),
                'data': csv_data[matched_col].tolist(),
                'color': sc.get('color', '#000'),
                'line_width': sc.get('line_width', 2.5),
                'line_style': sc.get('line_style', 'solid'),
                'smooth': sc.get('smooth', False),
                'label_placement': sc.get('label_placement', 'none'),
                'label_font_size': sc.get('label_font_size', 14),
                'label_font_weight': sc.get('label_font_weight', 'bold'),
                'label_x_percent': sc.get('label_x_percent', 35),
            })

    return build_perfect_echarts("", {
        'x_data': x_data,
        'series': series_data,
        'annotations': analysis.get('annotations', {}),
        'y_axis': analysis.get('y_axis', {}),
        'x_axis': analysis.get('x_axis', {}),
        'layout': analysis.get('layout', {}),
        'data_table': analysis.get('data_table', {}),
    })

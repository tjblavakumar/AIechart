"""
Chart Editor Module
Provides inline visual controls to customize the generated ECharts chart.
Reads from chart_figure + styling_config, applies edits, regenerates chart.
"""

import copy
import streamlit as st
from chart_builder import generate_chart_from_analysis


def init_editor_state():
    """Initialize editor session state."""
    if "editor_open" not in st.session_state:
        st.session_state.editor_open = False


def _safe_get(d, *keys, default=None):
    """Safely traverse nested dicts."""
    current = d
    for k in keys:
        if isinstance(current, dict):
            current = current.get(k, default)
        else:
            return default
    return current


def render_editor():
    """Render the chart editor panel. Returns True if chart was updated."""
    config = st.session_state.get("styling_config")
    if not config:
        st.warning("No styling config available.")
        return False

    # Work on a deep copy so we only apply on "Apply"
    if "editor_config" not in st.session_state:
        st.session_state.editor_config = copy.deepcopy(config)

    ec = st.session_state.editor_config
    updated = False

    st.markdown("### ✏️ Chart Editor")
    st.caption("Adjust styling below, then click Apply to update the chart.")

    # ── 1. Series Styling ──
    with st.expander("🎨 Line / Series Styling", expanded=True):
        series_list = ec.get("series", [])
        for i, s in enumerate(series_list):
            st.markdown(f"**{s.get('name', f'Series {i+1}')}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                new_color = st.color_picker(
                    f"Color", value=s.get("color", "#000000"),
                    key=f"ed_series_color_{i}")
                s["color"] = new_color
            with c2:
                new_width = st.slider(
                    f"Line width", 0.5, 6.0,
                    value=float(s.get("line_width", 2.5)), step=0.5,
                    key=f"ed_series_width_{i}")
                s["line_width"] = new_width
            with c3:
                new_style = st.selectbox(
                    f"Line style",
                    ["solid", "dashed", "dotted"],
                    index=["solid", "dashed", "dotted"].index(
                        s.get("line_style", "solid")),
                    key=f"ed_series_style_{i}")
                s["line_style"] = new_style

    # ── 2. Inline Label Styling ──
    with st.expander("🏷️ Inline Labels"):
        for i, s in enumerate(series_list):
            st.markdown(f"**{s.get('name', f'Series {i+1}')}**")
            c1, c2, c3 = st.columns(3)
            with c1:
                placement_opts = ["above", "below", "none"]
                cur_place = s.get("label_placement", "none")
                if cur_place not in placement_opts:
                    cur_place = "above" if cur_place in ("inline_above",) else "none"
                new_place = st.selectbox(
                    "Position", placement_opts,
                    index=placement_opts.index(cur_place),
                    key=f"ed_label_pos_{i}")
                s["label_placement"] = new_place
            with c2:
                new_lfs = st.slider(
                    "Font size", 8, 24,
                    value=int(s.get("label_font_size", 14)),
                    key=f"ed_label_fs_{i}")
                s["label_font_size"] = new_lfs
            with c3:
                fw_opts = ["normal", "bold"]
                new_fw = st.selectbox(
                    "Font weight", fw_opts,
                    index=fw_opts.index(s.get("label_font_weight", "bold")),
                    key=f"ed_label_fw_{i}")
                s["label_font_weight"] = new_fw

            new_xpct = st.slider(
                "Horizontal position (%)", 5, 95,
                value=int(s.get("label_x_percent", 35)),
                key=f"ed_label_xpct_{i}")
            s["label_x_percent"] = new_xpct

    # ── 3. X-Axis Styling ──
    with st.expander("📏 X-Axis"):
        x_cfg = ec.setdefault("x_axis", {})
        c1, c2 = st.columns(2)
        with c1:
            x_label_fs = st.slider("Label font size", 8, 20,
                value=int(x_cfg.get("label_font_size", 13)),
                key="ed_x_label_fs")
            x_cfg["label_font_size"] = x_label_fs

            x_label_color = st.color_picker("Label color",
                value=x_cfg.get("label_color", "#333333"),
                key="ed_x_label_color")
            x_cfg["label_color"] = x_label_color

            x_line_show = st.checkbox("Show axis line",
                value=x_cfg.get("axis_line_show", True),
                key="ed_x_line_show")
            x_cfg["axis_line_show"] = x_line_show
        with c2:
            x_line_color = st.color_picker("Axis line color",
                value=x_cfg.get("axis_line_color", "#333333"),
                key="ed_x_line_color")
            x_cfg["axis_line_color"] = x_line_color

            x_line_width = st.slider("Axis line width", 0.5, 4.0,
                value=float(x_cfg.get("axis_line_width", 1.0)), step=0.5,
                key="ed_x_line_width")
            x_cfg["axis_line_width"] = x_line_width

            x_tick = st.checkbox("Show ticks",
                value=x_cfg.get("tick_show", False),
                key="ed_x_tick")
            x_cfg["tick_show"] = x_tick

            x_grid = st.checkbox("Show grid lines",
                value=x_cfg.get("grid_lines", False),
                key="ed_x_grid")
            x_cfg["grid_lines"] = x_grid

            if x_grid:
                x_grid_color = st.color_picker("Grid color",
                    value=x_cfg.get("grid_color", "#e0e0e0"),
                    key="ed_x_grid_color")
                x_cfg["grid_color"] = x_grid_color

    # ── 4. Y-Axis Styling ──
    with st.expander("📐 Y-Axis"):
        y_cfg = ec.setdefault("y_axis", {})
        c1, c2 = st.columns(2)
        with c1:
            y_min = st.number_input("Min", value=float(y_cfg.get("min", 0)),
                step=0.5, key="ed_y_min")
            y_cfg["min"] = y_min

            y_max = st.number_input("Max", value=float(y_cfg.get("max", 8)),
                step=0.5, key="ed_y_max")
            y_cfg["max"] = y_max

            y_interval = st.number_input("Interval", value=float(y_cfg.get("interval", 1)),
                step=0.5, min_value=0.5, key="ed_y_interval")
            y_cfg["interval"] = y_interval

            y_label_fs = st.slider("Label font size", 8, 20,
                value=int(y_cfg.get("label_font_size", 13)),
                key="ed_y_label_fs")
            y_cfg["label_font_size"] = y_label_fs

            y_label_color = st.color_picker("Label color",
                value=y_cfg.get("label_color", "#333333"),
                key="ed_y_label_color")
            y_cfg["label_color"] = y_label_color
        with c2:
            y_line_show = st.checkbox("Show axis line",
                value=y_cfg.get("axis_line_show", False),
                key="ed_y_line_show")
            y_cfg["axis_line_show"] = y_line_show

            y_line_color = st.color_picker("Axis line color",
                value=y_cfg.get("axis_line_color", "#333333"),
                key="ed_y_line_color")
            y_cfg["axis_line_color"] = y_line_color

            y_line_width = st.slider("Axis line width", 0.5, 4.0,
                value=float(y_cfg.get("axis_line_width", 1.0)), step=0.5,
                key="ed_y_line_width")
            y_cfg["axis_line_width"] = y_line_width

            y_tick = st.checkbox("Show ticks",
                value=y_cfg.get("tick_show", False),
                key="ed_y_tick")
            y_cfg["tick_show"] = y_tick

            y_grid = st.checkbox("Show grid lines",
                value=y_cfg.get("grid_lines", False),
                key="ed_y_grid")
            y_cfg["grid_lines"] = y_grid

            if y_grid:
                y_grid_color = st.color_picker("Grid color",
                    value=y_cfg.get("grid_color", "#e0e0e0"),
                    key="ed_y_grid_color")
                y_cfg["grid_color"] = y_grid_color

    # ── 5. Annotations ──
    with st.expander("📌 Annotations"):
        annot = ec.setdefault("annotations", {})
        h_lines = annot.get("horizontal_lines", [])
        if h_lines:
            st.markdown("**Horizontal Lines**")
            for i, hl in enumerate(h_lines):
                c1, c2, c3 = st.columns(3)
                with c1:
                    hl_val = st.number_input(f"Y value", value=float(hl.get("value", 2.0)),
                        step=0.5, key=f"ed_hl_val_{i}")
                    hl["value"] = hl_val
                with c2:
                    hl_color = st.color_picker(f"Color",
                        value=hl.get("color", "#000000"),
                        key=f"ed_hl_color_{i}")
                    hl["color"] = hl_color
                with c3:
                    hl_width = st.slider(f"Width", 0.5, 4.0,
                        value=float(hl.get("width", 1.5)), step=0.5,
                        key=f"ed_hl_width_{i}")
                    hl["width"] = hl_width

                    hl_style = st.selectbox(f"Style",
                        ["dashed", "solid", "dotted"],
                        index=["dashed", "solid", "dotted"].index(
                            hl.get("style", "dashed")),
                        key=f"ed_hl_style_{i}")
                    hl["style"] = hl_style
        else:
            st.caption("No horizontal lines configured.")

        v_bands = annot.get("vertical_bands", [])
        if v_bands:
            st.markdown("**Vertical Bands**")
            for i, vb in enumerate(v_bands):
                c1, c2 = st.columns(2)
                with c1:
                    vb_year = st.text_input(f"Center year",
                        value=str(vb.get("year", "")),
                        key=f"ed_vb_year_{i}")
                    vb["year"] = vb_year
                with c2:
                    vb_months = st.slider(f"Width (months)", 1, 12,
                        value=int(vb.get("width_months", 3)),
                        key=f"ed_vb_months_{i}")
                    vb["width_months"] = vb_months

    # ── 6. Data Table ──
    with st.expander("📋 Data Table"):
        dt = ec.setdefault("data_table", {})
        dt_visible = st.checkbox("Show data table",
            value=dt.get("visible", False),
            key="ed_dt_visible")
        dt["visible"] = dt_visible

        if dt_visible:
            c1, c2 = st.columns(2)
            with c1:
                dt_fs = st.slider("Font size", 8, 18,
                    value=int(dt.get("font_size", 11)),
                    key="ed_dt_fs")
                dt["font_size"] = dt_fs

                dt_pos = st.selectbox("Position",
                    ["bottom_right_inside", "bottom_left_inside", "top_right_inside", "top_left_inside"],
                    index=0, key="ed_dt_pos")
                dt["position"] = dt_pos
            with c2:
                dt_header_color = st.color_picker("Header color",
                    value=dt.get("header_color", "#333333") if dt.get("header_color", "#333") != "same_as_series" else "#333333",
                    key="ed_dt_hcolor")
                dt["header_color"] = dt_header_color

                dt_border_color = st.color_picker("Border color",
                    value=dt.get("border_color", "#999999") if dt.get("border_color", "#999") not in ("same_as_series", "none") else "#999999",
                    key="ed_dt_bcolor")
                dt["border_color"] = dt_border_color

    # ── 7. Layout / Background ──
    with st.expander("🖼️ Layout"):
        layout = ec.setdefault("layout", {})
        bg_color = st.color_picker("Background color",
            value=layout.get("background_color", "#ffffff"),
            key="ed_bg_color")
        layout["background_color"] = bg_color

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            gl = st.number_input("Grid left", value=int(layout.get("grid_left", 55)),
                step=5, key="ed_gl")
            layout["grid_left"] = gl
        with c2:
            gr = st.number_input("Grid right", value=int(layout.get("grid_right", 40)),
                step=5, key="ed_gr")
            layout["grid_right"] = gr
        with c3:
            gt = st.number_input("Grid top", value=int(layout.get("grid_top", 25)),
                step=5, key="ed_gt")
            layout["grid_top"] = gt
        with c4:
            gb = st.number_input("Grid bottom", value=int(layout.get("grid_bottom", 45)),
                step=5, key="ed_gb")
            layout["grid_bottom"] = gb

    # ── Apply / Cancel buttons ──
    st.markdown("---")
    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("✅ Apply Changes", type="primary", use_container_width=True, key="ed_apply"):
            # Save edited config back and regenerate chart
            st.session_state.styling_config = copy.deepcopy(ec)
            csv_data = st.session_state.csv_data
            try:
                new_chart = generate_chart_from_analysis(ec, csv_data)
                st.session_state.chart_figure = new_chart
                st.session_state.editor_open = False
                # Clear editor working copy
                if "editor_config" in st.session_state:
                    del st.session_state["editor_config"]
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to regenerate chart: {str(e)}")
    with btn2:
        if st.button("❌ Cancel", use_container_width=True, key="ed_cancel"):
            st.session_state.editor_open = False
            if "editor_config" in st.session_state:
                del st.session_state["editor_config"]
            st.rerun()

    return False

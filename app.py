"""
Chart Style Replicator
Upload CSV + Reference Image → AI analyzes style → Generate matching chart
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import json
from streamlit_echarts import st_echarts

# Load environment variables
load_dotenv()

# Import AI helper
from ai_helper import (
    init_bedrock_client,
    analyze_chart_style,
    process_nl_command,
    apply_updates,
)

# Import chart generator
from chart_builder import generate_chart_from_analysis

# Import chatbot
from chatbot import (
    init_chatbot_state,
    handle_user_message,
    get_current_mode,
    notify_mode_change,
)

# Page config
st.set_page_config(
    page_title="Chart Style Replicator",
    page_icon="📊",
    layout="wide"
)

# Initialize session state
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "csv_data": None,
        "reference_image": None,
        "styling_config": None,
        "chart_figure": None,
        "analysis_complete": False,
        "approved": False,
        "bedrock_client": None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()
init_chatbot_state()


# Initialize Bedrock client (cached)
if st.session_state.bedrock_client is None:
    try:
        st.session_state.bedrock_client = init_bedrock_client()
    except Exception as e:
        st.error(f"❌ Failed to initialize AWS Bedrock: {str(e)}")
        st.info("💡 Check your AWS credentials in .env file")
        st.stop()

# ─── Custom CSS for right panel styling ─────────────────────────────────────────
st.markdown("""
<style>
    /* Right chat panel styling */
    .chat-panel-header {
        background: linear-gradient(135deg, #2A6DB5, #5BA3E8);
        color: white;
        padding: 14px 18px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px rgba(42, 109, 181, 0.3);
    }
    .chat-panel-header h3 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
    }
    .chat-panel-header .mode-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
        margin-top: 4px;
        background: rgba(255,255,255,0.2);
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar for file uploads (left) ────────────────────────────────────────────
with st.sidebar:
    st.header("📁 Step 1: Upload Files")

    csv_file = st.file_uploader(
        "Upload CSV Data",
        type=["csv"],
        help="CSV with columns: date, key, value"
    )

    if csv_file:
        try:
            df = pd.read_csv(csv_file)
            required_cols = ['date', 'key', 'value']
            if not all(col in df.columns for col in required_cols):
                st.error(f"❌ CSV must have columns: {', '.join(required_cols)}")
            else:
                st.session_state.csv_data = df
                st.success(f"✅ {csv_file.name} ({len(df)} rows)")
        except Exception as e:
            st.error(f"❌ Error loading CSV: {str(e)}")

    image_file = st.file_uploader(
        "Upload Reference Chart",
        type=["png", "jpg", "jpeg"],
        help="Reference chart image to replicate styling"
    )

    if image_file:
        st.session_state.reference_image = image_file.read()
        st.success(f"✅ {image_file.name}")
        st.image(st.session_state.reference_image, caption="Reference", width=250)

    st.markdown("---")
    can_analyze = (
        st.session_state.csv_data is not None and
        st.session_state.reference_image is not None and
        not st.session_state.analysis_complete
    )

    if st.button("🔍 Analyze Style", disabled=not can_analyze, type="primary", use_container_width=True):
        with st.spinner("🤖 AI is analyzing the reference chart..."):
            try:
                config = analyze_chart_style(
                    st.session_state.bedrock_client,
                    st.session_state.reference_image
                )
                st.session_state.styling_config = config
                st.session_state.analysis_complete = True
                st.success("✅ Analysis complete!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Analysis failed: {str(e)}")


# ─── Two-column layout: Main content (left) + Chatbot (right) ───────────────────
main_col, chat_col = st.columns([7, 3])

# ─── LEFT COLUMN: Main App Content ──────────────────────────────────────────────
with main_col:
    st.title("📊 Chart Style Replicator")
    st.markdown("Upload your data and reference chart → AI extracts styling → Generate matching chart")

    if not st.session_state.analysis_complete:
        st.info("👈 Upload CSV and reference image, then click 'Analyze Style'")
        with st.expander("📋 CSV Format Example"):
            st.code("""date,key,value
2020-01-01,Headline,2.1
2020-01-01,Core,1.8
2020-02-01,Headline,2.3
2020-02-01,Core,1.9""")

    elif st.session_state.styling_config and not st.session_state.approved:
        st.header("🎨 Detected Chart Styling")
        st.markdown("Review the detected styling below. You can refine it using natural language.")

        config = st.session_state.styling_config

        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("📊 Chart Configuration")
            st.markdown(f"**Chart Type:** {config.get('chart_type', 'line').title()}")

            st.markdown("**Series:**")
            for i, series in enumerate(config.get('series', [])):
                color = series.get('color', '#000000')
                name = series.get('name', f'Series {i+1}')
                line_width = series.get('line_width', 2)
                line_style = series.get('line_style', 'solid')
                st.markdown(f"""
                {i+1}. **{name}**
                   - Color: <span style="background-color:{color}; padding:2px 10px; border-radius:3px; color:white;">{color}</span>
                   - Line: {line_style}, {line_width}px
                """, unsafe_allow_html=True)

            legend = config.get('legend_text', {})
            st.markdown(f"**Legend Position:** {legend.get('type', 'legend_box')}")

            y_axis = config.get('y_axis', {})
            st.markdown(f"**Y-Axis:** {y_axis.get('format', 'number')} format, suffix: '{y_axis.get('suffix', '')}'")

            x_axis = config.get('x_axis', {})
            st.markdown(f"**X-Axis:** {x_axis.get('tick_interval', 'monthly')} ticks")

            annotations = config.get('annotations', {})
            h_lines = annotations.get('horizontal_lines', [])
            if h_lines:
                st.markdown("**Horizontal Lines:**")
                for line in h_lines:
                    st.markdown(f"  - At {line.get('value')}: {line.get('style')} {line.get('color')}")

            data_table = config.get('data_table', {})
            if data_table.get('visible'):
                st.markdown(f"**Data Table:** {data_table.get('periods', 6)} periods, {data_table.get('position', 'below')}")

        with col2:
            with st.expander("🔧 Configuration JSON", expanded=False):
                st.json(config)

        st.markdown("---")
        st.subheader("✏️ Refine Styling (Natural Language)")

        col_input, col_button = st.columns([4, 1])
        with col_input:
            nl_command = st.text_input(
                "Tell me what to change:",
                placeholder="e.g., 'change headline color to darker blue'",
                key="nl_input"
            )
        with col_button:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Update", type="secondary", use_container_width=True):
                if nl_command:
                    with st.spinner("🤖 Processing your request..."):
                        try:
                            result = process_nl_command(
                                st.session_state.bedrock_client,
                                nl_command,
                                st.session_state.styling_config
                            )
                            if result.get('success'):
                                updated_config = apply_updates(
                                    st.session_state.styling_config,
                                    result.get('updates', {})
                                )
                                st.session_state.styling_config = updated_config
                                st.success(f"✅ {result.get('message', 'Updated!')}")
                                st.rerun()
                            else:
                                st.error(f"❌ {result.get('message', 'Failed to process command')}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

        st.markdown("---")
        if st.button("✅ Approve & Generate Chart", type="primary", use_container_width=True):
            st.session_state.approved = True
            st.rerun()

    # Generate and display chart
    elif st.session_state.approved and st.session_state.styling_config:
        st.header("📈 Generated Chart")

        if st.session_state.chart_figure is None:
            with st.spinner("🎨 Generating chart..."):
                try:
                    config = st.session_state.styling_config
                    df = st.session_state.csv_data
                    chart_json = generate_chart_from_analysis(config, df)
                    st.session_state.chart_figure = chart_json
                    notify_mode_change()
                except Exception as e:
                    st.error(f"❌ Chart generation failed: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

        if st.session_state.chart_figure:
            st_echarts(
                options=st.session_state.chart_figure,
                height="500px",
            )

            st.markdown("---")
            st.subheader("💾 Export")

            exp1, exp2, exp3 = st.columns(3)

            with exp1:
                html_template = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Chart</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
</head><body>
<div id="chart" style="width:100%;height:600px;"></div>
<script>
var chart = echarts.init(document.getElementById('chart'));
var option = {json.dumps(st.session_state.chart_figure)};
chart.setOption(option);
window.addEventListener('resize', function(){{ chart.resize(); }});
</script></body></html>"""
                st.download_button(
                    label="📥 Download HTML",
                    data=html_template,
                    file_name=f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                    mime="text/html",
                    use_container_width=True
                )

            with exp2:
                st.download_button(
                    label="📥 Download JSON",
                    data=json.dumps(st.session_state.chart_figure, indent=2),
                    file_name=f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

            with exp3:
                csv_export = st.session_state.csv_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv_export,
                    file_name=f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            st.markdown("---")
            if st.button("🔄 Start Over", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


# ─── RIGHT COLUMN: Always-visible Chatbot Panel ─────────────────────────────────
with chat_col:
    mode = get_current_mode()
    mode_label = "📘 Guide" if mode == "guide" else "📊 Analyst"

    st.markdown(
        '<div class="chat-panel-header">'
        '<h3>🤖 AI Assistant</h3>'
        '<span class="mode-badge">{mode}</span>'
        '</div>'.format(mode=mode_label),
        unsafe_allow_html=True
    )

    # Chat messages area
    chat_area = st.container(height=480)
    with chat_area:
        if not st.session_state.chat_history:
            if mode == "guide":
                st.info(
                    "👋 Hi! I'm your chart styling guide.\n\n"
                    "Ask me about:\n"
                    "- How to upload data\n"
                    "- CSV format requirements\n"
                    "- Configuring chart styles\n"
                    "- Generating your chart"
                )
            else:
                st.info(
                    "📊 Analyst mode active!\n\n"
                    "I can help with:\n"
                    "- Trend analysis\n"
                    "- Anomaly detection\n"
                    "- Executive summaries\n"
                    "- Data-driven insights"
                )

        for msg in st.session_state.chat_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                st.info(content)
            elif role == "user":
                with st.chat_message("user"):
                    st.markdown(content)
            elif role == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(content)

    # Chat input
    user_input = st.chat_input("Type your message...", key="chatbot_input")
    if user_input and user_input.strip():
        with st.spinner("🤖 Thinking..."):
            handle_user_message(user_input.strip())
        st.rerun()

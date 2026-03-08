"""
AI Chatbot Module for Chart Style Replicator
Handles chat state, mode detection, system prompts, message handling, and web search.
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict
import streamlit as st
import pandas as pd

from ai_helper import invoke_claude

# Web search keywords that trigger Tavily in Analyst Mode
SEARCH_KEYWORDS = [
    "why", "what happened", "what caused", "explain", "reason",
    "context", "news", "event", "policy", "fed ", "federal reserve",
    "inflation", "recession", "pandemic", "covid", "war", "crisis",
]
YEAR_PATTERN_KEYWORDS = ["in 20", "in 19", "during 20", "since 20", "after 20", "before 20"]


def init_chatbot_state() -> None:
    """Initialize chatbot-specific session state keys."""
    defaults = {
        "chat_history": [],
        "chat_open": False,
        "tavily_client": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Initialize Tavily client if API key is available
    if st.session_state.tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if api_key and api_key != "your_tavily_api_key_here":
            try:
                from tavily import TavilyClient
                st.session_state.tavily_client = TavilyClient(api_key=api_key)
            except Exception:
                st.session_state.tavily_client = None


def get_current_mode() -> str:
    """Return 'guide' or 'analyst' based on chart_figure state."""
    if st.session_state.get("chart_figure") is None:
        return "guide"
    return "analyst"


def build_system_prompt(web_search_results: Optional[str] = None) -> str:
    """Construct the system prompt based on current mode and app state."""
    mode = get_current_mode()

    if mode == "guide":
        return _build_guide_prompt()
    else:
        return _build_analyst_prompt(web_search_results)


def _build_guide_prompt() -> str:
    """Build system prompt for Guide Mode."""
    csv_uploaded = st.session_state.get("csv_data") is not None
    image_uploaded = st.session_state.get("reference_image") is not None
    analysis_done = st.session_state.get("analysis_complete", False)
    approved = st.session_state.get("approved", False)
    styling_config = st.session_state.get("styling_config")

    prompt = """You are a helpful chart styling guide assistant for the Chart Style Replicator tool.

Current application state:
- CSV data uploaded: {csv}
- Reference image uploaded: {img}
- Style analysis complete: {analysis}
- Chart approved: {approved}
""".format(
        csv="yes" if csv_uploaded else "no",
        img="yes" if image_uploaded else "no",
        analysis="yes" if analysis_done else "no",
        approved="yes" if approved else "no",
    )

    if styling_config:
        prompt += """
Current styling configuration:
{config}
""".format(config=json.dumps(styling_config, indent=2))

    prompt += """
Help the user navigate the tool workflow:
1. Upload CSV data (columns: date, key, value in long format)
2. Upload a reference chart image (PNG/JPG)
3. Click "Analyze Style" to extract styling from the reference
4. Review detected styling and refine with natural language commands
5. Click "Approve & Generate Chart" to produce the final chart

Only answer questions related to this tool and chart styling.
If asked about unrelated topics, politely redirect to tool usage."""

    return prompt


def _build_analyst_prompt(web_search_results: Optional[str] = None) -> str:
    """Build system prompt for Analyst Mode."""
    csv_data = st.session_state.get("csv_data")
    chart_json = st.session_state.get("chart_figure")
    styling_config = st.session_state.get("styling_config")

    # Data summary
    data_summary = "No data available."
    if csv_data is not None and isinstance(csv_data, pd.DataFrame):
        data_summary = "Dataset: {rows} rows, columns: {cols}\n\nData summary:\n{desc}".format(
            rows=len(csv_data),
            cols=", ".join(csv_data.columns.tolist()),
            desc=csv_data.describe().to_string(),
        )

    # Chart config summary (truncated to avoid token bloat)
    chart_summary = "No chart configuration available."
    if chart_json:
        try:
            summary = {k: v for k, v in chart_json.items() if k not in ("graphic", "series")}
            summary["series_count"] = len(chart_json.get("series", []))
            summary["series_names"] = [s.get("name", "?") for s in chart_json.get("series", [])]
            chart_summary = json.dumps(summary, indent=2, default=str)
        except Exception:
            chart_summary = str(chart_json)[:2000]

    prompt = """You are an economist-perspective data analyst assistant.

You have access to the following chart data:
{data_summary}

Chart configuration:
{chart_summary}
""".format(data_summary=data_summary, chart_summary=chart_summary)

    if styling_config:
        prompt += """
Styling configuration:
{config}
""".format(config=json.dumps(styling_config, indent=2, default=str)[:1500])

    if web_search_results:
        prompt += """
Additional web context:
{web}
""".format(web=web_search_results)

    prompt += """
Provide data-driven analysis including:
- Trend identification and interpretation
- Anomaly and outlier detection with possible explanations
- Contextual interpretation from an economist perspective
- When asked, generate executive summaries with key findings, inflection points, and data series interpretation

Be thorough, precise, and insightful. Use specific data points from the dataset to support your analysis."""

    return prompt


def build_messages() -> List[Dict]:
    """Convert chat_history to messages format for invoke_claude.
    
    Filters out system notification messages (role='system').
    Returns list of {"role": "user"|"assistant", "content": str}.
    """
    messages = []
    for msg in st.session_state.get("chat_history", []):
        if msg.get("role") in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def notify_mode_change() -> None:
    """Append a system notification when mode transitions to Analyst."""
    st.session_state.chat_history.append({
        "role": "system",
        "content": "📊 Mode changed to Analyst. I now have access to your chart data and can help with analysis, trends, anomalies, and executive summaries. Ask me anything about your data!",
        "timestamp": datetime.now().isoformat(),
    })


def _should_web_search(query: str) -> bool:
    """Check if query warrants a web search (Analyst Mode only)."""
    query_lower = query.lower()
    for kw in SEARCH_KEYWORDS:
        if kw in query_lower:
            return True
    for kw in YEAR_PATTERN_KEYWORDS:
        if kw in query_lower:
            return True
    return False


def perform_web_search(query: str) -> Optional[str]:
    """Execute a Tavily search and return formatted results.
    
    Returns None if client unavailable or search fails.
    """
    client = st.session_state.get("tavily_client")
    if client is None:
        return None
    try:
        results = client.search(query=query, max_results=3)
        if not results or not results.get("results"):
            return None
        formatted = []
        for r in results["results"]:
            formatted.append("- {title}\n  {content}\n  Source: {url}".format(
                title=r.get("title", ""),
                content=r.get("content", "")[:300],
                url=r.get("url", ""),
            ))
        return "\n\n".join(formatted)
    except Exception:
        return None


def handle_user_message(user_input: str) -> str:
    """Process a user message and return the assistant response."""
    # Append user message
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat(),
    })

    # Web search in Analyst Mode if keywords match
    web_results = None
    web_search_failed = False
    mode = get_current_mode()
    if mode == "analyst" and _should_web_search(user_input):
        web_results = perform_web_search(user_input)
        if web_results is None and st.session_state.get("tavily_client") is not None:
            web_search_failed = True

    # Build prompt and messages
    system_prompt = build_system_prompt(web_search_results=web_results)
    messages = build_messages()

    try:
        bedrock_client = st.session_state.get("bedrock_client")
        if bedrock_client is None:
            raise Exception("Bedrock client not initialized")

        response_text = invoke_claude(bedrock_client, messages, system_prompt)

        if web_search_failed:
            response_text += "\n\n_Note: Web search was unavailable for this response._"

    except Exception as e:
        response_text = "I'm having trouble connecting to the AI service. Please try again. (Error: {})".format(str(e))

    # Append assistant response
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response_text,
        "timestamp": datetime.now().isoformat(),
    })

    return response_text

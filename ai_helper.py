"""
AI Helper Module for Chart Style Replicator
Handles AWS Bedrock interactions for vision analysis and ECharts generation.
"""

import json
import os
import base64
import re
from typing import Optional, Dict, Any, List
import boto3
from botocore.exceptions import ClientError
import pandas as pd

# Model configuration
CLAUDE_MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
MAX_TOKENS = 4096
TEMPERATURE = 0.0

# Vision analysis prompt
VISION_ANALYSIS_PROMPT = """You are a chart styling expert with pixel-perfect precision. Analyze this reference chart image and extract EVERY visual detail.

Measure carefully:
- Font sizes in pixels (compare to chart dimensions)
- Line thicknesses in pixels
- Exact hex colors (use color picker precision)
- Spacing and positioning

Return ONLY valid JSON (no markdown, no explanation):

{
  "chart_type": "line",
  "series": [
    {
      "name": "Series Name",
      "color": "#hex",
      "line_width": 2.5,
      "line_style": "solid",
      "smooth": false,
      "label_placement": "above",
      "label_font_size": 14,
      "label_font_weight": "bold",
      "label_x_percent": 35
    }
  ],
  "legend_text": {
    "type": "inline_above",
    "font_size": 14,
    "font_weight": "bold",
    "font_color": "same_as_series"
  },
  "y_axis": {
    "format": "percentage",
    "suffix": "%",
    "decimal_places": 0,
    "min": 0,
    "max": 8,
    "interval": 1,
    "grid_lines": false,
    "grid_color": "#e0e0e0",
    "label_font_size": 13,
    "label_color": "#333333",
    "axis_line_show": false,
    "tick_show": false
  },
  "x_axis": {
    "format": "year",
    "tick_interval": "yearly",
    "grid_lines": false,
    "label_font_size": 13,
    "label_color": "#333333",
    "axis_line_color": "#333333",
    "axis_line_width": 1,
    "tick_show": false
  },
  "annotations": {
    "horizontal_lines": [
      {
        "value": 2.0,
        "color": "#000000",
        "style": "dashed",
        "width": 1.5,
        "label": "2%"
      }
    ],
    "vertical_bands": [
      {
        "year": "2020",
        "color": "rgba(200,200,200,0.4)",
        "width_months": 3
      }
    ]
  },
  "data_table": {
    "visible": true,
    "position": "bottom_right_inside",
    "font_size": 11,
    "font_family": "Arial",
    "header_font_weight": "bold",
    "header_color": "#333333",
    "value_font_weight": "bold",
    "value_color": "same_as_series",
    "border_color": "#999999",
    "border_width": 0.5,
    "background": "#ffffff"
  },
  "layout": {
    "background_color": "#ffffff",
    "font_family": "Arial, sans-serif",
    "grid_left": 55,
    "grid_right": 40,
    "grid_top": 25,
    "grid_bottom": 45
  }
}

CRITICAL RULES:
- label_placement: "above" = label ABOVE the line in middle of chart, "below" = BELOW the line, "end" = at right edge, "none" = no inline label
- For THIS chart type (financial line chart with inline labels), ALWAYS use "above" for the top series and "below" for the bottom series
- DO NOT use "inline_end" — use "above" or "below" instead
- label_x_percent: horizontal position as percentage of chart width (e.g. 35 = 35% from left)
- smooth: false = angular/straight line segments, true = curved/smooth
- For vertical_bands, specify the CENTER YEAR and approximate width in months
- Extract EXACT hex colors — be precise
- Measure font sizes relative to chart: axis labels are typically 12-14px, inline labels 13-16px
- line_width: measure carefully — thin=1.5, medium=2.5, thick=3.5
- horizontal_lines width: dashed reference lines are typically 1-1.5px
- Check if data table exists and extract its exact styling
- axis_line_show/tick_show: look carefully if axis lines and ticks are visible
"""


def init_bedrock_client():
    """Initialize AWS Bedrock Runtime client."""
    try:
        client = boto3.client(
            service_name='bedrock-runtime',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            aws_session_token=os.getenv('AWS_SESSION_TOKEN')
        )
        return client
    except Exception as e:
        raise Exception(f"Failed to initialize Bedrock client: {str(e)}")


def invoke_claude(client, messages: List[Dict], system_prompt: str = "") -> str:
    """Invoke Claude via Bedrock and return response text."""
    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "messages": messages
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        response = client.invoke_model(
            modelId=CLAUDE_MODEL_ID,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
        
    except ClientError as e:
        raise Exception(f"Bedrock API error: {str(e)}")
    except Exception as e:
        raise Exception(f"Error invoking Claude: {str(e)}")


def analyze_chart_style(client, image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyze reference chart image and extract styling parameters.
    
    Args:
        client: Bedrock client
        image_bytes: Image file bytes
        
    Returns:
        Dict with styling configuration
    """
    try:
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Determine image type
        if image_bytes[:4] == b'\x89PNG':
            media_type = "image/png"
        else:
            media_type = "image/jpeg"
        
        # Create message with image
        messages = [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": "Analyze this chart image and extract the styling parameters as specified."
                }
            ]
        }]
        
        # Invoke Claude with vision
        response_text = invoke_claude(client, messages, VISION_ANALYSIS_PROMPT)
        
        # Parse JSON response
        # Try to extract JSON from response (in case there's extra text)
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            config = json.loads(json_match.group(0))
        else:
            config = json.loads(response_text)
        
        return config
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"Vision analysis failed: {str(e)}")


def process_nl_command(client, command: str, current_config: Dict) -> Dict[str, Any]:
    """
    Process natural language command and return parameter updates.
    
    Args:
        client: Bedrock client
        command: User's natural language instruction
        current_config: Current styling configuration
        
    Returns:
        Dict with updates, success status, and message
    """
    try:
        nl_prompt = f"""You are a chart styling assistant. The user wants to modify the chart styling.

Current Configuration:
{json.dumps(current_config, indent=2)}

User Command: "{command}"

Interpret the command and return ONLY valid JSON with the updates to apply:

{{
  "updates": {{
    "path.to.parameter": new_value,
    ...
  }},
  "success": true,
  "message": "Explanation of what was changed"
}}

Examples:
- "change headline color to red" → {{"updates": {{"series.0.color": "#ff0000"}}, "success": true, "message": "Changed headline color to red"}}
- "move labels to line ends" → {{"updates": {{"legend_text.type": "inline_end"}}, "success": true, "message": "Moved labels to line ends"}}
- "add horizontal line at 3%" → {{"updates": {{"annotations.horizontal_lines": [...existing..., {{"value": 3.0, "color": "#000000", "style": "dashed", "width": 1.5, "label": "3%"}}]}}, "success": true, "message": "Added horizontal line at 3%"}}

Return ONLY the JSON, no explanation."""

        messages = [{
            "role": "user",
            "content": nl_prompt
        }]
        
        response_text = invoke_claude(client, messages)
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            result = json.loads(response_text)
        
        return result
        
    except json.JSONDecodeError as e:
        return {
            "updates": {},
            "success": False,
            "message": f"Failed to parse AI response: {str(e)}"
        }
    except Exception as e:
        return {
            "updates": {},
            "success": False,
            "message": f"Error processing command: {str(e)}"
        }


def apply_updates(config: Dict, updates: Dict) -> Dict:
    """
    Apply updates to configuration using dot-notation paths.
    
    Args:
        config: Current configuration
        updates: Dict with dot-notation paths as keys
        
    Returns:
        Updated configuration
    """
    import copy
    new_config = copy.deepcopy(config)
    
    for path, value in updates.items():
        parts = path.split('.')
        current = new_config
        
        # Navigate to the parent of the target
        for part in parts[:-1]:
            if part.isdigit():
                part = int(part)
            if isinstance(current, list):
                current = current[part]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # Set the value
        last_part = parts[-1]
        if last_part.isdigit():
            last_part = int(last_part)
        current[last_part] = value
    
    return new_config


def generate_echarts_json(analysis: Dict, csv_data: pd.DataFrame) -> Dict:
    """
    Generate ECharts option JSON from vision analysis and CSV data.
    
    Args:
        analysis: Vision analysis result
        csv_data: pandas DataFrame with CSV data
        
    Returns:
        ECharts option JSON
    """
    try:
        # Pivot data if in long format
        if 'key' in csv_data.columns and 'value' in csv_data.columns:
            csv_data = csv_data.pivot(index='date', columns='key', values='value').reset_index()
        
        # Get column names
        columns = list(csv_data.columns)
        if len(columns) < 2:
            raise ValueError("CSV must have at least 2 columns (x-axis + 1 series)")
        
        # First column is x-axis
        x_col = columns[0]
        x_data = csv_data[x_col].astype(str).tolist()
        
        # Get configuration from analysis
        chart_type = analysis.get('chart_type', 'line')
        series_configs = analysis.get('series', [])
        colors = analysis.get('colors', ['#1f77b4', '#ff7f0e', '#2ca02c'])
        y_axis_config = analysis.get('y_axis', {})
        annotations = analysis.get('annotations', {})
        legend_config = analysis.get('legend_text', {})
        
        # Build series
        series = []
        for i, col in enumerate(columns[1:]):
            if pd.api.types.is_numeric_dtype(csv_data[col]):
                # Get series config from analysis
                series_info = series_configs[i] if i < len(series_configs) else {}
                series_name = series_info.get('name', col)
                series_color = series_info.get('color', colors[i % len(colors)])
                line_width = series_info.get('line_width', 2)
                label_placement = series_info.get('label_placement', 'end')
                
                series_obj = {
                    "name": series_name,
                    "type": "line" if chart_type == "line" else "bar",
                    "data": csv_data[col].tolist(),
                    "itemStyle": {"color": series_color},
                    "lineStyle": {"width": line_width},
                    "smooth": True,
                    "smoothMonotone": "x"
                }
                
                # Add labels based on placement
                if label_placement == "end":
                    series_obj["endLabel"] = {
                        "show": True,
                        "formatter": "{a}",
                        "fontSize": 12,
                        "distance": 10
                    }
                elif label_placement in ["above", "below"]:
                    # Will be handled by render function with markPoint
                    series_obj["_label_placement"] = label_placement
                
                # Add markLine to first series for annotations
                if i == 0:
                    mark_data = []
                    
                    # Horizontal lines
                    for hline in annotations.get('horizontal_lines', []):
                        mark_data.append({
                            "yAxis": hline.get('value'),
                            "name": hline.get('label', ''),
                            "lineStyle": {
                                "color": hline.get('color', '#000000'),
                                "type": hline.get('style', 'dashed'),
                                "width": hline.get('width', 1.5)
                            },
                            "label": {
                                "show": bool(hline.get('label')),
                                "position": "end",
                                "formatter": "{b}"
                            }
                        })
                    
                    # Vertical lines
                    for vline in annotations.get('vertical_lines', []):
                        vline_value = vline.get('value')
                        
                        # If value is just a year like "2020", find matching date in x_data
                        if isinstance(vline_value, str) and len(vline_value) == 4 and vline_value.isdigit():
                            # Find first date in x_data that starts with this year
                            for x_val in x_data:
                                if str(x_val).startswith(vline_value):
                                    vline_value = x_val
                                    break
                        
                        mark_data.append({
                            "xAxis": vline_value,
                            "name": vline.get('label', ''),
                            "lineStyle": {
                                "color": vline.get('color', '#cccccc'),
                                "type": vline.get('style', 'solid'),
                                "width": vline.get('width', 1)
                            },
                            "label": {
                                "show": bool(vline.get('label')),
                                "position": "end",
                                "formatter": "{b}"
                            }
                        })
                    
                    if mark_data:
                        series_obj["markLine"] = {
                            "silent": True,
                            "data": mark_data
                        }
                
                series.append(series_obj)
        
        # Build Y-axis config
        y_axis = {
            "type": "value",
            "axisLabel": {"fontSize": 11}
        }
        
        if y_axis_config.get('format') == 'percentage':
            y_axis["axisLabel"]["formatter"] = "{value}%"
        elif y_axis_config.get('suffix'):
            suffix = y_axis_config['suffix']
            y_axis["axisLabel"]["formatter"] = f"{{value}}{suffix}"
        
        if y_axis_config.get('grid_lines'):
            y_axis["splitLine"] = {
                "show": True,
                "lineStyle": {"color": y_axis_config.get('grid_color', '#e0e0e0')}
            }
        
        # Determine if we need extra right margin for endLabels
        legend_type = legend_config.get('type', 'inline_end')
        use_inline_labels = legend_type in ['inline_end', 'inline_above', 'inline_below']
        
        # Build chart
        chart = {
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "line"}
            },
            "toolbox": {
                "feature": {
                    "saveAsImage": {"title": "Save as PNG"}
                }
            },
            "xAxis": {
                "type": "category",
                "data": x_data,
                "boundaryGap": False,
                "axisLabel": {"fontSize": 11}
            },
            "yAxis": y_axis,
            "series": series,
            "grid": {
                "left": "8%",
                "right": "25%" if use_inline_labels else "8%",
                "top": "8%",
                "bottom": "8%",
                "containLabel": True
            }
        }
        
        # Store analysis for later use (data table, label placement)
        chart["_analysis"] = analysis
        
        return chart
        
    except Exception as e:
        raise Exception(f"Failed to generate ECharts JSON: {str(e)}")

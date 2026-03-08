# Chart Style Replicator

Upload a CSV + a reference chart image → AI extracts the exact styling → generates a matching ECharts chart.

Built for teams that need charts to follow a company standard without manual formatting.

## How It Works

1. Upload your data (CSV) and a reference chart (PNG/JPG)
2. AI (Claude 3.5 Sonnet v2 via AWS Bedrock) analyzes the reference image and extracts every visual detail — colors, line widths, font sizes, axis styling, annotations, data table layout
3. Review the detected styling, refine with natural language if needed
4. Generate the chart — all styling comes from the AI analysis, nothing hardcoded
5. Export as HTML, JSON, or CSV

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access (Claude 3.5 Sonnet v2 enabled in us-east-1)

## Installation

```bash
# Clone the repo
git clone <your-repo-url>
cd chart-style-replicator

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env` and fill in your AWS credentials:

```bash
cp .env .env.local   # or just edit .env directly
```

```env
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_SESSION_TOKEN=your_session_token
AWS_REGION=us-east-1
```

If using temporary credentials (SSO/assume-role), include the session token. For long-term IAM keys, you can omit it.

## Run

```bash
streamlit run app.py
```

Opens at http://localhost:8501

## CSV Format

Long format with columns: `date`, `key`, `value`

```csv
date,key,value
2020-01-01,Headline,2.1
2020-01-01,Core,1.8
2020-02-01,Headline,2.3
2020-02-01,Core,1.9
```

The app pivots this automatically. Series names in the `key` column are matched to the AI-detected series names.

## Natural Language Editing

After the AI analyzes your reference, you can refine before generating:

- "change headline color to #305c86"
- "make lines thicker"
- "move labels above the lines"
- "add horizontal line at 3%"

## Project Structure

```
app.py            Streamlit UI — upload, preview, generate, export
ai_helper.py      AWS Bedrock vision analysis + NL editing
chart_builder.py  ECharts JSON builder (uses AI-extracted values)
.env              AWS credentials (not committed)
requirements.txt  Python dependencies
mydata/           Sample test data
```

## What the AI Extracts

- Series colors, line widths, line styles, smoothing
- Inline label positions, font sizes, font weights
- X/Y axis: font sizes, colors, line visibility, tick visibility, grid lines
- Annotations: horizontal dashed lines, vertical shaded bands
- Data table: position, font, colors, border styling
- Layout: background color, font family, grid margins

## Troubleshooting

**"Failed to initialize AWS Bedrock"**
Check `.env` credentials and that Bedrock + Claude 3.5 Sonnet v2 are enabled in your region.

**"Analysis failed"**
Make sure the reference image is a clear, readable chart in PNG or JPG format.

**"Chart generation failed"**
Verify CSV has `date`, `key`, `value` columns with parseable dates and numeric values.

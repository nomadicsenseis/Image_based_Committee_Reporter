# Dashboard Image Analyzer

This tool automatically analyzes dashboard images using the Claude 3 Sonnet model via Amazon Bedrock and generates comprehensive reports in Markdown format.

## Prerequisites

1. AWS credentials with access to Amazon Bedrock
2. Python 3.6+
3. Required Python packages:
   - boto3
   - dotenv

## Setup

1. The tool will automatically use AWS credentials from the `.devcontainer/.env` file if available. If not, it will create a sample `.env` file for you to edit:
   ```
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_REGION=us-east-1
   MODEL_ARN=anthropic.claude-3-sonnet-20240229-v1:0
   ```

2. Create an `img` folder in the project root to store your dashboard images:
   ```
   mkdir -p img
   ```

3. Upload your dashboard images to the `img` directory before analysis.

4. Install required dependencies:
   ```
   pip install boto3 python-dotenv
   ```

## Image Naming Convention

For best results when using automatic image discovery, use a consistent naming convention that includes the date or period:

```
dashboard_January_2024.jpg
revenue_Q1_2024.png
customer_satisfaction_2024-03.jpg
```

## Usage

### Basic Usage

Analyze specific images:
```
python dashboard_analyzer.py --images img/dashboard1.jpg img/dashboard2.jpg --date "January 2024"
```

Analyze all images in the `img` folder:
```
python dashboard_analyzer.py --folder --date "Q1 2024"
```

### Command Line Arguments

- `--images`: One or more paths to dashboard image files
- `--folder`: Use all images in the img folder
- `--date`: Date or period for the dashboard (e.g., "January 2024" or "Q1 2024")
- `--debug`: Enable debug mode for verbose output

### Examples

Analyze a specific dashboard image:
```
python dashboard_analyzer.py --images img/revenue_dashboard.jpg --date "March 2024"
```

Analyze all images for a specific period:
```
python dashboard_analyzer.py --folder --date "Q1 2024"
```

## Output

The tool generates a comprehensive report with the following sections:

1. Executive Summary
2. Key Metrics
3. Trend Analysis
4. Areas of Concern
5. Recommendations

The report is saved to the `reports` folder with a filename based on the date:
```
reports/dashboard_report_March_2024.md
reports/dashboard_report_Q1_2024.md
```

## Prompt Customization

You can customize the analysis prompt by modifying the `get_prompt_template()` method in the script. The prompt includes:

- Instructions for analysis
- Example reports to guide the model
- Specific instructions for the current task

## Docker Support

A Dockerfile is included to containerize the tool:

```
# Build the Docker image
docker build -f dashboard_analyzer_dockerfile -t dashboard-analyzer .

# Run the container
docker run --rm -v "$(pwd)/img:/app/img" -v "$(pwd)/reports:/app/reports" dashboard-analyzer
```

You can also use the included build_and_run.sh script for an interactive setup and execution.

## Troubleshooting

1. **Authentication Errors**: Ensure your AWS credentials in the `.env` file are correct and have appropriate permissions.

2. **Image Encoding Errors**: Make sure your image files are valid and in a supported format (JPEG, PNG, GIF).

3. **Model Invocation Errors**: Check if you're using the correct model ARN and have access to it.

4. **No Images Found**: When using `--folder`, check that your images are in the `img` directory and follow the naming convention if filtering by date. 
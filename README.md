# NPS Copilot

This repository contains tools for analyzing customer satisfaction and Net Promoter Score (NPS) data.

## Projects

### 1. NPS Core Analysis System

The main application in the `src` directory provides tools for querying and analyzing NPS data from Redshift using Amazon Bedrock's Claude model.

### 2. Dashboard Image Analyzer

Located in the `dashboard_analyzer` directory, this tool uses Amazon Bedrock's Claude 3 Sonnet model to analyze dashboard images and generate comprehensive reports.

To use the Dashboard Image Analyzer:

1. Navigate to the `dashboard_analyzer` directory
2. Upload your dashboard images to the `img` folder
3. Run the setup script: `./build_and_run.sh`
4. Configure AWS credentials when prompted
5. Choose from the available options to analyze your images

For more details, see the [Dashboard Analyzer README](dashboard_analyzer/dashboard_analyzer_readme.md).

A tool for analyzing dashboard images and generating reports using Amazon Bedrock's Claude 3 Sonnet model.

## Features

- Analyzes dashboard images to extract key metrics and insights
- Generates concise committee reports based on the analysis
- Supports both single image and folder-based analysis
- Uses context images for better report formatting and style
- Saves reports in date-specific subfolders

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your AWS credentials and Bedrock model ARN
```

## Usage

### Command Line

```bash
# Analyze a single image
python dashboard_report_generator.py --images img/example.png --date 2024-03-30

# Analyze all images in a folder
python dashboard_report_generator.py --folder --date 2024-03-30

# Use context images from a specific date
python dashboard_report_generator.py --date 2024-03-30 --context-date 2024-04-07
```

### Docker

```bash
# Build and run with default settings
./build_and_run.sh

# Analyze specific images
./build_and_run.sh --date 2024-03-30 --images img/example1.png img/example2.png
```

## Report Format

Reports are generated in Markdown format and include:
- Executive summary
- Key performance indicators
- Significant trends and insights
- Recommendations and conclusions

Reports are saved in the `reports` directory, organized by date.

## Testing

Run the test suite:
```bash
python test_dashboard_analyzer.py
```

## License

MIT 
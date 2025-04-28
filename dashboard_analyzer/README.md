# Dashboard Report Generator

A tool that analyzes dashboard images using AWS Bedrock Claude 3 to generate insightful airline committee reports.

## Features

- Analyzes dashboard images to extract key performance indicators (KPIs)
- Identifies trends and patterns in operational, customer, disruption, and commercial data
- Generates structured, insightful reports suitable for committee meetings
- Automatically compresses large images for optimal processing
- Saves reports in Markdown format for easy sharing and viewing
- Supports date-based organization of dashboard images
- Learns from existing reports by using them as examples in the prompt
- Uses date-specific context images for consistent analysis
- Integrates with Microsoft Teams to share reports directly in channels or chats

## Directory Structure

- `img/context/` - Contains example images used as context for the model
  - Context images should be named with a date suffix (e.g., `operations_07042025.png`)
- `img/inference/` - Contains images to be analyzed for report generation
  - `img/inference/YYYY-MM-DD/` - Date-based subfolders for organizing dashboard images
- `reports/` - Where generated reports are stored
  - `reports/YYYY-MM-DD/` - Date-based organization of generated reports
  - Reports in these folders can be used as examples for future report generation

## Requirements

- Python 3.8+
- AWS credentials with Bedrock access
- Microsoft Graph API credentials (for Teams integration)
- Required packages: boto3, python-dotenv, Pillow, requests

## Setup

1. Ensure AWS credentials are configured in the `.env` file in the `.devcontainer` folder:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-1
MODEL_ARN=anthropic.claude-3-sonnet-20240229-v1:0
```

2. For Microsoft Teams integration, add the following to your `.env` file:

```
# Microsoft Graph API credentials
MS_TENANT_ID=your_tenant_id
MS_CLIENT_ID=your_client_id
MS_CLIENT_SECRET=your_client_secret

# Teams target (use one of these)
MS_TEAMS_CHANNEL_ID=team_id/channel_id
MS_TEAMS_CHAT_ID=chat_id
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Place context/example images in the `img/context` directory
   - Name context images with a date suffix (e.g., `operations_07042025.png`)
   - Different date suffixes can be used for different reference periods
5. Place dashboard images to be analyzed in the `img/inference` directory
   - For date-based organization, create subfolders with date names (e.g., `2025-04-07`)
   - Place the 4 images for each report (operations, customer, disruptions, commercial) in the appropriate date folder
6. Sample reports should be saved in date folders in the `reports` directory
   - These reports will be used as examples for future reports
   - For example: `reports/07-03-2025/airline_committee_report.md`

## Usage

### Basic Usage

Analyze all images in the `img/inference` directory:

```bash
python dashboard_report_generator.py --all-inference
```

Analyze specific images:

```bash
python dashboard_report_generator.py --images img/inference/operations_dashboard.png img/inference/customer_dashboard.jpg
```

### Date-Based Organization

Analyze all images in a specific date folder:

```bash
python dashboard_report_generator.py --date 2025-04-07
```

This will:
- Process all images in the `img/inference/2025-04-07/` folder
- Include the date in the default query
- Name the output file with the date included
- Save the report in `reports/2025-04-07/` folder

### Context Control

Specify which date's context images to use:

```bash
python dashboard_report_generator.py --date 2025-04-07 --context-date 07042025
```

This will:
- Use images from `img/context/` that match the specified date pattern (e.g., `*_07042025.png`)
- Include example reports from the `reports/` directory as part of the system prompt
- Process the input images from the specified date folder

### Microsoft Teams Integration

Send the generated report to Teams after creation:

```bash
python dashboard_report_generator.py --date 2025-04-07 --teams
```

Specify a specific Teams channel or chat:

```bash
python dashboard_report_generator.py --date 2025-04-07 --teams --teams-channel team_id/channel_id
```

```bash
python dashboard_report_generator.py --date 2025-04-07 --teams --teams-chat chat_id
```

### Advanced Options

Add a custom query to guide the analysis:

```bash
python dashboard_report_generator.py --date 2025-04-07 --query "Create a report focusing on the trends in NPS scores and their relationship to operational metrics for April 7th, 2025."
```

Specify an output filename for the report:

```bash
python dashboard_report_generator.py --date 2025-04-07 --output quarterly_report_q2_2025.md
```

### Legacy Support

You can still use the `--all` flag to analyze all images in the main `img` directory, but this approach is deprecated:

```bash
python dashboard_report_generator.py --all
```

## Output

Reports are saved in Markdown format in the `reports` directory. The filename will be auto-generated based on the current timestamp and date (if using date-based organization) unless specified with the `--output` option.

## Example Report Structure

The generated reports follow this structure:

- **Operations**: Analysis of operational metrics like punctuality and flight performance
- **Customer**: Analysis of NPS scores and customer experience metrics
- **Disruptions**: Analysis of cancellations, mishandlings, and other disruption data
- **Commercial**: Analysis of commercial performance metrics

Each section includes trends, relationships between KPIs, and potential future impacts.

## Learning From Previous Reports

The system is designed to learn from previous reports:

1. When you generate a report, it's saved in `reports/YYYY-MM-DD/`
2. Future report generation will automatically use these existing reports as examples
3. This creates a continuous learning loop, where each new report benefits from the quality and structure of previous reports

This approach helps maintain consistency in reporting style while allowing for improvements over time.

## Microsoft Teams Integration

The report is sent to Microsoft Teams as an HTML message with the following format:
- A heading with the report date (extracted from the folder structure)
- The full report content as a preformatted text block

You can either configure default Teams targets in the `.env` file or specify them as command line arguments. 
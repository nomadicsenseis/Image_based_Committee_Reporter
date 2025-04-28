#!/bin/bash

# Build and run the Dashboard Analyzer Docker container

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Set the script directory as the working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
echo -e "${GREEN}Working in directory: $SCRIPT_DIR${NC}"

# Step 1: Create or copy .env file
echo -e "${YELLOW}Checking for .env file...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}No .env file found in current directory.${NC}"
    echo -e "${YELLOW}Attempting to use credentials from .devcontainer folder...${NC}"
    python create_env_file.py
    
    if [ ! -f .env ]; then
        echo -e "${RED}Failed to create .env file. Please create it manually.${NC}"
        exit 1
    fi
    
    if [ -f "../.devcontainer/.env" ]; then
        echo -e "${GREEN}Successfully copied credentials from .devcontainer folder.${NC}"
    else
        echo -e "${YELLOW}Created a sample .env file.${NC}"
        echo -e "${YELLOW}Please edit the .env file with your AWS credentials before continuing.${NC}"
        echo -e "${YELLOW}Press Enter to continue or Ctrl+C to exit...${NC}"
        read
    fi
else
    echo -e "${GREEN}Found existing .env file.${NC}"
fi

# Step 2: Check if the img directory exists
echo -e "${YELLOW}Checking for img directory...${NC}"
if [ ! -d img ]; then
    echo -e "${YELLOW}Creating img directory...${NC}"
    mkdir -p img/context img/inference
    echo -e "${GREEN}Created img directory structure.${NC}"
    echo -e "${YELLOW}Please upload your dashboard images to the appropriate date folders in img/context and img/inference.${NC}"
else
    echo -e "${GREEN}Found img directory.${NC}"
    # Ensure subdirectories exist
    mkdir -p img/context img/inference
fi

# Step 3: Check if there are any images in the img directory
IMG_COUNT=$(find img -type f -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" | wc -l)
if [ "$IMG_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}No images found in img directory.${NC}"
    echo -e "${YELLOW}Please upload your dashboard images to the appropriate date folders in img/context and img/inference.${NC}"
    echo -e "${YELLOW}Press Enter when you've uploaded your images or Ctrl+C to exit...${NC}"
    read
    
    # Check again after user acknowledgment
    IMG_COUNT=$(find img -type f -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" | wc -l)
    if [ "$IMG_COUNT" -eq 0 ]; then
        echo -e "${RED}Still no images found. Exiting.${NC}"
        exit 1
    else
        echo -e "${GREEN}Found $IMG_COUNT images in img directory.${NC}"
    fi
else
    echo -e "${GREEN}Found $IMG_COUNT images in img directory.${NC}"
fi

# Step 4: Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f dashboard_analyzer_dockerfile -t dashboard-analyzer .

if [ $? -ne 0 ]; then
    echo -e "${RED}Docker build failed.${NC}"
    exit 1
else
    echo -e "${GREEN}Docker image built successfully.${NC}"
fi

# Step 5: Ask for run options
echo -e "${YELLOW}Run options:${NC}"
echo "1) Run tests only"
echo "2) Analyze all images in img directory"
echo "3) Analyze specific images"
echo "4) Exit"
read -p "Choose an option (1-4): " OPTION

case $OPTION in
    1)
        echo -e "${YELLOW}Running tests...${NC}"
        docker run --rm -v "$SCRIPT_DIR/img:/app/img" -v "$SCRIPT_DIR/reports:/app/reports" dashboard-analyzer python test_dashboard_analyzer.py
        ;;
    2)
        echo -e "${YELLOW}Analyzing all images...${NC}"
        read -p "Enter date (format: DD-MM-YYYY): " DATE
        read -p "Enter context date (format: DD-MM-YYYY): " CONTEXT_DATE
        docker run --rm -v "$SCRIPT_DIR/img:/app/img" -v "$SCRIPT_DIR/reports:/app/reports" dashboard-analyzer python dashboard_report_generator.py --date "$DATE" --context-date "$CONTEXT_DATE" --save-report
        ;;
    3)
        echo -e "${YELLOW}Available images:${NC}"
        find "$SCRIPT_DIR/img" -type f -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif"
        echo
        read -p "Enter image filenames (space-separated): " IMAGES
        read -p "Enter date (format: DD-MM-YYYY): " DATE
        read -p "Enter context date (format: DD-MM-YYYY): " CONTEXT_DATE
        
        # Convert space-separated list to Docker-friendly format
        IMG_ARGS=""
        for IMG in $IMAGES; do
            IMG_ARGS="$IMG_ARGS --image-file /app/img/$IMG"
        done
        
        docker run --rm -v "$SCRIPT_DIR/img:/app/img" -v "$SCRIPT_DIR/reports:/app/reports" dashboard-analyzer python dashboard_report_generator.py $IMG_ARGS --date "$DATE" --context-date "$CONTEXT_DATE" --save-report
        ;;
    4)
        echo -e "${YELLOW}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option.${NC}"
        exit 1
        ;;
esac

# Step 6: Show reports if they exist
if [ -d "$SCRIPT_DIR/reports" ] && [ "$(ls -A "$SCRIPT_DIR/reports")" ]; then
    echo -e "${GREEN}Reports generated:${NC}"
    ls -1 "$SCRIPT_DIR/reports/"
    
    # Ask if user wants to open the latest report
    LATEST_REPORT=$(ls -t "$SCRIPT_DIR/reports/" | head -1)
    if [ -n "$LATEST_REPORT" ]; then
        read -p "Open the latest report (${LATEST_REPORT})? (y/n): " OPEN_REPORT
        if [[ $OPEN_REPORT =~ ^[Yy]$ ]]; then
            # Try to open with common tools depending on OS
            if command -v xdg-open &> /dev/null; then
                xdg-open "$SCRIPT_DIR/reports/$LATEST_REPORT"
            elif command -v open &> /dev/null; then
                open "$SCRIPT_DIR/reports/$LATEST_REPORT"
            elif command -v start &> /dev/null; then
                start "$SCRIPT_DIR/reports/$LATEST_REPORT"
            else
                echo -e "${YELLOW}Couldn't automatically open the report.${NC}"
                echo -e "${YELLOW}Please open manually: $SCRIPT_DIR/reports/$LATEST_REPORT${NC}"
            fi
        fi
    fi
else
    echo -e "${YELLOW}No reports generated yet.${NC}"
fi

echo -e "${GREEN}Done!${NC}" 
#!/usr/bin/env python
import os
import argparse
from dotenv import load_dotenv
from dashboard_report_generator import DashboardReportGenerator

# Get the directory of the current file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the workspace root directory (parent of current directory)
WORKSPACE_ROOT = os.path.dirname(SCRIPT_DIR)
# Path to the .env file in the .devcontainer folder
DEVCONTAINER_ENV_PATH = os.path.join(WORKSPACE_ROOT, '.devcontainer', '.env')

def test_env_variables():
    """Test if all required environment variables are set"""
    # Load .env directly from .devcontainer folder
    if os.path.exists(DEVCONTAINER_ENV_PATH):
        load_dotenv(DEVCONTAINER_ENV_PATH)
        print(f"✅ Loaded environment variables from {DEVCONTAINER_ENV_PATH}")
    else:
        print(f"❌ No .env file found in .devcontainer folder at {DEVCONTAINER_ENV_PATH}")
        return False
    
    # Check for AWS credentials
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("❌ Missing AWS_ACCESS_KEY_ID environment variable")
        return False
    
    if not os.getenv('AWS_SECRET_ACCESS_KEY'):
        print("❌ Missing AWS_SECRET_ACCESS_KEY environment variable")
        return False
    
    # Check for AWS region - support both AWS_REGION and AWS_DEFAULT_REGION
    if os.getenv('AWS_REGION'):
        aws_region = os.getenv('AWS_REGION')
    elif os.getenv('AWS_DEFAULT_REGION'):
        aws_region = os.getenv('AWS_DEFAULT_REGION')
        # Set AWS_REGION to match AWS_DEFAULT_REGION for compatibility
        os.environ['AWS_REGION'] = aws_region
        print(f"✅ Using AWS_DEFAULT_REGION ({aws_region}) as AWS_REGION")
    else:
        print("❌ Missing AWS_REGION or AWS_DEFAULT_REGION environment variable")
        return False
    
    print("✅ All required environment variables are set")
    
    # Check MODEL_ARN (optional but recommended)
    if os.getenv('MODEL_ARN'):
        print(f"✅ MODEL_ARN is set: {os.getenv('MODEL_ARN')}")
    else:
        print("⚠️ MODEL_ARN is not set, will use default")
    
    return True

def test_directories():
    """Test if required directories exist"""
    # Check img directory
    img_dir = os.path.join(SCRIPT_DIR, 'img')
    if not os.path.exists(img_dir):
        print(f"❌ '{img_dir}' directory does not exist")
        try:
            os.makedirs(img_dir)
            print(f"✅ Created '{img_dir}' directory")
        except Exception as e:
            print(f"❌ Failed to create '{img_dir}' directory: {str(e)}")
            return False
    else:
        print(f"✅ '{img_dir}' directory exists")
    
    # Check if img directory has any images
    image_files = [f for f in os.listdir(img_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if not image_files:
        print("⚠️ No image files found in 'img' directory")
    else:
        print(f"✅ Found {len(image_files)} image files in 'img' directory")
    
    # Check reports directory (should be created by the analyzer)
    reports_dir = os.path.join(SCRIPT_DIR, 'reports')
    if not os.path.exists(reports_dir):
        print("⚠️ 'reports' directory does not exist yet (will be created when running the analyzer)")
    else:
        print(f"✅ '{reports_dir}' directory exists")
    
    return True

def test_bedrock_connection():
    """Test connection to Bedrock"""
    try:
        analyzer = DashboardReportGenerator(debug_mode=True)
        if analyzer.client:
            print("✅ Successfully connected to Bedrock")
            return True
        else:
            print("❌ Failed to connect to Bedrock")
            return False
    except Exception as e:
        print(f"❌ Error initializing DashboardReportGenerator: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test Dashboard Image Analyzer')
    parser.add_argument('--full', action='store_true', help='Run a full test with a sample image')
    args = parser.parse_args()
    
    print("=" * 50)
    print("🧪 Testing Dashboard Image Analyzer")
    print("=" * 50)
    
    # Test environment variables
    env_result = test_env_variables()
    
    # Test directories
    dir_result = test_directories()
    
    # Test Bedrock connection
    connection_result = test_bedrock_connection()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary")
    print("=" * 50)
    print(f"Environment Variables: {'✅ PASS' if env_result else '❌ FAIL'}")
    print(f"Directories: {'✅ PASS' if dir_result else '❌ FAIL'}")
    print(f"Bedrock Connection: {'✅ PASS' if connection_result else '❌ FAIL'}")
    
    # If all tests passed and --full is specified, run a full test
    if env_result and dir_result and connection_result and args.full:
        print("\n" + "=" * 50)
        print("🧪 Running Full Test")
        print("=" * 50)
        
        # Check if there are any images to test with
        img_dir = os.path.join(SCRIPT_DIR, 'img')
        image_files = [os.path.join(img_dir, f) for f in os.listdir(img_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        
        if not image_files:
            print("❌ No images available for testing")
            print(f"Please add at least one image to the '{img_dir}' directory and run again with --full")
            return
        
        # Use the first image for testing
        test_image = image_files[0]
        print(f"Using image for test: {test_image}")
        
        # Initialize analyzer
        analyzer = DashboardReportGenerator(debug_mode=True)
        
        # Run the analysis on a single test image
        print("Running test analysis...")
        report = analyzer.analyze_dashboard_images([test_image], "Test Period")
        
        if report and len(report) > 100:  # Simple check that we got some content
            print("✅ Test analysis successful")
            
            # Save test report
            report_path = analyzer.save_report(report, "TEST_RUN")
            if report_path:
                print(f"✅ Test report saved to: {report_path}")
                print("Test completed successfully!")
            else:
                print("❌ Failed to save test report")
        else:
            print("❌ Test analysis failed or returned empty result")
    
    # Overall result
    if env_result and dir_result and connection_result:
        print("\n✅ All basic tests PASSED")
        if not args.full:
            print("Run with --full to perform a complete test with image analysis")
    else:
        print("\n❌ Some tests FAILED - please fix the issues before using the tool")

if __name__ == "__main__":
    main() 
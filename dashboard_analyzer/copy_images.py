#!/usr/bin/env python
"""
Script to copy dashboard images from a source directory to the dashboard_analyzer/img folder
"""
import os
import sys
import shutil
import argparse

# Get the directory of the current file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(SCRIPT_DIR, "img")

def ensure_img_dir():
    """Make sure the img directory exists"""
    if not os.path.exists(IMG_DIR):
        try:
            os.makedirs(IMG_DIR)
            print(f"✅ Created directory: {IMG_DIR}")
        except Exception as e:
            print(f"❌ Error creating directory {IMG_DIR}: {e}")
            return False
    return True

def copy_images(source_dir, file_types=None):
    """
    Copy images from source_dir to IMG_DIR
    
    Args:
        source_dir (str): Path to the source directory containing images
        file_types (list): List of file extensions to copy (default: ['.png', '.jpg', '.jpeg'])
    
    Returns:
        bool: True if images were copied successfully, False otherwise
    """
    if not file_types:
        file_types = ['.png', '.jpg', '.jpeg']
    
    # Validate source directory
    if not os.path.exists(source_dir):
        print(f"❌ Source directory doesn't exist: {source_dir}")
        return False
    
    # Make sure the img directory exists
    if not ensure_img_dir():
        return False
    
    # Count files copied
    copied_count = 0
    
    try:
        # Loop through files in source directory
        for filename in os.listdir(source_dir):
            _, ext = os.path.splitext(filename.lower())
            
            # Check if file has the right extension
            if ext in file_types:
                source_path = os.path.join(source_dir, filename)
                dest_path = os.path.join(IMG_DIR, filename)
                
                # Copy the file
                shutil.copy2(source_path, dest_path)
                copied_count += 1
                print(f"✅ Copied {filename} to {IMG_DIR}")
        
        if copied_count == 0:
            print(f"⚠️ No image files found in {source_dir}")
            return False
        
        print(f"✅ Successfully copied {copied_count} image(s) to {IMG_DIR}")
        return True
    
    except Exception as e:
        print(f"❌ Error copying images: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Copy dashboard images to the img folder")
    parser.add_argument("source_dir", help="Path to the source directory containing the images")
    parser.add_argument("--types", help="Comma-separated list of file extensions to copy (default: png,jpg,jpeg)",
                        default="png,jpg,jpeg")
    
    args = parser.parse_args()
    
    # Parse file types
    file_types = [f".{ext.strip().lower()}" for ext in args.types.split(',')]
    
    # Copy images
    success = copy_images(args.source_dir, file_types)
    
    # Return appropriate exit code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 
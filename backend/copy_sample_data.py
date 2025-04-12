import os
import shutil
import sys

def copy_sample_data():
    """
    Copy the sample MCP server data to the project data directory.
    """
    source_path = os.path.expanduser("~/attachments/c1f38ac2-0feb-4f27-aea3-b1e9e5699b8e/mcp_chunk_1.json")
    
    dest_dir = os.path.expanduser("~/mcp-analysis-system/data/raw")
    
    dest_path = os.path.join(dest_dir, "mcp_chunk_1.json")
    
    if not os.path.exists(source_path):
        print(f"Error: Source file not found at {source_path}")
        return False
    
    os.makedirs(dest_dir, exist_ok=True)
    
    try:
        shutil.copy2(source_path, dest_path)
        print(f"Successfully copied sample data to {dest_path}")
        return True
    except Exception as e:
        print(f"Error copying file: {str(e)}")
        return False

if __name__ == "__main__":
    success = copy_sample_data()
    sys.exit(0 if success else 1)

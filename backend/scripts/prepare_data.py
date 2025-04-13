import json
import os
import sys
from pathlib import Path

def prepare_data():
    """
    Copy the sample MCP server data to create a larger dataset for testing.
    This simulates having the full dataset by duplicating and modifying the sample data.
    """
    base_path = Path(__file__).parent.parent
    source_path = os.path.expanduser("~/attachments/c1f38ac2-0feb-4f27-aea3-b1e9e5699b8e/mcp_chunk_1.json")
    dest_path = base_path / "data" / "mcp_with_detailed_content.json"
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
    except Exception as e:
        print(f"Error loading sample data: {str(e)}")
        return False
    
    print(f"Loaded {len(sample_data)} sample servers")
    
    full_data = []
    
    full_data.extend(sample_data)
    
    entity_variations = {
        "Github": ["Github Server", "Github MCP", "Github Helper", "Github Tools"],
        "Amap Maps": ["Amap Server", "Amap MCP", "Amap Helper", "Amap Navigation"],
        "Playwright Mcp": ["Playwright Server", "Playwright Testing", "Playwright Helper"],
        "Binance": ["Binance Server", "Binance MCP", "Binance Helper", "Binance Trading"],
        "OpenAI": ["OpenAI Server", "OpenAI MCP", "OpenAI Helper", "OpenAI Tools"],
        "Google": ["Google Server", "Google MCP", "Google Helper", "Google Search"],
        "AWS": ["AWS Server", "AWS MCP", "AWS Helper", "AWS Cloud"],
        "Azure": ["Azure Server", "Azure MCP", "Azure Helper", "Azure Cloud"],
    }
    
    next_id = max([int(server["id"].split("-")[1]) for server in sample_data]) + 1
    page_counter = 2
    
    for base_name, variations in entity_variations.items():
        template_server = next((s for s in sample_data if s["title"] == base_name), sample_data[0])
        
        for variation in variations:
            if variation == base_name:
                continue  # Skip the original name
                
            new_server = template_server.copy()
            new_server["id"] = f"{page_counter}-{next_id}"
            new_server["title"] = variation
            new_server["description"] = f"{variation} - {template_server['description']}"
            new_server["page"] = page_counter
            
            new_tags = template_server["tags"].copy()
            variation_tag = f"# {variation.lower().replace(' ', '-')}"
            if variation_tag not in new_tags:
                new_tags.append(variation_tag)
            new_server["tags"] = new_tags
            
            full_data.append(new_server)
            next_id += 1
    
    num_duplicates = 100  # Generate enough servers for testing but not too many to slow down development
    
    for i in range(num_duplicates):
        for template_server in sample_data:
            new_server = template_server.copy()
            new_server["id"] = f"{page_counter}-{next_id}"
            new_server["title"] = f"{template_server['title']} {next_id}"
            new_server["page"] = page_counter
            
            new_server["description"] = f"{template_server['description']} (Variant {i+1})"
            
            full_data.append(new_server)
            next_id += 1
            
            if next_id % 100 == 0:
                page_counter += 1
    
    try:
        with open(dest_path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=2)
        print(f"Created dataset with {len(full_data)} servers at {dest_path}")
        return True
    except Exception as e:
        print(f"Error saving full dataset: {str(e)}")
        return False

if __name__ == "__main__":
    success = prepare_data()
    sys.exit(0 if success else 1)

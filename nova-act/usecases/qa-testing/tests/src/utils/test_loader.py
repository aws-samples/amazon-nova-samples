import json
from pathlib import Path
from typing import List, Dict, Any

def get_all_test_files() -> List[Path]:
    """Get all JSON test files from test_data directory."""
    test_data_dir = Path(__file__).parent.parent / "test_data"
    return list(test_data_dir.glob("*.json"))

def load_all_test_data() -> List[Dict[str, Any]]:
    """Load all test data from JSON files."""
    test_files = get_all_test_files()
    test_data = []
    
    for file_path in test_files:
        with open(file_path, "r") as f:
            data = json.load(f)
            data["_source_file"] = file_path.name
            test_data.append(data)
    
    return test_data
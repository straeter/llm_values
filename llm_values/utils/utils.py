import importlib.resources
import json
import os
import re


def load_json_file(filename, folder="data"):
    if folder == "resources":
        with importlib.resources.open_text('llm_values.resources', filename) as json_file:
            json_data = json.load(json_file)
    else:
        with importlib.resources.open_text('llm_values.data', filename) as json_file:
            json_data = json.load(json_file)
    return json_data


def save_json_file(data, file_path):
    folder, filename = os.path.split(file_path)
    os.makedirs(folder, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def extract_rating(s):
    # This regex looks for digits inside double brackets
    match = re.search(r'\[\[(\d+)\]\]', s)
    if match:
        return int(match.group(1))  # Convert the found digits into an integer
    else:
        return None  # Return None if no matching pattern is found

import json
import os


def load_json_file(filename, folder="data"):
    try:
        with open(os.path.join(folder, filename), 'r', encoding='utf-8') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        with open(os.path.join("../../", folder, filename), 'r', encoding='utf-8') as file:
            json_data = json.load(file)

    return json_data


def save_json_file(data, file_path):
    folder, filename = os.path.split(file_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)




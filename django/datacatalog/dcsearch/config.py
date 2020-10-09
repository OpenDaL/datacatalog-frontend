# -*- coding: utf-8 -*-
"""
JSON file config data for application
"""
import json
from pathlib import Path

cur_path = Path(__file__).absolute().parent


def load_config(filename):
    """
    Load a JSON file from this package with the given filename
    """
    filepath = Path(cur_path, filename)
    with open(filepath, 'r', encoding='utf-8') as jsonfile:
        return json.load(jsonfile)


# Load all config data into memory
dropdown_lists = load_config('dropdown.json')
language_mapping = load_config('languages.json')
subject_data = load_config('subject_scheme.json')
sourcename_mapping = load_config('sourcenames.json')
metadata_schema = load_config('metadata_schema.json')
search_tips = load_config('search_tips.json')

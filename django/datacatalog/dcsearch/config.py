# -*- coding: utf-8 -*-
"""
JSON file config data for application

Copyright (C) 2021  Tom Brouwer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
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

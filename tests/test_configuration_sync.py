"""
The subject scheme and languages mapping should match the subjects and
languages in the dropdown.json file
"""
from pathlib import Path
import json

repo_root = Path(__file__).parent.parent
files_folder = Path(repo_root, 'django/datacatalog/dcsearch')


def _load_json(file_path):
    """
    Load a JSON file
    """
    with open(file_path, 'r', encoding='utf8') as jsonfile:
        return json.load(jsonfile)


dropdown_data = _load_json(Path(files_folder, 'dropdown.json'))
subject_data = _load_json(Path(files_folder, 'subject_scheme.json'))
language_data = _load_json(Path(files_folder, 'languages.json'))


def test_subject_scheme_in_sync():
    """
    Test if all subjects defined in the dropdown list, can be found in the
    subject_data
    """
    subject_dropdown_keys = list(dropdown_data['subject'].keys())
    subjects_in_scheme = set(subject_data.keys())

    # Can also subtract sets and check length, but this prints better info
    for subject_id in subject_dropdown_keys:
        assert subject_id in subjects_in_scheme


def test_languages_in_sync():
    """
    Test if all languages defined in the dropdown list, can be found in the
    language json
    """
    language_dropdown_keys = list(dropdown_data['language'].keys())
    available_languages = set(language_data.keys())

    # Can also subtract sets and check length, but this prints better info
    for language in language_dropdown_keys:
        assert language in available_languages

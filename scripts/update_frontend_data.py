# -*- coding: utf-8 -*-
"""
Update the configuration json file for the dropdown lists, by querying
ElasticSearch, and the sourcenames.json, based on the sources.json
"""
import json
import getpass
import argparse
import yaml
from pathlib import Path

import requests


def load_yaml(fileloc):
    with open(fileloc, 'r', encoding='utf8') as yamlfile:
        return yaml.safe_load(yamlfile)


def save_json(data, fileloc):
    with open(fileloc, 'w', encoding='utf8') as jsonfile:
        json.dump(data, jsonfile, ensure_ascii=False)


def is_valid_yaml_file(parser, fileloc):
    path = Path(fileloc)
    if not path.is_file():
        parser.error('The file {} does not exist'.format(fileloc))
    elif not path.suffix == '.yaml':
        parser.error('The file {} is not a YAML file'.format(fileloc))
    else:
        return path


if __name__ == "__main__":
    # Parse the script arguments
    aparser = argparse.ArgumentParser(
        description="Fill the dropdown.json based on the data on ES"
    )
    aparser.add_argument(
        "es_host",
        help="IP Address/Domain of ElasticSearch instance (e.g. 127.0.0.1)",
        type=str
    )
    aparser.add_argument(
        "sources_file",
        help="Location of the sources.yaml file",
        type=lambda loc: is_valid_yaml_file(aparser, loc)
    )

    # Get arguments
    args = aparser.parse_args()
    es_ip = args.es_host
    sources_loc = args.sources_file

    es_pass = getpass.getpass(
        "Password for the 'frontend' ES user (Empty if None): "
    )

    # Build aggregations
    rsession = requests.session()
    if es_pass != '':
        rsession.auth = ('frontend', es_pass)

    AGGREGATE_KEYS = ["type", "subject", "format", "language"]
    URL = 'http://{}:9200/resource_metadata/_doc/_search'.format(es_ip)
    cur_path = Path(__file__).absolute().parent
    headers = {'Content-Type': 'application/json'}
    store_loc = Path(cur_path, '../django/datacatalog/dcsearch/dropdown.json')
    ITERATION_SIZE = 100

    key_data = {}
    for key in AGGREGATE_KEYS:
        key_data[key] = {}
        QUERY = {
            "aggs": {
                "my_buckets": {
                    "composite": {
                        "size": ITERATION_SIZE,
                        "sources": [
                            {key: {"terms": {"field": key}}}
                        ]
                    }
                }
             }
        }
        response = rsession.post(
            URL,
            data=json.dumps(QUERY, ensure_ascii=False).encode('utf-8'),
            headers=headers
        )
        data = response.json()
        vcounts = {b['key'][key]: b['doc_count'] for b
                   in data['aggregations']['my_buckets']['buckets']}
        key_data[key].update(vcounts)
        while len(vcounts) == ITERATION_SIZE:
            after_key = data['aggregations']['my_buckets']['after_key']
            QUERY['aggs']['my_buckets']['composite']['after'] = after_key
            response = rsession.post(
                URL,
                data=json.dumps(QUERY, ensure_ascii=False).encode('utf-8'),
                headers=headers
            )
            data = response.json()
            vcounts = {b['key'][key]: b['doc_count'] for b
                       in data['aggregations']['my_buckets']['buckets']}
            key_data[key].update(vcounts)

    save_json(key_data, store_loc)

    # Update the sourcenames.json file
    sources = load_yaml(sources_loc)
    source_names = {s['id']: s['name'] for s in sources}
    store_loc = Path(
        cur_path, '../django/datacatalog/dcsearch/sourcenames.json'
    )
    save_json(source_names, store_loc)

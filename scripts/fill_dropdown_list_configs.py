# -*- coding: utf-8 -*-
"""
This script creates the configuration json for the dropdown lists, to present
the user with a list of possible types, subjects, formats and languages by
deriving this data from ES. Reduces the number of costly aggregation queries
on ES.
"""
import json
import os
import getpass
import argparse

import requests

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

    # Get arguments
    args = aparser.parse_args()
    es_ip = args.es_host

    es_pass = getpass.getpass(
        "Password for the 'frontend' ES user (Empty if None): "
    )
    rsession = requests.session()
    if es_pass != '':
        rsession.auth = ('frontend', es_pass)

    AGGREGATE_KEYS = ["type", "subject", "format", "language"]
    URL = 'http://{}:9200/resource_metadata/_doc/_search'.format(es_ip)
    cur_path = os.path.dirname(os.path.realpath(__file__))
    headers = {'Content-Type': 'application/json'}
    STORE_LOC = os.path.join(cur_path,
                             '../django/datacatalog/dcsearch/dropdown.json')
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

    with open(STORE_LOC, 'w', encoding='utf8') as jsonfile:
        json.dump(key_data, jsonfile, ensure_ascii=False)

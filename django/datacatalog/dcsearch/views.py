from os import path
import json
from urllib.parse import quote_plus
import math
import copy

import requests

from django.template import loader
from django.shortcuts import render
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.urls import reverse

from .forms import SearchForm, AggregationsForm, subject_data,\
    language_mapping, SearchComponentsForm

empty_payloads = set(['*', ''])

VIZ_KEY_PRIORITY = ['subject', 'format', 'created', 'issued', 'modified',
                    'language', 'version', 'status', 'license']
ES_URL = 'http://{}/resource_metadata/_doc'.format(settings.ES_LOC)
RESULTS_PER_PAGE = 10
ADDITONAL_CRITERIA = {
    "type": "type",
    "subject": "subject",
    "format": "format",
    "language": "language",
    "bbox": "location",
    "created": "created date",
    "issued": "issued date",
    "modified": "modified date",
    "timeperiod": "temporal coverage"
}

rsession = requests.Session()
if settings.ES_PASS is not None:
    rsession.auth = ('frontend', settings.ES_PASS)

cur_path = path.dirname(path.realpath(__file__))
md_schema_loc = path.join(cur_path, 'metadata_schema.json')
sources_loc = path.join(cur_path, 'sources.json')
tips_loc = path.join(cur_path, 'search_tips.json')


def load_json(file_loc):
    with open(file_loc, 'r', encoding='utf8') as jsonfile:
        return json.load(jsonfile)


md_schema = load_json(md_schema_loc)
sources = load_json(sources_loc)
tips = load_json(tips_loc)

source_names = {s['id']: s['name'] for s in sources}
keyname_mapping = {k: v['name'] for k, v in md_schema.items()}

plain_keys = set(
    ['status', 'issued', 'modified', 'created', 'maintenance', 'context',
     'size', 'sampleSize', 'coordinateSystem', 'quality', 'lineage', 'format']
)


def _get_child_subjects(id_):
    """
    Get a list of child subjects from a given subject id
    """
    return_subjects = set()
    for sid, payload in subject_data.items():
        if id_ in payload['parents'] or id_ in payload['relations']:
            if sid not in return_subjects:
                return_subjects.add(sid)
                return_subjects.update(_get_child_subjects(sid))
    return list(return_subjects)


def _get_parent_subjects(id_):
    """
    Get a list of parent subjects for a given subject id
    """
    parent_subjects = subject_data.get(id_, {}).get('parents', [])
    related_subjects = subject_data.get(id_, {}).get('relations', [])
    combined_subjects = parent_subjects + related_subjects
    added_subjects = []
    # Recurse through direct parents
    for subject in combined_subjects:
        added_subjects.extend(_get_parent_subjects(subject))

    return list(set(combined_subjects + added_subjects))


def _get_parent_types(type_id):
    """
    List the parents of the given type
    """
    type_parts = type_id.split(':')
    parents = []
    for i in range(len(type_parts) - 1):
        parents.append(':'.join(type_parts[:-i-1]))

    return parents


def _construct_query(post_data, aggs=None, return_results=True):
    """
    Construct the ES query from cleaned form data

    Arguments:
        post_data --- dict: The cleaned form data

        aggs=None --- dict: The aggregation style (short|long|selected) for
        each field. If given, aggregations are returned instead of individual
        results

        return_results=True --- bool: Allows to disable the returning of
        results in case on aggregations are required.
    """
    query = {
        "query": {
            "bool": {
                "filter": [],
                "must": []
            }
        }
    }

    query_part = query['query']

    kw_payload = post_data.get('keywords')

    # result sorting:
    if return_results:  # Only valid if a list of results should be returned
        sort_by = post_data.get('sort_by')
        if sort_by and not sort_by == 'relevance':
            query['sort'] = {sort_by: {'order': 'desc'}}
        elif kw_payload is None:
            # Sort by metadata quality, if no keywords are provided
            # Otherwise ES will do keywords based sorting
            query['sort'] = {'_metadata_scores.total': {'order': 'desc'}}
        else:
            # No use to score and sort, if only aggs are requested
            query = {
                'query': {
                    "function_score": {
                        'query': {
                            'bool': {
                                'filter': [],
                                'must': [],
                            }
                        },
                        "script_score": {
                            "script": {
                              "source": "1 + 0.5 * doc['_metadata_scores.total'].value"
                            }
                        },
                        "boost_mode": "multiply"
                    }
                }
            }
            query_part = query['query']['function_score']['query']

    if return_results:
        query['size'] = RESULTS_PER_PAGE

    if aggs is not None:
        # Return aggregations rather than search results
        query['aggs'] = {}

        # Parse the requested aggregations
        for field, aggstyle in aggs.items():
            if aggstyle == 'long':
                aggsize = 50
            elif aggstyle == 'short':
                aggsize = 5
            else:
                # If aggstyle=='selected', do nothing
                continue
            query['aggs'][field] = {
                "terms": {
                    "field": field,
                    "size": aggsize
                }
            }

    # Pagination:
    page = post_data.get('page')
    if page is not None and page != 0:
        query['from'] = page * RESULTS_PER_PAGE

    # Process Keyword query
    if kw_payload is not None:
        search_fields = []
        in_title = post_data.get('in_title')
        in_desc = post_data.get('in_desc')
        if in_title:
            search_fields.append('title')
        if in_desc:
            search_fields.append('abstractORdescription')

        if len(search_fields) > 0:
            # Should always be the case, since this is caught by the form
            # validation
            simple_query = {
                "simple_query_string": {
                    "query": kw_payload,
                    "fields": search_fields,
                    "default_operator": "and",
                    "flags": "OR|AND|NOT|PREFIX|ESCAPE|PHRASE|PRECEDENCE|WHITESPACE"
                }
            }

            query_part['bool']['must'].append(simple_query)

    # Process format query
    format_payload = post_data.get('format')
    if not (format_payload is None or format_payload == '*'):
        format_query = {
            'terms': {
                'format': [format_payload]
            }
        }
        query_part['bool']['filter'].append(format_query)

    # Process subject query
    subject_payload = post_data.get('subject')
    if not (subject_payload is None or subject_payload == '*'):
        subject_query = {
            'term': {
                'subject': subject_payload
            }
        }
        query_part['bool']['filter'].append(subject_query)

    # Process language query
    language_payload = post_data.get('language')
    if not (language_payload is None or language_payload == '*'):
        language_query = {
            'terms': {
                'language': [language_payload]
            }
        }
        query_part['bool']['filter'].append(language_query)

    # Process type query
    type_payload = post_data.get('type')
    if not (type_payload is None or type_payload == '*'):
        type_query = {
            'term': {
                'type': type_payload
            }
        }
        query_part['bool']['filter'].append(type_query)

    # Process bounding box:
    if post_data.get('bbox_xmin'):
        bbox_type = post_data['bboxtype']
        if bbox_type == 'within':
            relation = 'within'
        else:
            relation = 'intersects'
        loc_query = {
            "nested": {
                "path": "location",
                "query": {
                    "constant_score": {
                        "filter": {
                            "geo_shape": {
                                "location.geometry": {
                                    "shape": {
                                        "type": "envelope",
                                        "coordinates": [
                                            [
                                                post_data['bbox_xmin'],
                                                post_data['bbox_ymax']
                                            ],
                                            [
                                                post_data['bbox_xmax'],
                                                post_data['bbox_ymin']
                                            ]
                                        ]
                                    },
                                    "relation": relation
                                }
                            }
                        }
                    }
                }
            }
        }
        query_part['bool']['filter'].append(loc_query)

    # Process date field queries:
    date_fields = ['created', 'issued', 'modified']
    for date_id in date_fields:
        date_lte = post_data.get(f'{date_id}_lte')
        date_gte = post_data.get(f'{date_id}_gte')
        date_query = {
            "range": {
                date_id: {}
            }
        }
        if date_lte is not None:
            date_query['range'][date_id]['lte'] = date_lte.isoformat()
        if date_gte is not None:
            date_query['range'][date_id]['gte'] = date_gte.isoformat()

        if date_query['range'][date_id] != {}:
            query_part['bool']['filter'].append(date_query)

    # Process temporal coverage query
    period_lte = post_data.get('timeperiod_lte')
    period_gte = post_data.get('timeperiod_gte')
    if period_lte is not None or period_gte is not None:
        per_query = {
            "nested": {
                "path": "timePeriod",
                "query": {
                    "bool": {
                        "filter": []
                    }
                }
            }
        }
        filter_query = per_query["nested"]["query"]["bool"]["filter"]
        if period_lte is not None:
            filter_query.append({
                "range": {"timePeriod.start": {"lte": period_lte.isoformat()}}
            })
        if period_gte is not None:
            filter_query.append({
                "range": {"timePeriod.end": {"gte": period_gte.isoformat()}}
            })
        query_part['bool']['filter'].append(per_query)

    if query_part['bool']['must'] == []:
        del query_part['bool']['must']
    if query_part['bool']['filter'] == []:
        del query_part['bool']['filter']

    return query


def _query_elasticsearch(query):
    """
    Based on the post data, constructs the query to elasticsearch
    """
    headers = {'content-type': 'application/json'}
    if 'function_score' in query['query']:
        query_part = query['query']['function_score']['query']
    else:
        query_part = query['query']

    if 'must' in query_part['bool'] or 'filter' in query_part['bool']:
        response = rsession.post(
            ES_URL.strip('/') + '/_search',
            json.dumps(query, ensure_ascii=False).encode('utf8'),
            headers=headers)
        response.raise_for_status()  # For more sensible log messages
        query_data = response.json()

        search_summary = {
            'count': query_data['hits']['total']['value'],
            'count_rel': query_data['hits']['total']['relation'],
            'results': [h['_source'] for h in query_data['hits']['hits']]
        }
        for result in search_summary['results']:
            result.update(result.pop('notIndexed_'))

        if 'aggregations' in query_data:
            aggregation_data = {}
            for field, aggdat in query_data['aggregations'].items():
                value_counts =\
                    {b['key']: b['doc_count'] for b in aggdat['buckets']}
                aggregation_data[field] = value_counts
            search_summary['aggs'] = aggregation_data
    else:
        search_summary = {
            'count': 0,
            'count_rel': 'eq',
            'results': []
        }

    return search_summary


def _get_es_entry(entry_id):
    """
    Get the data of a specific entry from ES
    """
    response = rsession.get(
        ES_URL.strip('/') + '/{}'.format(entry_id)
    )
    rdata = response.json()

    if rdata.get('found'):
        result = rdata['_source']
        result.update(result.pop('notIndexed_'))

        return result
    else:
        return None


def _payload_is_valid(str_):
    """
    Check if a POST value is valid data
    """
    return str_ is not None and str_ not in empty_payloads


def _get_searchparam_visualization(post_data):
    """
    Based on the post data, creates a dict with key value combinations to
    display at the top of the page
    """
    viz_data = {}

    # First do keys with Straightforward visualization
    simple_vizualization = ['keywords', 'type', 'format']
    for key in simple_vizualization:
        payload = post_data.get(key)
        if _payload_is_valid(payload):
            viz_data[key.capitalize()] = payload

    # Language visualization:
    lang_data = post_data.get('language')
    if _payload_is_valid(lang_data):
        viz_data['Language'] = language_mapping[lang_data]

    # Subject visualization:
    subject = post_data.get('subject')
    if _payload_is_valid(subject):
        viz_data['Subject'] = subject_data[subject]['name']

    # Visualize bounding box:
    all_bbox_keys = ['bbox_ymax', 'bbox_xmax', 'bbox_ymin', 'bbox_xmin']
    bbox = []
    for key in all_bbox_keys:
        payload = post_data.get(key)
        if payload is None:
            break
        try:
            bbox.append("{0:.2f}".format(payload))
        except ValueError:
            break
    else:
        viz_data['BBOX'] = ', '.join(bbox)

    # Vlsualize dates:
    date_prefixes = ['issued', 'created', 'modified', 'timeperiod']
    for prefix in date_prefixes:
        lte_p = post_data.get(prefix + '_lte')
        gte_p = post_data.get(prefix + '_gte')
        lte_valid = _payload_is_valid(lte_p)
        gte_valid = _payload_is_valid(gte_p)

        if not lte_valid and not gte_valid:
            continue
        elif lte_valid and gte_valid:
            value = gte_p.strftime('%Y-%m-%d') + ' to ' + lte_p.strftime('%Y-%m-%d')
        elif lte_valid:
            value = 'before ' + lte_p.strftime('%Y-%m-%d')
        else:
            value = 'after ' + gte_p.strftime('%Y-%m-%d')

        viz_data[prefix.capitalize()] = value

    return viz_data


def _get_title_description(entry_data):
    """
    Gets the title and description of the entry
    """
    title = entry_data.get('title')  # Always has a value in the db
    description = entry_data.get('abstractORdescription')  # May be None

    return title, description


def _get_result_key_priority(search_query):
    """
    Determines in what order key/value combinations of keys have to be
    visualized. If keys such as type and format are queried, they don't need
    to be shown anymore, since they're the same for all results. Dates do need
    to be shown
    """
    none_values = set([None, '', '*'])
    # Determine which keys were queried
    queried_keys = set()
    for key, value in search_query.items():
        if value not in none_values:
            queried_keys.add(key)

    # Now reorder the default list:
    key_priority = copy.copy(VIZ_KEY_PRIORITY)
    deferred = []
    for ind_ in reversed(range(len(key_priority))):
        p_key = key_priority[ind_]
        # In case it is queried, defer it in priority list
        if p_key in queried_keys:
            # This already ensures date keys are not moved, since in the query
            # These have _lte and _gte attached
            del key_priority[ind_]
            deferred.append(p_key)

    # Add deferred to end of list
    return key_priority + deferred


def _get_most_detailed_subjects(subjects: list) -> list:
    """
    Return the lowest level subjects (of which no childs are in the list)
    """
    low_level_subjects = []
    for subject in subjects:
        children = _get_child_subjects(subject)
        for child in children:
            if child in subjects:
                break
        else:
            low_level_subjects.append(subject)

    return low_level_subjects


def _get_result_visualizations(entries, search_query):
    """
    Convert a list of entries to visualization data for the results list
    """
    # Determine priority in visualization
    key_list = _get_result_key_priority(search_query)

    # For each entry, determine the visualization
    entry_visualizations = []
    for entry_data in entries:
        # Get the title and description
        title, description = _get_title_description(entry_data)

        # Type will be the first property that is added
        properties = []
        dstype = entry_data.pop('type', None)
        if dstype is not None:
            most_detailed_type = max(dstype, key=lambda k: len(k))
            properties.append(('Type', most_detailed_type))

        # Add other keys to the properties list
        for key in key_list:
            if key in entry_data:
                data = entry_data[key]
                if isinstance(data, str):
                    properties.append((key.capitalize(), data))
                elif isinstance(data, list):
                    if key == 'subject':
                        detailed_subjects = _get_most_detailed_subjects(data)
                        viz = ', '.join(
                            [subject_data.get(s, {}).get('name', 'undefined')
                             for s in detailed_subjects]
                        )
                    elif key == 'language':
                        viz = ', '.join(
                            [language_mapping.get(l, 'undefined')
                             for l in data]
                        )
                    else:
                        viz = ','.join(data)
                    properties.append((key.capitalize(), viz))
                elif isinstance(data, dict):
                    if key == 'version':
                        viz = data.get('value')
                    elif key == 'license':
                        viz = data.get('name')

                    if viz is not None:
                        properties.append((key.capitalize(), viz))
                if len(properties) == 5:
                    break

        entry_visualizations.append({
            'title': title,
            'description': description,
            'properties': properties,
            'sourcename': source_names.get(entry_data['_source_id']),
            'href_id': quote_plus(entry_data['id'])
        })

    return entry_visualizations


def _get_key_value_viz(key, value):
    """
    Get the visualization of a specific key value pair. Returns a dict if it
    should be visualized, otherwise Empty list
    """
    key_name = keyname_mapping.get(key)
    k_v_list = []

    if key in plain_keys:
        # First consider keys that can be easily visualized
        if isinstance(value, list):
            struct_value = ', '.join([str(v) for v in value])
        else:
            struct_value = str(value)
        k_v_list.append((key_name, struct_value))
    elif key == 'version':
        struct_value = value.get('value')
        if struct_value is not None:
            k_v_list.append(('Version', struct_value))
    elif key == 'creator':
        organizations = []
        names = []
        for creator in value:
            if 'name' in creator:
                names.append(creator['name'])
            elif 'organization' in creator:
                organizations.append(creator['organization'])

        if organizations != []:
            if len(organizations) == 1:
                k_v_list.append(('Organization', organizations[0]))
            else:
                k_v_list.append(('Organizations', ', '.join(organizations)))

        if names != []:
            if len(organizations) == 1:
                k_v_list.append(('Creator', names[0]))
            else:
                k_v_list.append(('Creators', ', '.join(names)))
    elif key == 'publisher':
        struct_value = value.get('value')
        if struct_value is not None:
            k_v_list.append(('Publisher', struct_value))
    elif key == 'otherDates':
        date_type = value.get('type')
        date = value.get('value')
        if date_type is not None and date is not None:
            k_v_list.append((date_type.capitalize(), date))
    elif key == 'license':
        for k in ['name', 'content']:
            if k in value:
                k_v_list.append(('License', value[k]))
                break
    elif key == 'identifier':
        itype = value.get('type')
        ival = value.get('value')
        if itype is not None and ival is not None:
            k_v_list.append((itype, ival))
    elif key == 'subject':
        detailed_subjects = _get_most_detailed_subjects(value)
        subjects = [subject_data[s]['name'] for s in detailed_subjects]
        if len(subjects) == 1:
            k_v_list.append(('Subject', subjects[0]))
        else:
            k_v_list.append(('Subjects', ', '.join(subjects)))
    elif key == 'publishedIn':
        name = value.get('name')
        volume = value.get('volume')
        issue = value.get('issue')
        pages = value.get('pages')
        if name is not None:
            struct_value = name
            if volume is not None:
                struct_value += ', {}'.format(volume)
            if issue is not None:
                if volume is None:
                    struct_value += ', '
                struct_value += ' ({})'.format(issue)
            if pages is not None:
                struct_value += ', pp. {}'.format(pages)
            k_v_list.append((key_name, struct_value))
    elif key == 'location':
        names_points = []
        bboxes = []
        for location in value:
            if 'name' in location:
                names_points.append(location['name'])
            elif 'geometry' in location:
                geometry = location['geometry']
                if geometry['type'].lower() == 'point':
                    p_data = ','.join(["{0:.2f}".format(c)
                                       for c in geometry['coordinates']])
                    names_points.append(p_data)
                elif geometry['type'].lower() == 'envelope':
                    bbox_order = [(0, 1), (1, 0), (1, 1), (0, 0)]
                    bb_data = ', '.join(
                        ["{0:.2f}".format(geometry['coordinates'][i][j])
                         for i, j in bbox_order]
                    )
                    bboxes.append(bb_data)

        if names_points != []:
            if len(names_points) == 1:
                k_v_list.append(('Location', names_points[0]))
            else:
                k_v_list.append(('Locations', '; '.join(names_points)))

        if bboxes != []:
            if len(bboxes) == 1:
                k_v_list.append(('Bounding Box', bboxes[0]))
            else:
                k_v_list.append(('Bounding Boxes', '; '.join(bboxes)))
    elif key.endswith('Resolution'):
        if key == 'spatialResolution':
            suffix = ' m'
        elif key == 'temporalResolution':
            suffix = ' s'
        k_v_list.append((key_name, str(value) + suffix))
    elif key == 'timePeriod':
        all_key_value = {}
        for period in value:
            p_str = '{} - {}'.format(period['start'], period['end'])
            type = period['type']
            if type in all_key_value:
                all_key_value[type].append(p_str)
            else:
                all_key_value[type] = [p_str]

        for type, p_list in all_key_value.items():
            k_v_list.append((type, ';'.join(p_list)))
    elif key == 'language':
        full_langs = [language_mapping[l] for l in value]
        if len(full_langs) == 1:
            k_v_list.append(('Language', full_langs[0]))
        else:
            k_v_list.append(('Languages', '; '.join(full_langs)))

    return k_v_list


def _get_resource_visualization(entry_data):
    """
    Get the context for the resource page
    """
    # First get the visualization of the base keys:
    title, description = _get_title_description(entry_data)

    type_ = entry_data.get('type')
    if type_ is not None:
        type_ = max(type_, key=lambda k: len(k))  # Longest is most detailed
        desc_type = 'Abstract' if type_.startswith('Doc') else 'Description'
    else:
        desc_type = 'Description'

    viz_data = {
        'title': title,
        'description': description,
        'type': type_,
        'desc_type': desc_type
    }

    # Build key value dict to construct the table:
    full_kvlist = []
    for k, v in entry_data.items():
        full_kvlist += _get_key_value_viz(k, v)

    if full_kvlist == []:
        viz_data['key_value_data'] = None
    else:
        viz_data['key_value_data'] = full_kvlist

    # Get catalog name and url
    ct_name = source_names.get(entry_data['_source_id'], '')

    viz_data['catalog'] = {
        'name': ct_name,
        'href': entry_data['externalReference']['URL']
    }

    # Get relations:
    relations = entry_data.get('relations')
    if relations is not None:
        relation_data = {}
        for relation in relations:
            if relation['identifierType'] == 'ExternalURL':
                rel_name = relation.get('name')
                if rel_name is not None:
                    if rel_name in relation_data:
                        relation_data[rel_name].append(relation['identifier'])
                    else:
                        relation_data[rel_name] = [relation['identifier']]
        viz_data['relations'] = relation_data
    else:
        viz_data['relations'] = None

    return viz_data


def _get_additional_criteria(post_data):
    """
    Count which main criteria the user has used in their query

    Args:
        post_data --- dict: The user query sent in the post request

    Returns:
        int --- The number of search criteria defined in the query
    """
    additional_criteria = []
    for crit in ADDITONAL_CRITERIA:
        for k, v in post_data.items():
            if crit in k and _payload_is_valid(v):
                additional_criteria.append(ADDITONAL_CRITERIA[crit])
                break

    return additional_criteria


def _get_search_tips(post_data):
    """
    Generate a list of search tips, based on the query of the user

    Args:
        post_data --- dict: The user query sent in the post request

    Returns:
        list[str] --- The search tip messages
    """
    search_tips = []
    support_url = reverse('dcsearch:support')

    type_ = post_data.get('type')
    if _payload_is_valid(type_):
        parents = _get_parent_types(type_)
        if parents != []:
            # Propose to use parent types, to yield more results
            if len(parents) > 1:
                parent_phrase = "s '{}' or '{}'".format(
                    "', '".join(parents[:-1]),
                    parents[-1]
                )
            else:
                parent_phrase = " '{}'".format(parents[0])

            search_tips.append(tips["use_general_type"].format(
                type_,
                parent_phrase
            ))

    subject = post_data.get('subject')
    if _payload_is_valid(subject):
        parents = _get_parent_subjects(subject)
        if parents != []:
            # Propose to use parent subjects, to yield more results
            parent_names = [subject_data[p]['name'] for p in parents]
            if len(parent_names) > 1:
                parent_phrase = "s '{}' or '{}'".format(
                    "', '".join(parent_names[:-1]),
                    parent_names[-1]
                )
            else:
                parent_phrase = " '{}'".format(parent_names[0])

            search_tips.append(tips["use_parent_subject"].format(
                subject_data[subject]['name'],
                parent_phrase
            ))

    bbox_type = post_data.get('bboxtype')
    if _payload_is_valid(bbox_type) and bbox_type == 'within':
        # If 'within' is used for the BBOX query, suggest to use 'intersecting'
        search_tips.append(tips['use_intersecting_bbox'])

    additionals = _get_additional_criteria(post_data)
    if additionals != []:
        # Indicate that not all requirements in addition to keywors are there

        # Construct phrases for singular and plural...
        if len(additionals) == 1:
            id_modifier = 'singular'
            additionals_phrase = "<i>{}</i>".format(additionals[0])
        else:
            id_modifier = 'plural'
            additionals_phrase = '<i>{}</i> or <i>{}</i>'.format(
                "</i>, <i>".join(additionals[:-1]),
                additionals[-1]
            )

        base_msg_id = "use_less_criteria_{}".format(id_modifier)
        criteria_tip = tips[base_msg_id].format(
            support_url + '#metadata-completeness',
            additionals_phrase
        )

        # Determine whether to recommend adding them as keywords:
        recommend_keywords = False
        for key in ['type', 'subject', 'location', 'temporal coverage']:
            if key in additionals:
                recommend_keywords = True
                break

        if recommend_keywords:
            kw_msg_id = "use_less_criteria_{}_add_keywords".format(id_modifier)
            criteria_tip += tips[kw_msg_id]

        search_tips.append(criteria_tip)

    keywords = post_data.get('keywords')
    if _payload_is_valid(keywords):
        search_tips.append(
            tips["check_keywords"].format(
                support_url + '#advanced-text-search'
            )
        )

    return search_tips


@require_http_methods(["GET", "POST"])
def search(request):
    """
    The search page. Through get request a page for search is served. After a
    post request, it yields the search results
    """
    if request.method == "POST":
        form = SearchForm(request.POST, label_suffix='')
        if form.is_valid():
            query_params = form.cleaned_data

            # Query ES based on the data
            es_query = _construct_query(query_params)
            query_results = _query_elasticsearch(es_query)

            max_page = math.ceil(query_results['count'] / 10) - 1 if query_results['count'] > 0 else 0
            max_page = max_page if max_page < 100 else 99

            page_nr = query_params.get('page')
            if page_nr is None:
                # Return to search page with everything filled in
                return render(request, 'dcsearch/search.html', {'form': form})
            elif page_nr > max_page:
                raise Http404('Page number not found!')

            # Visualization of search keys
            context = {
                'searchparams': _get_searchparam_visualization(query_params),
                'result_count': query_results['count'],
                'results': _get_result_visualizations(query_results['results'],
                                                      query_params),
                'page': page_nr,
                'max_page': max_page,
                'form': form,
                'count_rel': query_results['count_rel']
            }

            # If there is a low number of entries, provide search tips:
            if context['result_count'] <= 100:
                search_tips = _get_search_tips(query_params)
                if len(search_tips) > 0:
                    context['search_tips'] = search_tips

            return render(request, 'dcsearch/results.html', context)
    else:
        form = SearchForm(label_suffix='')

    return render(request, 'dcsearch/search.html', {'form': form})


@require_http_methods(["POST"])
def result_list(request):
    """
    Upon a POST request, this returns the HTML for the search results list
    """
    form = SearchForm(request.POST, label_suffix='')
    if form.is_valid():
        query_params = form.cleaned_data

        # Query ES based on the data
        es_query = _construct_query(query_params)
        query_results = _query_elasticsearch(es_query)

        max_page = math.ceil(query_results['count'] / 10) - 1 if query_results['count'] > 0 else 0
        max_page = max_page if max_page < 100 else 99

        page_nr = query_params.get('page')
        if page_nr > max_page:
            raise Http404('Page number not found!')

        # Visualization of search keys
        context = {
            'results': _get_result_visualizations(query_results['results'],
                                                  query_params)
        }

        return render(request, 'dcsearch/result_list.html', context)
    else:
        return HttpResponseBadRequest('Invalid form data')


@require_http_methods(["POST"])
def aggregations(request):
    """
    Upon a POST request, this returns the aggregation data as JSON
    """
    form = AggregationsForm(request.POST, label_suffix='')
    if form.is_valid():
        query_params = form.cleaned_data

        # First parse the aggregation properties
        aggs = {}
        for agg in query_params['aggregations'].split(','):
            field, aggstyle = agg.split(':')
            aggs[field] = aggstyle

        # Disable aggregations on fields that are already queried
        count_selected = 0
        for fn in ['type', 'format', 'language', 'subject']:
            fv = query_params.get(fn)
            if not (fv is None or fv == '*'):
                count_selected += 1
                aggs[fn] = 'selected'

        # Only do query if one of the items is 'short' or 'long'
        if len(aggs) > count_selected:
            es_query = _construct_query(query_params, aggs=aggs)
            query_results = _query_elasticsearch(es_query)

        # Create JSON response payload
        agg_data = {}
        for field, aggstyle in aggs.items():
            if field == 'subject':
                def id_to_name(s): return subject_data[s]['name']
            elif field == 'language':
                def id_to_name(l): return language_mapping[l]
            else:
                def id_to_name(id_): return id_

            if aggstyle != 'selected':
                raw_agg = query_results['aggs'][field]
                aggs = {k: {'name': id_to_name(k), 'count': v} for
                        k, v in raw_agg.items()}
            else:
                aggs = {
                    query_params[field]: {
                        'name': id_to_name(query_params[field])
                    }
                }

            context = {
                'aggs': aggs,
                'aggstyle': aggstyle,
                'field': field
            }

            agg_data[field] = loader.render_to_string(
                'dcsearch/filterlist.html', context
            )

        return JsonResponse(agg_data)
    else:
        return HttpResponseBadRequest('Invalid form data')


@require_http_methods(["POST"])
def search_components(request):
    """
    Upon a POST request, this returns one or more components of the search
    results page
    """
    form = SearchComponentsForm(request.POST, label_suffix='')
    if form.is_valid():
        query_params = form.cleaned_data
        views = query_params['views']
        query_needed = False  # Determine if an ES query is required
        results_needed = False

        # First determine if a query is required, and what to query
        if 'aggs' in views and query_params['aggregations'] is not None:
            # First parse the aggregation properties
            aggs = {}
            for agg in query_params['aggregations'].split(','):
                field, aggstyle = agg.split(':')
                aggs[field] = aggstyle

            # Disable aggregations on fields that are already queried
            count_selected = 0
            for fn in ['type', 'format', 'language', 'subject']:
                fv = query_params.get(fn)
                if not (fv is None or fv == '*'):
                    count_selected += 1
                    aggs[fn] = 'selected'

            if len(aggs) > count_selected:
                query_needed = True
        else:
            aggs = None

        if 'results' in views:
            query_needed = True
            results_needed = True

        if query_needed:
            es_query = _construct_query(
                query_params, aggs=aggs, return_results=results_needed
            )
            query_results = _query_elasticsearch(es_query)

        component_data = {}
        if 'aggs' in views:
            component_data['aggs'] = {}
            for field, aggstyle in aggs.items():
                if field == 'subject':
                    def id_to_name(s): return subject_data[s]['name']
                elif field == 'language':
                    def id_to_name(l): return language_mapping[l]
                else:
                    def id_to_name(id_): return id_

                if aggstyle != 'selected':
                    raw_agg = query_results['aggs'][field]
                    aggs = {k: {'name': id_to_name(k), 'count': v} for
                            k, v in raw_agg.items()}
                else:
                    aggs = {
                        query_params[field]: {
                            'name': id_to_name(query_params[field])
                        }
                    }

                context = {
                    'aggs': aggs,
                    'aggstyle': aggstyle,
                    'field': field
                }

                component_data['aggs'][field] = loader.render_to_string(
                    'dcsearch/filterlist.html', context
                )

        if 'results' in views:
            context = {
                'results': _get_result_visualizations(query_results['results'],
                                                      query_params)
            }
            component_data['results'] = loader.render_to_string(
                'dcsearch/result_list.html', context
            )

            max_page = math.ceil(query_results['count'] / 10) - 1 if query_results['count'] > 0 else 0
            max_page = max_page if max_page < 100 else 99

            component_data['maxPage'] = max_page
            component_data['count'] = query_results['count']

        if 'tips' in views:
            search_tips = None
            if query_results['count'] <= 100:
                search_tips = _get_search_tips(query_params)
                if len(search_tips) == 0:
                    search_tips = None

            component_data['tips'] = loader.render_to_string(
                'dcsearch/search_tips.html', {'tips': search_tips}
            )

        if 'header' in views:
            component_data['header'] = {
                'description': loader.render_to_string(
                    'dcsearch/result_header.html',
                    {
                        'count': query_results['count'],
                        'count_rel': query_results['count_rel']
                    }
                ),
                'querySummary': loader.render_to_string(
                    'dcsearch/result_query_summary.html',
                    {'searchparams': _get_searchparam_visualization(query_params)}
                )
            }

        return JsonResponse(component_data)
    else:
        return HttpResponseBadRequest('Invalid form data')


@require_http_methods(["GET"])
def get_resource(request, resource_id):
    """
    Gives a resource description by id
    """
    entry = _get_es_entry(resource_id)
    if entry is None:
        raise Http404('Resource with id {} not found!'.format(resource_id))

    context = _get_resource_visualization(entry)

    return render(request, 'dcsearch/resource.html', context)


@require_http_methods(["GET"])
def get_static_page(request, page_id=None):
    """
    Renders static pages
    """
    if page_id is None:
        raise Http404('Page not Found!')

    return render(request, f'dcsearch/{page_id}.html')

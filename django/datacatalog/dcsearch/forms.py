# -*- coding: utf-8 -*-
"""
Forms for the dcsearch app
"""
import copy

from django import forms
from django.core.validators import RegexValidator
from django.forms.widgets import Select, RadioSelect

from . import config

dropdown_lists = copy.deepcopy(config.dropdown_lists)  # It's edited below

# Create dropdown visualization for several keys:
for key, data in dropdown_lists.items():
    if key == 'subject':
        # processed seperatly
        continue
    for value, count in data.items():
        if key == 'language':
            name = '{} ({})'.format(config.language_mapping[value], count)
        else:
            name = '{} ({})'.format(value, count)

        data[value] = name


# Process subject data, to illustrate hierarchy
def create_tree(data):
    def get_subdata(key):
        kdat = {k: {} for k, v in data.items() if key in v['parents']
                or key in v['relations']}
        for k in kdat.keys():
            kdat[k] = get_subdata(k)
        return kdat

    # Get firstlevel
    tree = {k: {} for k, v in data.items() if v['parents'] == []}
    for ky in tree.keys():
        tree[ky] = get_subdata(ky)

    return tree


subject_tree = create_tree(config.subject_data)


def get_subject_visualization(tree_data):
    def key_viz_list(key, data, level=0):
        key_viz_data = []
        # First visualize the requested key:
        count = dropdown_lists['subject'].get(key, 0)
        viz_dat = (
            key,
            '{}{} ({})'.format(
                '&nbsp;' * level * 4, config.subject_data[key]['name'],
                count
            )
        )
        key_viz_data.append(viz_dat)

        # Now the underlying things:
        for ky in data[key]:
            key_viz_data += key_viz_list(ky, data[key], level=level + 1)

        return key_viz_data

    s_visualization_list = []
    for key in tree_data:
        s_visualization_list += key_viz_list(key, tree_data)

    return s_visualization_list


sdata = get_subject_visualization(subject_tree)

dropdown_lists = {k: dict(sorted(v.items(), key=lambda k: k[1]))
                  for k, v in dropdown_lists.items() if k != 'subject'}

dropdown_lists['subject'] = sdata


class SelectSpaced(Select):
    option_template_name = 'dcsearch/select_option_spacify.html'

    def __init__(self):
        super().__init__(attrs={'class': 'searchable-select'})


class SelectOptimized(Select):
    def __init__(self):
        super().__init__(attrs={'class': 'searchable-select'})


class SelectSorting(Select):
    def __init__(self):
        super().__init__(attrs={'onchange': 'changeSortingOrder();'})


class RadioNoLabelWrap(RadioSelect):
    option_template_name = 'dcsearch/radio_option_label_seperate.html'


class HTML5DateWidget(forms.DateInput):
    input_type = 'date'


def force_in_bounds(cdata, key, min, max):
    """
    Foces the number stored under the key to be within the min max bound. If
    not in bound, it will be restored to nearest limit
    """
    payload = cdata.get(key)
    if payload > max:
        cdata[key] = max
    elif payload < min:
        cdata[key] = min


class SearchForm(forms.Form):
    """
    The form for the search fields of the advanced search page
    """
    # Keyword fields
    keywords = forms.CharField(
        label="Keywords",
        required=False,
        empty_value=None,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Enter keywords here',
                'aria-label': 'Search Keywords'
            }
        )
    )
    in_title = forms.BooleanField(initial=True, label="Search in title",
                                  required=False)
    in_desc = forms.BooleanField(initial=True, label="Search in Description",
                                 required=False)

    # Dropdown fields & checkboxes:
    type = forms.ChoiceField(
        choices=[('*', '(Any)')] + list(dropdown_lists['type'].items()),
        label="Type",
        widget=SelectOptimized()
    )

    subject = forms.ChoiceField(
        choices=[('*', '(Any)')] + list(dropdown_lists['subject']),
        label="Subject",
        widget=SelectSpaced()
    )

    format = forms.ChoiceField(
        choices=[('*', '(Any)')] + list(dropdown_lists['format'].items()),
        label="Format",
        widget=SelectOptimized()
    )

    language = forms.ChoiceField(
        choices=[('*', '(Any)')] + list(dropdown_lists['language'].items()),
        label="Language",
        widget=SelectOptimized()
    )

    source = forms.ChoiceField(
        # Though it's hidden, add choices for validation
        choices=[('*', '(Any)')] + list(config.sourcename_mapping.items()),
        label="Source",
        widget=forms.HiddenInput()
    )

    # Location fields
    bboxtype = forms.ChoiceField(
        choices=[
            ('within', 'within the BBOX'),
            ('intersects', 'intersecting the BBOX'),
        ],
        widget=RadioNoLabelWrap(),
        required=False
    )
    bbox_xmin = forms.FloatField(widget=forms.HiddenInput(), required=False)
    bbox_xmax = forms.FloatField(widget=forms.HiddenInput(), required=False)
    bbox_ymin = forms.FloatField(widget=forms.HiddenInput(), required=False)
    bbox_ymax = forms.FloatField(widget=forms.HiddenInput(), required=False)

    # Created date
    created_gte = forms.DateField(
        label="From",
        widget=HTML5DateWidget(),
        required=False
    )
    created_lte = forms.DateField(
        label="Until",
        widget=HTML5DateWidget(),
        required=False
    )

    # Issued date
    issued_gte = forms.DateField(
        label="From",
        widget=HTML5DateWidget(),
        required=False
    )
    issued_lte = forms.DateField(
        label="Until",
        widget=HTML5DateWidget(),
        required=False
    )

    # Modified date
    modified_gte = forms.DateField(
        label="From",
        widget=HTML5DateWidget(),
        required=False
    )
    modified_lte = forms.DateField(
        label="Until",
        widget=HTML5DateWidget(),
        required=False
    )

    # Temporal Coverage
    timeperiod_gte = forms.DateField(
        label="From",
        widget=HTML5DateWidget(),
        required=False
    )
    timeperiod_lte = forms.DateField(
        label="Until",
        widget=HTML5DateWidget(),
        required=False
    )

    # Search page
    page = forms.IntegerField(
        initial=0,
        required=False,
        min_value=0,
        max_value=99
    )

    # Result sorting
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('created', 'Date Created'),
            ('modified', 'Date Modified'),
            ('issued', 'Date Issued')
        ],
        label="Sort by",
        required=False,
        widget=SelectSorting()
    )

    def clean(self):
        cleaned_data = super().clean()

        # Check if one of the required fields is given:
        required_fields = ['keywords', 'type', 'subject', 'format', 'language',
                           'bbox_xmin']
        for field in required_fields:
            dat = cleaned_data.get(field)
            if not (dat is None or dat == '*'):
                break
        else:
            raise forms.ValidationError(
                ('You have to specify either Keywords, a Type, a Subject,'
                 ' a Format, a Language or a Bounding Box'),
                code='sparse'
            )

        # If keywords are given, either title or description must be selected
        if cleaned_data.get('keywords') is not None:
            if not cleaned_data['in_title'] and not cleaned_data['in_desc']:
                self.add_error(
                    'keywords',
                    "You have entered keywords, but did not select one of "
                    "'Search in title' or 'Search in description'")

        # Check bigger than / smaller than for each time field
        time_fields = [
            ('Created date', 'created'),
            ('Issued date', 'issued'),
            ('Modified date', 'modified'),
            ('Temporal Coverage', 'timeperiod')
        ]
        for field_desc, field_id in time_fields:
            from_id = f'{field_id}_gte'
            until_id = f'{field_id}_lte'
            from_date = cleaned_data.get(from_id)
            until_date = cleaned_data.get(until_id)
            if from_date and until_date:
                if cleaned_data[from_id] > cleaned_data[until_id]:
                    msg = ("'Until' has to be larger than"
                           " or equal to 'From'")
                    self.add_error(until_id, msg)

        # If one bbox field is given, check if all are given:
        bbox_fields = ['bbox_xmin', 'bbox_xmax', 'bbox_ymin', 'bbox_ymax']
        count_given = 0
        for field in bbox_fields:
            if cleaned_data.get(field):
                count_given += 1

        if 0 < count_given < 4:
            self.add_error('bbox_ymax', "Given BBOX is incomplete!")
        elif count_given == 4:
            # Also check for existing bbox type, if bbox is given
            if not cleaned_data.get('bboxtype'):
                self.add_error('bboxtype',
                               "Please select either 'within' or 'intersect'")

            # Correct values if out of bounds
            force_in_bounds(cleaned_data, 'bbox_xmin', -180, 180)
            force_in_bounds(cleaned_data, 'bbox_xmax', -180, 180)
            force_in_bounds(cleaned_data, 'bbox_ymin', -90, 90)
            force_in_bounds(cleaned_data, 'bbox_ymax', -90, 90)

        return cleaned_data


# Workaround for missing group repeat in default regex package
_single_agg_regex = r'((type|subject|format|language):(short|long))'
_full_agg_regex = f'^{_single_agg_regex}(,{_single_agg_regex}){{0,3}}$'

_single_view_regex = r'(aggs|header|tips|results)'
_full_view_regex = f'^{_single_view_regex}(,{_single_view_regex}){{0,3}}$'


class SearchComponentsForm(SearchForm):
    """
    Extension of SearchForm. Used to request parts of the page through AJAX
    """

    aggregations = forms.CharField(
        required=False,
        empty_value=None,
        validators=[
            RegexValidator(_full_agg_regex, 'Invalid Aggregations requested')
        ]
    )

    views = forms.CharField(
        required=True,
        empty_value=None,
        validators=[
            RegexValidator(_full_view_regex, 'Invalid Views requested')
        ]
    )

# OpenDataLibrary.com front-end
The OpenDataLibrary.com front-end is written in Python, using the Django
framework. To run the code locally, create a virtual environment, make sure
the ENV_TYPE is set to local, and run the development server:

```bash
>> python3.7 -m venv frontend
>> source ./frontend/bin/activate
>> pip install -r $REPO_DIR/datacatalog-frontend/djano/datacatalog/requirements.txt
>> export ENV_TYPE=local
>> cd $REPO_DIR/django/datacatalog
>> python manage.py runserver
```

Please note that the local ES IP should be configured in the
[local.py settings](django/datacatalog/datacatalog/settings/local.py).

Running the code in production requires setting up a WSGI server, possibly in
conjunction with NGINX.

## Regular maintenance

### Update the dropdown lists
The counts for dropdown lists, are currently included as static json files.
These can be updated by running the
[fill_dropdown_list_configs.py](scripts/fill_dropdown_list_configs.py) in a
virtual environment where Python > 3.6 and the requests package are available.

Input for this script is the location of the ES database (PUBLIC IP), that
contains the resource metadata, as well as the password for the 'frontend'
ES user (found at `/home/ubuntu/es_creds.txt` on that server).
The script uses aggregations to determine the counts for the dropdown lists
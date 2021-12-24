# OpenDataLibrary.com Frontend
The OpenDataLibrary.com front-end is written in Python, using the Django
framework. It uses an ElasticSearch instance with resource metadata to offer
search and filtering functionality.

## 1. Usage
To use the front-end locally, you need to have python3.7. Then you can use the
scripts to install your local environment and activate it:
```bash
./local_install.sh
source local_activate.sh
```

Before running the server, make sure that:
1. Your ENV_TYPE environent variable is set: `export ENV_TYPE='local'`
2. You've set the correct ES_LOC and ES_PASS in [local.py](django/datacatalog/datacatalog/settings/local.py)

Now do:
```bash
cd django/datacatalog
python manage.py runserver
```

To run the front-end on a server, use UWSGI in combination with the NGINX
reverse proxy. The configuration for this can be found in the 'opendal-systems-setup'
respository.

## 2. Updates
Before starting to develop, please enable the githooks:
```bash
./enable_githooks.sh
```

To improve the websites performance, the dropdown lists and some other files
are committed to this repository. After a database update, these can be updated
using the [update_frontend_data.py](scripts/update_frontend_data.py) script.

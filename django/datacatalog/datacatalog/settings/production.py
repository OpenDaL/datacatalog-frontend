# -*- coding: utf-8 -*-
"""
Settings for production environment
"""
import os
from pathlib import Path

# SECURITY WARNING: keep the secret key used in production secret!
CONFIG_DIR = os.environ.get('CONFIG_DIR')

if CONFIG_DIR is None:
    raise ValueError('No CONFIG_DIR environment variable defined!')

file_loc = os.path.join(CONFIG_DIR, 'DJANGO_SECRET_KEY')
with open(file_loc, 'r', encoding='utf8') as sk_file:
    SECRET_KEY = sk_file.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


STATIC_ROOT = '/data/www/{}/static'.format(os.environ.get('ENV_TYPE'))

ALLOWED_HOSTS = ['.opendatalibrary.com', '35.174.100.130']

file_loc = os.path.join(CONFIG_DIR, 'ES_LOC')
with open(file_loc, 'r', encoding='utf8') as sk_file:
    ES_LOC = sk_file.read().strip()

file_loc = os.path.join(CONFIG_DIR, 'ES_PASS')
if Path(file_loc).is_file():
    with open(file_loc, 'r', encoding='utf8') as sk_file:
        ES_PASS = sk_file.read().strip()
        if ES_PASS == '':
            ES_PASS = None
else:
    ES_PASS = None

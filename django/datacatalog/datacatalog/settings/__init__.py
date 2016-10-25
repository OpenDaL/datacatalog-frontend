# -*- coding: utf-8 -*-
import os
from .base import *

# Detect production environment
env_type = os.environ.get('ENV_TYPE')
if env_type == 'production' or env_type == 'staging':
    # Both can use same settings because $CONFIG_DIR are different for both
    from .production import *
elif env_type == 'local':
    from .local import *
else:
    raise ValueError('ENV_TYPE environment variable is not correctly defined. Current Value: {}'.format(env_type))

# /bin/bash
set -e

# Absolute path to this script. /home/user/bin/foo.sh
SCRIPT=$(readlink -f $BASH_SOURCE)
SCRIPTPATH=`dirname $SCRIPT`
ENV_DIR=$SCRIPTPATH/.env

# Remove possible old virtual env, for fresh installation
rm -r -f $ENV_DIR

# Create new virtual env and activate
python3.7 -m venv $ENV_DIR
source $ENV_DIR/bin/activate

# Install required packages
pip install --upgrade pip
pip install wheel
pip install -r django/datacatalog/requirements.txt

deactivate

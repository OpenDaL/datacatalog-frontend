# /bin/bash
set -e

if [ -z "$VENV_DIR" ]
then
    echo "VENV_DIR environment variable not set, please set it first"
    exit 1
fi

# Remove possible old virtual env, for fresh installation
rm -r -f $VENV_DIR/opendal_frontend

# Create new virtual env and activate
python3.7 -m venv $VENV_DIR/opendal_frontend
source $VENV_DIR/opendal_frontend/bin/activate

# Install required packages
pip install --upgrade pip
pip install wheel
pip install -r django/datacatalog/requirements.txt

deactivate
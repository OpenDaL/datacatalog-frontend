export ENV_TYPE=local
if [ -z "$VENV_DIR" ]
then
    echo "VENV_DIR environment variable not set, please set it first"
else
    source $VENV_DIR/opendal_frontend/bin/activate
fi
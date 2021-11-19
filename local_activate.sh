export ENV_TYPE=local

SCRIPT=$(readlink -f $BASH_SOURCE)
SCRIPTPATH=`dirname $SCRIPT`
ENV_DIR=$SCRIPTPATH/.env

source $ENV_DIR/bin/activate
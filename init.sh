#!/bin/bash
# exit when any command fails
set -e

# Create required directory structure (if it does not already exist)
if [[ ! -d "$LAB_DATA_DIR" ]]; then
    echo "Creating directory $LAB_DATA_DIR"
    mkdir -p $LAB_DATA_DIR
fi

if [[ ! -d "$LAB_STATIC_ROOT" ]]; then
    echo "Creating directory $LAB_STATIC_ROOT"
    mkdir -p $LAB_STATIC_ROOT
fi
# static files
if [ ! "$(ls -A $LAB_STATIC_ROOT)" ]; then
    echo "Copying file to  $LAB_STATIC_ROOT"
    cp -r $LAB_MNG_DIR/data/static/* $LAB_STATIC_ROOT/
fi


cd ${LAB_HOME}


# Launch the CMD *after* the ENTRYPOINT completes
exec "$@"
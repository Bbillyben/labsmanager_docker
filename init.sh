#!/bin/bash
# exit when any command fails
set -e
echo ">> ================ INITIALISATION ================ <<" 
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

if [[ ! -d "$LAB_MEDIA_ROOT" ]]; then
    echo "Creating directory $LAB_MEDIA_ROOT"
    mkdir -p $LAB_MEDIA_ROOT
fi
if [ ! "$(ls -A $LAB_MEDIA_ROOT)" ]; then
    echo "Copying file to  $LAB_MEDIA_ROOT"
    cp -r $LAB_MNG_DIR/data/media/* $LAB_MEDIA_ROOT/
fi

if [[ ! -d "$LAB_STATIC_COLOR_THEMES_DIR" ]]; then
    echo "Creating directory $LAB_STATIC_COLOR_THEMES_DIR"
    mkdir -p $LAB_STATIC_COLOR_THEMES_DIR
fi
if [ ! "$(ls -A $LAB_STATIC_COLOR_THEMES_DIR)" ]; then
    echo "Copying file to  $LAB_STATIC_COLOR_THEMES_DIR"
    cp -r $LAB_MNG_DIR/data/static/css/color-themes/* $LAB_STATIC_COLOR_THEMES_DIR/
fi

cd ${LAB_HOME}


# Launch the CMD *after* the ENTRYPOINT completes
exec "$@"
# pull official base image
FROM python:3.9-slim as base

# set variable 
ENV LAB_HOME="/home/labsmanager"
ENV LAB_MNG_DIR="${LAB_HOME}/labsmanager"
ENV LAB_DATA_DIR="${LAB_HOME}/data"
ENV LAB_STATIC_ROOT="${LAB_DATA_DIR}/static"
ENV LAB_MEDIA_ROOT="${LAB_DATA_DIR}/media"
ENV LAB_STATIC_COLOR_THEMES_DIR="${LAB_STATIC_ROOT}/css/color-themes"
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# set work directory
WORKDIR ${LAB_MNG_DIR}

# RUN apt-get upgrade && apt-get update
RUN apt-get update


# Install required system packages
RUN apt-get install -y  --no-install-recommends \
    git gcc g++ gettext gnupg libffi-dev \
    # Weasyprint requirements : https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#debian-11
    poppler-utils libpango-1.0-0 libpangoft2-1.0-0 \
    # Image format support
    libjpeg-dev webp \
    # SQLite support
    sqlite3 \
    # PostgreSQL support
    libpq-dev postgresql-client \
    # MySQL / MariaDB support
    default-libmysqlclient-dev mariadb-client && \
    apt-get autoclean && apt-get autoremove

# Update pip
RUN pip install --upgrade pip

# Install required base-level python packages
COPY ./requirements.txt base_requirements.txt
RUN pip install --disable-pip-version-check -U -r base_requirements.txt


# Copy source code
COPY labsmanager ${LAB_HOME}/labsmanager
#COPY labsmanager/data/static ${LAB_DATA_DIR}/static
COPY requirements.txt ${LAB_HOME}/requirements.txt
COPY gunicorn.conf.py ${LAB_HOME}/gunicorn.conf.py
COPY init.sh ${LAB_MNG_DIR}/init.sh
COPY tasks.py ${LAB_HOME}/tasks.py

# copy initial reports file
# RUN mkdir -p {LAB_MEDIA_ROOT}/report/report_template/
# COPY ./labsmanager/templates/reports/* ${LAB_MEDIA_ROOT}/report/report_template/

# Server init entrypoint
ENTRYPOINT ["/bin/bash", "init.sh"]

# Launch the production server
CMD gunicorn -c ${LAB_HOME}/gunicorn.conf.py labsmanager.wsgi -b 0.0.0.0:8000 --chdir ./labsmanager
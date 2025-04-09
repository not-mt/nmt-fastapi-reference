# install the latest shared library as a build stage, so that we do not
#   need to include any extra utilities (like git) in the final image
FROM ubuntu:24.04 AS lib-builder
WORKDIR /tmp
RUN apt-get update && \
    apt-get -y install git && \
    git clone https://github.com/not-mt/nmt-fastapi-library.git

# second stage of build
FROM ubuntu:24.04
LABEL maintainer="Alex Haye <alexander.haye@windstream.com>"

# build args/envs
ARG APP_UID=5001
ARG APP_GID=5001
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# install OS packages
RUN apt-get update && \
    apt-get -y dist-upgrade && \
    apt-get -y install \
        procps \
        psmisc \
        nginx \
        supervisor \
        python3-venv

# basic OS settings
RUN chmod -R 1777 /run

# prepare application directories
RUN mkdir -p /app/src /app/static

# install shared library
COPY --from=lib-builder /tmp/nmt-fastapi-library /nmt-fastapi-library

# setup nginx
COPY ./docker/nginx.conf /etc/nginx/nginx.conf

# setup unprivileged group, user
RUN groupadd -g $APP_GID app && \
    useradd -d /app -s /bin/bash -u $APP_UID -g $APP_GID app && \
    chmod -R g+ws /app && \
    chown -R app:app /app

# install the entrypoint script, nginx, supervisord configs, etc.
COPY ./docker/nginx.conf /etc/nginx/nginx.conf
COPY ./docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY ./docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

# NOTE: this will guarantee that the venv is installed as an unprivileged user
USER app:app
WORKDIR /app

# install the app source, pyproject.toml, etc
COPY ./alembic  /app/alembic
COPY ./alembic.ini /app/
COPY ./LICENSE /app/
COPY ./nmtfast-config-default.yaml /app/
COPY ./poetry.lock /app/
COPY ./poetry.toml /app/
COPY ./pyproject.toml /app/
COPY ./README.md /app/
COPY ./src /app/src

# prepare virtualenv and install python packages
COPY ./samples/poetry.toml /app/poetry.toml
RUN python3 -m venv /app/venv && \
    . /app/venv/bin/activate && \
    pip install poetry && \
    poetry lock && \
    poetry install --without dev

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]

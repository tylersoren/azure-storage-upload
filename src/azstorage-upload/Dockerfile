FROM python:3.8-slim

LABEL maintainer="<email address here>"

USER root

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN python3.8 -m pip install -r requirements.txt

# Install setproctitle required for datadog gunicorn integration
RUN apt-get update && \
      apt-get install gcc -y && \
      python3.8 -m pip install setproctitle

COPY . /app

# Create the application user and group
RUN groupadd -r flask && useradd -r -s /bin/false -g flask user

# Change ownership of the app folder from root to the new user
RUN chown -R user:flask /app

# Set all Files to be read only and allow execute
RUN chmod -R 551 /app/*

# Run as the new user
USER user

# Run application on gunicorn WSGI server with port 8000 - log to standard out
ENTRYPOINT gunicorn -c gunicorn_config.py app:app

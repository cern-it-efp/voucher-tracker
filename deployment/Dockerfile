FROM ubuntu:18.04

# ------------------ General Stuff
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    awscli \
    python3-pip \
    nano \
    vim \
    zip \
    git \
    snapd \
    net-tools \
    jq
    #python \
    #python-pip \
    #python2.7 \

RUN pip3 install \
    pyyaml \
    jsonschema \
    azure-cli \
    google-cloud \
    google-cloud-resource-manager \
    google-cloud-bigquery \
    google-api \
    google-api-python-client \
    google-auth-oauthlib \
    boto3
    #google-cloud-api \
    #google-api-client \

RUN pip3 install --upgrade requests

# ------------------ install az-ci
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# ------------------ Clone TS repo and get bash
RUN echo "git clone -q https://gitlab.cern.ch/ipeluaga/v-track-private ; cd v-track-private" > ~/.bashrc

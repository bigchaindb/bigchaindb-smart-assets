FROM python:3.6

RUN mkdir -p /usr/src/app
COPY . /usr/src/app/

WORKDIR /usr/src/app/bigchaindb/

RUN apt-get -qq update \
    && apt-get -y upgrade \
    && pip install --no-cache-dir . \
    && apt-get autoremove \
    && apt-get clean

WORKDIR /usr/src/app/

RUN pip install --no-cache-dir -e .[dev]


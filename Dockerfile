FROM python:3.9-alpine

RUN apk add --no-cache --update screen bash

EXPOSE 9999

ENV MODEM_PATH /dev/cellular_modem
ENV SIM_KEY XXXXXX
ENV HOST cloudsocket.hologram.io
ENV PORT 9999
ENV MAX_QUEUE_SIZE 10

COPY ./cellular_message_relay.py /usr/bin/cellular_message_relay.py
COPY ./requirements.txt /tmp/

RUN chmod +x /usr/bin/cellular_message_relay.py && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  adduser -D cellular_message_relay && \
  apk --purge del apk-tools && \
  rm /tmp/requirements.txt

USER cellular_message_relay

ENTRYPOINT python -u /usr/bin/cellular_message_relay.py

FROM python:3.9-alpine

RUN apk add --no-cache --update screen bash

EXPOSE 9999

ENV MODEM_PATH /dev/usb_modem
ENV SIM_KEY XXXXXX
ENV MAX_QUEUE_SIZE 10

COPY ./usb_modem_relay.py /usr/bin/usb_modem_relay.py
COPY ./requirements.txt /tmp/

RUN chmod +x /usr/bin/usb_modem_relay.py && \
  pip install --no-cache-dir -r /tmp/requirements.txt && \
  adduser -D usb_modem_relay && \
  apk --purge del apk-tools && \
  rm /tmp/requirements.txt

USER usb_modem_relay

ENTRYPOINT python -u /usr/bin/usb_modem_relay.py

# GSM Message Relay container
<a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a><br>

Acts as a message gateway for cellular modems (see branches for different models). Accepts messages via POST and interacts with the modem to attempt to send over network to Hologram messaging API. Use something like https://github.com/aneisch/cellular_bridge or a CloudFlare Worker to bridge the connection to your messaging platform.

## Usage
To transmit a message:
```bash
curl -vvv -X POST -d '{"message":"hi there from a cellular network!"}' localhost:9999/send_message
```

### Example docker-compose

```yaml
version: '3.2'
services:
    cellular_message_relay:
        container_name: cellular_message_relay
        image: ghcr.io/aneisch/cellular_message_relay:sim7080g
        ports:
            - '9999:9999'
        environment:
            # Optional MODEM_PATH - defaults to /dev/cellular_modem
            #- MODEM_PATH=/dev/cellular_modem
            # SIM key from Hologram Device dashboard
            - SIM_KEY=XXXX
            # Set a max queue size to limit usage in case we think we need to send 10,000 messages or something
            - MAX_QUEUE_SIZE=5
        devices:
            - /dev/cellular_modem:/dev/cellular_modem
        restart: always
```
### Home Assistant Configuration

Works great with [RESTful Notifications](https://www.home-assistant.io/integrations/notify.rest/) to relay messages.

```yaml
# configration.yaml
notify:
  - name: gsm_message
    platform: rest
    resource: http://10.0.1.22:9999/send_message
    method: POST_JSON
    data:
      priority: "{{ data.priority }}"
```

# GSM Message Relay container
<a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a><br>

Acts as a message gateway for SIM800C cellular modem (and probably works with others). Accepts messages via POST and interacts with the modem to attempt to send over network to Hologram messaging API.

## Usage
To transmit a message:
```bash
curl -vvv -X POST -d '{"message":"hi there from a cellular network!"}' localhost:9999/send_message
```

### Example docker-compose

```yaml
version: '3.2'
services:
    gsm_message_relay:
        container_name: gsm_message_relay
        image: ghcr.io/aneisch/gsm_message_relay:latest
        ports:
            - '9999:9999'
        environment:
            # Optional GSM_MODEM - defaults to /dev/gsm_modem
            #- GSM_MODEM=/dev/gsm_modem
            # SIM key from Hologram Device dashboard
            - SIM_KEY=XXXX
        devices:
            - /dev/gsm_modem:/dev/gsm_modem
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
```
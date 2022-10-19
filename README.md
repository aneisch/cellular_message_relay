# Thermostat MQTT container
<a href="https://www.buymeacoffee.com/aneisch" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a><br>

Acts as a message gateway for SIM800C GSM module. Accepts messages via POST and attempts to send them over GSM network to Hologram messaging API. 

## Usage
To transmit a message:
```bash
curl -vvv -X POST -d '{"message":"hi there from a cellular network!"}' localhost:9999/send_message
```

### Example docker-compose

```yaml
version: '3.2'
services:
    thermostat_api_server:
        container_name: gsm_message_relay
        image: ghcr.io/aneisch/gsm_message_relay:latest
        ports:
            - '8080:8080'
        environment:
            # Name for Device in HA
            # Optional GSM_MODEM - defaults to /dev/gsm_modem
            #- GSM_MODEM=/dev/gsm_modem
            # SIM key from Hologram Device dashboard
            - SIM_KEY=10.0.1.22 
        restart: always
```
### Home Assistant Configuration

Works great with [RESTful Notifications](https://www.home-assistant.io/integrations/notify.rest/) to relay messages.
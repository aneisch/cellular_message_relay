#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs
from urllib.parse import unquote
import os
import socketserver
import json
import pexpect
import sys
import ast
import time
import queue
import threading 
import logging
import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s -- %(levelname)s -- %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

modem_path = os.environ['MODEM_PATH']
sim_key = os.environ['SIM_KEY']
host = os.environ['HOST']
port = os.environ['PORT']
power_toggle_webhook = os.environ['POWER_TOGGLE_WEBHOOK']

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

def gsm_send(message):
    attempts = 0
    max_attempts = 7
    success = False

    while attempts < max_attempts:
            os.system("killall screen >/dev/null 2>&1; screen -wipe >/dev/null 2>&1")
            attempts += 1
            logger.info(f"Attempting to send message: {message} {attempts}/{max_attempts}")

            try:
                child = pexpect.spawn(f"screen -S gsm {modem_path} 115200", env={'TERM': 'vt100'})
            except Exception as e:
                logger.error(f"spawn error: {e}")   
                continue      

            try:
                command = "AT"
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=2)
                logger.info(f"{command} success, modem healthy")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                if "http" in power_toggle_webhook:
                    logger.critical(f"Modem unhealthy, power cycling..")
                    requests.post(power_toggle_webhook)
                    time.sleep(15)
                continue

            # Disable flight mode
            try:
                command = "AT+CFUN=1"
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=5)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Set to LTE only
            try:
                command = "AT+CNMP=38"
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=5)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                time.sleep(10)
                continue

            # # Set to Cat-M1 over NB-IoT
            # try:
            #     command = "AT+CMNB=1"
            #     child.send(f"{command}\r\n")
            #     child.expect("OK", timeout=5)
            #     print(f"{command} success")
            # except Exception as e:
            #     print(f"{command} Error: {e}")
            #     time.sleep(10)
            #     continue

            # Check IP
            try:
                command = "AT+CNACT?"
                child.send(f"{command}\r\n")
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Deactivate PDP
            try:
                command = 'AT+CNACT=0,0'
                child.send(f"{command}\r\n")
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Activate PDP
            try:
                command = 'AT+CNACT=0,1'
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=5)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Check IP
            try:
                command = "AT+CNACT?"
                child.send(f"{command}\r\n")
                child.expect(".*10\..*", timeout=10)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(15)
                continue

            # Set up TCP
            try:
                socket_connected = False
                command = 'AT+CASSLCFG=0,"SSL",0'
                child.send(f"{command}\r\n")
                #child.expect("OK", timeout=5)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Close any session
            try:
                command = 'AT+CACLOSE=0'
                child.send(f"{command}\r\n")
                #child.expect("OK", timeout=5)
                logger.info(f"{command} success")
            except Exception as e:
                e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                logger.error(f"{command} Error. Buffer: {e}")
                #time.sleep(10)
                continue

            # Open connection, try a few times in case socket error
            for i in range(0,5):
                try:
                    socket_connected = False
                    command = f'AT+CAOPEN=0,0,"TCP","{host}",{int(port)}'
                    child.send(f"{command}\r\n")
                    child.expect([".*CAOPEN: 0,0",".*CADATAIND: 0"], timeout=20)
                    logger.info(f"{command} success")
                    socket_connected = True
                    break
                except Exception as e:
                    e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                    logger.error(f"{command} Error. Buffer: {e}")
                    command = 'AT+CACLOSE=0'
                    child.send(f"{command}\r\n")
                    #time.sleep(2)

            if socket_connected == False:
                continue

            # Prepare and send message. Try a few times
            for i in range(0,5):
                try:
                    message_sent = False
                    command = f"AT+CASEND=0,{len(message)}"
                    child.send(f"{command}\r\n")
                    child.expect(">.*")
                    logger.info(f"{command} success")
                    command = f"{message}"
                    child.send(f"{command}\r\n")
                    #child.expect([".*OK.*","CADATAIND"], timeout=5)
                    child.expect(".*OK.*", timeout=5)
                    logger.info(f"{command} success")
                    message_sent = True
                    break
                except Exception as e:
                    e = str(e).split("buffer (last 100 chars): b'")[1].split("'")[0]
                    logger.error(f"CASEND Error. Buffer: {e}")
                    #time.sleep(10)

            if message_sent == False:
                continue

            # Close TCP and Deactivate PDP
            child.send(f"AT+CACLOSE=0\r\n")
            child.send(f"AT+CNACT=0,0\r\n")
            success = True
            break

    if success:
        logger.info(f"Successfully sent message after {attempts} attempts")
        q.task_done()

def worker():
    while True:
        message = q.get()
        gsm_send(message)

class MyHttpRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send_empty_200(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get('Content-length'))).decode("utf-8")
        data = unquote(data).strip("data=")

        final_locator = f'/{self.path.split("/")[-1:][0]}' # eg /status

        if "/send_message" in final_locator:
            try:
                data = ast.literal_eval(data)
                # Rename key to cut down on data use
                data['m'] = data['message']
                data['p'] = data['priority']
                del data['message']
                del data['priority']

            except:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
            
            # Terrible minipulation of this payload, but it works
            data = json.dumps(data).replace('"','\\"')

            message = '''{"k":"%s","d":"%s"}''' % (sim_key,data)
            self.send_empty_200()
            q.put(message)
            logger.info(f"Added '{message}' to message queue")

        else:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

server = ThreadingSimpleServer(('0.0.0.0', 9999), MyHttpRequestHandler)

q = queue.Queue(maxsize=int(os.environ['MAX_QUEUE_SIZE']))
threading.Thread(target=worker, daemon=True).start()
q.join()

server.serve_forever()

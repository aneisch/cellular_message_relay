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

modem_path = os.environ['MODEM_PATH']
sim_key = os.environ['SIM_KEY']

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

def gsm_send(message):
    attempts = 0
    success = False

    while attempts < 5:
            os.system("killall screen 2> /dev/null; screen -wipe 2> /dev/null")
            attempts += 1
            print(f"Attempting to send message: {message} {attempts}/5")

            try:
                child = pexpect.spawn(f"screen -S gsm {modem_path} 115200", env={'TERM': 'vt100'})
            except Exception as e:
                print(f"spawn error: {e}")   
                continue             

            # Enable.. something?
            try:
                child.send("AT+CFUN=1\r\n")
                child.expect("OK", timeout=5)
            except Exception as e:
                print(f"CFUN Error: {e}")
                time.sleep(10)
                continue

            # Shut the modem
            try:
                child.send("AT+CIPSHUT\r\n")
                child.expect("SHUT OK", timeout=5)
            except Exception as e:
                print(f"CIPSHUT Error: {e}")
                time.sleep(10)
                continue

            # Set APN
            try:
                child.send("AT+CSTT=\"hologram\"\r\n")
                child.expect("OK", timeout=5)
            except Exception as e:
                print(f"CSST Error: {e}")
                time.sleep(10)
                continue

            # Connect
            try:
                child.send("AT+CIICR\r\n")
                child.expect("OK", timeout=20)
            except Exception as e:
                print(f"CIICR Error: {e}")
                time.sleep(10)
                continue

            # Connect and show IP
            try:
                child.send("AT+CIFSR\r\n")
                child.expect("10.*", timeout=5)
            except Exception as e:
                print(f"CIFSR Error: {e}")
                time.sleep(10)
                continue

            # Initiate TCP
            try:
                child.send('AT+CIPSTART="TCP","cloudsocket.hologram.io",9999\r\n')
                child.expect("CONNECT OK", timeout=5)
            except Exception as e:
                print(f"CIPSTART Error: {e}")
                time.sleep(10)
                continue

            # Prepare message
            try:
                child.send(f'AT+CIPSEND={len(message)}\r\n')
                child.expect(">.*")

                child.send(f'{message}\r\n')
                child.expect("OK")
            except Exception as e:
                print(f"CIPSEND Error: {e}")
                time.sleep(10)
                continue

            # Shut the modem down again
            child.send('AT+CIPSHUT\r\n')

            success = True
            break

    if success:
        print(f"Successfully sent message after {attempts} attempts")


class MyHttpRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send_empty_200(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get('Content-length'))).decode("utf-8")
        data = unquote(data).strip("data=")

        received_message = {}

        final_locator = f'/{self.path.split("/")[-1:][0]}' # eg /status

        if "/send_message" in final_locator:
            try:
                my_dict = ast.literal_eval(data)
                message = my_dict['message']
            except:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
            
            message = '''{"k":"%s","d":"%s"}''' % (sim_key,message)
            self.send_empty_200()
            gsm_send(message)

        else:
            self.send_response(400)
            self.send_header("Content-Length", "0")
            self.end_headers()


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass

server = ThreadingSimpleServer(('0.0.0.0', 9999), MyHttpRequestHandler)
server.serve_forever()
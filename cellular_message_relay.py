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

modem_path = os.environ['MODEM_PATH']
sim_key = os.environ['SIM_KEY']
host = os.environ['HOST']
port = os.environ['PORT']

# Allow faster script restart
socketserver.TCPServer.allow_reuse_address = True

def gsm_send(message):
    attempts = 0
    max_attempts = 7
    success = False

    while attempts < max_attempts:
            os.system("killall screen 2> /dev/null; screen -wipe 2> /dev/null")
            attempts += 1
            print(f"Attempting to send message: {message} {attempts}/{max_attempts}")
                

            try:
                child = pexpect.spawn(f"screen -S gsm {modem_path} 115200", env={'TERM': 'vt100'})
            except Exception as e:
                print(f"spawn error: {e}")   
                continue        

            if attempts == 4:     
                #Enable flight mode
                try:
                    command = "AT+CFUN=0"
                    child.send(f"{command}\r\n")
                    child.expect("OK", timeout=5)
                    print(f"{command} success")
                except Exception as e:
                    print(f"{command} Error: {e}")
                    time.sleep(10)
                    continue

            # Disable flight mode
            try:
                command = "AT+CFUN=1"
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=5)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # # Set to LTE only
            # try:
            #     command = "AT+CNMP=38"
            #     child.send(f"{command}\r\n")
            #     child.expect("OK", timeout=5)
            #     print(f"{command} success")
            # except Exception as e:
            #     print(f"{command} Error: {e}")
            #     time.sleep(10)
            #     continue

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
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Deactivate PDP
            try:
                command = 'AT+CNACT=0,0'
                child.send(f"{command}\r\n")
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Activate PDP
            try:
                command = 'AT+CNACT=0,1'
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=5)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Check IP
            try:
                command = "AT+CNACT?"
                child.send(f"{command}\r\n")
                child.expect("OK", timeout=30)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(15)
                continue

            # Set up TCP
            try:
                command = 'AT+CASSLCFG=0,"SSL",0'
                child.send(f"{command}\r\n")
                #child.expect("OK", timeout=5)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Close any session
            try:
                command = 'AT+CACLOSE=0'
                child.send(f"{command}\r\n")
                #child.expect("OK", timeout=5)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Open connection
            try:
                command = f'AT+CAOPEN=0,0,"TCP","{host}",{int(port)}'
                child.send(f"{command}\r\n")
                child.expect(".*CAOPEN: 0,0", timeout=10)
                print(f"{command} success")
            except Exception as e:
                print(f"{command} Error: {e}")
                time.sleep(10)
                continue

            # Prepare message
            try:
                command = f"AT+CASEND=0,{len(message)}"
                child.send(f"{command}\r\n")
                child.expect(">.*")
                child.send(f"{message}\r\n")
                child.expect(".*CADATAIND: 0", timeout=20)
                print(f"{command} success")
            except Exception as e:
                print(f"CASEND Error: {e}")
                command = 'AT+CACLOSE=0'
                child.send(f"{command}\r\n")
                time.sleep(10)
                continue

            # # Check message ACK
            # try:
            #     command = 'AT+CAACK=0'
            #     child.send(f"{command}\r\n")
            #     child.expect(f"{len(message)},0", timeout=5)
            #     print(f"{command} success")
            # except Exception as e:
            #     print(f"{command} Error: {e}")
            #     command = 'AT+CACLOSE=0'
            #     child.send(f"{command}\r\n")
            #     time.sleep(10)
            #     continue

            # Deactivate PDP
            command = 'AT+CNACT=0,0'
            child.send(f"{command}\r\n")
            success = True
            break

    if success:
        print(f"Successfully sent message after {attempts} attempts")
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

        received_message = {}

        final_locator = f'/{self.path.split("/")[-1:][0]}' # eg /status

        if "/send_message" in final_locator:
            try:
                data = ast.literal_eval(data)
            except:
                self.send_response(400)
                self.send_header("Content-Length", "0")
                self.end_headers()
            
            # Terrible minipulation of this payload, but it works
            data = json.dumps(data).replace('"','\\"')

            message = '''{"k":"%s","d":"%s"}''' % (sim_key,data)
            self.send_empty_200()
            q.put(message)
            print(f"Added '{message}' to message queue")

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
import json
import threading
import time
import socket
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# Configuracion MQTT
MQTT_BROKER = '127.0.0.1'
MQTT_PORT = 1883
MQTT_COMMAND_EXPONE = "telescopio/tel84/instrumentos/ccd/expone"
MQTT_COMMAND_INIT = "telescopio/tel84/instrumentos/ccd/inicializa"

MQTT_PUBLISH_TEMP = "telescopio/tel84/instrumentos/ccd/status/temperatura"
MQTT_PUBLISH_PROGRESS = "telescopio/tel84/instrumentos/ccd/progreso"
MQTT_PUBLISH_STATUS = "telescopio/tel84/instrumentos/ccd/status"

# Configuracion CCD Server
TCP_HOST = "127.0.0.1"
TCP_PORT = 8888

# MQTT Callback functions
def on_connect(client, userdata, flags, rc):
    print("Connectado al MQTT broker")
    client.subscribe([(MQTT_COMMAND_INIT, 0), (MQTT_COMMAND_EXPONE, 0)])

def on_message(client, userdata, message):
    if message.topic == MQTT_COMMAND_EXPONE:
        on_command_expone(message.topic, message.payload.decode('utf-8', 'ignore'))
    elif message.topic == MQTT_COMMAND_INIT:
        on_command_init(message.topic, message.payload.decode('utf-8', 'ignore'))

def on_command_expone(topic, payload):
    json_payload = json.loads(payload)
    command = f"EXPONE {json_payload['tiempo']}"
    expone_thread = threading.Thread(target=ejecuta_exposicion, args=(command,))
    expone_thread.start()

def ejecuta_exposicion(command):
    response = send_command(command)
    task_id = response.split()[-1]
    progress = 0
    while progress < 100:
        time.sleep(1)
        # Preguntamos al CCD_Server el progreso
        resp = send_command(f'PROGRESO {task_id}')
        progress = int(resp)
        # Publicar a MQTT
        publish.single(topic=MQTT_PUBLISH_PROGRESS, payload=progress, hostname=MQTT_BROKER, port=MQTT_PORT)

def on_command_init(topic, payload):
    json_payload = json.loads(payload)
    command = f"INIT {json_payload['x']} {json_payload['y']}"
    send_command(command)

def send_command(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((TCP_HOST, TCP_PORT))
        print(f'Sending: {command}')
        sock.sendall(command.encode('utf-8') + b'\n')
        data = sock.recv(100)
        response = data.decode('utf-8').strip()
        print(f'Received: {response}')
    return response

# Init MQTT
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
mqtt_thread.start()


mqtt_thread.join()

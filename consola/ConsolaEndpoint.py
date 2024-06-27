import json
import math
import threading
import time
from datetime import datetime, timedelta

import astropy.units as u
from astropy.coordinates import EarthLocation, AltAz, SkyCoord, Angle, ICRS
from astropy.time import Time

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

# Configuración del cliente MQTT
MQTT_BROKER = '127.0.0.1'
MQTT_PORT = 1883
MQTT_COMMAND_ZENITH = "telescopio/tel84/instrumentos/consola/zenith"
MQTT_COMMAND_MOVE = "telescopio/tel84/instrumentos/consola/mueve"

MQTT_PUBLISH_POSITION = "telescopio/tel84/instrumentos/consola/posicion"

move_to_zenith = False
move_to_position = False
sky_coord = { }

# Coordenadas del telescopio en la Sierra de San Pedro Martir
location = EarthLocation(lat=31.0456*u.deg, lon=-115.4545*u.deg, height=2800*u.m)

# MQTT Callback functions
def on_connect(client, userdata, flags, rc):
    print("Connectado al MQTT broker")
    client.subscribe([(MQTT_COMMAND_ZENITH, 0), (MQTT_COMMAND_MOVE, 0)])

def on_message(client, userdata, message):
    if message.topic == MQTT_COMMAND_ZENITH:
        on_command_zenith(message.topic)
    elif message.topic == MQTT_COMMAND_MOVE:
        on_command_move(message.topic, message.payload.decode('utf-8', 'ignore'))

def on_command_zenith(topic):
    time_now = Time(datetime.utcnow())
    global move_to_zenith
    move_to_zenith = True

def on_command_move(topic, payload):
    json_payload = json.loads(payload)
    global sky_coord
    sky_coord['ra'] = str(json_payload['ar'])
    sky_coord['dec'] = str(json_payload['dec'])
    #sky_coord = SkyCoord(ra=json_payload['ar'], dec=json_payload['dec'])

    global move_to_position
    move_to_position = True

    global move_to_zenith
    move_to_zenith = False

def calculate_star_position(star, time_now):
    # Calcular la altitud y azimut de la estrella
    altaz = star.transform_to(AltAz(obstime=time_now, location=location))
    return altaz.alt.degree, altaz.az.degree

def run_consola():
    while True:
        # Obtener el tiempo actual
        time_now = Time(datetime.utcnow())

        if move_to_zenith:
            zenith_altaz = SkyCoord(alt=90*u.deg, az=0*u.deg, frame=AltAz(obstime=time_now, location=location))
            zenith_equatorial = zenith_altaz.transform_to('icrs')
            payload = {
                'altitude': f"{zenith_altaz.alt.degree:.2f}°",
                'azimuth': f"{zenith_altaz.az.degree:.2f}°",
                'ra': f"{zenith_equatorial.ra.to_string(u.hour)}",
                'dec': f"{zenith_equatorial.dec.to_string(u.degree)}",
                'time': f"{time_now.iso}"
            }
            publish.single(topic=MQTT_PUBLISH_POSITION, payload=json.dumps(payload), hostname=MQTT_BROKER, port=MQTT_PORT, retain=True)
        elif move_to_position:
            ra_value = str(sky_coord['ra'])
            dec_value = str(sky_coord['dec'])
            object_coord = SkyCoord(ra=ra_value, dec=dec_value)
            altaz_frame = AltAz(obstime=time_now, location=location)
            object_altaz = object_coord.transform_to(altaz_frame)
            payload = {
                'altitude': f"{object_altaz.alt.degree:.2f}°",
                'azimuth': f"{object_altaz.az.degree:.2f}°",
                'ra': f"{object_coord.ra.to_string(u.hour)}",
                'dec': f"{object_coord.dec.to_string(u.degree)}",
                'time': f"{time_now.iso}"
            }
            publish.single(topic=MQTT_PUBLISH_POSITION, payload=json.dumps(payload), hostname=MQTT_BROKER, port=MQTT_PORT, retain=True)

        # Esperar un segundo antes de la siguiente publicación
        time.sleep(0.7)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

mqtt_client.connect(MQTT_BROKER, MQTT_PORT)

mqtt_thread = threading.Thread(target=mqtt_client.loop_forever)
mqtt_thread.start()

consola_thread = threading.Thread(target=run_consola)
consola_thread.start()

mqtt_thread.join()
consola_thread.join()

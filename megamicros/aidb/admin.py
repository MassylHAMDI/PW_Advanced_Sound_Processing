from django.contrib import admin
from django.conf import settings

from megamicros.log import log, logging
from megamicros import mqtt

# Mqtt Macros should not be defined in settings since settings is not defined in megamicros.db
# ... or we should define default values 

# Register your models here.
# ...

# Set general log level 
log.setLevel( logging.INFO )


MEGAMICROS = getattr( settings, "MEGAMICROS", None )

if MEGAMICROS  is None:
    log.info( f" .Cannot set MQTT log handler: no parameters found in settings" )
elif 'MQTT_BROKER_HOST' not in MEGAMICROS or 'MQTT_BROKER_PORT' not in MEGAMICROS:
    log.info( f" .Cannot set MQTT log handler: no MQTT broker defined in settings" )
elif 'MQTT_CLIENT_ID' not in MEGAMICROS:
    log.info( f" .Cannot set MQTT log handler: no MQTT client identifier defined in settings" )
else:
    MQTT_BROKER_HOST = MEGAMICROS['MQTT_BROKER_HOST']
    MQTT_BROKER_PORT = MEGAMICROS['MQTT_BROKER_PORT']
    MQTT_CLIENT_ID = MEGAMICROS['MQTT_CLIENT_ID']

    if 'MQTT_LOG_TOPIC' not in MEGAMICROS:
        MQTT_LOG_TOPIC = 'megamicros/aidb/unknown/log'
    else: 
        MQTT_LOG_TOPIC = MEGAMICROS['MQTT_LOG_TOPIC']

    if 'MQTT_LOG_QOS' not in MEGAMICROS:
        MQTT_LOG_QOS = 1
    else: 
        MQTT_LOG_QOS = MEGAMICROS['MQTT_LOG_QOS']

    # create a MQTT client:
    mqtt_client = mqtt.MqttClient( host=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT, name=MQTT_CLIENT_ID )

    # create the Mqtt Publishing Handler, set the level and add it to the logger
    mqtt_handler = mqtt.MqttPubHandler( mqtt_client, topic=MQTT_LOG_TOPIC, qos=MQTT_LOG_QOS )

    # add the MQTT handler
    mqtt_handler.setLevel( logging.DEBUG )
    log.addHandler( mqtt_handler )
    log.info( f" .MQTT log handler added on topic '{mqtt_handler.getTopic()}'" )



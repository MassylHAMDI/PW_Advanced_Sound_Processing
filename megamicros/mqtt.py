# megamicros.mqtt.py mqtt client handler for MegaMicros libraries
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
MegaMicros documentation is available on https://readthedoc.biimea.io

!!! WARNING!!!
The MQTT client should be created and should connect to the broker outside the MqttHandler
In fact the client should be given as argument to the MqttHandler
"""

import paho.mqtt.client as mqtt
from megamicros.exception import MuException
from megamicros.log import log, logging

DEFAULT_BROKER_HOST = 'localhost'
DEFAULT_BROKER_PORT = 1883
DEFAULT_CLIENT_NAME = 'megamicros/unknown'
DEFAULT_TOPIC = 'megamicros/unknown/unknown/log'
DEFAULT_QOS = 1
DEFAULT_LEVEL = logging.NOTSET

class MqttClient :
    __client: mqtt.Client
    __connected: bool

    def __init__( self, host=DEFAULT_BROKER_HOST, port=DEFAULT_BROKER_PORT, name=DEFAULT_CLIENT_NAME ) :
        self.__connected = False
        try :
            self.__client = mqtt.Client( name )
            self.__client.connect( host=host, port=port, keepalive=60, bind_address="" )
            self.__connected = True
            log.info( f" .Connected on MQTT broker '{host}:{port}'")


        except Exception as e:
            log.error( f"MQTT broker connection failed: {e}" )
            raise

    def __del__( self ) :
        self.__client.disconnect()

    def is_connected( self ) -> bool : 
        return self.__connected

    def publish( self, message: str, topic: str, qos: int=1 ) :
        self.__client.publish( topic, message, qos, retain=False )



class MqttPubHandler( logging.Handler ) :

    __client: MqttClient
    __topic: str
    __qos: int

    def __init__( self, client: MqttClient, topic=DEFAULT_TOPIC, qos=DEFAULT_QOS, level=DEFAULT_LEVEL ) :
        try :
            super().__init__( level )
            if not client.is_connected():
                raise MuException( 'Cannot init logging Handler: MQTT client is not connected' )
            self.__client = client
            self.__topic = topic
            self.__qos = qos

        except Exception as e:
            log.error( f"MQTT broker connection failed: {e}" )
            raise

    def getTopic( self ) -> str :
        return self.__topic


    def __del__(self) :
        self.__client = None


    def emit( self, record ) :
        message = record.getMessage()
        self.__client.publish( message=message, topic=self.__topic, qos=self.__qos )




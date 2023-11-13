# megamicros_aiboard/apps/aibord/cards/labeling.py
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
Megamicros Broadcast server connection

MegaMicros documentation is available on https://readthedoc.biimea.io

see: https://plotly.com/javascript/reference/
"""

from os import path
from datetime import datetime, date, timedelta
import json
from dash import html, dcc, callback, clientside_callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash_websocket import DashWebsocket as WebSocket
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
from megamicros.log import log
import megamicros.aiboard.cpn_design as cpn
from megamicros.aiboard.session import session


WS_CONNECTING = 0
WS_OPEN = 1
WS_CLOSING = 2
WS_CLOSED = 3

DEFAULT_GRAPH_THEME = "plotly_dark"

station_connect_form = dbc.Card( [
    dbc.Container( [
        dbc.Form( [
            dbc.Row( [
                dbc.Col( [
                    dbc.Label("Host", html_for="station-host-input", className="align-middle" ),
                ], width=2 ),
                dbc.Col( [
                    dbc.Input( className="form-control me-sm-2 h-75", type="text", id="station-host-input", value="localhost", placeholder="localhost" ),    
                ], width=10 )
            ], className="mb-2" ),
            dbc.Row( [
                dbc.Col( [
                    dbc.Label("Port", html_for="station-port-input" ),
                ], width=2 ),
                dbc.Col( [
                    dbc.Input( className="form-control me-sm-2 h-75", type="text", id="station-port-input", value="9002", placeholder="9002" ),
                ], width=10 )
            ], className="mb-3" ),
            dbc.Row( [
                dbc.Col( [
                    dbc.Button( "Connecter", id="station-connect-button", outline=True, color="info", n_clicks=0 )
                ], width=3 ),
                dbc.Col( [
                    dbc.Button( "Déconnecter", id="station-disconnect-button", outline=True, color="info", n_clicks=0 )
                ], width=3  ),
            ], align="center" )
        ] )
    ], className="vstack gap-2" )
], body=True )


station_parameters_form = dbc.Card( [
    dbc.CardHeader( [
        dbc.Container( [
            dbc.Row( [
                dbc.Col( 'Parametres Megamicros', width=5 ),
                dbc.Tooltip( "Réaliser un autotest", target="station-selftest-btn", placement="top"  ),
				dbc.Col( dbc.Button( "auto-test", id="station-selftest-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=3 ),
                dbc.Tooltip( "télécharger les paramètres actuels", target="station-download-btn", placement="top"  ),
				dbc.Col( dbc.Button( "Download", id="station-download-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=2 ),
                dbc.Tooltip( "Uploader les paramètres actuels vers le serveur", target="station-upload-btn", placement="top"  ),
				dbc.Col( dbc.Button( "Upload", id="station-upload-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=2 ),
            ], align="center"  )
        ] )
    ] ),
    dbc.CardBody( [
        dbc.Container( [
            dbc.Row( [
                dbc.Col( dbc.Label("Sampling F. (Hz)", html_for="station-sr-input" ), width=3 ),
                dbc.Col( dbc.Input( className="me-sm-2 h-75", type="text", id="station-sr-input", value="50000" ) ),
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Duration (s)", html_for="station-duration-input" ), width=3 ),
                dbc.Col( dbc.Input( className="me-sm-2 h-75", type="text", id="station-duration-input", value="1" ) ),             
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Fuseau 1", html_for="station-mems-checklist-1" ), width=3 ),
                dbc.Col(
                    dbc.Checklist( 
                        options=[
                            {"label": "1", "value": 0}, {"label": "2", "value": 1}, {"label": "3", "value": 2}, {"label": "4", "value": 3},
                            {"label": "5", "value": 4}, {"label": "6", "value": 5}, {"label": "7", "value": 6}, {"label": "8", "value": 7},
                        ],   
                        value=[],
                        id="station-mems-checklist-1",
                        inline=True
                    )
                )
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Fuseau 2", html_for="station-mems-checklist-2" ), width=3 ),
                dbc.Col(
                    dbc.Checklist( 
                        options=[
                            {"label": "1", "value": 0}, {"label": "2", "value": 1}, {"label": "3", "value": 2}, {"label": "4", "value": 3},
                            {"label": "5", "value": 4}, {"label": "6", "value": 5}, {"label": "7", "value": 6}, {"label": "8", "value": 7},
                        ],   
                        value=[],
                        id="station-mems-checklist-2",
                        inline=True
                    )
                )
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Fuseau 3", html_for="station-mems-checklist-3" ), width=3 ),
                dbc.Col(
                    dbc.Checklist( 
                        options=[
                            {"label": "1", "value": 0}, {"label": "2", "value": 1}, {"label": "3", "value": 2}, {"label": "4", "value": 3},
                            {"label": "5", "value": 4}, {"label": "6", "value": 5}, {"label": "7", "value": 6}, {"label": "8", "value": 7},
                        ],   
                        value=[],
                        id="station-mems-checklist-3",
                        inline=True
                    )
                )
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Fuseau 4", html_for="station-mems-checklist-4" ), width=3 ),
                dbc.Col(
                    dbc.Checklist( 
                        options=[
                            {"label": "1", "value": 0}, {"label": "2", "value": 1}, {"label": "3", "value": 2}, {"label": "4", "value": 3},
                            {"label": "5", "value": 4}, {"label": "6", "value": 5}, {"label": "7", "value": 6}, {"label": "8", "value": 7},
                        ],   
                        value=[],
                        id="station-mems-checklist-4",
                        inline=True
                    )
                )
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Counter", html_for="station-counter-switch" ), width=3 ),
                dbc.Col( dbc.Switch( id="station-counter-switch", value=False ), width=2 ),
                dbc.Col( dbc.Label("Counte skip", html_for="station-counterskip-switch" ), width=3 ),
                dbc.Col( dbc.Switch( id="station-counterskip-switch", value=False ), width=1 ),
            ] ),
            dbc.Row( [
                dbc.Col( dbc.Label("Buffer(s) size", html_for="station-buffersize-input" ), width=3 ),
                dbc.Col( dbc.Input( className="me-sm-2 h-75", type="number", id="station-buffersize-input", value="256" ), width=4 ), 
                dbc.Col( dbc.Label("Number", html_for="station-buffernumber-input" ), width=2 ),
                dbc.Col( dbc.Input( className="me-sm-2 h-75", type="number", id="station-buffernumber-input", value="8" ), width=3 ),             
            ] ),
        ] )
    ] )
] )


figure = dict(
    #data=[{"x": [], "y": []}],
    data=[{"y": []}],
    layout = {
        'xaxis': {'range': [0,255]},
        'yaxis': {'range': [-1,+1]},
        'title': 'MEMS', 
        'title_font_color': 'rgba(240,240,240,1)',
        'paper_bgcolor': 'rgba(18,18,18,1)',
        'plot_bgcolor': 'rgba(18,18,18,1)',
        'xaxis_color': 'rgba(36,46,58,1)',
        'yaxis_color': 'rgba(36,46,58,1)',
    }

    # layout=dict(
    #     xaxis=dict(range=[0, 255]), 
    #     yaxis=dict(range=[-30000, 30000]), 
    #     title='MEMS', 
    #     title_font_color="rgba(240,240,240,1)",
    #     paper_bgcolor='rgba(18,18,18,1)',
    #     plot_bgcolor='rgba(18,18,18,1)',
    #     xaxis_color='rgba(36,46,58,1)',
    #     yaxis_color='rgba(36,46,58,1)',
    #     autosize=False,
    # ),
)


station_display = dbc.Card( [
    dbc.CardHeader( [
        dbc.Container( [
            dbc.Row( [
                dbc.Col( 'Visualisations', width=5 ),
                dbc.Tooltip( "Lancer une exécution", target="station-display-go-btn", placement="top"  ),
                dbc.Col( dbc.Button( [html.I( className="bi bi-arrow-clockwise")], id="station-display-go-btn", size="sm",  outline=True, color="dark", n_clicks=0 ), width=1 ),
                dbc.Tooltip( "Lancer une exécution", target="station-display-stop-btn", placement="top"  ),
				dbc.Col( dbc.Button( "Stop", id="station-display-stop-btn", size="sm",  outline=True, color="danger", n_clicks=0 ), width=2 ),
                dbc.Tooltip( "Sélectionnez une activité", target="station-process-select", placement="top"  ),
                dbc.Col( [
                    dcc.Dropdown( id="station-graph-select", placeholder="---", options=[
                        {'label': 'Microphones', 'value': 'activity'}, 
                        {'label': 'Signaux', 'value': 'signal'}, 
                        {'label': 'Spectres', 'value': 'spectrum'}, 
                    ], value='activity' ),
                ], width=4 ),
            ], align="center"  )
        ] )
    ] ),
    dbc.CardBody( [
        dbc.Container( [
            dbc.Row( [
                dbc.Col( dcc.Graph( 
                    id='station-display-mems', 
                    style={"height":"400px"},
                    figure=dict( figure )
                ) )
            ] )
        ] )
    ] )
] )


station_control_card = dbc.Card( [

    dbc.CardHeader( [
        dbc.Container( [
            dbc.Row( [
                dbc.Col( 
                    dbc.Container( [
                        dbc.Row( [
                            dbc.Col( "Connexion à une station"  )
                        ] )
                    ] ), width=5
                ),
                dbc.Col( 
                    dbc.Container( [ 
                        dbc.Row( [
                        ], align="center" )
                    ] ), width=7
                )
            ], align="center"  )
        ])

    ] ),
    dbc.CardBody( [ 
        dbc.Container( [
            dbc.Row( [ 
                dbc.Col( station_connect_form, width=6 ),
                dbc.Col( station_display, width=6 ),
            ] ),
            dbc.Row( [
                dbc.Col( station_parameters_form, width=6 ),
            ] ),
        ], className="vstack gap-2"  )
    ], className="dbc"  ),

	dcc.Store( id='station-card-store' ),
    dcc.Store( id='server-store' ),
    WebSocket( id="station-ws" ),
    html.Div( id='websocket-status'),
    html.Div( id='websocket-error'),
    html.Div( id='server-status'),
    html.Div( children="", id='tmp-message' ),
    dcc.Store( id='settings-store', data={} ),

] )


# ----------------------------------------------------------------
# Control the websocket status
# Check whether connection is open or closed
# ----------------------------------------------------------------
@callback(
    Output( 'websocket-status', 'children' ),
    Input( 'station-ws', 'state' ),
    prevent_initial_call=True
)
def onWsStatus( ws_state ):

    if ws_state is None:
        raise PreventUpdate
    
    if ws_state['readyState'] == WS_OPEN:
        log.info( f" .Succesfully connected to remote server" )
        return  cpn.display_success_msg( 'Succesfully connected to remote server' )
        
    elif ws_state['readyState'] == WS_CLOSED:
        # Connection is closed: no more messages -> exit
        log.info( f" .Connection closed by server or server down. Reason: {ws_state['reason']}, code: {ws_state['code']}" )
        return  cpn.display_info_msg( 'Connection closed by server or server down' )


# ----------------------------------------------------------------
# Websocket error handling
# ----------------------------------------------------------------
@callback(
    Output("websocket-error", "children"), 
    Input("station-ws", "error"),
    prevent_initial_call=True
)
def onWsError( error ):

    if error is None:
        raise PreventUpdate
    
    log.info( f" .Websocket error: {error}" )
    return cpn.display_error_msg( 'Connexion au serveur perdue ou impossible' )



# ----------------------------------------------------------------
# Read values from formular and save them the client-side settings store
# ----------------------------------------------------------------
@callback(
    Output( 'settings-store', 'data' ),
    Input( 'station-sr-input', 'value' ),
    Input( 'station-duration-input', 'value' ),
    Input( 'station-counter-switch', 'value' ),
    Input( 'station-counterskip-switch', 'value' ),
    Input( 'station-buffersize-input', 'value' ),
    Input( 'station-buffernumber-input', 'value' ),
    Input( 'station-mems-checklist-1', 'value' ),
    Input( 'station-mems-checklist-2', 'value' ),
    Input( 'station-mems-checklist-3', 'value' ),
    Input( 'station-mems-checklist-4', 'value' ),
    State( 'settings-store', 'data' ),
    #prevent_initial_call=True
)
def onFormUpdate( sampling_frequency, duration, counter: bool, counter_skip: bool, buffer_size: int, buffer_number: int, mems1, mems2, mems3, mems4, settings_store ):

    # init settings store (should be coherent with the option's values set in the layout)
    if not settings_store:
        settings_store = {
            'sampling_frequency': 50000,
            'clockdiv': 9,
            'duration': 1,
            'counter': False,
            'counter_skip': False,
            'status': False,
            'pluggable_beams_number': 4,
            'available_mems': [],
            'mems': [],
            'available_analogs': [],
            'analogs': [],
            'usb_buffer_length': 256,
            'usb_buffers_number': 8
        }

    # check event
    triggered = ctx.triggered_id

    if triggered == 'station-sr-input' and sampling_frequency:
        settings_store['sampling_frequency'] = int( float( sampling_frequency ) )

    if triggered == 'station-duration-input' and duration:
        settings_store['duration'] = int( duration )

    if triggered == 'station-counter-switch':
        settings_store['counter'] = counter

    if triggered == 'station-counterskip-switch' and counter:
        settings_store['counter_skip'] = counter_skip

    if triggered == 'station-buffersize-input' and buffer_size is not None and buffer_size > 0:
        settings_store['usb_buffer_length'] = buffer_size

    if triggered == 'station-buffernumber-input' and buffer_number is not None and buffer_number > 0 and buffer_number <= 32:
        settings_store['usb_buffers_number'] = buffer_number

    if triggered == 'station-mems-checklist-1' or triggered == 'station-mems-checklist-2' or triggered == 'station-mems-checklist-3' or triggered == 'station-mems-checklist-4':
        mems = [i for i in range(8) if i in mems1] + [i+8 for i in range(8) if i in mems2] + [i+16 for i in range(8) if i in mems3] + [i+24 for i in range(8) if i in mems4]
        settings_store['mems'] = mems

    return settings_store



# ----------------------------------------------------------------
# Control the parameters formular card every time a websocket message is received
# Messages are supposed json encoded
# ----------------------------------------------------------------
@callback(
    Output( 'station-sr-input', 'value' ),
    Output( 'station-duration-input', 'value' ),
    Output( 'station-counter-switch', 'value' ),
    Output( 'station-counterskip-switch', 'value' ),
    Output( 'station-buffersize-input', 'value' ),
    Output( 'station-buffernumber-input', 'value' ),
    [Output( 'station-mems-checklist-1', 'value' ), Output( 'station-mems-checklist-1', 'options' )],
    [Output( 'station-mems-checklist-2', 'value' ), Output( 'station-mems-checklist-2', 'options' )],
    [Output( 'station-mems-checklist-3', 'value' ), Output( 'station-mems-checklist-3', 'options' )],
    [Output( 'station-mems-checklist-4', 'value' ), Output( 'station-mems-checklist-4', 'options' )],
    Output( 'server-status', 'children' ),
    Input( 'station-ws', 'message'),
    prevent_initial_call=True
)
def onWsMessage( ws_message ):
    
    output: cpn.Output = cpn.Ouput( [
        'sr_value', 'duration_value', 'counter_value', 'counterskip_value', 'buffersize_value', 'buffernumber_value', 'mems_values_1', 'mems_options_1', 'mems_values_2', 
        'mems_options_2', 'mems_values_3', 'mems_options_3', 'mems_values_4', 'mems_options_4', 'server_status_children' 
    ] )

    message = json.loads( ws_message['data'] )

    if 'request' in message:   

        # Error message from server
        if 'type' in message and message['type'] == 'status' and message['response'] == 'error':
            log.info( f" .Server error: {message['message']}")
            return output.generate( server_status_children = cpn.display_error_msg( message['message'] ) )

        # connection
        if message['request'] == 'connection':
            if message['type'] == 'status' and message['response'] == 'ok':
                log.info( f" .Connection accepted by server")
                return output.generate()
            else:
                log.info( f" .Unknown type or response for 'connection' request" )
                return output.generate( server_status_children = cpn.display_error_msg( 'Unknown response from server' ) )

        # Run accepted
        elif message['request'] == 'run':
            if message['type'] == 'status':
                if message['response'] == 'ok':
                    log.info( f" .Run accepted by server" )
                    return output.generate()
                elif message['response'] == 'completed':
                    log.info( f" .Run completed by server" )
                    return output.generate( server_status_children = cpn.display_info_msg( 'Run completed by server' ) )
                else:
                    log.info( f" .Unknown response [{message['response']} for 'run' request" )
                    return output.generate( server_status_children = cpn.display_error_msg( 'Unknown response from server' ) )
            else:
                log.info( f" .Unkown type of response from server for 'run' request" )
                return output.generate( server_status_children = cpn.display_error_msg( 'Unknown response from server' ) )

        # Selftest
        elif message['request'] == 'selftest' and message['type'] == 'status':
            if message['response'] == 'ok':
                log.info( f" .Selftest performed successfully" )
                return output.generate( server_status_children = cpn.display_success_msg( 'Selftest performed successfully' ) )
            else:
                log.info( f" .Unknown response [{message['response']} for 'selftest' request" )
                return output.generate( server_status_children = cpn.display_error_msg( 'Unknown response from server' ) )

        # Settings
        elif message['request'] == 'settings' and message['type'] == 'response':
            log.info( f" .Settings received successfully" )
            print( 'settings = ', message )
            
            return output.generate( 
                sr_value = str( message['response']['sampling_frequency'] ),
                duration_value = str( message['response']['duration'] ),
                counter_value = message['response']['counter'],
                counterskip_value = message['response']['counter_skip'],
                buffersize_value = message['response']['usb_buffer_length'],
                buffernumber_value = message['response']['usb_buffers_number'],
                mems_values_1 = [i for i in range(8) if i in message['response']['mems']],
                mems_values_2 = [i for i in range(8) if i+8 in message['response']['mems']],
                mems_values_3 = [i for i in range(8) if i+16 in message['response']['mems']],
                mems_values_4 = [i for i in range(8) if i+24 in message['response']['mems']],
                server_status_children = cpn.display_success_msg( 'Selftest performed successfully' ) 
            )
  
        # Unknown request 
        else:
            log.info( f" .Received message to unknown request [{message['request']}" )
            return output.generate( server_status_children = cpn.display_success_msg( 'Received message to unknown request' ) )
        
    else:
        # unknown message
        log.info( f" .Received unknown message from server: {message}")
        return output.generate( server_status_children = cpn.display_error_msg( f'Received unknown message from server: {message}' ) )



# ----------------------------------------------------------------
# Client-side callback for getting signals from websocket and displaying them
# Data are supposed filtered before. Only binary data are transmitted on the binary input
# ----------------------------------------------------------------
clientside_callback(
   """
   function( data ) {
        if(!data){console.log("init");return {};}
        const y = new Int32Array( data.data );
        const yy = Float32Array.from(y, x => x*3.779e-6);
        return {
            'data': [{y: yy, type: "scatter"}], 
            'layout': {
                'xaxis': {'range': [0,255]},
                'yaxis': {'range': [-1,+1]},
                'paper_bgcolor': 'rgba(18,18,18,1)', 
                'plot_bgcolor': 'rgba(18,18,18,1)',
            }
        }
   }
   """,
   Output( 'station-display-mems', 'figure' ),
   Input( 'station-ws', 'binary' ),
   prevent_initial_call=True
)


# ----------------------------------------------------------------
# Connect/disconnect/send to/from/to websocket
# Please beware that you cannot use no_update as output to prevent inapropriate connecting or disconnecting
# Values sent to server are thoses stored in the settings store
# ----------------------------------------------------------------
@callback(
    Output( 'station-ws', 'url' ), 
    Output( 'station-ws', 'close' ),
    Output( 'station-ws', 'send' ),
    Input( 'station-connect-button', 'n_clicks'),
    Input( 'station-disconnect-button', 'n_clicks'),
    Input( 'station-selftest-btn', 'n_clicks'),
    Input( 'station-download-btn', 'n_clicks'),
    Input( 'station-upload-btn', 'n_clicks'),
    Input( 'station-display-go-btn', 'n_clicks' ),
    Input( 'station-display-stop-btn', 'n_clicks'),
    State( 'station-host-input', 'value' ),
    State( 'station-port-input', 'value' ),
    State( 'settings-store', 'data' ),
    prevent_initial_call=True
)
def wsSend( connect_button, disconnect_button, selftest_button, download_button, upload_button, display_go, display_stop, host_value, port_value, settings_store ):

    clicked = ctx.triggered_id

    if clicked == 'station-connect-button':
        return f"ws://{host_value}:{port_value}", None, None

    elif clicked == 'station-disconnect-button':
        # generate an error:
        # An object was provided as `children` instead of a component, string, or number (or list of those).
        # this comes from the React part
        # The WinSocket dash_extensions component should be upgraded with open and close methods
        return None, "closing", None
    
    elif clicked == 'station-selftest-btn':
        # Request an autotest
        request = {'request': 'selftest'}
        return None, None, json.dumps( request )
    
    elif clicked == 'station-download-btn':
        # Request parameters download
        request = {'request': 'settings'}
        return None, None, json.dumps( request )
    
    elif clicked == 'station-upload-btn':
        # Send parameters to server
        request = {'request': 'settings', 'settings': {
            'sampling_frequency': settings_store['sampling_frequency'],
            'duration': settings_store['duration'],
            'counter': settings_store['counter'],
            'counter_skip': settings_store['counter_skip'],
            'mems': settings_store['mems'],
            'usb_buffer_length': settings_store['usb_buffer_length'],
            'usb_buffers_number': settings_store['usb_buffers_number'],
        } }
 
        print( 'request=', request )

        return None, None, json.dumps( request )

    elif clicked == 'station-display-go-btn':
        # Run Megamicros
        request = {'request': 'run'}
        return None, None, json.dumps( request )
    
    elif clicked == 'station-display-stop-btn':
        # Stop Megamicros run
        request = {'request': 'halt'}
        return None, None, json.dumps( request )        
            
    
# ----------------------------------------------------------------
# Errors 
# ----------------------------------------------------------------

@callback(
    Output( 'station-sr-input', 'valid' ),
    Output( 'station-sr-input', 'invalid' ),
    Output( 'station-duration-input', 'valid' ),
    Output( 'station-duration-input', 'invalid' ),
    Output( 'station-buffernumber-input', 'valid' ),
    Output( 'station-buffernumber-input', 'invalid' ),
    Output( 'station-buffersize-input', 'valid' ),
    Output( 'station-buffersize-input', 'invalid' ),
    Input( 'station-sr-input', 'value' ),
    Input( 'station-duration-input', 'value' ),
    Input( 'station-buffernumber-input', 'value' ),
    Input( 'station-buffersize-input', 'value' ),
)
def onFormUpdateValidate( sampling_frequency, duration, buffers_number, buffers_size ):

    output: cpn.Output = cpn.Ouput( [
        'sr_valid', 'sr_invalid', 'duration_valid', 'duration_invalid', 'buffernumber_valid', 'buffernumber_invalid',
        'buffersize_valid', 'buffersize_invalid'
    ] )

    trigerred = ctx.triggered_id

    if trigerred == 'station-sr-input':
        if sampling_frequency is None or sampling_frequency == '':
            return output.generate( sr_valid=False, sr_invalid=True )
        else:
            return output.generate( sr_valid=True, sr_invalid=False )
        
    elif trigerred == 'station-duration-input':
        if duration is None or duration == '':
            return output.generate( duration_valid=False, duration_invalid=True )
        else:
            return output.generate( duration_valid=True, duration_invalid=False )

    elif trigerred == 'station-buffernumber-input':
        if buffers_number is None or buffers_number <= 0 or buffers_number > 32:
            return output.generate( buffernumber_valid=False, buffernumber_invalid=True )
        else:
            return output.generate( buffernumber_valid=True, buffernumber_invalid=False )

    elif trigerred == 'station-buffersize-input':
        if buffers_size is None or buffers_size <= 0:
            return output.generate( buffersize_valid=False, buffersize_invalid=True )
        else:
            return output.generate( buffersize_valid=True, buffersize_invalid=False )

    else:
        return False, False, False, False, False, False, False, False
            
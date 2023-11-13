# megamicros_aiboard/apps/aibord/pages/p_config.py
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
Megamicors Aiboard connection page

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import json
import dash
from dash import dcc, html, callback, Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

from megamicros.log import log
from megamicros.aiboard.session import session


dash.register_page( 
    __name__,
    path='/config',
    title='Configuration',
    name='Paramètres',
    location='sidebar',
    order=1
)

connect_form = dbc.Card( [
    dbc.Form( [
        dbc.CardHeader( "Précisez votre login, adresse email et mot de passe d'accès enregistrés sur la base de donnée " ),
        dbc.CardBody( [
            html.Div( [
                dbc.Label("Base de donnée", html_for="select-database", width="3" ),
                dcc.Dropdown( id="select-database", value="http://127.0.0.1:8000" ),
                dbc.Label("Login", html_for="input-login", width="2" ),
                dbc.Input( className="form-control me-sm-2", type="text", id="input-login", value="admin", placeholder="Enter login" ),
                dbc.Label("Email", html_for="input-email", width="2" ),
                dbc.Input( type="email", id="input-email", value="bruno.gas@beamea.com", placeholder="Enter email" ),
                dbc.Label("Password", html_for="input-password", width="2" ),
                dbc.Input( type="password", id="input-password", value="htr4807", placeholder="Enter password" ),
            ] ),
            html.Br(),
            html.Div( [
                dbc.Label( "", html_for="submit-login" ),
                dbc.Button( children="Login", id="submit-login", color="primary" ),
                dcc.Loading( id="submit-login-loading", type="circle" ),
            ] )
        ] ),
    ], id="login-formular", action="/home" ),
    html.Div( id='login-message' ),
], className="dbc" )

logout_form = dbc.Card( [
    dbc.CardHeader( "Se déconnecter" ),
    dbc.CardBody( [ 
        dbc.Button(children="Logout", id="submit-logout", color="primary")
    ] ),
    html.Div( id='logout-message' ),
] )


layout = html.Div(children=[
    dcc.Location( id='url' ),

    html.H1(children='Connexion à la base de donnée'),
    html.Br(),

    dbc.Container( [
        dbc.Row( [
            dbc.Col( [
                connect_form,
            ], width=7 ),
            dbc.Col( [
                logout_form,
            ], width=5 )
        ] ),
    ] ),
])




"""
On connect, save configuration
"""
@callback(
    Output( 'badge-connected', 'children' ),
    Output( 'badge-connected', 'text_color' ),
    Output( 'flag-dbase', 'children' ),
    Output( 'config-store', 'data' ),
    Output( 'login-message', 'children' ),
    Output( 'submit-login-loading', 'children' ),
    Input( 'submit-login', 'n_clicks' ),
    Input( 'submit-logout', 'n_clicks' ),
    State( 'select-database', 'value'),
    State( 'input-login', 'value'),
    State( 'input-email', 'value'),
    State( 'input-password', 'value'),
    State( 'config-store', 'data' )
)
def onConnectDisconnect( n_clicks_in, n_clicks_out, dbhost, login, email, password, config_store  ):

    clicked = ctx.triggered_id
    config = None

    if clicked is None or (n_clicks_in==None and n_clicks_out==None):
        """ Nothing to do """
        raise PreventUpdate

    """
    Try to connect or disconnect
    """
    try:
        if config_store is not None:
            config = json.loads( config_store ) 

        if clicked=='submit-login':
            if config is not None and config['connected'] == True:
                raise Exception( "Vous êtes déjà connecté! Deconnectez-vous d'abord" )

            session.open( dbhost=dbhost, login=login, email=email, password=password )
            log.info( ' .Store configuration in navigator...' )
    
            config = {
                'host': dbhost,
                'login': login,
                'email': email,
                'password': password,
                'audio_device': 0,
                'connected': True
            }

            return 'Connected', 'info', dbhost, json.dumps( config ), no_update, no_update

        else:
            if config is None or config['connected'] == False:
                raise Exception( "Vous n'êtes pas connecté !" )

            session.close()

            config['connected'] = False

            return 'Not connected', 'secondary', '', json.dumps( config ), no_update, no_update


    except Exception as e:
        log.info( f" .Connection failed: {e}")
        return 'Not connected', 'secondary', '', no_update, html.Div( [
            dbc.Modal( [ dbc.ModalHeader( dbc.ModalTitle("Une erreur est survenue" ) ), dbc.ModalBody( f"{e}" ) ], is_open=True ),
        ] ), no_update



"""
Init formulars at page view
"""
@callback(
    Output(component_id='select-database', component_property='options'),
    Input('url', 'pathname')
)
def on_page_view( pathname ):
    """
    Set here all known database hosts
    """
    database_hosts = [
        {"label": 'http://dbwelfare.biimea.io', "value": 'http://dbwelfare.biimea.io'},
        {"label": 'http://127.0.0.1:8000', "value": 'http://127.0.0.1:8000'}
    ]

    return database_hosts


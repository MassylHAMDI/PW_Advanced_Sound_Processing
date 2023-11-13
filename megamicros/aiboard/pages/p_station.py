# megamicros_aiboard/apps/aibord/pages/p_station.py
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
Megamicors Aiboard station control page

MegaMicros documentation is available on https://readthedoc.biimea.io
"""


import dash
import json
from dash import html, dcc, callback, Input, Output, State, ctx, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from megamicros.aiboard.cards import station
from megamicros.log import log



"""
About using Websockets with Dash Plotly: https://community.plotly.com/t/support-for-websockets/19348/22
Websockt ReactJS component: https://www.dash-extensions.com/components/websocket
writen on javascript websocket : https://javascript.info/websocket
"""

DEFAULT_GRAPH_THEME = "plotly_dark"
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 9002

LAYEOUT_STYLE = {
    "max-width": "100%",
    "padding": 0,
    "padding-top": "20px", 
    "margin": 0, 
}


dash.register_page( 
    __name__,
    path='/station',
    title='Contrôle d\'une station Megamicros',
    name='Station',
    location='sidebar',
    order=4
)


"""
Main page layout
"""
layout = html.Div(children=[
    dcc.Location( id='url' ),

    html.H1(children='Contrôle d\'une station Megamicros'),
	html.Div( id='labeling-page-message' ),
    
    dbc.Container( [
		dbc.Row( [
			dbc.Col( station.station_control_card, width=12),
		] ),
	], className="vstack gap-3", style=LAYEOUT_STYLE )

] )



# Write to websocket.
"""
@callback(
    Output("ws", "send"), 
    [Input("input", "value")]
)
def send(value):

    clicked = ctx.triggered_id

    if clicked is None:
        raise PreventUpdate
    
    print( "sending data...")

    value = {
        "request": "selftest",
    }

    return json.dumps( value )


# Read from websocket.
@callback(
    Output("message", "children"), 
    [Input("ws", "message")]
)
def message(message):
    if message is None:
        return 'init'
    else:
        return f"Response from websocket: {message['data']}"  # read from websocket

"""

"""
Init formulars at page view
"""
@callback(
    Output("labeling-page-message", "children"), 
    Input('url', 'pathname')
)
def on_page_view( pathname ):
    """
    """
    raise PreventUpdate




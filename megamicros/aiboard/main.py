# megamicros_aiboard/apps/aiboard/main.py
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
# Megamicros AiBoard application main entry

MegaMicros documentation is available on https://readthedoc.biimea.io

Dependencies:
* sounddevice
* numpy
* scipy
* requests

Styling: https://hellodash.pythonanywhere.com/theme-explorer/about 
Dash extension: https://www.dash-extensions.com/
Dash plotly: https://dash.plotly.com
Dash multi-pages applications: https://dash.plotly.com/urls
About range sliders: see https://plotly.com/python/range-slider/
Spectrogram: https://stackoverflow.com/questions/38701969/dynamic-spectrum-using-plotly
Boostrap: https://getbootstrap.com/
Boostrap for Dash: https://dash-bootstrap-components.opensource.faculty.ai/

Start:
$ > export PYTHONPATH=your_install_path/Megamicros_directory/src

"""

import argparse

# for wabsocket with socketio
#from flask_socketio import SocketIO

from dash import Dash, html, dcc
import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from megamicros.log import log, formats_str, logging

#from dash_extensions.enrich import DashProxy, MultiplexerTransform

#app = Dash(__name__, use_pages=True, external_stylesheets=[dbc.themes.BOOTSTRAP])
#app = DashProxy(__name__, use_pages=True, external_stylesheets=[dbc.themes.SLATE], transforms=[MultiplexerTransform()])
dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
app = Dash(
    __name__, 
    use_pages=True, 
    external_stylesheets=[dbc.themes.SLATE, dbc_css, dbc.icons.BOOTSTRAP],
    #suppress_callback_exceptions=True
)
app.config.suppress_callback_exceptions = True

# for websockets with scketio
#socketio = SocketIO(app.server, logger=True, engineio_logger=True)

""" 
the style arguments for the navigation bar 
"""
NAVBAR_STYLE = {
    "padding": "1rem 1rem"
}

""" 
the style arguments for the sidebar. We use position:fixed and a fixed width 
"""
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": "2rem",
    "left": 0,
    "bottom": 0,
    "width": "18rem",
    "padding": "4rem 1rem",
    #"background-color": "#f8f9fa",
    #"background-color": "#000000",
}

""" 
the styles for the main content position it to the right of the sidebar 
and add some padding 
"""
CONTENT_STYLE = {
    "margin-top": "5.2rem",
    "margin-left": "18rem",
    "margin-right": "2rem",
    "padding": "2.5rem 1rem",
}

#BIIMEA_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
BIIMEA_LOGO = "./assets/logo-no-background.svg"
#BIIMEA_LOGO = "./assets/biimea-low-resolution-logo-white-on-transparent-background.png"
         
#DEFAULT_LOGGER_MODE = logging.INFO
DEFAULT_LOGGER_MODE = logging.DEBUG


"""
The navigation bar display
"""
navbar = dbc.Navbar(
    dbc.Container( [
        dbc.Row( [
            dbc.Col( [
                html.A( 
                    html.Img( src=BIIMEA_LOGO, height="50px" ), 
                    href="http://biimea.com",
                    style={"textDecoration": "none"}
                )
            ] ),
            #dbc.Col(
            #    html.A( 
            #        dbc.NavbarBrand( "Biimea", className="ms-2" ),
            #        href="http://biimea.com",
            #        style={"textDecoration": "none"}
            #    )
            #),
            dbc.Col( 
                dbc.Badge( "Not connected",  id="badge-connected", text_color="secondary", color="black", className="border me-1" ), 
                #width={"size": 4, "offset": 1} 
            ),
            dbc.Col(
                dbc.Col( dbc.Button( [html.I( className="bi bi bi-power")], id="p0-main-power-btn", size="lg",  outline=True, n_clicks=0, color="primary" ) ),
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
        ], 
        align="center", 
        justify="between" )
    ] ),
    fixed="top",
    color="#000000",
    dark=True,
    style=NAVBAR_STYLE
)


"""
The left fixed sidebar display
"""
sidebar = dbc.Container( [
    dbc.Card( [ 
        dbc.Row( [
            dbc.Col( html.H2( "AiBoard", className="display-4", style={"text-align": "center"} ) ),
        ] ),
        html.Hr(),
        dbc.Row( [
            dbc.Col( html.P( "The AI tools for MegaMicro arrays", className="lead", style={"text-align": "center"} ) )
        ] ),
        html.Hr(),
        dbc.Row( [
            dbc.Nav(
                [
                    dbc.NavLink( page['name'], href=page['relative_path'], active="exact", style={"margin": "0.5rem 0.5rem"} )
                    for page in dash.page_registry.values() if 'location' in page and page['location'] == 'sidebar'
                ],
                vertical=True,
                pills=True,
                style={"padding": "2rem 1rem"},
            ),
        ] ),
    ], body=True, className="dbc", color="#000000", style={"border-color": "grey"} ),

    dbc.Card( [ 
        dbc.Row( [
            dbc.Col( [ 
                html.H4( "Base de donnée", className="display-8", style={"text-align": "center"} ),
                html.P( '', id='flag-dbase', style={"text-align": "center", "padding": "0.5rem 0.5rem"} ), 
            ] ),
            html.Div( id="test-test" )
        ] ),
    ], body=True, className="dbc", color="#000000", style={"border-color": "grey", "margin-top": "1rem"} ),

    dcc.Store( id='config-store' ),

], style=SIDEBAR_STYLE )


"""
The global page layout
"""
app.layout = html.Div( [sidebar, navbar, dash.page_container], style=CONTENT_STYLE )




"""
Connection callback"""
@app.callback(
    Output( 'p0-main-power-btn', 'color' ),
    Input( 'p0-main-power-btn', 'n_clicks' )
)
def on_page_view( n_clicks ):

    clicked = ctx.triggered_id

    if clicked is None:
        raise PreventUpdate
    else:
        if ( n_clicks % 2 ) == 0:
            return "success"
        else:
            return "primary"




"""
Main page callback
"""
@app.callback(
    Output( 'test-test', 'children' ),
    Input( 'url', 'pathname' )
)
def on_page_view( pathname ):
    print( 'pathname=', pathname )

    return "cool !"



if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument( "-v", "--verbose", help=f"set the verbose level (debug, info, warning, error, fatal)" )
    args = parser.parse_args()
    
    """ set default logger level """
    verbose_mode = DEFAULT_LOGGER_MODE
    log.setLevel( DEFAULT_LOGGER_MODE )

    log.info( f"Starting Aiboard..." )

    """ process logger level command line argument """
    if args.verbose:
        """ user has set the verbose argument """
        verbose_arg : str = args.verbose
        verbose_mode = formats_str( verbose_arg )
        if verbose_mode is None:
            log.warning( f"Unknown verbose mode '{verbose_arg}'. Set to default 'info' mode. Please correct the command line argument 'verbose'" )
            verbose_mode = DEFAULT_LOGGER_MODE
    else:
        verbose_mode = DEFAULT_LOGGER_MODE

    log.setLevel( verbose_mode )
    verbose_arg = formats_str( verbose_mode )
    log.info( f" .Set verbose level to [{verbose_arg}]" )
 

    app.run_server(debug=True)

    # for websocket with socketio
    #socketio.run(app.server, port=8050, debug=True)

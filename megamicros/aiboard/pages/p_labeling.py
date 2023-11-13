import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from megamicros.aiboard.cards import sourcefile
from megamicros.log import log

"""
About range sliders: see https://plotly.com/python/range-slider/
Spectrogram: https://stackoverflow.com/questions/38701969/dynamic-spectrum-using-plotly
Boostrap: https://dash-bootstrap-components.opensource.faculty.ai/
"""

DEFAULT_ENERGY_SAMPLES_NUMBER = 1000
DEFAULT_GRAPH_THEME = "plotly_dark"
DEFAULT_FRAME_DURATION = 0.025
DEFAULT_GRAPH_SAMPLES_NUMBER = 10000

"""
Following constants are hardcoded in database
Should be loaded from database...
"""
FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4

LAYEOUT_STYLE = {
    "max-width": "100%",
    "padding": 0,
    "padding-top": "20px", 
    "margin": 0, 
}


dash.register_page( 
    __name__,
    path='/labeling',
    title='Etiquetage des données',
    name='Etiquetage',
    location='sidebar',
    order=3
)


"""
Main page layout
"""
layout = html.Div(children=[
    dcc.Location( id='url' ),

    html.H1(children='Etiquetage des données'),
	html.Div( id='labeling-page-message' ),
    
    dbc.Container( [
		dbc.Row( [
			dbc.Col( sourcefile.sourcefile_select_card, width=12),
		] ),
	], className="vstack gap-3", style=LAYEOUT_STYLE )

] )



"""
Init page view: check if user is connected to a database

@callback(
    Output( 'labeling-page-message', 'children' ),
    Input( 'url', 'pathname'),
	State( 'config-store', 'data' )
)
def on_page_view( pathname, config_store ):

	log.info( f" .Labeling page view request")
	if config_store is None or 'host' not in config_store:
		log.info( f" .Can't serve page view: user is not connected")
		return  dbc.Modal( [ 
			dbc.ModalHeader( 
			dbc.ModalTitle("Erreur" ) ), 
			dbc.ModalBody( f"Vous n'êtes pas connecté à une base de donnée" ) 
		], is_open=True ),

	else:
	    return no_update
"""
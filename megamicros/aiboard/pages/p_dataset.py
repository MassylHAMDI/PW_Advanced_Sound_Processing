
import dash
from dash import html, callback, Input, Output, State, dcc, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from megamicros.aiboard.cards import dataset, label
from megamicros.log import log

DEFAULT_GRAPH_THEME = "plotly_dark"


dash.register_page( 
    __name__,
    path='/dataset',
    title='Génération des bases',
    name='Dataset',
    location='sidebar',
    order=4
)


LAYEOUT_STYLE = {
    "max-width": "100%",
    "padding": 0,
    "padding-top": "20px", 
    "margin": 0, 
}


"""
Main page layout
"""
layout = html.Div(children=[
    dcc.Location( id='url' ),

    html.H1(children='Génération des bases d\'apprentissage'),
	html.Div( id='dataset-page-message' ),
	  
    dbc.Container( [
		dbc.Row( [
			dbc.Col( dataset.dataset_card, width=6),
            dbc.Col( label.select_card, width=6),
		] ),
	], className="vstack gap-3", style=LAYEOUT_STYLE )


] )

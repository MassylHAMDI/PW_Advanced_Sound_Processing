# megamicros_aiboard/apps/aibord/pages/p_label.py
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
Megamicors Aiboard labels configuring page

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from datetime import datetime
import json
import dash
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from megamicros.aiboard.cards import context, label, tag, tagcat, labeling


"""
Following constants are hardcoded in database
Should be loaded from database...
"""
FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4

CONTEXT_TYPE_A_PRIORI = 1
CONTEXT_TYPE_A_PPOSTERIORI = 2
CONTEXT_TYPES = [{'label': 'A priori', 'value': CONTEXT_TYPE_A_PRIORI}, {'label': 'A posteriori', 'value': CONTEXT_TYPE_A_PPOSTERIORI}]
CONTEXT_TYPES_OPTIONS = [{'label': 'A priori', 'value': 0}, {'label': 'A posteriori', 'value': 1}]

dash.register_page( 
    __name__,
    path='/label',
    title='Gestion des contextes et labels',
    name='Contextes et labels',
    location='sidebar',
    order=2
)


LAYEOUT_STYLE = {
    "max-width": "100%",
    "padding": 0,
    "padding-top": "20px", 
    "margin": 0, 
}

layout = html.Div(children=[
    dcc.Location( id='url' ),

    html.H1(children='Gestion des labels et étiquettes'),
	html.Div( id='label-page-message' ),
	  
    dbc.Container( [
		dbc.Row( [
			dbc.Col( tagcat.select_card, width=4 ),
			dbc.Col( tag.select_card, width=4 ),
			dbc.Col( context.select_card, width=4 ),
		] ),
		dbc.Row( [
			dbc.Col( label.select_card, width=6 ),
			dbc.Col( labeling.select_card, width=6 )
		] ),
		dbc.Row( [
			dbc.Col( labeling.select_card_by_file, width=6 )
		] ) 
	], className="vstack gap-3", style=LAYEOUT_STYLE )
] )


 
# megamicros_aiboard/apps/aibord/cards/sourcefile.py
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
Megamicors Aiboard sourcefile card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from datetime import datetime, date, timedelta
import json
import numpy as np
from scipy import signal
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from megamicros.data import MuAudio
import megamicros.aiboard.cpn_design as cpn
from megamicros.antenna import BmfAntenna, Mu32_Mems32_JetsonNano_0001
from megamicros.room import arrange_2D
from megamicros.log import log, tracedebug
from megamicros.aiboard.session import session 

FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4
DEFAULT_GRAPH_THEME = "plotly_dark"
DEFAULT_GRAPH_SAMPLES_NUMBER = 10000
DEFAULT_FRAME_DURATION = 0.025

"""
Right subcard for file info displaying 
"""
sourcefile_select_subcard_content = [
    dbc.Card( [
        dbc.Container( [
            dbc.Row( [ 
                dbc.Col( [
                    "Aucun fichier sélectionné."
                ], id="srcfile-select-subcard-content", width=12, style={"height":"200px", "overflow": "scroll"} ),
            ] ),
            html.Hr(),
            dbc.Row( [
                dbc.Col( [ 
                    dbc.Button("Télécharger", id="srcfile-select-subcard-upload-button", n_clicks=0, outline=True, color="info", class_name="me-1") 
                ], width=3 ),
                dbc.Col( [ 
                    dbc.Button("Modifier", id="srcfile-select-subcard-update-button", n_clicks=0, outline=True, color="info", class_name="me-1") 
                ], width=4 ),
                dbc.Col( [
                    dbc.Tooltip( "Sélectionner une méthode de segmentation", target="srcfile-select-subcard-segment-select", placement="top"  ),
                    dcc.Dropdown( id="srcfile-select-subcard-segment-select", placeholder="---", options=[
                        {'label': 'Energie', 'value': 'energy'}, 
                        {'label': 'Puissance', 'value': 'power'}, 
                        {'label': 'Q50%', 'value': 'q50'}
                    ], value='energy' ),
                ], width=4 ),
                dbc.Col( [
                    dcc.Loading( id="srcfile-select-subcard-upload-button-loading", type="circle" ),
                ], width=1 ),
            ], align="center" ),
            dbc.Modal( [
                dbc.ModalHeader( dbc.ModalTitle( "Modifier un commentaire de fichier" ) ),
                dbc.ModalBody( 
                    dbc.Form( [
                        dbc.Row( [
                            dbc.Col( 
                                dbc.Label( "Note", html_for="srcfile-select-subcard-form-comment", width=2 ) 
                            ),
                            dbc.Col( [ 
                                dbc.Textarea( id="srcfile-select-subcard-form-comment", size="sm", valid=True ),
                                dbc.FormText("Commentaire optionnel")
                            ], width=10 )
                        ], className="mb-3" ),
                        dbc.Row( [
                            dbc.Col(
                                dbc.Label( "Etiquettes", html_for="srcfile-select-subcard-form-tags", width=2 ),
                            ),
                            dbc.Col( [ 
                                dcc.Dropdown( id="srcfile-select-subcard-form-tags", placeholder="---", multi=True ),
                                dbc.FormText("Etiquettes, tags")
                            ], width=10 )
                        ], className="mb-3" ),
                        dbc.Row( [
                            dbc.Col( [
                                dbc.Button( "Valider", id="srcfile-select-subcard-update-confirm-button", outline=True, color="info", n_clicks=0 )
                            ] )
                        ], className="mb-3" )
                    ] ) 
                )
            ], id = "srcfile-select-subcard-form", is_open=False, className="dbc" ),
        ] )
    ], body=True, color="dark" )
]


"""
File search formular card
Displays selectors for file searching in database
"""
sourcefile_select_subcard_left = dbc.Card( [
    dbc.Container( [
        dbc.Row( [
            dbc.Col( [ 
                dbc.Label( "Domaine", html_for="srcfile-select-card-domain-select" ),
            ], width=2 ),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner un domaine", target="srcfile-select-card-domain-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-card-domain-select", placeholder="---" ),
            ], width=10 )
        ] ),
        dbc.Row( [                        
            dbc.Col( [ 
                dbc.Label( "Campagne", html_for="srcfile-select-card-campaign-select" ),
            ], width=2, ),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner une campagne de mesure", target="srcfile-select-card-campaign-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-card-campaign-select", placeholder="---" ),
            ], width=10 ),
        ], ),
        dbc.Row( [               
            dbc.Col( [ 
                dbc.Label( "Appareil", html_for="srcfile-select-card-device-select" ),
            ], width=2 ),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner un device", target="srcfile-select-card-device-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-card-device-select", placeholder="---" ),
            ], width=10 ),
        ] ),
        dbc.Row( [
            dbc.Col( [ 
                dbc.Label( "Date", html_for="srcfile-select-card-datetime-select" ),
            ], width=2),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner la date et l'heure d'enregistrement", target="srcfile-select-card-datetime-select", placement="top"  ),
                dcc.DatePickerSingle( id="srcfile-select-card-datetime-select", date=date(2022, 8, 5) ),
            ], width=10 )
        ], align="center"  ),
        dbc.Row( [
            dbc.Col( [
                dbc.Label( "Type", html_for="srcfile-select-card-filetype-select" ),
            ], width=2 ),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner un type de fichier", target="srcfile-select-card-filetype-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-card-filetype-select", placeholder="---", options=[
                    {'label': 'Fichiers audio MuH5', 'value':'MUH5'}, 
                    {'label': 'Fichiers sons wav', 'value':'WAV'}, 
                    {'label': 'Fichiers vidéo mp4', 'value': 'MP4'}
                ], value='MUH5' ),
            ], width=10 ),
        ] ),
        dbc.Row( [               
            dbc.Col( [ 
                dbc.Label( "Fichiers", html_for="srcfile-select-card-file-select" ),
            ], width=2 ),
            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner un fichier", target="srcfile-select-card-file-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-card-file-select", placeholder="---" ),
            ], width=10 ),
        ] ),

    ], className="vstack gap-2" )

], body=True )


"""
The labelgraph subcard that display the labelings already donne - or not, along files of a day
"""
sourcefile_select_subcard_labelgraph = dbc.Card( [
    dbc.Container( [
        dbc.Row( [
            dbc.Col( dcc.Graph( id='srcfile-select-subcard-labelgraph', style={"height":"300px"} ) )
        ] )
    ])
], body=True )

"""
The energy graph subcard
"""
sourcefile_select_subcard_energygraph = dbc.Card( [
    dbc.Container( [
        dbc.Row( 
            dbc.Col( dcc.Graph( id='srcfile-select-subcard-energygraph', style={"height":"300px"} ) )
        ),
        html.Br(),
        dbc.Row( 
            dbc.Col( dcc.Slider( min=0, max=100, step=1, id="srcfile-select-subcard-profilegraph-slider", marks=None, value=0, tooltip={"placement": "bottom", "always_visible": True}, disabled=True ) )
        ),
        dbc.Row( 
            dbc.Col( html.Hr() )
        ),
        dbc.Row( [
            dbc.Col(
                dbc.Button("Télécharger", id="srcfile-select-subcard-energygraph-upload-button", n_clicks=0, outline=True, color="info", class_name="me-1") 
            ),

            dbc.Col( [ 
                dbc.Tooltip( "Sélectionner un mode opératoire", target="srcfile-select-subcard-profilegraph-mode-select", placement="top"  ),
                dcc.Dropdown( id="srcfile-select-subcard-profilegraph-mode-select", placeholder="---", options=[
                    {'label': 'Manuel', 'value': 'manual'}, 
                    {'label': 'Segmentation', 'value': 'segment'},
                ], value='manual' ),
            ], width=3 ),

        ], align="center" )
    ] )
], body=True )


"""
The labeling formular
"""
sourcefile_select_subcard_labeling = dbc.Modal( [
    dbc.ModalHeader( dbc.ModalTitle( "Créer un étiquetage" ) ),
    dbc.ModalBody( 
        dbc.Form( [
            dbc.Container( [
                dbc.Row( dbc.Col( id="srcfile-select-subcard-labeling-form-content" ) ),
                dbc.Row( html.Hr() ),
                dbc.Row( [ 
                    dbc.Col( [ 
                        dbc.Label( "Label", html_for="srcfile-select-subcard-labeling-label-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner un label", target="srcfile-select-subcard-labeling-label-select", placement="top"  ),
                        dcc.Dropdown( id="srcfile-select-subcard-labeling-label-select", placeholder="---" ),
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [                
                    dbc.Col( [ 
                        dbc.Label( "Contexts", html_for="srcfile-select-subcard-labeling-contexts-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner un ou plusieurs contexts descriptifs", target="srcfile-select-subcard-labeling-contexts-select", placement="top"  ),
                        dcc.Dropdown( id="srcfile-select-subcard-labeling-contexts-select", placeholder="---", multi=True ),
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [                
                    dbc.Col( [ 
                        dbc.Label( "Tags", html_for="srcfile-select-subcard-labeling-tags-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner une ou plusieurs étiquettes", target="srcfile-select-subcard-labeling-tags-select", placement="top"  ),
                        dcc.Dropdown( id="srcfile-select-subcard-labeling-tags-select", placeholder="---", multi=True ),
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [
                    dbc.Col( 
                        dbc.Label( "Note", html_for="srcfile-select-subcard-labeling-comment"),
                        width=2 
                    ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Commenter l'étiquetage", target="srcfile-select-subcard-labeling-comment", placement="top"  ),
                        dbc.Textarea( id="srcfile-select-subcard-labeling-comment", size="sm", valid=True ),
                        dbc.FormText("Commentaire optionnel")
                    ], width=10 )
                ], className="mb-3", align="center" ),
                dbc.Row(
                    dbc.Col( html.Hr() )
                ),
                dbc.Row(
                    dbc.Col( [
                        dbc.Tooltip( "Cette action valide l'étiquetage", target="srcfile-select-subcard-labeling-confirm-button", placement="top"  ),
                        dbc.Button("Valider", id="srcfile-select-subcard-labeling-confirm-button", n_clicks=0, outline=True, color="info", class_name="me-1") 
                    ] )
                )
            ], className="vstack gap-2" )
        ] )
    )
], id = "srcfile-select-subcard-labeling-form", is_open=False, className="dbc"  )



"""
The audio graph subcard
"""
sourcefile_select_subcard_audiograph = dbc.Card( [
    dbc.Container( [
        dbc.Row(
            dbc.Col( dcc.Graph( id='srcfile-select-subcard-audiograph', style={"height":"400px"} ) )
        ),
        dbc.Row( html.Audio( id="srcfile-select-subcard-audioplayer", controls=True, src="" )
        ),
        dbc.Row( dbc.Col( html.Hr() ) ),
        dbc.Row( [
            dbc.Col( [
                dbc.DropdownMenu(
                    id="srcfile-select-subcard-audiograph-select",
                    label="Traitements",
                    children=[
                        dbc.DropdownMenuItem( "Energie Q50%", id="srcfile-select-subcard-audiograph-q50-button", n_clicks=0 ),
                        dbc.DropdownMenuItem( "Entropie de Wiener", id="srcfile-select-subcard-audiograph-flatness-button", n_clicks=0 ),
                        dbc.DropdownMenuItem( "Spectrogramme", id="srcfile-select-subcard-audiograph-spec-button", n_clicks=0 ),
                        dbc.DropdownMenuItem( "Beaforming", id="srcfile-select-subcard-audiograph-bmf-button", n_clicks=0 ),
                    ],
                ),
            ], width=2 ),
            dbc.Col( [
                dbc.Tooltip( "Etiqueter la scène sélectionnée", target="srcfile-select-subcard-audiograph-label-button", placement="top"  ),
                dbc.Button("Labeliser", id="srcfile-select-subcard-audiograph-label-button", n_clicks=0, outline=True, color="info", class_name="me-1") 
            ], width=2 ),        
        ] ),
        dbc.Row( [
            dbc.Col( id="srcfile-select-subcard-siggraph" )
        ] )

    ], className="vstack gap-2" ),
    sourcefile_select_subcard_labeling
], body=True )


"""
The main card
"""
sourcefile_select_card = dbc.Card( [

    dbc.CardHeader( [
    
        dbc.Container( [
            dbc.Row( [
                dbc.Col( 
                    dbc.Container( [
                        dbc.Row( [
                            dbc.Col( "Selectionner un fichier"  )
                        ] )
                    ] ), width=5
                ),
                dbc.Col( 
                    dbc.Container( [ 
                        dbc.Row( [
                            dbc.Col( dbc.Label( "Voie G", html_for="srcfile-select-card-left-channel-number" ), width=2 ),
                            dbc.Col( dbc.Input( id="srcfile-select-card-left-channel-number", type="number", min=0, max=32, step=1, value=1, size="sm", disabled=False ), className="dbc"  ),
                            dbc.Col( dbc.Label( "Voie D", html_for="srcfile-select-card-right-channel-number" ), width=2 ),
                            dbc.Col( dbc.Input( id="srcfile-select-card-right-channel-number", type="number", min=0, max=32, step=1, value=6, size="sm", disabled=False ), className="dbc" ),
                            dbc.Col( dbc.Label( "Buffer", html_for="srcfile-select-card-frame-length" ), width=1 ),
                            dbc.Col( dbc.Input( id="srcfile-select-card-frame-length", type="number", min=100, max=10000, step=1, value=100, size="sm", disabled=False ), className="dbc" ),
                            dbc.Tooltip( "Buffer de calcul en millisecondes", target="srcfile-select-card-frame-length", placement="top"  ),
                        ], align="center" )
                    ] ), width=7
                )
            ], align="center"  )
        ])

    ] ),
    dbc.CardBody( [ 
        dbc.Container( [
            dbc.Row( [ 
                dbc.Col( sourcefile_select_subcard_left, width=6 ),
                dbc.Col( sourcefile_select_subcard_content, width=6 )
            ] ),
            dbc.Row( [
                dbc.Col( sourcefile_select_subcard_labelgraph, width=12 )
            ] ),
            dbc.Row( [
                dbc.Col( sourcefile_select_subcard_energygraph, width=12)
            ] ),
            dbc.Row( [
                dbc.Col( sourcefile_select_subcard_audiograph, width=12 )
            ] )
        ], className="vstack gap-2"  )
    ], className="dbc"  ),

    html.Div( id='srcfile-select-card-errormsg' ),
	dcc.Store( id='srcfile-select-card-store' )
] )


@callback(
    Output( 'srcfile-select-card-domain-select', 'options' ),
    Output( 'srcfile-select-card-domain-select', 'value' ),
    Output( 'srcfile-select-card-campaign-select', 'options' ),
    Output( 'srcfile-select-card-campaign-select', 'value' ),
    Output( 'srcfile-select-card-device-select', 'options' ),
    Output( 'srcfile-select-card-device-select', 'value' ),
    Output( 'srcfile-select-card-datetime-select', 'date' ),
    Output( 'srcfile-select-card-filetype-select', 'options' ),
    Output( 'srcfile-select-card-filetype-select', 'value' ),
    Output( 'srcfile-select-card-file-select', 'options' ),
    Output( 'srcfile-select-card-file-select', 'value' ),
    Output( 'srcfile-select-subcard-content', 'children' ),
    Output( 'srcfile-select-subcard-labelgraph', 'figure' ),
    Output( 'srcfile-select-subcard-upload-button-loading', 'children' ),
    Output( 'srcfile-select-subcard-form', 'is_open' ),
    Output( 'srcfile-select-subcard-form-comment', 'value' ),
    Output( 'srcfile-select-subcard-form-tags', 'options' ),
    Output( 'srcfile-select-subcard-form-tags', 'value' ),
    Output( 'srcfile-select-subcard-energygraph', 'figure' ),
    Output( 'srcfile-select-subcard-profilegraph-slider', 'disabled' ),
    Output( 'srcfile-select-subcard-audiograph', 'figure' ),
    Output( 'srcfile-select-subcard-audioplayer', 'src' ),
    Output( 'srcfile-select-subcard-siggraph', 'children' ),
    Output( 'srcfile-select-subcard-labeling-form', 'is_open' ),
    Output( 'srcfile-select-subcard-labeling-form-content', 'children' ),
    Output( 'srcfile-select-subcard-labeling-label-select', 'options' ),
    Output( 'srcfile-select-subcard-labeling-label-select', 'value' ),
    Output( 'srcfile-select-subcard-labeling-contexts-select', 'options' ),
    Output( 'srcfile-select-subcard-labeling-contexts-select', 'value' ),
    Output( 'srcfile-select-subcard-labeling-tags-select', 'options' ),
    Output( 'srcfile-select-subcard-labeling-tags-select', 'value' ),
    Output( 'srcfile-select-subcard-labeling-comment', 'value' ),
	Output( 'srcfile-select-card-store', 'data' ),
	Output( 'srcfile-select-card-errormsg', 'children' ),
	Input( 'srcfile-select-card-domain-select', 'value' ),
	Input( 'srcfile-select-card-campaign-select', 'value' ),
	Input( 'srcfile-select-card-device-select', 'value' ),
	Input( 'srcfile-select-card-datetime-select', 'date' ),
	Input( 'srcfile-select-card-filetype-select', 'value' ),
    Input( 'srcfile-select-card-file-select', 'value' ),
    Input( 'srcfile-select-subcard-upload-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-update-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-update-confirm-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-energygraph-upload-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-profilegraph-mode-select', 'value' ),
    Input( 'srcfile-select-subcard-profilegraph-slider', 'value' ),
    Input( 'srcfile-select-subcard-audiograph', 'relayoutData' ),
    Input( 'srcfile-select-subcard-audiograph-spec-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-audiograph-q50-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-audiograph-flatness-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-audiograph-bmf-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-audiograph-label-button', 'n_clicks' ),
    Input( 'srcfile-select-subcard-labeling-confirm-button', 'n_clicks' ),
    State( 'srcfile-select-card-left-channel-number', 'value' ),
    State( 'srcfile-select-card-right-channel-number', 'value' ),
    State( 'srcfile-select-card-frame-length', 'value' ),
    State( 'srcfile-select-subcard-form-comment', 'value' ),
    State( 'srcfile-select-subcard-form-tags', 'value' ),
    State( 'srcfile-select-subcard-segment-select', 'value' ),
    State( 'srcfile-select-subcard-energygraph', 'relayoutData' ),
    State( 'srcfile-select-subcard-labeling-label-select', 'value' ),
    State( 'srcfile-select-subcard-labeling-contexts-select', 'value' ),
    State( 'srcfile-select-subcard-labeling-tags-select', 'value' ),
    State( 'srcfile-select-subcard-labeling-comment', 'value' ),
    State( 'srcfile-select-card-store', 'data' ),
    State( 'config-store', 'data' )
)
def onSourceFileSelect( domain_idx, campaign_idx, device_idx, datetime_value, filetype, file_idx, 
    upload_btn, update_btn, update_confirm_btn, energy_upload_btn, profile_mode, slider_level,
    audio_graph, spectrum_btn, q50_btn, flatness_btn, bmf_btn, label_btn, lbl_confirm_btn,
    left_channel, right_channel, frame_duration, form_comment, form_tags_idx, segment_algo, energy_graph,
    lbl_label_idx, lbl_contexts_idx, lbl_tags_idx, lbl_comment,
    card_store, config_store ):

    def generate_file_content( file, tags ):
        """
        Display the source file content
        * file (dict): file fields
        * tags (list): complete tags list registered in database    
        """

        if file['type'] != FILETYPE_MUH5:
            """ Not done yet... """
            return html.Div( html.P( f"Contenu non visible pour les fichiers autres que MUH5" ) )
        
        """ set the tags list """
        tags_str = []
        for tag_url in file['tags']:
            tags_str.append( next( tag['name'] for tag in tags if tag['url']==tag_url ) )
        if not tags_str:
            tags_str  = '-'

        content = html.Div( [
            html.P( [
                f"Nom du fichier: {file['filename']}",
                html.Ul( [
                    html.Li( f"Date d'enregistrement: {file['datetime']}" ),
                    html.Li( f"Durée d'enregistrement: {cpn.format_duration( file['duration'] )}" ),
                    html.Li( f"Fréquence d'échantillonnage: {file['info']['sampling_frequency']} Hz" ),
                    html.Li( f"Nombre de voies: {file['info']['mems_number']+file['info']['analogs_number']+file['info']['counter']}"),
                    html.Li( f"Tags: {tags_str}" ),
                    html.Li( f"Commentaire: {file['comment']}" ),
                ] )
            ] ),
        ] )

        return content
    
    def generate_labeling_content( file, labeling ):
        """
        Display info regarding the current labeling operation 
        """
        if file['type'] != FILETYPE_MUH5:
            """ Not done yet... """
            return html.Div( html.P( f"Contenu non visible pour les fichiers autres que MUH5" ) )
                                 
        content = html.Div( [
            html.P( [ 
                f"Nom du fichier: {file['filename']}",
                html.Ul( [
                    html.Li( f"Date d'enregistrement: {file['datetime']}" ),
                    html.Li( f"Durée d'enregistrement: {cpn.format_duration( file['duration'] )}" ),
                    html.Li( f"Fréquence d'échantillonnage: {file['info']['sampling_frequency']} Hz" ),
                    html.Li( f"Nombre de voies: {file['info']['mems_number']+file['info']['analogs_number']+file['info']['counter']}" ),
                ] )
            ] ),
            html.P( [
                f"Caractéristiques de la sélection:",
                html.Ul( [
                    html.Li( f"Selection: [{cpn.format_duration(labeling['range_start'])} -> {cpn.format_duration(labeling['range_end'])}" ),
                    html.Li ( f"Durée: {cpn.format_duration(labeling['duration'])}s" ), 
                    html.Li( f"Nombre d'échantillons: {labeling['samples_number']}" ),
                ] )
            ] )
        ] )

        return content


    def generate_fig_init( title:str|None=None ):
        if title is None:
            title = "No content"
        fig = go.Figure()
        fig.update_layout( 
            title=title, 
            title_font_color="grey", 
            template=DEFAULT_GRAPH_THEME 
        )

        return fig

    def generate_card_init():
        """
        Generate the initial card state
        """

        """ init labeling and energy graph """
        labelfig = generate_fig_init( title="Graphe d'étiquetage des Fichiers: (0) fichiers lus" )
        energyfig = generate_fig_init( title="Profil énergie du fichier: aucun profil chargé" )
        audiofig = generate_fig_init( title="Audio: signal not présent" )

        """ Populates selectors """
        domains = session.load_domains()
        store['domains'] = domains
        domains_options = cpn.populate_selector( domains )

        campaigns = session.load_campaigns()
        store['campaigns'] = campaigns
        campaigns_options = cpn.populate_selector( campaigns )

        devices = session.load_devices()
        store['devices'] = devices
        devices_options = cpn.populate_selector( devices )

        return output.generate( 
            labelgraph_figure=labelfig,
            energygraph_figure=energyfig,
            audiograph_figure=audiofig,
            domain_options=domains_options, 
            campaign_options=campaigns_options, 
            device_options=devices_options, 
            store_data = json.dumps( store )
        )

    def rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency ):
        """
        Get the new range limits from the rangeslider graph 
        """
        if audio_graph is None or 'autosize' in audio_graph or 'xaxis.autorange' in audio_graph:
            """ Full signal selected """
            range_start = start
            range_end = end

        elif 'xaxis.range' in audio_graph:
            """ range signal selected """ 
            range_start = start + int( audio_graph['xaxis.range'][0] * ratio ) / sampling_frequency
            range_end = start + int( audio_graph['xaxis.range'][1] * ratio ) / sampling_frequency
        else:
            range_start = start + int( audio_graph['xaxis.range[0]'] * ratio ) / sampling_frequency
            range_end = start + int( audio_graph['xaxis.range[1]'] * ratio ) / sampling_frequency

        return ( range_start, range_end )


    output: cpn.Output = cpn.Ouput( [
        'domain_options', 'domain_value', 'campaign_options', 'campaign_value', 'device_options', 'device_value',
        'datetime_date', 'filetype_options', 'filetype_value', 'file_options', 'file_value', 'content_children', 
        'labelgraph_figure', 'loading_children', 'form_is_open', 'form_comment_value', 'form_tags_options', 'form_tags_value',
        'energygraph_figure', 'slider_disabled', 'audiograph_figure', 'audioplayer_src', 'siggraph_children', 'labeling_form_is_open', 'labeling_form_content_children',
        'labeling_label_options', 'labeling_label_value', 'labeling_contexts_options', 'labeling_contexts_value', 'labeling_tags_options', 'labeling_tags_value', 'labeling_comment_value',
        'store_data', 'errormsg_children'
    ] )

    if config_store is None:
        """ User is not connected to database - > exit after graph init """

        return output.generate(
            labelgraph_figure = generate_fig_init( title="Graphe d'étiquetage des Fichiers: (0) fichiers lus" ),
            energygraph_figure = generate_fig_init( title="Profil énergie du fichier: aucun profil chargé" ),
            audiograph_figure = generate_fig_init( title="Audio: signal not présent" )
        )


    if card_store is None:
        """ Init local memory """
        store = {}
    else:
        """ load local memory content """
        store = json.loads( card_store ) 

    try:
        clicked = ctx.triggered_id
        dbhost =  json.loads( config_store )['host']

        if clicked is None:
            """ Initial card state """
            return generate_card_init()

        elif clicked == 'srcfile-select-card-domain-select' or clicked == 'srcfile-select-card-campaign-select' or clicked == 'srcfile-select-card-device-select' or clicked == 'srcfile-select-card-filetype-select' or clicked=='srcfile-select-card-datetime-select' :
            """ find files that matches selected options (domain, campaign, device, file type and datetime) and generate the labeling graph """

            if domain_idx is None or campaign_idx is None or device_idx is None or datetime_value is None or filetype is None:
                """ Some option(s) have not been selected on madatory selectors """
                return output.generate()

            types_ext = {'MUH5':'muh5', 'WAV':'wav', 'MP4':'mp4'}

            """ Complete datetime since the formular don't set time seconds and milliseconds nor 'T' and 'Z' """
            date_time = datetime_value + 'T00:00:00.0Z'

            """ Get device directories """
            if 'directories_url' not in store or clicked == 'srcfile-select-card-device-select':
                directories_url = session.get_device( id=store['devices'][device_idx]['id'] )['directories']
                store['directories_url'] = directories_url
            else:
                directories_url = store['directories_url']       
            
            """ get files """
            for dir_url in directories_url:
                """ check campaign within current directory """
                directory = session.get_directory( url=dir_url )
                campaign_url =  directory['campaign']
                if session.get_campaign( url=campaign_url )['id'] != store['campaigns'][campaign_idx]['id']:
                    """ current directory dont match with the selected campaign """
                    continue

                """ Check for files with correct extension at the given date """
                files = session.load_directory_files( directory['id'], types_ext[filetype], file_datetime=date_time )
                store['files'] = files
                files_options = cpn.populate_selector( files, field='filename' )

            if 'files' not in store:
                raise Exception( "No file found !" )
            
            log.info( f" .Received {len( store['files'] )} {filetype} file names" )

            """ update the labeling-graph figure """
            files_number = len( files )
            x = []
            y0 = []
            y1 = []
            labelings_number = 0
            for file in files:
                """ count all labelings in file """
                x.append( file['datetime'] )
                if not file['labels']:
                    y0.append( 1 )
                    y1.append( 0 )
                else:
                    y0.append( 0 )
                    y1.append( len( file['labels'] ) )
                    labelings_number += len( file['labels'] )

            fig = go.Figure()
            if labelings_number > 0:
                """ trace two relative graphs """
                fig.add_trace( go.Bar( x=x, y=y0, name='No labels', marker_color='blue' ) )
                fig.add_trace( go.Bar( x=x, y=y1, name='Labels', marker_color='green' ) )
            else:
                """ trace only one graph with all values set to zero """
                fig.add_trace( go.Bar( x=x, y=[0,]*files_number, name='Files', marker_color='blue' ) )

            fig.update_layout( 
                barmode='relative',
                title=f"Graphe d'étiquetage des Fichiers: ({files_number}) fichiers lus",
                title_font_color="green",
                xaxis_tickangle=-90, 
                template=DEFAULT_GRAPH_THEME
            )

            return output.generate(
                labelgraph_figure=fig,
                file_options=files_options,
                store_data = json.dumps( store )
            )

        elif clicked == 'srcfile-select-card-file-select':
            """ display info about the selected file and generate the file updating window """
            
            if file_idx is None:
                """ file has been unselected -> remove content zone, tags and subsequent graphs and data """
                store['tags'] = None
                if 'energy' in store:
                    store['energy'] = None
                if 'audio' in store:
                    store['audio'] = None

                return output.generate( 
                    content_children=html.Div( 'Aucun fichier sélectionné.' ),
                    labelgraph_figure = generate_fig_init( title="Graphe d'étiquetage des Fichiers: (0) fichiers lus" ),
                    energygraph_figure = generate_fig_init( title="Profil énergie du fichier: aucun profil chargé" ),
                    audiograph_figure = generate_fig_init( title="Audio: signal not présent" ),
                    store_data = json.dumps( store )
                )   

            """ get the selected file """
            file = store['files'][file_idx]
            tags = session.load_tags()
            store['tags'] = tags
            
            return output.generate( 
                content_children=generate_file_content( file, tags ),
                store_data = json.dumps( store )
            )

        elif clicked == 'srcfile-select-subcard-update-button':
            """ open the file comment updating window """

            """ get the selected file comment for populating the formular """
            file = store['files'][file_idx]
            file_comment = file['comment']

            tags = store['tags']
            tags_options = cpn.populate_selector( tags )

            tags_url = file['tags']
            tags_idx = []
            for tag_url in tags_url:
                tags_idx.append( next( i for i, _ in enumerate( tags ) if tags[i]['url']==tag_url ) )

            return output.generate( 
                form_is_open = True,
                form_comment_value = file_comment,
                form_tags_options = tags_options,
                form_tags_value = tags_idx,
                store_data = json.dumps( store )
            )

        elif clicked == 'srcfile-select-subcard-update-confirm-button':
            """ save updated content """

            """ get the selected file identifier for updating """
            file_id = store['files'][file_idx]['id']

            """ shaping of tags """
            tags = store['tags']
            tags_id = []
            if form_tags_idx:
                 for tag_idx in form_tags_idx:
                      tags_id.append( tags[tag_idx]['id'] )

            """ process updating """
            session.patch_sourcefile( file_id, tags_id, form_comment )

            """ reload file content, save and display """
            file = session.get_sourcefile( id=file_id )
            store['files'][file_idx] = file
            
            return output.generate( 
                form_is_open = False,
                form_comment_value = '',
                form_tags_options = [],
                form_tags_value = [],
                content_children = generate_file_content( file, tags ),
                store_data = json.dumps( store )
            )

        elif clicked == 'srcfile-select-subcard-upload-button' or clicked == 'srcfile-select-subcard-profilegraph-mode-select':
            """ upload signal profile and display it """
            print( "mode=", profile_mode )
            if file_idx is None:
                """ no selected file -> cannot upload """
                log.info( " .No selecetd file: cannot upload. Please select one !" )
                raise Exception( "Aucun fichier sélectionné !" )

            file  = store['files'][file_idx]
            if segment_algo is None: 
                segment_algo = 'energy'
            url_endpoint = f"/sourcefile/{str( file['id'] )}/segment/{segment_algo}/"

            if frame_duration is None:
                frame_duration = 100
            url_endpoint += f"?frame_duration={frame_duration}"                

            log.info( f" .Send segmentation request on database endpoint {dbhost+url_endpoint}..." )

            """ perform database request for signal profile """
            data = session.get( request=url_endpoint ).json()
            profile = np.array( data['data'] )
            
            log.info( f" .Received {profile.size} samples ({profile.size*profile.itemsize} data Bytes)" )    
            store['energy'] = {
                'frames_number': profile.size,
                'frame_duration': frame_duration,
                'frame_width': data['frame_width'],
                'bytes': profile.size*profile.itemsize,
                'url': dbhost+url_endpoint,
                'max_value': data['max_value'],
                'min_value': data['min_value'],
                'profile': list( profile )
            }

            profilefig = go.Figure()
            profilefig.update_layout( 
                title = f"Profil '{segment_algo}' du fichier: {profile.size} points", 
                title_font_color="green", 
                template=DEFAULT_GRAPH_THEME
            )

            if profile_mode == 'manual':
                """ generate figure with range slider """
                log.info( " .Use the profile graph mode 'manual'" )
                profilefig.update_layout( 
                    xaxis=dict(
                        rangeslider=dict(
                            visible=True
                        ),
                    )
                )

                profilefig.add_trace(
                    go.Scatter(x=list( [i for i in range(profile.size)] ), y=list( profile ))
                )

                slider_disabled = True
            
            elif profile_mode == 'segment':
                """ segmentation figure """
                log.info( " .Use the profile graph mode 'segmentation'" )
                profilefig.add_trace(
                    go.Scatter(x=list( [i for i in range(profile.size)] ), y=list( profile ))
                )

                slider_disabled = False

            return output.generate( 
                energygraph_figure=profilefig,
                slider_disabled = slider_disabled,
                store_data = json.dumps( store )
            )            

        elif clicked == 'srcfile-select-subcard-profilegraph-slider':
            """ The profile graph slider has change -> update """

            energy = store['energy']
            profile = energy['profile']
            frames_number = energy['frames_number']
            max_value = energy['max_value']

            """ build the segmentation graph """
            selected_level = slider_level * max_value / 100
            print( "selected_level=", selected_level )
            segment_graph = [ max_value if level>=selected_level else 0 for level in profile ]

            profilefig = go.Figure()
            profilefig.update_layout( 
                title = f"Profil '{segment_algo}' du fichier: {frames_number} points", 
                title_font_color="green", 
                template=DEFAULT_GRAPH_THEME
            )

            profilefig.add_trace(
                go.Scatter( x=list( [i for i in range(frames_number)] ), y=profile )
            )
            profilefig.add_trace(
                go.Scatter( x=list( [i for i in range(frames_number)] ), y=segment_graph )
            )

            return output.generate( 
                energygraph_figure=profilefig,
            ) 

        elif clicked == 'srcfile-select-subcard-energygraph-upload-button':
            """
            Load file samples from left channel according energy graph selected range and plot
            """

            """ Get ranges from energy graph """
            energy = store['energy']
            if energy_graph is None or 'autosize' in energy_graph or 'xaxis.autorange' in energy_graph:
                first = 0
                last = energy['frames_number'] - 1
            elif 'xaxis.range' in energy_graph:        
                first = int( energy_graph['xaxis.range'][0] )
                last = int( energy_graph['xaxis.range'][1] )
            else:
                first = int( energy_graph['xaxis.range[0]'] )
                last = int( energy_graph['xaxis.range[1]'] )

            """ upload data from database """
            file  = store['files'][file_idx]
            duration = file['duration']
            sampling_frequency = file['info']['sampling_frequency']
            start = first * duration / energy['frames_number']
            end = last * duration / energy['frames_number']
            url_endpoint = f"/sourcefile/{file['id']}/range/{start}/{end}/channels/{left_channel}/{right_channel}/"

            log.info( f" .Send request for {start}s to {end}s range signal on {dbhost+url_endpoint} endpoint..." )
            audio = np.frombuffer( session.get( url_endpoint ).content, dtype=np.float32 )
            channels_number = 2
            samples_number = int( audio.size/channels_number )

            """ do subsampling """
            step = int( samples_number // DEFAULT_GRAPH_SAMPLES_NUMBER )
            subsamples_number = int( samples_number // step )
            
            """ Compute the graph ratio """
            ratio = int( ( (end - start) * sampling_frequency ) // DEFAULT_GRAPH_SAMPLES_NUMBER )

            log.info( f" .Signal sub-sampling set to 1/{step} before plotting" )
            audio = np.reshape( audio, ( samples_number, channels_number ) )

            """ set audio graph and plot """
            audiofig = go.Figure()
            audiofig.update_layout( 
                title = f"Audio: {(end-start):.2f}s duration (subsampling 1/{step})", 
                title_font_color="green", 
                template=DEFAULT_GRAPH_THEME,
                xaxis=dict(
                    rangeslider=dict(
                        visible=True
                    ),
                )
            )
            audiofig.add_trace(
                go.Scatter(x=list( [i for i in range(subsamples_number)] ), y=list( audio[::step,0] )))

            """ set the audio player """

            if file['type']!=FILETYPE_WAV and file['type']!=FILETYPE_MUH5:
                raise Exception ( f"Cannot set audio player for files of type {file['type']}") 

            audio_url = f"{dbhost}/sourcefile/{file['id']}/audio/{start}/{end}/channels/{left_channel}/{right_channel}/"

            log.info( f" .Audio player ready on {audio_url}" )

            """ store """
            store['audio'] = {
                'samples_number': samples_number,
                'channels_number': channels_number,
                'sampling_frequency': sampling_frequency,
                'step': step,
                'subsamples_number': subsamples_number,
                'start': start,
                'end': end,
                'ratio': ratio,
                'url': audio_url
            }

            return output.generate( 
                audiograph_figure = audiofig,
                audioplayer_src = audio_url,
                store_data = json.dumps( store )
            )

        elif clicked == "srcfile-select-subcard-audiograph":
            """ on audio graph resizing, update audio player to the new audio range """
            
            if not ( 'files' in store and 'audio' in store ):
                """ it may arrives that audiograph sends an event at very first initial state """
                return generate_card_init()

            file = store['files'][file_idx]
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']

            """ get range from selector """
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            """ set the url request """
            audio_url = f"{dbhost}/sourcefile/{file['id']}/audio/{range_start}/{range_end}/channels/{left_channel}/{right_channel}/"
            log.info( f" .Audio player ready on {audio_url}" )

            return output.generate( 
                audioplayer_src = audio_url,
            )


        elif clicked == "srcfile-select-subcard-audiograph-spec-button":
            """ display signal spectrogram """

            file = store['files'][file_idx]
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']

            """ get range from selector """
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            """ get audio content """
            range_fileurl = f"{dbhost}/sourcefile/{file['id']}/range/{range_start}/{range_end}/channels/{left_channel}/{right_channel}/"
            log.info( f" .Send request for {range_start}s to {range_end}s range signal on {range_fileurl} endpoint..." )

            sound = np.frombuffer( session.get( range_fileurl, full_url=True ).content, dtype=np.float32 )
            channels_number = 2
            samples_number = int( sound.size/channels_number )
            log.info( f" .Received {samples_number} samples ({sound.size*sound.itemsize} data Bytes)")

            """ Use only left channel """
            sound = np.reshape( sound, (samples_number, channels_number) )[:,0]
            frame_width = int( sampling_frequency * DEFAULT_FRAME_DURATION )

            """ compute and display the spectrogram """
            w = signal.blackman( frame_width )
            freqs, bins, Pxx = signal.spectrogram( sound, sampling_frequency, window=w, nfft=frame_width )
            fig = go.Figure()
            fig.update_layout( title_text="Spectrogramme" )
            fig.update_layout( template=DEFAULT_GRAPH_THEME )       
            fig.update_layout( yaxis = dict(title = 'Frequency') )            
            fig.update_layout( xaxis = dict(title = 'Time') )            
            fig.add_trace(
                go.Heatmap(
                    x= bins,
                    y= freqs,
                    z= 10*np.log10(Pxx),
                    colorscale='Jet',
                )
            )  

            return output.generate( 
                siggraph_children = dcc.Graph( figure=fig ),
            )       

        elif clicked == "srcfile-select-subcard-audiograph-q50-button":
            """ display signal Q50 measure """

            file = store['files'][file_idx]
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']

            """ get range from selector """
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            """ get audio content """
            range_fileurl = f"{dbhost}/sourcefile/{file['id']}/range/{range_start}/{range_end}/channels/{left_channel}/{right_channel}/"
            log.info( f" .Send request for {range_start}s to {range_end}s range signal on {range_fileurl} endpoint..." )

            sound = np.frombuffer( session.get( range_fileurl, full_url=True ).content, dtype=np.float32 )
            channels_number = 2
            samples_number = int( sound.size/channels_number )
            log.info( f" .Received {samples_number} samples ({sound.size*sound.itemsize} data Bytes)")

            """ Use only left channel """
            sound = np.reshape( sound, (samples_number, channels_number) )[:,0]

            """ compute the Q50 """
            frame_width = int( sampling_frequency * DEFAULT_FRAME_DURATION )
            frames_number = int( samples_number / frame_width )
            lost_samples_number = samples_number % frame_width
            sound = sound[:samples_number-lost_samples_number]
            sound = np.reshape( sound, (frames_number, frame_width) )
            spec = np.fft.rfft( sound, axis=1 )
            modspec2 = np.abs( spec )    
            modspec2 *= modspec2   

            n_freq = np.size( modspec2,1 )
            frequencies = np.array( [i for i in range( n_freq )] ) * sampling_frequency / n_freq / 2
            
            q55 = np.zeros( frames_number )
            for i in range( frames_number ):
                e = np.abs( spec[i,:] ) * np.abs( spec[i,:] )
                ew = e * frequencies
                q55[i] = np.sum( ew ) / np.sum( e )

            fig = go.Figure()
            fig.update_layout( title_text="Centre de gravité spectrale Q50%" )
            fig.update_layout( template=DEFAULT_GRAPH_THEME )            
            fig.add_trace(
                go.Scatter(x=list( [i for i in range(frames_number)] ), y=list( q55 ))
            )

            return output.generate( 
                siggraph_children = dcc.Graph( figure=fig ),
            )  


        elif clicked == "srcfile-select-subcard-audiograph-flatness-button":
            """ display signal flatness """

            file = store['files'][file_idx]
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']

            """ get range from selector """
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            """ get audio content """
            range_fileurl = f"{dbhost}/sourcefile/{file['id']}/range/{range_start}/{range_end}/channels/{left_channel}/{right_channel}/"
            log.info( f" .Send request for {range_start}s to {range_end}s range signal on {range_fileurl} endpoint..." )

            sound = np.frombuffer( session.get( range_fileurl, full_url=True ).content, dtype=np.float32 )
            channels_number = 2
            samples_number = int( sound.size/channels_number )
            log.info( f" .Received {samples_number} samples ({sound.size*sound.itemsize} data Bytes)")

            """ Use only left channel """
            sound = np.reshape( sound, (samples_number, channels_number) )[:,0]

            """ Compute the flatness """
            frame_width = int( sampling_frequency * DEFAULT_FRAME_DURATION )
            frames_number = int( samples_number / frame_width )
            lost_samples_number = samples_number % frame_width
            sound = sound[:samples_number-lost_samples_number]
            sound = np.reshape( sound, (frames_number, frame_width) )
            spec = np.fft.rfft( sound, axis=1 )
            flatness = np.zeros( frames_number )
            for i in range( frames_number ):
                e = np.abs( spec[i,:] ) * np.abs( spec[i,:] )
                le = np.log( e )
                flatness[i] = np.exp( np.sum( le )/frame_width ) / np.sum( e ) / frame_width

            fig = go.Figure()
            fig.update_layout( title_text="Entropie de Wiener (spectral flatness)" )
            fig.update_layout( template=DEFAULT_GRAPH_THEME )            
            fig.add_trace(
                go.Scatter(x=list( [i for i in range(frames_number)] ), y=list( flatness ))
            )

            return output.generate( 
                siggraph_children = dcc.Graph( figure=fig ),
            )  

        elif clicked == 'srcfile-select-subcard-audiograph-bmf-button':
            # Display beamformed signal
            file = store['files'][file_idx]
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']
            mems_number = file['info']['mems_number']
            counter = file['info']['counter'] and not file['info']['counter_skip']
            channels_number = mems_number
            if counter:
                channels = ','.join([str(i+1) for i in range(mems_number)])
            else:
                channels = ','.join([str(i) for i in range(mems_number)])

            # Get range from selector
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            # Get audio content from all available mems (overwriting the url channels part)
            range_fileurl = f"{dbhost}/sourcefile/{file['id']}/range/{range_start}/{range_end}/channels/{left_channel}/{right_channel}/?channels={channels}"
            log.info( f" .Send request for {range_start}s to {range_end}s range signal on {range_fileurl} endpoint..." )
            sound = np.frombuffer( session.get( range_fileurl, full_url=True ).content, dtype=np.float32 )
            samples_number = int( sound.size/channels_number )
            log.info( f" .Received {samples_number} samples ({sound.size*sound.itemsize} data Bytes, {channels_number} channels)")

            # Space quantization
            ROOM_SIZE = (7, 10, 2.2)
            ANTENNA_POSITION = (2.5, 5, 2.18)
            FRAME_LENGTH = 512
            sq_x = 4
            sq_y = 4
            nx: int = int( ROOM_SIZE[0] * sq_x )
            ny: int = int( ROOM_SIZE[1] * sq_y )
            ground_elevation = 0.20
            space_q = arrange_2D( ROOM_SIZE, sq_x=sq_x, sq_y=sq_y, ground_elevation=ground_elevation )

            # Create antenna with beamformer
            bmf_antenna: BmfAntenna = BmfAntenna( 
                mems = Mu32_Mems32_JetsonNano_0001.mems(),
                position = ANTENNA_POSITION,
                frame_length = FRAME_LENGTH,
                space_q = space_q,
                sampling_frequency = sampling_frequency
            )

            bmf_antenna.set_data(  np.reshape( sound, (channels_number, samples_number) ) )

            # Comput BMF
            BF: np.ndarray = np.zeros( (len(space_q),) )
            E = []
            for bf in bmf_antenna:
                E.append( np.sum( bf ) )
                BF += bf

            # Compute beamformed antenna output
            #BF: np.ndarray = np.zeros( (len(space_q),) )
            #E = []
            #sound = np.reshape( sound, (channels_number, samples_number) )
            #antenna_output: MuAudio = MuAudio( sound, sampling_frequency )
            #antenna_output.set_frame_size( FRAME_LENGTH )

            # Prepare figure
            #fig = go.Figure()
            #fig.update_layout( title_text="Beamforming" )
            #fig.update_layout( template=DEFAULT_GRAPH_THEME )   

            # Compute BMF
            #for idx, sig in enumerate( antenna_output ):
            #    bf = bmf.beamform( sig, mode='bmf', n_win=2 )
            #    #img = np.reshape( bf, (nx, ny) )
            #    #fig.add_image( go.Image(z=img) )

            #    E.append( np.sum(bf) )
            #    BF += bf

            import plotly.express as px
            img = np.reshape( BF, (nx, ny) )
            fig = px.imshow( img )


# img_rgb = np.array([[[255, 0, 0], [0, 255, 0], [0, 0, 255]],
#                 [[0, 255, 0], [0, 0, 255], [255, 0, 0]]
#                 ], dtype=np.uint8)
# fig = px.imshow(img_rgb)
# fig.show()

#import plotly.graph_objects as go
#rgb_values = [[[240,128,128], [222, 49, 99], [210,105,30],
#               [255,127,80], [240, 128, 128], [139,69,19]]]
#fig = go.Figure(data=go.Image(z=rgb_values))
#fig.show()

            #fig.add_trace(
            #    go.Scatter(x=list( [i for i in range(frames_number)] ), y=list( flatness ))
            #)

            return output.generate( 
                siggraph_children = dcc.Graph( figure=fig ),
            )  


        elif clicked == 'srcfile-select-subcard-audiograph-label-button':
            """ Open the labeling formular for current scene """

            """ populate selectors """
            labels = session.load_labels()
            store['labels'] = labels
            label_options = cpn.populate_selector( labels )

            contexts = session.load_contexts()
            store['contexts'] = contexts
            contexts_options = cpn.populate_selector( contexts )

            tags = session.load_tags()
            store['tags'] = tags
            tags_options = cpn.populate_selector( tags )

            """ get ranges from energy graph """
            file = store['files'][file_idx]
            file_datetime = file['datetime']
            audio = store['audio']
            start = audio['start']
            end = audio['end']
            sampling_frequency = audio['sampling_frequency']
            ratio = audio['ratio']

            """ get range from selector """
            range_start, range_end = rangeslider_get_ranges( audio_graph, start, end, ratio, sampling_frequency )

            """ Control date format by adding microseconds if needed """
            file_datetime = cpn.add_seconds_to_formated_date( file_datetime )

            """ Convert to timestamp by using the official datetime of the file """
            label_datetime_start = datetime.strptime( file_datetime , "%Y-%m-%dT%H:%M:%S.%fZ" ) + timedelta( seconds=range_start )
            label_datetime_end = datetime.strptime( file_datetime , "%Y-%m-%dT%H:%M:%S.%fZ" ) + timedelta( seconds=range_end )

            """ store labeling params """
            store['labeling'] = {
                'range_start': range_start,
                'range_end': range_end,
                'duration': range_end - range_start,
                'samples_number': int( round( (range_end - range_start) * sampling_frequency ) ),
                'label_timestamp_start': datetime.timestamp( label_datetime_start ),
                'label_timestamp_end': datetime.timestamp( label_datetime_end ),
            }

            return output.generate(
                labeling_form_is_open = True,
                labeling_form_content_children = generate_labeling_content( file, store['labeling'] ),
                labeling_label_options = label_options,
                labeling_label_value = None,
                labeling_contexts_options = contexts_options,
                labeling_contexts_value = [],
                labeling_tags_options = tags_options,
                labeling_tags_value = [],
                store_data = json.dumps( store )
            )

        elif clicked == 'srcfile-select-subcard-labeling-confirm-button':
            """ create the labeling in database """

            labels = store['labels']
            contexts = store['contexts']
            tags = store['tags']
            file = store['files'][file_idx]
            label_timestamp_start = store['labeling']['label_timestamp_start']
            label_timestamp_end = store['labeling']['label_timestamp_end']

            """ get label url """
            if lbl_label_idx is None:
                raise Exception( "Aucun label choisi !" )
            label_id = labels[lbl_label_idx]['id']

            """ get contexts if any """
            contexts_id = [ contexts[lbl_context_idx]['id'] for lbl_context_idx in lbl_contexts_idx ]

            """ get tags if any """
            tags_id = [ tags[lbl_tag_idx]['id'] for lbl_tag_idx in lbl_tags_idx]

            """ save in databse """
            response = session.create_labeling( file['id'], label_id, contexts_id, tags_id, label_timestamp_start, label_timestamp_end, comment=lbl_comment )

            """ reset memory """
            store['labels'] = None
            store['contexts'] = None
            store['tags'] = None

            return output.generate(
                labeling_form_is_open = False,
                labeling_label_options = [],
                labeling_label_value = None,
                labeling_contexts_options = [],
                labeling_contexts_value = [],
                labeling_tags_options = [],
                labeling_tags_value = [],
                store_data = json.dumps( store )
            )


    except Exception as e:
        log.info( f" .Error on labeling card: {e}" )
        tracedebug()
        return output.generate( errormsg_children=cpn.display_error_msg( str( e ) ) )

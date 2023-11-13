# megamicros_aiboard/apps/aibord/cards/dataset.py
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
Megamicors Aiboard dataset card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from datetime import datetime, date, timedelta
import json
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

import megamicros.aiboard.cpn_design as cpn
from megamicros.log import log, tracedebug
from megamicros.aiboard.session import session


DEFAULT_GRAPH_THEME = "plotly_dark"


"""
The dataset formular
"""
dataset_form_card = dbc.Modal( [
    dbc.ModalHeader( dbc.ModalTitle( "Créer un dataset" ) ),
    dbc.ModalBody( 
        dbc.Form( [
            dbc.Container( [
                dbc.Row( [ 
                    dbc.Col( [ 
                        dbc.Label( "Nom", html_for="dataset-card-form-name" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Nom donné au dataset", target="dataset-card-form-name", placement="top"  ),
						dbc.Input( type="text", id="dataset-card-form-name", size="sm" ),
						dbc.FormText("Nom donné au dataset")
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [ 
                    dbc.Col( [ 
                        dbc.Label( "Code", html_for="dataset-card-form-code" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Code donné au dataset", target="dataset-card-form-code", placement="top"  ),
						dbc.Input( type="text", id="dataset-card-form-code", size="sm" ),
						dbc.FormText("Code donné au dataset")
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [                
                    dbc.Col( [ 
                        dbc.Label( "Labels", html_for="dataset-card-form-labels-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner un ou plusieurs labels", target="dataset-card-form-labels-select", placement="top"  ),
                        dcc.Dropdown( id="dataset-card-form-labels-select", placeholder="---", multi=True ),
                        dbc.FormText("Label(s) à rechercher")
                    ], width=10 ),
                ], align="center" ),

                dbc.Row( [                
                    dbc.Col( [ 
                        dbc.Label( "Contexts", html_for="dataset-card-form-contexts-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner un ou plusieurs contexts", target="dataset-card-form-contexts-select", placement="top"  ),
                        dcc.Dropdown( id="dataset-card-form-contexts-select", placeholder="---", multi=True ),
                        dbc.FormText("Contexte(s) à associer")
                    ], width=10 ),
                ], align="center" ),

                dbc.Row( [                
                    dbc.Col( [ 
                        dbc.Label( "Tags", html_for="dataset-card-form-tags-select" ),
                    ], width=2, ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Sélectionner une ou plusieurs étiquettes", target="dataset-card-form-tags-select", placement="top"  ),
                        dcc.Dropdown( id="dataset-card-form-tags-select", placeholder="---", multi=True ),
                        dbc.FormText("# Tagger le dataset")
                    ], width=10 ),
                ], align="center" ),
                dbc.Row( [
                    dbc.Col( 
                        dbc.Label( "Note", html_for="dataset-card-form-comment"),
                        width=2 
                    ),
                    dbc.Col( [ 
                        dbc.Tooltip( "Commentaitre sur le dataset", target="dataset-card-form-comment", placement="top"  ),
                        dbc.Textarea( id="dataset-card-form-comment", size="sm", valid=True ),
                        dbc.FormText("Commentaire optionnel")
                    ], width=10 )
                ], className="mb-3", align="center" ),

                dbc.Row(
                    dbc.Col(  dbc.Label( "Canaux", html_for="dataset-card-form-channels"), width=2)
                ),
                dbc.Row( [
                    dbc.Col( [
                        dbc.Checklist(
                            options=[ {'label':i, 'value':i} for i in range(8) ],
                            id="dataset-card-form-channels-beam-1",
                            input_style={"backgroundColor": "grey", "borderColor": "black"},
                            label_checked_style={"color": "green"},
                            input_checked_style={
                                "backgroundColor": "green",
                                "borderColor": "green",
                            },
                            inline=True,
                            className="dbc" 
                        ),
                        dbc.Checklist(
                            options=[ {'label':i, 'value':i} for i in range(8) ],
                            id="dataset-card-form-channels-beam-2",
                            input_style={"backgroundColor": "grey", "borderColor": "black"},
                            label_checked_style={"color": "green"},
                            input_checked_style={
                                "backgroundColor": "green",
                                "borderColor": "green",
                            },
                            inline=True,
                        ),
                        dbc.Checklist(
                            options=[ {'label':i, 'value':i} for i in range(8) ],
                            id="dataset-card-form-channels-beam-3",
                            input_style={"backgroundColor": "grey", "borderColor": "black"},
                            label_checked_style={"color": "green"},
                            input_checked_style={
                                "backgroundColor": "green",
                                "borderColor": "green",
                            },
                            inline=True,
                        ),
                        dbc.Checklist(
                            options=[ {'label':i, 'value':i} for i in range(8) ],
                            id="dataset-card-form-channels-beam-4",
                            input_style={"backgroundColor": "grey", "borderColor": "black"},
                            label_checked_style={"color": "green"},
                            input_checked_style={
                                "backgroundColor": "green",
                                "borderColor": "green",
                            },
                            inline=True,
                        ),

                    ], width={"size": 12, "offset": 1} )
                ], className="mb-3", align="center", justify="center" ),

                dbc.Row(
                    dbc.Col( html.Hr() )
                ),
                dbc.Row(
                    dbc.Col( [
                        dbc.Tooltip( "Cette action valide la cration du dataset", target="dataset-card-form-confirm-btn", placement="top"  ),
                        dbc.Button("Valider", id="dataset-card-form-confirm-btn", n_clicks=0, outline=True, color="info", class_name="me-1") 
                    ] )
                )
            ], className="vstack gap-2" )
        ] )
    )
], id = "dataset-card-form", is_open=False, className="dbc"  )





"""
The main card
"""
dataset_card = dbc.Card( [

    dbc.CardHeader( [
    
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Gérer une base", width=6 ),
                dbc.Tooltip( "Créer un dataset", target="dataset-card-create-btn", placement="top"  ),
				dbc.Col( dbc.Button( "+", id="dataset-card-create-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=1 ),
                dbc.Tooltip( "Sauvegarder le dataset", target="dataset-card-store-btn", placement="top"  ),
				dbc.Col( dbc.Button( "Sauvegarder", id="dataset-card-store-btn", size="sm",  outline=True, color="info", n_clicks=0, disabled=True ) ),
                dbc.Tooltip( "Supprimer le dataset", target="dataset-card-delete-btn", placement="top"  ),
				dbc.Col( dbc.Button( "x", id="dataset-card-delete-btn", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) ),
                dbc.Tooltip( "Télécharger le dataset", target="dataset-card-download-btn", placement="top"  ),
				dbc.Col( dbc.Button( [html.I( className="bi bi-cloud-download")], id="dataset-card-download-btn", size="sm",  outline=True, color="dark", n_clicks=0, disabled=True ) )
			], align="center" )
		] )

    ] ),
    dbc.CardBody( [ 
        dbc.Container( [
            dbc.Row( [ 
                dbc.Col( [

                        dbc.Container( [
                            dbc.Row( [
                                dbc.Col( [ 
                                    dbc.Label( "Domaine", html_for="dataset-card-domain-select" ),
                                ], width=2 ),
                                dbc.Col( [ 
                                    dbc.Tooltip( "Sélectionner un domaine", target="dataset-card-domain-select", placement="top"  ),
                                    dcc.Dropdown( id="dataset-card-domain-select", placeholder="---" ),
                                ], width=10 )
                            ], align="center" ),
                            dbc.Row( [               
                                dbc.Col( [ 
                                    dbc.Label( "Dataset", html_for="dataset-card-dataset-select" ),
                                ], width=2 ),
                                dbc.Col( [ 
                                    dbc.Tooltip( "Sélectionner un dataset", target="dataset-card-dataset-select", placement="top"  ),
                                    dcc.Dropdown( id="dataset-card-dataset-select", placeholder="---" ),
                                ], width=10 ),
                            ], align="center" ),
                        ], className="vstack gap-2" )

                ], width=12 ),
            ] ),
            dbc.Row( [ 
                dbc.Col( [ 
                    dbc.Card( [
                        dbc.Container( [

                            dbc.Row( [ 
                                dbc.Col( [
                                    "Aucun fichier sélectionné."
                                ], id="dataset-card-content", width=12, style={"height":"300px", "overflow": "scroll"} ),
                            ] ),

                        ] )

                    ], body=True)
                ], width=12 )

            ] ),
        ], className="vstack gap-3"  )
    ], className="dbc"  ),

    dataset_form_card,

    html.Div( id='dataset-card-errormsg' ),
	dcc.Store( id='dataset-card-store' )
] )


@callback(
    Output( 'dataset-card-form-name', 'valid' ),
    Output( 'dataset-card-form-name', 'invalid' ),
    Output( 'dataset-card-form-code', 'valid' ),
    Output( 'dataset-card-form-code', 'invalid' ),
    Input( 'dataset-card-form-name', 'value' ),
    Input( 'dataset-card-form-code', 'value' )
)
def onDatasetForm_name_valider( name, code ):

    clicked = ctx.triggered_id

    if clicked == 'dataset-card-form-name':
        if name is None or name == '':
            return False, True, no_update, no_update
        else:
            return True, False, no_update, no_update
        
    elif clicked == 'dataset-card-form-code':
        if code is None or code == '':
            return no_update, no_update, False, True
        else:
            return no_update, no_update, True, False

    else:
        return False, False, False, False
            




@callback(
    Output( 'dataset-card-create-btn', 'disabled' ),
    Output( 'dataset-card-store-btn', 'disabled' ),
    Output( 'dataset-card-delete-btn', 'disabled' ),
    Output( 'dataset-card-download-btn', 'disabled' ),
	Input( 'dataset-card-dataset-select', 'value' ),
    State( 'config-store', 'data' )
)
def onDatasetSelect_enabler( dataset_idx, config_store ):
    """
    This callback is used for enabling or disabling dataset management buttons
    """
    output: cpn.Output = cpn.Ouput( [
        'create_disabled', 'store_disabled', 'delete_disabled', 'download_disabled'
    ] )

    if config_store is None:
        raise PreventUpdate
    
    clicked = ctx.triggered_id
    if clicked is None:
        """ initial state """
        return output.generate( 
            create_disabled = False
        )

    elif clicked == 'dataset-card-dataset-select':
        """ a dataset may be selected """
        if dataset_idx is None:
            """ dataset has been unselected -> disables buttons """
            return output.generate(
                store_disabled = True,
                delete_disabled = True,
                download_disabled = True
            )
        else:
            """ a dataset is selected -> enable action buttons """
            return output.generate(
                store_disabled = False,
                delete_disabled = False,
                download_disabled = False
            )
        
    else:
        raise PreventUpdate


@callback(
    Output( 'dataset-card-domain-select', 'options' ),
    Output( 'dataset-card-domain-select', 'value' ),
    Output( 'dataset-card-dataset-select', 'options' ),
    Output( 'dataset-card-dataset-select', 'value' ),
    Output( 'dataset-card-content', 'children' ),

    Output( 'dataset-card-form', 'is_open' ),
    Output( 'dataset-card-form-name', 'value' ),
    Output( 'dataset-card-form-code', 'value' ),
    Output( 'dataset-card-form-labels-select', 'options' ),
    Output( 'dataset-card-form-labels-select', 'value' ),
    Output( 'dataset-card-form-contexts-select', 'options' ),
    Output( 'dataset-card-form-contexts-select', 'value' ),
    Output( 'dataset-card-form-tags-select', 'options' ),
    Output( 'dataset-card-form-tags-select', 'value' ),
    Output( 'dataset-card-form-comment', 'value' ),
    Output( 'dataset-card-form-channels-beam-1', 'value' ),
    Output( 'dataset-card-form-channels-beam-2', 'value' ),
    Output( 'dataset-card-form-channels-beam-3', 'value' ),
    Output( 'dataset-card-form-channels-beam-4', 'value' ),

	Output( 'dataset-card-store', 'data' ),
	Output( 'dataset-card-errormsg', 'children' ),
	Input( 'dataset-card-domain-select', 'value' ),
	Input( 'dataset-card-dataset-select', 'value' ),
    Input( 'dataset-card-create-btn', 'n_clicks' ),
    Input( 'dataset-card-store-btn', 'n_clicks' ),
    Input( 'dataset-card-delete-btn', 'n_clicks' ),
    Input( 'dataset-card-download-btn', 'n_clicks' ),

    Input( 'dataset-card-form-confirm-btn', 'n_clicks' ),

    State( 'dataset-card-form-name', 'value' ),
    State( 'dataset-card-form-code', 'value' ),
    State( 'dataset-card-form-labels-select', 'value' ),
    State( 'dataset-card-form-contexts-select', 'value' ),
    State( 'dataset-card-form-tags-select', 'value' ),
    State( 'dataset-card-form-comment', 'value' ),

    State( 'dataset-card-form-channels-beam-1', 'value' ),
    State( 'dataset-card-form-channels-beam-2', 'value' ),
    State( 'dataset-card-form-channels-beam-3', 'value' ),
    State( 'dataset-card-form-channels-beam-4', 'value' ),

    State( 'dataset-card-store', 'data' ),
    State( 'config-store', 'data' )
)
def onDatasetSelect( domain_idx, dataset_idx, create_btn, store_btn, delete_btn, download_btn, form_confirm_btn, name, code, labels_idx, contexts_idx, tags_idx, comment, beam_1, beam_2, beam_3, beam_4, card_store, config_store ):
    
    output: cpn.Output = cpn.Ouput( [
        'domain_options', 'domain_value', 'dataset_options', 'dataset_value', 'content_children',
        'form_is_open', 'form_name', 'form_code', 'form_labels_options', 'form_labels_value', 'form_contexts_options', 
        'form_contexts_value', 'form_tags_option', 'form_tags_value', 'form_comment', 'form_beam_1', 'form_beam_2', 'form_beam_3', 'form_beam_4',
        'store_data', 'errormsg_children'
    ] )

    def generate_card_init( dbhost, store ):
        """
        Generate the initial card state
        """

        """ Populates selectors """
        domains = session.load_domains()
        store['domains'] = domains
        domains_options = cpn.populate_selector( domains )

        """ loads labels and contexts for further use """
        labels = session.load_labels()
        store['labels'] = labels

        contexts = session.load_contexts()
        store['contexts'] = contexts

        tags = session.load_tags()
        store['tags'] = tags

        return output.generate( 
            domain_options=domains_options, 
            store_data = json.dumps( store )
        )

    def generate_dataset_content( dataset, labels, contexts, tags ):
        """
        Generate the dataset content
        """

        """ build the label's names list """
        labels_name = []
        for label_url in dataset['labels']:
            labels_name.append( next( f"{label['name']} ({label['code']})" for label in labels if label['url']==label_url ) )

        """ build the context's names list """
        contexts_name = []
        for context_url in dataset['contexts']:
            contexts_name.append( next( f"{context['name']} ({context['code']})" for context in contexts if context['url']==context_url ) )

        """ build the tag's names list """
        tags_name = []
        for tag_url in dataset['tags']:
            tags_name.append( next( f"{tag['name']}" for tag in tags if tag['url']==tag_url ) )

        content = html.Div( [
            html.P( [ 
                f"Dataset: {dataset['name']}",
                html.Ul( [
                    html.Li( f"Code: {dataset['code']}" ),
                    html.Li( f"Date de création: {dataset['crdate']}" ),
                    html.Li( [
                        f"Labels présents dans le dataset: ",
                        html.Ul( [ html.Li( f"{label_name}" ) for label_name in labels_name ] )
                    ] ),
                    html.Li( f"Voies: {dataset['channels']}" ),
                    html.Li( [
                        f"Contextes: ",
                        html.Ul( [ html.Li( f"{context_name}" ) for context_name in contexts_name ] )
                    ] ),
                    html.Li( f"Tags #: {tags_name}" ),
                ] ),
                f"Informations sur le dataset:",
                html.Ul( [
                    html.Li( f"Nombre total d'exemples : {len(dataset['filelabelings'])}" ),
                    html.Li( f"Infos: {dataset['comment']}" ),
                ] )

            ] ),
        ] )

        return content


    if config_store is None:
        """ User is not connected to database - > exit """

        raise PreventUpdate

    if card_store is None:
        """ Init local memory """
        store = {}
    else:
        """ load local memory content """
        store = json.loads( card_store ) 

    try:
        """ main events entry """
        clicked = ctx.triggered_id
        dbhost =  json.loads( config_store )['host']

        if clicked is None:
            """ Initial card state """
            return generate_card_init( dbhost, store )

        elif clicked == 'dataset-card-domain-select':
            """ check all dataset of the selected domain """

            if domain_idx is None:
                """ domain has been unselected -> clean up """
                store['datasets'] = None
                return output.generate( 
                    dataset_options = [],
                    dataset_value = None,
                    store_data = json.dumps( store )
                )

            """ populate dataset selector """
            datasets = session.load_datasets()
            store['datasets'] = datasets
            dataset_options = cpn.populate_selector( datasets )

            return output.generate( 
                dataset_options=dataset_options, 
                store_data = json.dumps( store )
            )

        elif clicked == 'dataset-card-dataset-select':
            """ dataset selecting """

            dataset = store['datasets'][dataset_idx]
            labels = store['labels']
            contexts = store['contexts']
            tags = store['tags']

            return output.generate(
                content_children = generate_dataset_content( dataset, labels, contexts, tags )
            )

        elif clicked == 'dataset-card-create-btn':
            """ dataset creating -> open the formular window """

            labels = store['labels']
            labels_options = cpn.populate_selector( labels )

            contexts = store['contexts']
            contexts_options = cpn.populate_selector( contexts )

            tags = store['tags']
            tags_options = cpn.populate_selector( tags )

            return output.generate(
                form_is_open = True,
                form_labels_options = labels_options,
                orm_contexts_options = contexts_options,
                form_tags_option = tags_options
            )

        elif clicked == 'dataset-card-form-confirm-btn':
            """ save new dataset in database """

            """ check errors """
            if labels_idx is None:
                raise Exception( "Vous devez sélectionner au moins un label !" )
            
            if domain_idx is None:
                raise Exception( "Vous devez sélectionner un domain d'application !" )

            labels = store['labels']
            labels_id = [labels[label_idx]['id'] for label_idx in labels_idx]

            contexts = store['contexts']
            if contexts_idx is None or not contexts_idx:
                contexts_id = []
            else:
                contexts_id = [contexts[context_idx]['id'] for context_idx in contexts_idx]

            tags = store['tags']
            if tags_idx is None or not tags_idx:
                tags_id = []
            else:
                tags_id = [tags[tag_idx]['id'] for tag_idx in tags_idx]      

            domain_id = store['domains'][domain_idx]['id']

            channels = []
            if beam_1 is not None:
                channels = beam_1

            if beam_2 is not None:
                channels += [i+8 for i in beam_2]

            if beam_3 is not None:
                channels += [i+16 for i in beam_3]

            if beam_4 is not None:
                channels += [i+24 for i in beam_4]
            
            """ save in database """
            session.create_dataset( name, code, domain_id, labels_id, channels, contexts_id, tags_id, comment )

            """ reload dataset """
            datasets = session.load_datasets()
            store['datasets'] = datasets
            dataset_options = cpn.populate_selector( datasets )

            """ exit and close de formular window """
            return output.generate(
                form_is_open = False,
                form_name = '',
                form_code = '',
                form_labels_options = [],
                form_labels_value = [],
                form_contexts_options = [],
                form_contexts_value = [],
                form_tags_option = [],
                form_tags_value = [],
                form_comment = '',
                form_beam_1 = [],
                form_beam_2 = [],
                form_beam_3 = [],
                form_beam_4 = [],
                dataset_options = dataset_options
            )

        else:
            raise Exception( "Evènement inconnu" )

    except Exception as e:
        log.info( f" .Error on labeling card: {e}" )
        tracedebug()
        return output.generate( errormsg_children=cpn.display_error_msg( str( e ) ) )

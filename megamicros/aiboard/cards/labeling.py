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
Megamicros Aiboard labeling card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from os import path
from datetime import datetime, date, timedelta
import json
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from megamicros.log import log
from megamicros.aiboard.session import session

# for sliders, see https://plotly.com/python/sliders/

FILETYPE_H5 = 1
FILETYPE_MP4 = 2
FILETYPE_WAV = 3
FILETYPE_MUH5 = 4


"""
Label selecting card by file
"""
select_card_by_file = dbc.Card( [
    dbc.CardHeader( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Etiquetages", width=3 ),
				dbc.Col( dbc.Button( "Modifier", id="p3-bflabeling-card-update-btn", size="sm", outline=True, color="info", n_clicks=0, disabled=True ) ),
				dbc.Col( dbc.Button( "x", id="p3-bflabeling-card-delete-btn", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) ),
                dbc.Col( dbc.Input( id="p3-bflabeling-card-leftchannel-number", type="number", min=0, max=32, step=1, value=1, size="sm", disabled=True ), width=2, className="dbc" ),
                dbc.Col( dbc.Input( id="p3-bflabeling-card-rightchannel-number", type="number", min=0, max=32, step=1, value=8, size="sm", disabled=True ), width=2, className="dbc" ),
                dbc.Col( dbc.Button( [html.I( className="bi bi-arrow-clockwise")], id="p3-bflabeling-card-refresh-btn", size="sm",  outline=True, color="dark", n_clicks=0, disabled=True ) ),
                dbc.Tooltip( "Modifier l'étiquetage", target="p3-bflabeling-card-update-btn", placement="top" ),
                dbc.Tooltip( "Supprimer l'étiquetage", target="p3-bflabeling-card-delete-btn", placement="top"  ),
                dbc.Tooltip( "Canal gauche: choisir un micro mems (1 à 32)", target="p3-bflabeling-card-leftchannel-number", placement="top"  ),
                dbc.Tooltip( "Canal droit: choisir un micro mems (1 à 32)", target="p3-bflabeling-card-rightchannel-number", placement="top"  ),
                dbc.Tooltip( "Recharger le fichier audio", target="p3-bflabeling-card-refresh-btn", placement="top"  ),
            ] )
        ] )
    ] ),

    dbc.CardBody( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Recherche par les fichiers", html_for="p3-bflabeling-card-domain-select" ),
                    dbc.Tooltip( "Sélectionner un domaine", target="p3-bflabeling-card-domain-select", placement="top"  ),
					dcc.Dropdown( id="p3-bflabeling-card-domain-select", placeholder="---" ),
				] )
            ] ),
            html.Br(),
			dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Campagne", html_for="p3-bflabeling-card-campaign-select" ),
                    dbc.Tooltip( "Sélectionner une campagne de mesure", target="p3-bflabeling-card-campaign-select", placement="top"  ),
					dcc.Dropdown( id="p3-bflabeling-card-campaign-select", placeholder="---" ),
				] )
            ] ),
            html.Br(),
			dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Appareil", html_for="p3-bflabeling-card-device-select" ),
                    dbc.Tooltip( "Sélectionner un device", target="p3-bflabeling-card-device-select", placement="top"  ),
					dcc.Dropdown( id="p3-bflabeling-card-device-select", placeholder="---" ),
				] )
            ] ),
            html.Br(),
			dbc.Row( [
				dbc.Col( [ 
                    dbc.Label( "Date et heure", html_for="p3-bflabeling-card-datetime-select", width=4 ),
                    dbc.Tooltip( "Sélectionner l'heure d'enregistrement", target="p3-bflabeling-card-datetime-select", placement="top"  ),
                    dcc.DatePickerSingle( id="p3-bflabeling-card-datetime-select", date=date(2022, 8, 5), className="mb-2" ),
				] )
            ] ),
            html.Br(),
			dbc.Row( [
				dbc.Col( [
					dbc.Label( "Type de fichier", html_for="p3-bflabeling-card-filetype-select" ),
                    dbc.Tooltip( "Sélectionner un type de fichier", target="p3-bflabeling-card-filetype-select", placement="top"  ),
                    dcc.Dropdown( id="p3-bflabeling-card-filetype-select", placeholder="---", options=[
                        {'label': 'Fichiers audio MuH5', 'value':'MUH5'}, 
                        {'label': 'Fichiers sons wav', 'value':'WAV'}, 
                        {'label': 'Fichiers vidéo mp4', 'value': 'MP4'}
                    ], value='MUH5' ),
				] )
            ] ),
            html.Br(),
            dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Fichiers trouvés", id="p3-bflabeling-card-file-select-label", html_for="p3-bflabeling-card-file-select" )
				], width=3 ),
				dbc.Col( [ 
                    dbc.Tooltip( "Sélectionner un fichier dans la liste", target="p3-bflabeling-card-file-select", placement="top" ),
					dcc.Dropdown( id="p3-bflabeling-card-file-select", placeholder="---" ),
				] ),
            ] ),
            html.Br(),
            dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Label(s)", id="p3-bflabeling-card-label-select-label", html_for="p3-bflabeling-card-label-select" )
				], width=3 ),
				dbc.Col( [ 
                    dbc.Tooltip( "Sélectionner un label parmi les labels disponibles", target="p3-bflabeling-card-label-select", placement="top" ),
					dcc.Dropdown( id="p3-bflabeling-card-label-select", placeholder="---" ),
				] ),
            ] ),
            dbc.Row( [
                dbc.Col( id="p3-bflabeling-card-content" )
            ] )
        ] )
    ], className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( "Mettre à jour une labelisation" ),
		dbc.ModalBody( 
			dbc.Form( [

				dbc.Row( [
					dbc.Label( "Label", html_for="p3-bflabeling-form-label", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-bflabeling-form-label", placeholder="---" ),
						dbc.FormText("Label")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Contextes", html_for="p3-bflabeling-form-context", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-bflabeling-form-context", placeholder="---", multi=True ),
						dbc.FormText("Contextes")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Etiquettes", html_for="p3-bflabeling-form-tags", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-bflabeling-form-tags", placeholder="---", multi=True ),
						dbc.FormText("Tags")
					], width=8 )
				], className="mb-3" ),

    			dbc.Row( [
					dbc.Label( "Note", html_for="p3-bflabeling-form-comment", width=3 ),
					dbc.Col( [ 
						dbc.Textarea( id="p3-bflabeling-form-comment", size="sm", valid=True ),
						dbc.FormText("Commentaire optionnel")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Col( [
						dbc.Button( "Valider", id="p3-bflabeling-form-confirm-btn", outline=True, color="info", n_clicks=0 )
					] )
				], className="mb-3" )
            ] )
        )
    ], id = "p3-bflabeling-form", is_open=False, className="dbc" ),
        
	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( "Suppression" ) ),
		dbc.ModalBody( "Voulez-vous vraiment supprimer cette labélisation ?"),
		dbc.ModalFooter( [
			dbc.Button(
				"Confirmer", id="p3-bflabeling-card-delete-confirm-btn", className="ms-auto", outline=True, color="danger", n_clicks=0
			),
			dbc.Button(
				"Annuler", id="p3-bflabeling-card-delete-cancel-btn", className="ms-auto", outline=True, color="secondary", n_clicks=0
			),
		] ),
	], id = "p3-bflabeling-card-delete-confirm", is_open = False ),

    html.Div( id='p3-bflabeling-card-errormsg' ),
	dcc.Store( id='p3-bflabeling-card-store' )
] )


@callback(
    Output( 'p3-bflabeling-card-refresh-btn', 'disabled'),
    Output( 'p3-bflabeling-card-leftchannel-number', 'disabled'),
    Output( 'p3-bflabeling-card-rightchannel-number', 'disabled'), 
    Input( 'p3-bflabeling-card-domain-select', 'value' )
)
def setBFLabelingRefreshDisable( value ):
	""" refresh button and channel's selectors are disabled if no domain is selected """
	return (True, True, True) if value is None else (False, False, False)


@callback(
    Output( 'p3-bflabeling-card-update-btn', 'disabled'), 
    Output( 'p3-bflabeling-card-delete-btn', 'disabled'), 
    Input( 'p3-bflabeling-card-label-select', 'value' )
)
def setBFLabelingUpdateDisable( value ):
	""" update and delete buttons are disabled if no file is selected """
	return (True, True) if value is None else (False, False)


@callback(
    Output( 'p3-bflabeling-card-domain-select', 'options' ),
    Output( 'p3-bflabeling-card-domain-select', 'value' ),
    Output( 'p3-bflabeling-card-campaign-select', 'options' ),
    Output( 'p3-bflabeling-card-campaign-select', 'value' ),
    Output( 'p3-bflabeling-card-device-select', 'options' ),
    Output( 'p3-bflabeling-card-device-select', 'value' ),
    Output( 'p3-bflabeling-card-datetime-select', 'date' ),
    Output( 'p3-bflabeling-card-filetype-select', 'options' ),
    Output( 'p3-bflabeling-card-filetype-select', 'value' ),
    Output( 'p3-bflabeling-card-file-select', 'options' ),
    Output( 'p3-bflabeling-card-file-select', 'value' ),
    Output( 'p3-bflabeling-card-label-select', 'options' ),
    Output( 'p3-bflabeling-card-label-select', 'value' ),
	Output( 'p3-bflabeling-card-content', 'children' ),
        
    Output( 'p3-bflabeling-form', 'is_open' ),
    Output( 'p3-bflabeling-form-label', 'options' ),
    Output( 'p3-bflabeling-form-label', 'value' ),
    Output( 'p3-bflabeling-form-context', 'options' ),
    Output( 'p3-bflabeling-form-context', 'value' ),
    Output( 'p3-bflabeling-form-tags', 'options' ),
    Output( 'p3-bflabeling-form-tags', 'value' ),
    Output( 'p3-bflabeling-form-comment', 'value' ),
           
    Output( 'p3-bflabeling-card-delete-confirm', 'is_open' ),
	Output( 'p3-bflabeling-card-store', 'data' ),
	Output( 'p3-bflabeling-card-errormsg', 'children' ),

	Input( 'p3-bflabeling-card-domain-select', 'value' ),
	Input( 'p3-bflabeling-card-campaign-select', 'value' ),
	Input( 'p3-bflabeling-card-device-select', 'value' ),
	Input( 'p3-bflabeling-card-datetime-select', 'date' ),
	Input( 'p3-bflabeling-card-filetype-select', 'value' ),
    Input( 'p3-bflabeling-card-file-select', 'value' ),
    Input( 'p3-bflabeling-card-label-select', 'value' ),
    Input( 'p3-bflabeling-card-refresh-btn', 'n_clicks' ),
    Input( 'p3-bflabeling-card-update-btn', 'n_clicks' ),
    Input( 'p3-bflabeling-card-delete-btn', 'n_clicks' ),

    Input( 'p3-bflabeling-card-leftchannel-number', 'value'),
    Input( 'p3-bflabeling-card-rightchannel-number', 'value'), 
    Input( 'p3-bflabeling-card-delete-cancel-btn', 'n_clicks' ),
    Input( 'p3-bflabeling-card-delete-confirm-btn', 'n_clicks' ),
          
    Input( 'p3-bflabeling-form-confirm-btn', 'n_clicks' ),
    State( 'p3-bflabeling-form-label', 'value' ),
    State( 'p3-bflabeling-form-context', 'value' ),
    State( 'p3-bflabeling-form-tags', 'value' ),
    State( 'p3-bflabeling-form-comment', 'value' ),
          
	State( 'p3-bflabeling-card-store', 'data' ),
    State( 'config-store', 'data' )
)
def onBFLabelingCard( domain_idx, campaign_idx, device_idx, datetime_value, filetype, file_idx, label_idx, refresh_btn, update_btn, delete_btn, leftchannel, rightchannel, delete_cancel_btn, delete_confirm_btn, confirm_btn, label_form_idx, contexts_form_idx, tags_form_idx, comment, card_store, config_store ):

    def output( **kwargs ):
        return (
            kwargs['domain_options'] if 'domain_options' in kwargs else no_update,
            kwargs['domain_value'] if 'domain_value' in kwargs else no_update,
            kwargs['campaign_options'] if 'campaign_options' in kwargs else no_update,
            kwargs['campaign_value'] if 'campaign_value' in kwargs else no_update,
            kwargs['device_options'] if 'device_options' in kwargs else no_update,
            kwargs['device_value'] if 'device_value' in kwargs else no_update,
            kwargs['datetime_date'] if 'datetime_date' in kwargs else no_update,
            kwargs['filetype_options'] if 'filetype_options' in kwargs else no_update,
            kwargs['filetype_value'] if 'filetype_value' in kwargs else no_update,
            kwargs['file_options'] if 'file_options' in kwargs else no_update,
            kwargs['file_value'] if 'file_value' in kwargs else no_update,
            kwargs['label_options'] if 'label_options' in kwargs else no_update,
            kwargs['label_value'] if 'label_value' in kwargs else no_update,
            kwargs['content_children'] if 'content_children' in kwargs else no_update,
            kwargs['form_is_open'] if 'form_is_open' in kwargs else no_update,
            kwargs['form_label_options'] if 'form_label_options' in kwargs else no_update,
            kwargs['form_label_value'] if 'form_label_value' in kwargs else no_update,
            kwargs['form_context_options'] if 'form_context_options' in kwargs else no_update,
            kwargs['form_context_value'] if 'form_context_value' in kwargs else no_update,
            kwargs['form_tags_options'] if 'form_tags_options' in kwargs else no_update,
            kwargs['form_tags_value'] if 'form_tags_value' in kwargs else no_update,
            kwargs['form_comment_value'] if 'form_comment_value' in kwargs else no_update,
            kwargs['delete_confirm_is_open'] if 'delete_confirm_is_open' in kwargs else no_update,
            kwargs['store_data'] if 'store_data' in kwargs else no_update,
            kwargs['errormsg_children'] if 'ferrormsg_children' in kwargs else no_update,
        )

    def display_error_msg( message: str ):
        return html.Div( [
            dbc.Modal( [ 
                dbc.ModalHeader( dbc.ModalTitle("Erreur" ) ), 
                dbc.ModalBody( message ) 
            ], is_open=True ),
        ] )

    def display_empty_content( message: str ):
        return [
            html.Hr(),
            html.P( [
                html.I( message )
            ] )
        ]

    def populate_selector( data, field='name' ):
        """
        Populate dropdown selector options 
        """
        options = []
        for index, label in enumerate( data ):
            options.append( {"label": label[field], "value": index} )

        return options

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
        clicked = ctx.triggered_id
        dbhost =  json.loads( config_store )['host']

        if clicked is None:
            """ Populates selectors """

            domains = session.load_domains()
            store['domains'] = domains
            domains_options = populate_selector( domains )

            campaigns = session.load_campaigns()
            store['campaigns'] = campaigns
            campaigns_options = populate_selector( campaigns )

            devices = session.load_devices()
            store['devices'] = devices
            devices_options = populate_selector( devices )

            return output( 
                domain_options=domains_options, 
                campaign_options=campaigns_options, 
                device_options=devices_options, 
                content_children=display_empty_content( "Aucune sélection" ),
                store_data = json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-card-domain-select' or clicked == 'p3-bflabeling-card-campaign-select' or clicked == 'p3-bflabeling-card-device-select' or clicked == 'p3-bflabeling-card-filetype-select' or clicked=='p3-bflabeling-card-datetime-select' :
            """ find files that matches selected options (domain, campaign, device, file type and datetime) """
            
            if domain_idx is None or campaign_idx is None or device_idx is None or datetime_value is None or filetype is None:
                """ Some option(s) have not been selected on madatory selectors """
                return output()

            types_ext = {'MUH5':'muh5', 'WAV':'wav', 'MP4':'mp4'}

            """ Complete datetime since the formular don't set time seconds and milliseconds nor 'T' and 'Z' """
            date_time = datetime_value + 'T00:00:00.0Z'

            """ Get device directories """
            if 'directories_url' not in store or clicked == 'p3-bflabeling-card-device-select':
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
                    """ current directory dont match with the slected campaign """
                    continue

                """ Check for files with correct extension at the given date """
                files = session.load_directory_files( directory['id'], types_ext[filetype], date_time )
                store['files'] = files
                files_options = populate_selector( files, field='filename' )

            log.info( f" .Received {len( files_options )} {filetype} file names" )

            return output(
                file_options=files_options,
                store_data = json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-card-file-select':
            """ Files selector is actionned """

            if file_idx == None:
                """ File has been unselected """
                store['labelings'] = None
                store['sourcefile'] = None
                return output(
                    label_options=[],
                    label_value=None,
                    content_children= [],
                    store_data = json.dumps( store )
                )
            
            """ store file content """
            store['sourcefile'] = store['files'][file_idx]

            """ get labelings in selected file """
            labelings = session.load_labelings(  store['sourcefile']['id'] )
            store['labelings'] = labelings

            """ populates the label selector with labelings that have been found in file """
            labels_options = populate_selector( labelings,field='label_name' )
            return output(
                label_options=labels_options,
                label_value=None,
                content_children=display_empty_content( 'Aucun label trouvé' if not labels_options else f"{len(labels_options)} labels trouvés" ),
                store_data = json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-card-label-select':
            """ label selector is actionned """

            if label_idx == None:
                """ Label has been unselected """
                store['labeling'] = None
                store['audio'] = None
                return output(
                    content_children=[],
                    store_data = json.dumps( store )                  
                )      

            """ get file details """
            sourcefile = store['sourcefile']

            """ get labeling details """
            labeling = store['labelings'][label_idx]
            store['labeling'] = labeling

            if sourcefile['type'] == FILETYPE_MUH5:
                datetime_file = datetime.strptime( sourcefile['datetime'], "%Y-%m-%dT%H:%M:%S.%fZ" )
            elif sourcefile['type'] == FILETYPE_WAV:
                datetime_file = datetime.strptime( sourcefile['datetime'], "%Y-%m-%dT%H:%M:%SZ" )
            else:
                log.error(  f"Bad file type <{sourcefile['type']}>" )
                raise Exception( "Erreur interne sur un type de fichier non reconnu."  )

            """ set the database request endpoint for signal uploading """
            timestamp_start = labeling['datetime_start']
            timestamp_end = labeling['datetime_end']
            datetime_start = datetime.fromtimestamp( timestamp_start )
            datetime_end = datetime.fromtimestamp( timestamp_end )
            start = ( datetime_start - datetime_file ).total_seconds()
            end = ( datetime_end - datetime_file ).total_seconds()
            duration = end - start
            audio_fileurl = f"{sourcefile['url']}audio/{start}/{end}/channels/{leftchannel}/{rightchannel}/"
            
            audio_download_filename = path.splitext( sourcefile['filename'] )[0]
            audio_download_filename = f"{audio_download_filename}-{labeling['label_code']}-{labeling['id']}-{leftchannel}-{rightchannel}.wav"

            """ display content """
            content = [
                html.Hr(),
                dbc.Card( [
                    dbc.Container( [
                        dbc.Row( [
                            dbc.Col( [
                                html.P( f"Fichier: {sourcefile['filename']}" ),
                                html.P( f"Label: {labeling['label_name']} (code: {labeling['label_code']})" ),
                                html.P( f"Date: {datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' )}" ),
                                html.P( f"Durée: {duration}s (From {start} to {end})" ),
                            ] )
                        ] ),
                        dbc.Row( [ 
                            dbc.Col( html.Audio( id="p3-bflabeling-card-file-audio", controls=True, src=audio_fileurl ) ),
                            dbc.Col( dbc.Button( html.I( className="bi bi-cloud-download"), id="p3-bflabeling-card-file-audio-download", href=audio_fileurl, download=audio_download_filename, external_link=True, outline=True, color="primary", size="md" ) ),
                            dbc.Tooltip( "Ecouter la séquence", target="p3-bflabeling-card-file-audio", placement="top" ),
                            dbc.Tooltip( "Télécharger le fichier au format wav", target="p3-bflabeling-card-file-audio-download", placement="top" ),
                        ], align="center" )
                    ] )
                ], body=True, color="dark" )
            ]

            store['audio'] = {
                'url': audio_fileurl,
                'start': start,
                'end': end,
                'duration': duration,
                'date': datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                'file': sourcefile['filename'],
                'file_url': sourcefile['url']
            }

            return output(
                content_children= content,
                store_data = json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-card-update-btn':
            """ update formular is requested by user -> launches the formular """

            labeling = store['labeling']            
            
            """ set label selector """
            labels = session.load_labels()
            store['labels'] = labels
            labels_form_options = populate_selector( labels )
            label_form_idx = next( i for i, label in enumerate( labels ) if label['url']==labeling['label'] )

            """ set contexts selector """
            contexts = session.load_contexts()
            store['contexts'] = contexts
            contexts_options = populate_selector( contexts )
    
            contexts_form_idx = []
            if labeling['contexts']:
                for context_url in labeling['contexts']:
                    contexts_form_idx.append( next( i for i, context in enumerate( contexts ) if context['url']==context_url ) )

            """ set tags selector """
            tags = session.load_tags()
            store['tags'] = tags
            tags_options = populate_selector( tags )

            tags_form_idx = []
            if labeling['tags']:
                for tag_url in labeling['tags']:
                    tags_form_idx.append( next( i for i, tag in enumerate( tags ) if tag['url']==tag_url ) )

            return output(
                form_is_open=True,
                form_label_options=labels_form_options,
                form_label_value=label_form_idx,
                form_context_options=contexts_options,
                form_context_value=contexts_form_idx,
                form_tags_options=tags_options,
                form_tags_value=tags_form_idx,
                form_comment_value=labeling['comment'],
                store_data = json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-form-confirm-btn':
            """ update confirm -> save in database """
            
            """ check validity """
            if label_form_idx is None:
                raise Exception( "Aucun label défini !" )

            labels = store['labels']

            """ get contexts database identifier from contexts indexes """
            if contexts_form_idx:
                contexts = store['contexts']
                contexts_id = [contexts[idx]['id'] for idx in contexts_form_idx]
            else:
                contexts_id = None 

            """ get tags database identifier from tags indexes """
            if tags_form_idx:
                tags = store['tags']
                tags_id = [tags[idx]['id'] for idx in tags_form_idx]
            else:
                tags_id = None

            response = session.patch_labeling( store['labeling']['id'], labels[label_form_idx]['id'], contexts_id, tags_id, comment )

            """ save new data for subsequent updates """
            store['labeling']['comment'] = comment
            store['labeling']['label'] = labels[label_form_idx]['url']
            if contexts_form_idx:
                store['labeling']['contexts'] = [contexts[idx]['url'] for idx in contexts_form_idx]
            else:
                store['labeling']['contexts'] = []
            if tags_form_idx:
                store['labeling']['tags'] = [tags[idx]['url'] for idx in tags_form_idx]
            else:
                store['labeling']['tags'] = []
            
            content = [
                html.Hr(),
                html.P( f"Fichier: {store['audio']['file']}" ),
                html.P( f"Label: {labels[label_form_idx]['name']} (code: {labels[label_form_idx]['code']})" ),
                html.P( f"Date: {store['audio']['date']}" ),
                html.P( f"Durée: {store['audio']['duration']}s (From {store['audio']['start']} to {store['audio']['end']})" ),
                html.Audio( controls=True, src=store['audio']['url'] )
            ]

            return output(
                content_children=content,
                form_is_open=False,
                form_label_options=[],
                form_label_value=None,
                form_context_options=[],
                form_context_value=[],
                form_tags_options=[],       
                form_tags_value=[],
                form_comment_value=None,
                store_data=json.dumps( store )
            )

        elif clicked == 'p3-bflabeling-card-delete-btn':
            """ delete selected labeling -> ask for confirm """

            if not ( 'labeling' in store and 'id' in store['labeling'] ):
                log.info( " .Bad user request: no labeling to delete. " )
                raise Exception( "Erreur: aucune labélisation sélectionnée" )

            return output( delete_confirm_is_open=True )

        elif clicked == 'p3-bflabeling-card-delete-cancel-btn':
            """ user canceled the delete action """

            """ close the confirm popup """
            return output( delete_confirm_is_open=False )

        elif clicked == 'p3-bflabeling-card-delete-confirm-btn':
            """ user confirm the delete actiuon -> delete labeling"""

            session.delete_labeling( store['labeling']['id'] )

            """ reload labelings in selected file """
            labelings = session.load_labelings( sourcefile_id=store['sourcefile']['id'] )

            store['labelings'] = labelings

            """ populates the label selector with labelings that have been found in file """
            labels_options = populate_selector( labelings, field='label_name' )

            """ unselect the labeling and close the confirm popup """
            return output(
                label_options=labels_options,
                label_value=None,
                content_children=display_empty_content( "Aucune sélection" ),
                delete_confirm_is_open=False,
                store_data=json.dumps( store )  
            ) 
        
        else:
            log.error( f"Internal error: unknown ctx.triggered_id value: '{clicked}'." )
            raise Exception( f"Internal error. Please see the log file" )

    except Exception as e:
        import traceback
        log.info( f" .Error on labeling card: {e}" )
        print( traceback.format_exc() )
        return output( errormsg_children=display_error_msg( str( e ) ) )



"""
Label selecting card
"""
select_card = dbc.Card( [
    dbc.CardHeader( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Etiquetages", width=3 ),
				dbc.Col( dbc.Button( "Modifier", id="p3-labeling-card-update-btn", size="sm", outline=True, color="info", n_clicks=0, disabled=True ) ),
				dbc.Col( dbc.Button( "x", id="p3-labeling-card-delete-btn", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) ),
                dbc.Col( dbc.Input( id="p3-labeling-card-leftchannel-number", type="number", min=0, max=32, step=1, value=1, size="sm", disabled=True ), width=2, className="dbc" ),
                dbc.Col( dbc.Input( id="p3-labeling-card-rightchannel-number", type="number", min=0, max=32, step=1, value=8, size="sm", disabled=True ), width=2, className="dbc" ),
                dbc.Col( dbc.Button( [html.I( className="bi bi-arrow-clockwise")], id="p3-labeling-card-refresh-btn", size="sm",  outline=True, color="dark", n_clicks=0, disabled=True ) ),
                dbc.Tooltip( "Modifier l'étiquetage", target="p3-labeling-card-update-btn", placement="top" ),
                dbc.Tooltip( "Supprimer l'étiquetage", target="p3-labeling-card-delete-btn", placement="top"  ),
                dbc.Tooltip( "Canal gauche: choisir un micro mems (1 à 32)", target="p3-labeling-card-leftchannel-number", placement="top"  ),
                dbc.Tooltip( "Canal droit: choisir un micro mems (1 à 32)", target="p3-labeling-card-rightchannel-number", placement="top"  ),
                dbc.Tooltip( "Recharger le fichier audio", target="p3-labeling-card-refresh-btn", placement="top"  ),
			] )
		] )    
    ] ),

    dbc.CardBody( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Recherche par les labels", html_for="p3-labeling-card-label-select" ),
                    dbc.Tooltip( "Sélectionner un label", target="p3-labeling-card-label-select", placement="top"  ),
					dcc.Dropdown( id="p3-labeling-card-label-select", placeholder="---" ),
				] )
			] ),
			html.Br(),
			dbc.Row( [
				dbc.Col( [ 
					dbc.Label( "Fichiers trouvés", id="p3-labeling-card-file-select-label", html_for="p3-labeling-card-file-select" )
				], width=3 ),
				dbc.Col( [ 
                    dbc.Tooltip( "Sélectionner un fichier dans la liste", target="p3-labeling-card-file-select", placement="top" ),
					dcc.Dropdown( id="p3-labeling-card-file-select", placeholder="---" ),
				] ),
			] ),
            dbc.Row( [
                dbc.Col( id="p3-labeling-card-content" )
            ])
		] )
    ], className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( "Mettre à jour une labelisation" ),
		dbc.ModalBody( 
			dbc.Form( [

				dbc.Row( [
					dbc.Label( "Label", html_for="p3-labeling-form-label", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-labeling-form-label", placeholder="---" ),
						dbc.FormText("Label")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Contextes", html_for="p3-labeling-form-context", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-labeling-form-context", placeholder="---", multi=True ),
						dbc.FormText("Contextes")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Etiquettes", html_for="p3-labeling-form-tags", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-labeling-form-tags", placeholder="---", multi=True ),
						dbc.FormText("Tags")
					], width=8 )
				], className="mb-3" ),

    			dbc.Row( [
					dbc.Label( "Note", html_for="p3-labeling-form-comment", width=3 ),
					dbc.Col( [ 
						dbc.Textarea( id="p3-labeling-form-comment", size="sm", valid=True ),
						dbc.FormText("Commentaire optionnel")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Col( [
						dbc.Button( "Valider", id="p3-labeling-form-confirm-btn", outline=True, color="info", n_clicks=0 )
					] )
				], className="mb-3" )
            ] )
        )
    ], id = "p3-labeling-form", is_open=False, className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( "Suppression" ) ),
		dbc.ModalBody( "Voulez-vous vraiment supprimer cette labélisation ?"),
		dbc.ModalFooter( [
			dbc.Button(
				"Confirmer", id="p3-labeling-card-delete-confirm-btn", className="ms-auto", outline=True, color="danger", n_clicks=0
			),
			dbc.Button(
				"Annuler", id="p3-labeling-card-delete-cancel-btn", className="ms-auto", outline=True, color="secondary", n_clicks=0
			),
		] ),
	], id = "p3-labeling-card-delete-confirm", is_open = False ),

    html.Div( id='p3-labeling-card-errormsg' ),
	dcc.Store( id='p3-labeling-card-store' )
] )


@callback(
    Output( 'p3-labeling-card-refresh-btn', 'disabled'),
    Output( 'p3-labeling-card-leftchannel-number', 'disabled'),
    Output( 'p3-labeling-card-rightchannel-number', 'disabled'), 
    Input( 'p3-labeling-card-label-select', 'value' )
)
def setLabelingRefreshDisable( value ):
	""" refresh button and channel's slectrors are disabled if no label is selected """
	return (True, True, True) if value is None else (False, False, False)


@callback(
    Output( 'p3-labeling-card-update-btn', 'disabled'), 
    Output( 'p3-labeling-card-delete-btn', 'disabled'), 
    Input( 'p3-labeling-card-file-select', 'value' )
)
def setLabelingUpdateDisable( value ):
	""" update and delete buttons are disabled if no file is selected """
	return (True, True) if value is None else (False, False)


@callback(

    Output( 'p3-labeling-card-label-select', 'options' ),
    Output( 'p3-labeling-card-label-select', 'value' ),
    Output( 'p3-labeling-card-file-select', 'options' ),
    Output( 'p3-labeling-card-file-select', 'value' ),
	Output( 'p3-labeling-card-content', 'children' ),
    Output( 'p3-labeling-form', 'is_open' ),
    Output( 'p3-labeling-form-label', 'options' ),
    Output( 'p3-labeling-form-label', 'value' ),
    Output( 'p3-labeling-form-context', 'options' ),
    Output( 'p3-labeling-form-context', 'value' ),
    Output( 'p3-labeling-form-tags', 'options' ),
    Output( 'p3-labeling-form-tags', 'value' ),
    Output( 'p3-labeling-form-comment', 'value' ),
    Output( 'p3-labeling-card-delete-confirm', 'is_open' ),
	Output( 'p3-labeling-card-store', 'data' ),
	Output( 'p3-labeling-card-errormsg', 'children' ),

	Input( 'p3-labeling-card-label-select', 'value' ),
	Input( 'p3-labeling-card-file-select', 'value' ),
    Input( 'p3-labeling-card-refresh-btn', 'n_clicks' ),
    Input( 'p3-labeling-card-update-btn', 'n_clicks' ),
    Input( 'p3-labeling-card-delete-btn', 'n_clicks' ),

    Input( 'p3-labeling-card-leftchannel-number', 'value'),
    Input( 'p3-labeling-card-rightchannel-number', 'value'), 
    Input( 'p3-labeling-card-delete-cancel-btn', 'n_clicks' ),
    Input( 'p3-labeling-card-delete-confirm-btn', 'n_clicks' ),
    Input( 'p3-labeling-form-confirm-btn', 'n_clicks' ),
    State( 'p3-labeling-form-label', 'value' ),
    State( 'p3-labeling-form-context', 'value' ),
    State( 'p3-labeling-form-tags', 'value' ),
    State( 'p3-labeling-form-comment', 'value' ),
	State( 'p3-labeling-card-store', 'data' ),
    State( 'config-store', 'data' )
)
def onLabelingCard( label_idx, file_idx, refresh_btn, update_btn, delete_btn, leftchannel, rightchannel, delete_cancel_btn, delete_confirm_btn, confirm_btn, label_form_idx, contexts_form_idx, tags_form_idx, comment, card_store, config_store ):

    def display_error_msg( message: str ):
        return html.Div( [
            dbc.Modal( [ 
                dbc.ModalHeader( dbc.ModalTitle("Erreur" ) ), 
                dbc.ModalBody( message ) 
            ], is_open=True ),
        ] )

    def display_empty_content( message: str ):
        return [
            html.Hr(),
            html.P( [
                html.I( message )
            ] )
        ]

    def output( **kwargs ):
        return list(
            kwargs['label_options'] if 'label_options' in kwargs else no_update,
            kwargs['label_value'] if 'label_value' in kwargs else no_update,
            kwargs['file_options'] if 'file_options' in kwargs else no_update,
            kwargs['file_value'] if 'file_value' in kwargs else no_update,
            kwargs['content_children'] if 'content_children' in kwargs else no_update,
            kwargs['form_is_open'] if 'form_is_open' in kwargs else no_update,
            kwargs['form_label_options'] if 'form_label_options' in kwargs else no_update,
            kwargs['form_label_value'] if 'form_label_value' in kwargs else no_update,
            kwargs['form_context_options'] if 'form_context_options' in kwargs else no_update,
            kwargs['form_context_value'] if 'form_context_value' in kwargs else no_update,
            kwargs['form_tags_options'] if 'form_tags_options' in kwargs else no_update,
            kwargs['form_tags_value'] if 'form_tags_value' in kwargs else no_update,
            kwargs['form_comment_value'] if 'form_comment_value' in kwargs else no_update,
            kwargs['delete_confirm_is_open'] if 'fdelete_confirm_is_open' in kwargs else no_update,
            kwargs['store_data'] if 'store_data' in kwargs else no_update,
            kwargs['errormsg_children'] if 'ferrormsg_children' in kwargs else no_update,
        )

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
        clicked = ctx.triggered_id
        dbhost =  json.loads( config_store )['host']

        if clicked is None:
            """ Populates selector """

            labels = session.load_labels()
            store['labels'] = labels
            labels_options = []
            for index, label in enumerate( labels ):
                labels_options.append( {"label": label['name'], "value": index} )

            return (
                labels_options, 
                no_update, no_update, no_update, 
                display_empty_content( "Aucune sélection" ), 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                json.dumps( store ), 
                no_update 
            )

        elif clicked == 'p3-labeling-card-refresh-btn-old':
            """ Reinit and re-populate selector """

            labels = session.load_labels()
            store['labels'] = labels
            labels_options = []
            for index, label in enumerate( labels ):
                labels_options.append( {"label": label['name'], "value": index} )

            return (
                labels_options, 
                None, 
                no_update, 
                None, 
                display_empty_content( "Aucune sélection" ), 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                json.dumps( store ), 
                no_update
            )
        
        elif clicked == 'p3-labeling-card-label-select':
            """ a label has been selected """

            if label_idx is None:
                """ label has been deselected """
                return (
                    no_update,
                    [],
                    no_update,
                    [],                     
                    display_empty_content( "Aucune sélection" ),
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update,
                )

            """ get files that are labelized with """
            files = session.load_labelings( label_id=store['labels'][label_idx]['id'] )

            if not files:
                raise Exception( f"Aucun fichier labélisé avec le label <{store['labels'][label_idx]['name']}>" )

            store['labelized_files'] = files

            """ populate the file selector """
            files_options = []
            for index, file in enumerate( files ):
                files_options.append( {"label": file['sourcefile_filename'], "value": index} )

            return (
                no_update, no_update, 
                files_options, 
                no_update,
                display_empty_content( f"{len( files )} fichier(s) trouvés: sélectionnez un fichier" ),
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                json.dumps( store ), 
                no_update
            )

        elif clicked == 'p3-labeling-card-refresh-btn':
            """ reinstall fileuploading with current channel's values """

            if 'audio' in store:
                duration = store['audio']['duration']
                start = store['audio']['start']
                end = store['audio']['end']
                audio_fileurl = f"{store['audio']['file_url']}audio/{start}/{end}/channels/{leftchannel}/{rightchannel}/"
                timestamp_start = store['labelized_files'][file_idx]['datetime_start']
                timestamp_end = store['labelized_files'][file_idx]['datetime_end']
                datetime_start = datetime.fromtimestamp( timestamp_start )

                """ re-display content """
                #content = [
                #    html.Hr(),
                #    html.P( f"Fichier: {store['labelized_files'][file_idx]['sourcefile_filename']}" ),
                #    html.P( f"Label: {store['labels'][label_idx]['name']} (code: {store['labels'][label_idx]['code']})" ),
                #    html.P( f"Date: {datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' )}" ),
                #    html.P( f"Durée: {duration}s (From {start} to {end})" ),
                #    html.Audio( controls=True, src=audio_fileurl )
                #]

                audio_download_filename = path.splitext( store['labelized_files'][file_idx]['sourcefile_filename'] )[0]
                audio_download_filename = f"{audio_download_filename}-{store['labels'][label_idx]['code']}-{store['labeling']['id']}-{leftchannel}-{rightchannel}.wav"

                """ re-display content """
                content = [
                    html.Hr(),
                    dbc.Card( [
                        dbc.Container( [
                            dbc.Row( [
                                dbc.Col( [
                                    html.P( f"Fichier: {store['labelized_files'][file_idx]['sourcefile_filename']}" ),
                                    html.P( f"Label: {store['labels'][label_idx]['name']} (code: {store['labels'][label_idx]['code']})" ),
                                    html.P( f"Date: {datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' )}" ),
                                    html.P( f"Durée: {duration}s (From {start} to {end})" ),
                                ] )
                            ] ),
                            dbc.Row( [ 
                                dbc.Col( html.Audio( id="p3-labeling-card-file-audio", controls=True, src=audio_fileurl ) ),
                                dbc.Col( dbc.Button( html.I( className="bi bi-cloud-download"), id="p3-labeling-card-file-audio-download", download=audio_download_filename, href=audio_fileurl, external_link=True, outline=True, color="primary", size="md" ) ),
                                dbc.Tooltip( "Ecouter la séquence", target="p3-labeling-card-file-audio", placement="top" ),
                                dbc.Tooltip( "Télécharger le fichier au format wav", target="p3-labeling-card-file-audio-download", placement="top" ),
                            ], align="center" )
                        ] )
                    ], body=True, color="dark" )
                ]

                return (
                    no_update, no_update, no_update, no_update,
                    content,
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                    json.dumps( store ), 
                    no_update
                )

            else:
                """ no selected file -> nothing to change """
                return (
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                )

        elif clicked == 'p3-labeling-card-file-select':
            """ a file have been selected """

            if file_idx is None:
                """ file has been unselected """
                return (
                    no_update, no_update,
                    no_update,
                    [],
                    display_empty_content( f"{len( store['labelized_files'] )} fichier(s) trouvés: sélectionnez un fichier" ),
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                    no_update, no_update,
                )                

            """ get file details """
            file_url = store['labelized_files'][file_idx]['sourcefile']
            file_details = session.get_sourcefile( url=file_url )
            store['file_details'] = file_details
            store['labeling'] = store['labelized_files'][file_idx]

            if file_details['type'] == FILETYPE_MUH5:
                datetime_file = datetime.strptime( file_details['datetime'], "%Y-%m-%dT%H:%M:%S.%fZ" )
            elif file_details['type'] == FILETYPE_WAV:
                datetime_file = datetime.strptime( file_details['datetime'], "%Y-%m-%dT%H:%M:%SZ" )
            else:
                log.error(  f"Bad file type <{file_details['type']}>" )
                raise Exception( "Erreur interne sur un type de fichier non inconnu."  )

            """ set the database request endpoint for signal uploading """
            timestamp_start = store['labelized_files'][file_idx]['datetime_start']
            timestamp_end = store['labelized_files'][file_idx]['datetime_end']
            datetime_start = datetime.fromtimestamp( timestamp_start )
            datetime_end = datetime.fromtimestamp( timestamp_end )
            start = ( datetime_start - datetime_file ).total_seconds()
            end = ( datetime_end - datetime_file ).total_seconds()
            duration = end - start
            audio_fileurl = f"{file_url}audio/{start}/{end}/channels/{leftchannel}/{rightchannel}/"
            
            audio_download_filename = path.splitext( store['labelized_files'][file_idx]['sourcefile_filename'] )[0]
            audio_download_filename = f"{audio_download_filename}-{store['labels'][label_idx]['code']}-{store['labeling']['id']}-{leftchannel}-{rightchannel}.wav"

            """ display content """
            content = [
                html.Hr(),
                dbc.Card( [
                    dbc.Container( [
                        dbc.Row( [
                            dbc.Col( [
                                html.P( f"Fichier: {store['labelized_files'][file_idx]['sourcefile_filename']}" ),
                                html.P( f"Label: {store['labels'][label_idx]['name']} (code: {store['labels'][label_idx]['code']})" ),
                                html.P( f"Date: {datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' )}" ),
                                html.P( f"Durée: {duration}s (From {start} to {end})" ),
                            ] )
                        ] ),
                        dbc.Row( [ 
                            dbc.Col( html.Audio( id="p3-labeling-card-file-audio", controls=True, src=audio_fileurl ) ),
                            dbc.Col( dbc.Button( html.I( className="bi bi-cloud-download"), id="p3-labeling-card-file-audio-download", href=audio_fileurl, download=audio_download_filename, external_link=True, outline=True, color="primary", size="md" ) ),
                            dbc.Tooltip( "Ecouter la séquence", target="p3-labeling-card-file-audio", placement="top" ),
                            dbc.Tooltip( "Télécharger le fichier au format wav", target="p3-labeling-card-file-audio-download", placement="top" ),
                        ], align="center" )
                    ] )
                ], body=True, color="dark" )
            ]

            store['audio'] = {
                'url': audio_fileurl,
                'start': start,
                'end': end,
                'duration': duration,
                'date': datetime_start.strftime( '%Y-%m-%d %H:%M:%S.%f' ),
                'file': store['labelized_files'][file_idx]['sourcefile_filename'],
                'file_url': file_url
            }

            return (
                no_update, no_update, no_update, no_update,
                content,
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                json.dumps( store ), 
                no_update
            )

        elif clicked == 'p3-labeling-card-leftchannel-number':
            log.info( f" .Changing left channel to {leftchannel}" )
            return (
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
            )

        elif clicked == 'p3-labeling-card-rightchannel-number':
            log.info( f" .Changing right channel to {rightchannel}" )
            return (
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
            )

        elif clicked == 'p3-labeling-card-update-btn':
            """ update formular is requested by user -> launches the formular """

            labeling = store['labeling']            
            
            """ set label selector """
            labels = store['labels']
            labels_options = []
            for index, label in enumerate( labels ):
                labels_options.append( {"label": label['name'], "value": index} )

            label_form_idx = next( i for i, label in enumerate( labels ) if label['url']==labeling['label'] )

            """ set contexts selector """
            contexts = session.load_contexts()
            store['contexts'] = contexts
            contexts_options = []
            for index, context in enumerate( contexts ):
                contexts_options.append( {"label": context['name'], "value": index} )         

            """ set tags selector """
            tags = session.load_tags()
            store['tags'] = tags
            tags_options = []
            for index, tag in enumerate( tags ):
                tags_options.append( {"label": tag['name'], "value": index} )

            contexts_form_idx = []
            if labeling['contexts']:
                for context_url in labeling['contexts']:
                    contexts_form_idx.append( next( i for i, context in enumerate( contexts ) if context['url']==context_url ) )

            tags_form_idx = []
            if labeling['tags']:
                for tag_url in labeling['tags']:
                    tags_form_idx.append( next( i for i, tag in enumerate( tags ) if tag['url']==tag_url ) )

            return (
                no_update, no_update, no_update, no_update, no_update,
                True,
                labels_options,
                label_form_idx,
                contexts_options, 
                contexts_form_idx,
                tags_options,
                tags_form_idx,
                labeling['comment'],
                no_update,
                json.dumps( store ),
                no_update
            )

        elif clicked == 'p3-labeling-form-confirm-btn':
            """ update confirm -> save in database """
            
            """ check validity """
            if label_form_idx is None:
                raise Exception( "Aucun label défini !" )

            labels = store['labels']

            """ get contexts database identifier from contexts indexes """
            if contexts_form_idx:
                contexts = store['contexts']
                contexts_id = [contexts[idx]['id'] for idx in contexts_form_idx]
            else:
                contexts_id = None 

            """ get tags database identifier from tags indexes """
            if tags_form_idx:
                tags = store['tags']
                tags_id = [tags[idx]['id'] for idx in tags_form_idx]
            else:
                tags_id = None

            response = session.patch_labeling( store['labeling']['id'], labels[label_form_idx]['id'], contexts_id, tags_id, comment=comment )

            """ save new data for subsequent updates """
            store['labeling']['comment'] = comment
            store['labeling']['label'] = labels[label_form_idx]['url']
            if contexts_form_idx:
                store['labeling']['contexts'] = [contexts[idx]['url'] for idx in contexts_form_idx]
            else:
                store['labeling']['contexts'] = []
            if tags_form_idx:
                store['labeling']['tags'] = [tags[idx]['url'] for idx in tags_form_idx]
            else:
                store['labeling']['tags'] = []
            
            content = [
                html.Hr(),
                html.P( f"Fichier: {store['audio']['file']}" ),
                html.P( f"Label: {labels[label_form_idx]['name']} (code: {labels[label_form_idx]['code']})" ),
                html.P( f"Date: {store['audio']['date']}" ),
                html.P( f"Durée: {store['audio']['duration']}s (From {store['audio']['start']} to {store['audio']['end']})" ),
                html.Audio( controls=True, src=store['audio']['url'] )
            ]

            return(
                no_update, no_update, no_update, no_update,
                content,
                False,
                [], 
                None,
                [],
                [],
                [],
                [],
                None,
                no_update,
                json.dumps( store ),
                no_update
            )

        elif clicked == 'p3-labeling-card-delete-btn':
            """ delete selected labeling -> ask for confirm """

            if not ( 'labeling' in store and 'id' in store['labeling'] ):
                log.info( " .Bad user request: no labeling to delete. " )
                raise Exception( "Erreur: aucune labélisation sélectionnée" )

            return(
                no_update, no_update, no_update, no_update, no_update, no_update, 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                True,
                json.dumps( store ),
                no_update
            )

        elif clicked == 'p3-labeling-card-delete-cancel-btn':
            """ user canceled the delete action """

            """ close the confirm popup """
            return(
                no_update, no_update, no_update, no_update, no_update, no_update, 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False,
                json.dumps( store ),
                no_update
            )

        elif clicked == 'p3-labeling-card-delete-confirm-btn':
            """ user confirm the delete action -> delete labeling"""

            session.delete_labeling( store['labeling']['id'] )

            """ reloads labels """
            labels = session.load_labels()
            store['labels'] = labels
            labels_options = []
            for index, label in enumerate( labels ):
                labels_options.append( {"label": label['name'], "value": index} )

            """ unselect the labeling and close the confirm popup """
            return (
                labels_options, None, 
                [], None, 
                display_empty_content( "Aucune sélection" ),
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False,
                json.dumps( store ),
                no_update
            )

        else:
            log.error( f"Internal error: unknown ctx.triggered_id value: '{clicked}'." )
            raise Exception( f"Internal error. Please see the log file" )

    except Exception as e:
        log.info( f" .Error on labeling card: {e}" )
        return (
            no_update, no_update, no_update, no_update, no_update, no_update, no_update, 
            no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
            display_error_msg( str( e ) )
        )


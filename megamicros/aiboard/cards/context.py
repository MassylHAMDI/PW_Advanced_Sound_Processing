# megamicros_aiboard/apps/aibord/cards/context.py
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
Megamicors Aiboard context card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import json
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from megamicros.log import log
from megamicros.aiboard.session import session


CONTEXT_TYPE_A_PRIORI = 1
CONTEXT_TYPE_A_PPOSTERIORI = 2
CONTEXT_TYPES = [{'label': 'A priori', 'value': CONTEXT_TYPE_A_PRIORI}, {'label': 'A posteriori', 'value': CONTEXT_TYPE_A_PPOSTERIORI}]
CONTEXT_TYPES_OPTIONS = [{'label': 'A priori', 'value': 0}, {'label': 'A posteriori', 'value': 1}]

"""
Context handling card
"""
select_card = dbc.Card( [
	dbc.CardHeader( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Contextes", width=6 ),
				dbc.Col( dbc.Button( "+", id="p3-context-card-create-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=1 ),
				dbc.Col( dbc.Button( "Modifier", id="p3-context-card-update-btn", size="sm",  outline=True, color="info", n_clicks=0, disabled=True ) ),
				dbc.Col( dbc.Button( "x", id="p3-context-card-delete-btn", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) )
			] )
		] )
	] ),

	dbc.CardBody( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( [
					dbc.Label( "Contextes existants", html_for="p3-context-card-select" ),
					dcc.Dropdown( id="p3-context-card-select", placeholder="---" ),
					html.Br(),
					html.Div( id="p3-context-card-content" )
				] )
			] )
		] )
	], className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( id="p3-context-form-title" ) ),
		dbc.ModalBody( 
			dbc.Form( [
				dbc.Row( [
					dbc.Label( "Nom", html_for="p3-context-form-name", width=3 ),
					dbc.Col( [ 
						dbc.Input( type="text", id="p3-context-form-name", size="sm" ),
						dbc.FormText("Nom donné au contexte")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Code", html_for="p3-context-form-code", width=3 ),
					dbc.Col( [ 
						dbc.Input( type="text", id="p3-context-form-code", size="sm" ),
						dbc.FormText("Code donné au contexte")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Type", html_for="p3-context-form-type", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( 
							id="p3-context-form-type", 
							placeholder="---", 
							options=CONTEXT_TYPES_OPTIONS
						),
						dbc.FormText("Contexte priori ou a posteriori")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Domaine", html_for="p3-context-form-domain", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-context-form-domain", placeholder="---" ),
						dbc.FormText("Domaine")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Etiquettes", html_for="p3-context-form-tags", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-context-form-tags", placeholder="---", multi=True ),
						dbc.FormText("Tags/catégories")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Parent", html_for="p3-context-form-parent", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-context-form-parent", placeholder="---" ),
						dbc.FormText("Contexte parent (option)")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Note", html_for="p3-context-form-comment", width=3 ),
					dbc.Col( [ 
						dbc.Textarea( id="p3-context-form-comment", size="sm", valid=True ),
						dbc.FormText("Commentaire optionnel")
					], width=8 )
				], className="mb-3" ),
                
				dbc.Row( [
					dbc.Col( [
						dbc.Button( id="p3-context-form-confirm-btn", outline=True, color="info", n_clicks=0 )
					] )
				], className="mb-3" )
			] ) 
		)
	], id = "p3-context-form", is_open=False, className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( "Suppression" ) ),
		dbc.ModalBody( "Voulez-vous vraiment supprimer ce contexte ?"),
		dbc.ModalFooter( [
			dbc.Button(
				"Confirmer", id="p3-context-card-delete-confirm-btn", className="ms-auto", outline=True, color="danger", n_clicks=0
			),
			dbc.Button(
				"Annuler", id="p3-context-card-delete-cancel-btn", className="ms-auto", outline=True, color="secondary", n_clicks=0
			),
		] ),
	], id = "p3-context-card-delete-confirm", is_open = False ),

    html.Div( id='p3-context-card-errormsg' ),
	dcc.Store( id='p3-context-card-store' )
] )

@callback(
    Output("p3-context-form-name", "valid"), 
	Output("p3-context-form-name", "invalid"),
    Input("p3-context-form-name", "value"),
)
def checkContextNameValidity( name ):
	""" 
	Context name error checking 
	"""
	return (False, True) if not name else (True, False)


@callback(
    Output("p3-context-form-code", "valid"), 
	Output("p3-context-form-code", "invalid"),
    Input("p3-context-form-code", "value")
)
def checkContextCodeValidity( code ):
	""" 
	Context code error checking 
	"""
	return (False, True) if not code else (True, False)



@callback(
    Output("p3-context-card-delete-btn", "disabled"),
    Output("p3-context-card-update-btn", "disabled"),
    Input("p3-context-card-select", "value")
)
def setContextDeleteDisable( value ):
	""" delete button is disabled if no tag is selected """
	return (True, True) if value is None else (False, False)	


@callback(
	Output( 'p3-context-card-select', 'options' ),
	Output( 'p3-context-card-select', 'value' ),
	Output( 'p3-context-card-content', 'children' ),

	Output( 'p3-context-form', 'is_open' ),
	Output( 'p3-context-form-title', 'children' ),
	Output( 'p3-context-form-confirm-btn', 'children' ),
	Output( 'p3-context-form-name', 'value' ),
	Output( 'p3-context-form-code', 'value' ),
	Output( 'p3-context-form-comment', 'value' ),
	Output( 'p3-context-form-domain', 'options' ),
	Output( 'p3-context-form-domain', 'value' ),
	Output( 'p3-context-form-tags', 'options' ),
	Output( 'p3-context-form-tags', 'value' ),
	Output( 'p3-context-form-parent', 'options' ),
	Output( 'p3-context-form-parent', 'value' ),
	Output( 'p3-context-form-type', 'value' ),       

	Output( 'p3-context-card-delete-confirm', 'is_open' ),
	Output( 'p3-context-card-store', 'data' ),
	Output( 'p3-context-card-errormsg', 'children' ),

	Input( 'p3-context-card-select', 'value' ),
	Input( 'p3-context-card-create-btn', 'n_clicks' ),
	Input( 'p3-context-card-update-btn', 'n_clicks' ),

    Input( 'p3-context-card-delete-btn', 'n_clicks' ),
	Input( 'p3-context-card-delete-cancel-btn', 'n_clicks' ),
	Input( 'p3-context-card-delete-confirm-btn', 'n_clicks' ),
       
	Input( 'p3-context-form-confirm-btn', 'n_clicks' ),
	State( 'p3-context-form-name', 'value' ),
    State( 'p3-context-form-code', 'value' ),
	State( 'p3-context-form-comment', 'value' ),
    State( 'p3-context-form-domain', 'value' ),
	State( 'p3-context-form-tags', 'value' ),
	State( 'p3-context-form-parent', 'value' ),
    State( 'p3-context-form-type', 'value' ),
       
	State( 'p3-context-card-store', 'data' ),
	State( 'config-store', 'data' )
)
def onContextCard( context_idx, create_btn, update_btn, delete_btn, delete_cancel_btn, delete_confirm_btn, confirm_btn, name, code, comment, domain_idx, tags_idx, parent_idx, type_idx, card_store, config_store ):
    """
    Callback for tag category selecting card
    """

    def display_error_msg( message: str ):
        return html.Div( [
            dbc.Modal( [ 
                dbc.ModalHeader( dbc.ModalTitle("Erreur" ) ), 
                dbc.ModalBody( message ) 
            ], is_open=True ),
        ] )

    def display_context_content( tagcat, parent_name=None, domain_name=None, tags_name=None, type_text=None ):
        return html.Div( [
            dbc.Row( [
                dbc.Col( [
                    html.P( f"Nom: {tagcat['name']}" ),
                    html.P( f"Code: {tagcat['code']}" ),
                    html.P( f"Type: {'-' if type_text is None else type_text}" ),
                    html.P( f"Parent: {'-' if parent_name is None else parent_name}" ),
                    html.P( f"Domaine: {'-' if domain_name is None else domain_name}" ),
                    html.P( f"Etiquettes: {'-' if tags_name is None else str( tags_name )}" ),
                    html.P( f"Date de création: {tagcat['crdate']}" ),
                    html.P( f"Note: {'-' if tagcat['comment'] is None else tagcat['comment']}" )
                ] )
            ] )
        ] ) if tagcat is not None else html.Div( [
            dbc.Row( [
                dbc.Col( "" )
            ] )
        ] )

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

        """ Init page -> load contexts from database """
        contexts = session.load_contexts()
        if len( contexts ) == 0:
            log.info( f" .Aucun contexte enregistré dans la base" )

        if clicked is None:
            """ Populate selector """
            contexts_options = []
            for index, context in enumerate( contexts ):
                contexts_options.append( {"label": context['name'], "value": index} )

            return (
                contexts_options, 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                json.dumps( store ), 
                no_update
            )

        elif clicked == 'p3-context-card-select':
            """ A label has been selected -> display content """

            if context_idx is None:
                """ no selected context (selector canceled) """
                return ( 
                    no_update, no_update, 
                    display_context_content( None ), 
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                )

            """ a context has been selected: look for parent name if any """
            parent_url = contexts[context_idx]['parent']
            parent_idx = next( (idx for idx, context in enumerate( contexts ) if context['url']==parent_url ), None )
            parent_name = None if parent_idx is None else contexts[parent_idx]['name']

            """ search domain name """
            domains = session.load_domains()
            domain_url = contexts[context_idx]['domain']
            domain_idx = next( (idx for idx, domain in enumerate( domains ) if domain['url']==domain_url ), None )
            domain_name = None if domain_idx is None else domains[domain_idx]['name']

            """ search tags name if any """
            tags = session.load_tags()
            tags_url = contexts[context_idx]['tags']
            tags_name = []
            for tag_url in tags_url:
                tag_idx = next( (idx for idx, tag in enumerate( tags ) if tag['url']==tag_url ), None )
                if tag_idx is None :
                    continue
                tags_name.append( tags[tag_idx]['name'] )
            if not tags_name:
                tags_name = None

            """ type """
            type = contexts[context_idx]['type']
            type_text = "A priori" if type==CONTEXT_TYPE_A_PRIORI else "A posteriori"

            return ( 
                no_update, no_update, 
                display_context_content( contexts[context_idx] if context_idx is not None else None, parent_name, domain_name, tags_name, type_text ), 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
            )

        elif clicked == 'p3-context-card-create-btn':
            """ creating formular is requested by user -> launches formular in create mode """
            store['form'] = 'create'

            """ populates domain selector """
            domains = session.load_domains()
            domains_options = []
            for index, domain in enumerate( domains ):
                domains_options.append( {"label": domain['name'], "value": index} )

            """ populates tag selector """
            tags = session.load_tags()
            tags_options = []
            for index, tag in enumerate( tags ):
                tags_options.append( {"label": tag['name'], "value": index} )

            """ populates parent selector """
            parents_options = []
            for index, parent in enumerate( contexts ):
                parents_options.append( {"label": parent['name'], "value": index} )

            return (
                no_update, no_update, no_update, 
                True, 
                'Créer un nouveau contexte', 
                'Créer', 
                '',
                '',
                '', 
                domains_options, 
                None,
                tags_options, 
                None, 
                parents_options, 
                None, 
                None,
                no_update,
                json.dumps( store ), 
                no_update
            )

        elif clicked == 'p3-context-card-update-btn':
            """ update formular is requested by user -> launches formular in update mode """
            store['form'] = 'update'

            """ populate domain selector """
            domains = session.load_domains()
            domains_options = []
            for index, domain in enumerate( domains ):
                domains_options.append( {"label": domain['name'], "value": index} )

            """ set domain selector value """
            domain_url = contexts[context_idx]['domain']
            domain_idx = next( i for i, _ in enumerate( domains ) if domains[i]['url']==domain_url )
            
            """ populates tag selector """
            tags = session.load_tags()
            tags_options = []
            for index, tag in enumerate( tags ):
                tags_options.append( {"label": tag['name'], "value": index} )

            """ set tag selector values """
            tags_url = contexts[context_idx]['tags']
            tags_idx = []
            for tag_url in tags_url:
                tags_idx.append( next( i for i, _ in enumerate( tags ) if tags[i]['url']==tag_url ) )

            """ populates parent selector """
            parents_options = []
            for index, parent in enumerate( contexts ):
                if index != context_idx:
                    """ A context cannot be its own parent """
                    parents_options.append( {"label": parent['name'], "value": index} )

            """ set parent selector value """
            parent_url = contexts[context_idx]['parent']
            if parent_url:
                parent_idx = next( i for i, _ in enumerate( contexts ) if contexts[i]['url']==parent_url )
            else:
                parent_idx = None

            """ set type selector value """
            type_idx = next( (idx for idx, ctx in enumerate( CONTEXT_TYPES ) if ctx['value']==contexts[context_idx]['type']), None )

            return (
                no_update, no_update, no_update, 
                True, 
                'Mettre à jour un context', 
                'Valider', 
                contexts[context_idx]['name'],
                contexts[context_idx]['code'], 
                contexts[context_idx]['comment'], 
                domains_options, 
                domain_idx,
                tags_options, 						# tags options
                tags_idx,							# list of selected tags
                parents_options, 
                parent_idx, 
                type_idx,
                no_update,
                json.dumps( store ), 
                no_update 
            )

        elif clicked == 'p3-context-card-delete-btn':
            """ delete selected label -> ask for confirm """
            store['form'] = 'delete'
            store['context_idx'] = context_idx
            return (
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                True, 
                json.dumps( store ), 
                no_update 
            )

        elif clicked == 'p3-context-card-delete-cancel-btn':
            """ cancel deleting """
            store['form'] = None
            store['context_idx'] = None
            return (
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False, 
                json.dumps( store ), 
                no_update
            )

        elif clicked == 'p3-context-card-delete-confirm-btn':
            """ delete """
            session.delete_context( id=contexts[context_idx]['id'] )

            """ reloads tags and populates selector with """
            contexts = session.load_contexts()
            contexts_options = []
            for index, context in enumerate( contexts ):
                contexts_options.append( {"label": context['name'], "value": index} )

            """ leave delete mode """
            store['form'] = None
            store['context_idx'] = None

            return (
                contexts_options, 						# populates tag selector
                None,									# unselect 
                display_context_content( None ),		# remove selected tag display
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
                False, 									# close popup window
                json.dumps( store ), 					# save data
                no_update
            )


        elif clicked == "p3-context-form-confirm-btn":
            """ User confirms creating/updating -> save in database and close formular """

            domains = session.load_domains()

            if store['form'] is None:
                """ No mode defined -> error """
                log.error( f"Internal error: form mode create or update not defined" )
                raise Exception( f"Internal error: form mode create or update not defined")
            
            elif store['form'] == 'create':
                """ create mode """

                """ check validity """
                log.info( f" .Saving new context..." )
                if code is None or not code:
                    raise Exception( f"Aucun code choisi !" )
                
                if [idx for idx, _ in enumerate( contexts ) if contexts[idx]['code']==code]:
                    raise Exception( f"Un context portant le même code {code} existe déjà !" )
                
                if type_idx is None:
                    raise Exception( f"Aucun type choisi !" )
                
                if domain_idx is None:
                    raise Exception( f"Aucun domaine choisi !" )
                
                parent_id = None if parent_idx is None else contexts[parent_idx]['id']

                tags = session.load_tags()
                tags_id = []
                if tags_idx:
                    for tag_idx in tags_idx:
                        tags_id.append( tags[tag_idx]['id'] )

                """ save """
                response = session.create_context( name, code, CONTEXT_TYPES[type_idx]['value'], domains[domain_idx]['id'], tags_id, parent_id, comment )

                """ reloads contexts and populates selector with """
                contexts = session.load_contexts()
                contexts_options = []
                for index, context in enumerate( contexts ):
                    contexts_options.append( {"label": context['name'], "value": index} )

                """ leave create mode """
                store['form'] = None

                """ displays the newly created context """ 
                context_id = response['id']
                context_idx = next( i for i, _ in enumerate( contexts ) if contexts[i]['id']==context_id )

                return (
                    contexts_options, 			# populate context selector
                    context_idx, 				# init the selector to the newley created category
                    display_context_content( 
                        contexts[context_idx], 
                        None if parent_idx is None else contexts[parent_idx]['name'], 
                        domains[domain_idx]['name'], 
                        None if tags_idx is None else [tags[idx]['name'] for idx in tags_idx], 
                        CONTEXT_TYPES[type_idx]['label'] 
                    ), 
                    False, 						# close the popup create window 
                    no_update, 
                    no_update, 
                    '',							# reset formular name field 
                    '',							# reset formular code field 
                    '', 						# reset formular comment field
                    [],							# reset domain selector options
                    '',							# reset domain selector value
                    [],							# reset tags selector options
                    [],							# reset tags selector value
                    [],							# reset parent selector options
                    '',							# reset parent selector value
                    '',							# reset type selector value
                    no_update,
                    json.dumps( store ), 		# store local data
                    no_update
                )

            elif store['form'] == 'update':
                """ update mode """
                
                """ check validity """
                if type_idx is None:
                    raise Exception( f"Aucun type choisi !" )
                
                if code is None or not code:
                    raise Exception( f"Aucun typecode choisi !" )
                
                if code != contexts[context_idx]['code']:
                    # code has changed -> check validity of the new code
                    if [idx for idx, _ in enumerate( contexts ) if contexts[idx]['code']==code]:
                        raise Exception( f"Un context portant le même code {code} existe déjà !" )
                
                if domain_idx is None:
                    raise Exception( f"Aucun domaine choisi !" )
                
                parent_id = None if parent_idx is None else contexts[parent_idx]['id']

                tags = session.load_tags()
                tags_id = []
                if tags_idx:
                    for tag_idx in tags_idx:
                        tags_id.append( tags[tag_idx]['id'] )

                response = session.update_context( 
                    contexts[context_idx]['id'], 
                    name, 
                    code, 
                    CONTEXT_TYPES[type_idx]['value'], 
                    domains[domain_idx]['id'], 
                    tags_id, 
                    parent_id, 
                    comment
                )

                """ reloads categories, populates selector with and display updated category """
                contexts = session.load_contexts()
                contexts_options = []
                for index, context in enumerate( contexts ):
                    contexts_options.append( {"label": context['name'], "value": index} )

                """ leave update mode """				
                store['form'] = None

                return (
                    contexts_options, 			# populate label selector
                    no_update,				       
                    display_context_content( 
                        contexts[context_idx], 
                        None if parent_idx is None else contexts[parent_idx]['name'], 
                        domains[domain_idx]['name'],
                        None if tags_idx is None else [tags[idx]['name'] for idx in tags_idx],
                        CONTEXT_TYPES[type_idx]['label'] 
                    ), 
                    False, 						# close the popup update window
                    no_update, 
                    no_update, 
                    '', 						# reset formular name 
                    '',							# reset formular code field 
                    '', 						# reset formular comment
                    [],							# reset domain selector options
                    '',							# reset domain selector value
                    [],							# reset tags selector options
                    [],							# reset tags selector value
                    [],							# reset parent selector options
                    '',							# reset parent selector value
                    '',							# reset type selector value
                    no_update,
                    json.dumps( store ), 		# stire local data
                    no_update
                )

            else:
                raise Exception( f" Internal error: unknown return option stored in local memory: '{store['form']}'." )


    except Exception as e:
        log.info( f" .Error on context card: {e}" )
        return (
            no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update,
            display_error_msg( str( e ) )
        )




# megamicros_aiboard/apps/aibord/cards/tag.py
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
Megamicors Aiboard tags card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import json
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from megamicros.log import log
from megamicros.aiboard.session import session


"""
tag_select_card
"""
select_card = dbc.Card( [
	dbc.CardHeader( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Etiquettes", width=6 ),
				dbc.Col( dbc.Button( "+", id="p3-select-tag-create", size="sm",  outline=True, color="info", n_clicks=0 ), width=1 ),
				dbc.Col( dbc.Button( "Modifier", id="p3-select-tag-update", size="sm",  outline=True, color="info", n_clicks=0, disabled=True ) ),
				dbc.Col( dbc.Button( "x", id="p3-select-tag-delete", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) )
			] )
		] )
	] ),

	dbc.CardBody( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( [
					dbc.Label( "Etiquettes existantes", html_for="p3-select-tag" ),
					dcc.Dropdown( id="p3-select-tag", placeholder="---" ),
					html.Br(),
					html.Div( id="p3-select-tag-content" )
				] )
			] )
		] )
	], className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( id="p3-tag-form-title" ) ),
		dbc.ModalBody( 
			dbc.Form( [
				dbc.Row( [
					dbc.Label( "Nom", html_for="p3-tag-form-name", width=3 ),
					dbc.Col( [ 
						dbc.Input( type="text", id="p3-tag-form-name", size="sm" ),
						dbc.FormText("Nom donné à l'étiquette")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Catégorie (*)", html_for="p3-tag-form-tagcats", width=3 ),
					dbc.Col( [ 
						dcc.Dropdown( id="p3-tag-form-tagcats", placeholder="---" ),
						dbc.FormText("Sélectionnez une catégorie")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Note", html_for="p3-tag-form-comment", width=3 ),
					dbc.Col( [ 
						dbc.Textarea( id="p3-tag-form-comment", size="sm", valid=True ),
						dbc.FormText("Commentaire optionnel")
					], width=8 )
				], className="mb-3" ),
				dbc.Row( [
					dbc.Col( [
						dbc.Button( id="p3-tag-form-confirm", outline=True, color="info", n_clicks=0 )
					] )
				], className="mb-3" )
			] ) 
		)
	], id = "p3-tag-form", is_open=False, className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( "Suppression" ) ),
		dbc.ModalBody( "Voulez-vous vraiment supprimer cette étiquette ?"),
		dbc.ModalFooter( [
			dbc.Button(
				"Confirmer", id="p3-select-tag-delete-confirm", className="ms-auto", outline=True, color="danger", n_clicks=0
			),
			dbc.Button(
				"Annuler", id="p3-select-tag-delete-cancel", className="ms-auto", outline=True, color="secondary", n_clicks=0
			),
		] ),
	], id = "p3-tag-delete-confirm", is_open = False ),

	html.Div( id='p3-select-tag-errormsg' ),
	dcc.Store( id='p3-select-tag-store' )
] )


@callback(
    Output( 'p3-tag-form-name', 'valid' ), 
	Output( 'p3-tag-form-name', 'invalid' ),
    Input( 'p3-tag-form-name', 'value' )
)
def checkTagFormValidity( name ):
	""" 
	Tag formular error checking 
	"""

	if name:
		if name=="":
			return False, True
		else:
			return True, False
		
	return False, True


@callback(
    Output("p3-select-tag-update", "disabled"), 
    Input("p3-select-tag", "value")
)
def setTagUpdateDisable( value ):
	""" update button is disabled if no tag is selected """
	return True if value is None else False


@callback(
    Output("p3-select-tag-delete", "disabled"), 
    Input("p3-select-tag", "value")
)
def setTagDeleteDisable( value ):
	""" delete button is disabled if no tag is selected """
	return True if value is None else False



@callback(
	Output( 'p3-select-tag', 'options' ),
	Output( 'p3-select-tag', 'value' ),
	Output( 'p3-select-tag-content', 'children' ),
	Output( 'p3-tag-form', 'is_open' ),
	Output( 'p3-tag-form-title', 'children' ),
	Output( 'p3-tag-form-confirm', 'children' ),
	Output( 'p3-tag-form-name', 'value' ),
	Output( 'p3-tag-form-comment', 'value' ),
	Output( 'p3-tag-form-tagcats', 'options' ),
	Output( 'p3-tag-form-tagcats', 'value' ),
	Output( 'p3-tag-delete-confirm', 'is_open' ), 
	Output( 'p3-select-tag-store', 'data' ),
	Output( 'p3-select-tag-errormsg', 'children' ),
	Input( 'p3-select-tag', 'value' ),
	Input( 'p3-select-tag-create', 'n_clicks' ),
	Input( 'p3-select-tag-update', 'n_clicks' ),
    Input( 'p3-select-tag-delete', 'n_clicks' ),
	Input( 'p3-select-tag-delete-cancel', 'n_clicks' ),
	Input( 'p3-select-tag-delete-confirm', 'n_clicks' ),
	Input( 'p3-tag-form-confirm', 'n_clicks' ),
	State( 'p3-tag-form-name', 'value' ),
	State( 'p3-tag-form-comment', 'value' ),
    State( 'p3-tag-form-tagcats', 'value' ),
	State( 'p3-select-tag-store', 'data' ),
	State( 'config-store', 'data' )
)
def onTagSelectCard( tag_idx, n_c1, n_c2, n_c3, n_c4, n_c5, n_c6, name, comment, tagcat_idx, card_store, config_store ):
    """
    Callback for tag selecting card
    """

    def display_error_msg( message: str ):
        return html.Div( [
            dbc.Modal( [ 
                dbc.ModalHeader( dbc.ModalTitle("Erreur" ) ), 
                dbc.ModalBody( message ) 
            ], is_open=True ),
        ] )

    def display_category_content( tag, tagcat ):
        return html.Div( [
            dbc.Row( [
                dbc.Col( [
                    html.P( f"Nom de l'étiquette: {tag['name']}" ),
                    html.P( f"Catégorie(s): {tagcat}" ),
                    html.P( f"Date de création: {tag['crdate']}" ),
                    html.P( f"Note: {'-' if tag['comment'] is None else tag['comment']}" )
                ] )
            ] )
        ] ) if tag is not None else html.Div( [
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

        """ Init page -> load tag and categories from database """
        tags = session.load_tags()
        tagcats = session.load_tagcats()
        if len( tags ) == 0:
            raise Exception( f"Aucune étiquette enregistrée dans la base" )

        if clicked is None:
            """ Populate selector """
            tags_options = []
            for index, tag in enumerate( tags ):
                tags_options.append( {"label": tag['name'], "value": index} )

            return tags_options, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, json.dumps( store ), no_update

        elif clicked == 'p3-select-tag':
            """ A tag has been selected -> get category name if any and display tag content """
            
            if tag_idx is None:
                """ no selected tag (selector canceled) """
                return (
                    no_update, no_update, 
                    display_category_content( None, None ), 
                    no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
                )

            """ a tag has been selected: look for a category """
            tagcat_id = tags[tag_idx]['tagcat']

            """ search for the category name of the tag if any """
            tagcat_idx = next( ( idx for idx, tagcat in enumerate( tagcats ) if tagcat['id'] == tagcat_id ), None )
            tagcatname = '-' if tagcat_idx is None else tagcats[tagcat_idx]['name'] 

            return (
                no_update, no_update, 
                display_category_content( tags[tag_idx] if tag_idx is not None else None, tagcatname ), 
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
            )

        elif clicked == 'p3-select-tag-create':
            """ create formular is requested by user -> launches formular with its categories in create mode """
            store['form'] = 'create'
            tagcats_options = []
            for index, tagcat in enumerate( tagcats ):
                tagcats_options.append( {"label": tagcat['name'], "value": index} )

            return no_update, no_update, no_update, True, 'Créer une nouvelle étiquette', 'Créer', no_update, no_update, tagcats_options, no_update, no_update, json.dumps( store ), no_update

        elif clicked == 'p3-select-tag-update':
            """ update formular is requested by user -> launches formular with its categories in update mode """
            store['form'] = 'update'
            tagcats_options = []
            for index, tagcat in enumerate( tagcats ):
                tagcats_options.append( {"label": tagcat['name'], "value": index} )

            tagcat_idx = [i for i, _ in enumerate( tagcats ) if tagcats[i]['id']==tags[tag_idx]['tagcat']][0]
            return no_update, no_update, no_update, True, 'Mettre à jour une étiquette', 'Valider', tags[tag_idx]['name'], tags[tag_idx]['comment'], tagcats_options, tagcat_idx, no_update, json.dumps( store ), no_update

        elif clicked == 'p3-select-tag-delete':
            """ delete selected category -> ask for confirm """
            store['form'] = 'delete'
            store['tag_idx'] = tag_idx
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, True, json.dumps( store ), no_update

        elif clicked == 'p3-select-tag-delete-cancel':
            """ cancel deleting """
            store['form'] = None
            store['tag_idx'] = None
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, False, json.dumps( store ), no_update

        elif clicked == 'p3-select-tag-delete-confirm':
            """ delete """
            session.delete_tag( tags[tag_idx]['id'] )

            """ reloads tags and populates selector with """
            tags = session.load_tags()
            tags_options = []
            for index, tag in enumerate( tags ):
                tags_options.append( {"label": tag['name'], "value": index} )

            """ leave delete mode """
            store['form'] = None
            store['tag_idx'] = None

            return (
                tags_options, 							# populates tag selector
                None,									# unselect 
                display_category_content( None, None ),	# remove selected tag display
                no_update, no_update, no_update, no_update, no_update, no_update, no_update, 
                False, 									# close popup window
                json.dumps( store ), 					# save data
                no_update
            )

        elif clicked == "p3-tag-form-confirm":
            """ User confirms creating/updating -> save in database and close formular """

            if store['form'] is None:
                """ No mode defined -> error """
                log.error( f"Internal error: form mode create or update not defined" )
                raise Exception( f"Internal error: form mode create or update not defined")
            
            elif store['form'] == 'create':
                """ create mode """

                """ check validity """
                if [idx for idx, _ in enumerate( tags ) if tags[idx]['name']==name]:
                    raise Exception( f"L'étiquette {name} existe déjà !" )

                if tagcat_idx is None:
                    raise Exception( f"Catégorie manquante !" )

                """ save """
                response = session.create_tag( name, tagcats[tagcat_idx]['id'], comment )

                """ reloads tags and populates selector with """
                tags = session.load_tags()
                tags_options = []
                for index, tag in enumerate( tags ):
                    tags_options.append( {"label": tag['name'], "value": index} )

                """ leave create mode """
                store['form'] = None

                """ display the newly created tag """ 
                tag_id = response['id']
                tag_idx = next( i for i, _ in enumerate( tags ) if tags[i]['id']==tag_id )

                return (
                    tags_options, 				# populate tag selector
                    tag_idx, 					# init the selector to the newley created tag
                    display_category_content( tags[tag_idx], tagcats[tagcat_idx]['name'] ), 
                    False, 						# close the popup cxreate window 
                    no_update, 
                    no_update, 
                    '',							# reset formular name field 
                    '', 						# reset formular comment field
                    no_update, 
                    '', 						# reset formular tagcat selector
                    no_update,
                    json.dumps( store ), 		# store local data
                    no_update
                )

            elif store['form'] == 'update':
                """ update """

                """ check validity """
                if tagcat_idx is None:
                    raise Exception( f"Catégorie manquante !" )

                session.update_tag( tags[tag_idx]['id'], name, tagcats[tagcat_idx]['id'], comment )

                """ reloads tags and populates selector with """
                tags = session.load_tags()
                tags_options = []
                for index, tag in enumerate( tags ):
                    tags_options.append( {"label": tag['name'], "value": index} )

                """ leave update mode """				
                store['form'] = None

                return (
                    tags_options, 				# populate tag selector
                    no_update,
                    display_category_content( tags[tag_idx], tagcats[tagcat_idx]['name'] ), 
                    False, 						# close the popup update window
                    no_update, 
                    no_update, 
                    '', 						# reset formular name 
                    '', 						# reset formular comment
                    no_update, 
                    '', 						# reset formular tagcat selector
                    no_update,
                    json.dumps( store ), 
                    no_update
                )

            else:
                raise Exception( f" Internal error: unknown return option stored in local memory: '{store['form']}'." )

        else:
            """ unknown entry -> nothing to do """
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update


    except Exception as e:
        log.info( f" .Error on tag select card: {e}" )
        store = {}
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, json.dumps( store ), display_error_msg( str( e ) )




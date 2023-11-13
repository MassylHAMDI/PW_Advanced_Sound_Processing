# megamicros_aiboard/apps/aibord/cards/tagcat.py
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
Megamicors Aiboard tags category card

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

from datetime import datetime
import json
from dash import html, dcc, callback, Input, Output, State, no_update, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from megamicros.log import log
from megamicros.aiboard.session import session

"""
Category select card
"""
select_card = dbc.Card( [
	dbc.CardHeader( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( "Catégories", width=6 ),
				dbc.Col( dbc.Button( "+", id="p3-tagcat-card-create-btn", size="sm",  outline=True, color="info", n_clicks=0 ), width=1 ),
				dbc.Col( dbc.Button( "Modifier", id="p3-tagcat-card-update-btn", size="sm",  outline=True, color="info", n_clicks=0, disabled=True ) ),
				dbc.Col( dbc.Button( "x", id="p3-tagcat-card-delete-btn", size="sm",  outline=True, color="danger", n_clicks=0, disabled=True ) )
			] )
		] )
	] ),

	dbc.CardBody( [
		dbc.Container( [
			dbc.Row( [
				dbc.Col( [
					dbc.Label( "Catégories existantes", html_for="p3-tagcat-card-select" ),
					dcc.Dropdown( id="p3-tagcat-card-select", placeholder="---" ),
					html.Br(),
					html.Div( id="p3-tagcat-card-content" )
				] )
			] )
		] )
	], className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( id="p3-tagcat-form-title" ) ),
		dbc.ModalBody( 
			dbc.Form( [
				dbc.Row( [
					dbc.Label( "Nom", html_for="p3-tagcat-form-name", width=3 ),
					dbc.Col( [ 
						dbc.Input( type="text", id="p3-tagcat-form-name", size="sm" ),
						dbc.FormText("Nom donné à l'étiquette")
					], width=8 )
				], className="mb-3" ),

				dbc.Row( [
					dbc.Label( "Note", html_for="p3-tagcat-form-comment", width=3 ),
					dbc.Col( [ 
						dbc.Textarea( id="p3-tagcat-form-comment", size="sm", valid=True ),
						dbc.FormText("Commentaire optionnel")
					], width=8 )
				], className="mb-3" ),
				dbc.Row( [
					dbc.Col( [
						dbc.Button( id="p3-tagcat-form-confirm-btn", outline=True, color="info", n_clicks=0 )
					] )
				], className="mb-3" )
			] ) 
		)
	], id = "p3-tagcat-form", is_open=False, className="dbc" ),

	dbc.Modal( [
		dbc.ModalHeader( dbc.ModalTitle( "Suppression" ) ),
		dbc.ModalBody( "Voulez-vous vraiment supprimer cette catégorie ?"),
		dbc.ModalFooter( [
			dbc.Button(
				"Confirmer", id="p3-tagcat-card-delete-confirm-btn", className="ms-auto", outline=True, color="danger", n_clicks=0
			),
			dbc.Button(
				"Annuler", id="p3-tagcat-card-delete-cancel-btn", className="ms-auto", outline=True, color="secondary", n_clicks=0
			),
		] ),
	], id = "p3-tagcat-card-delete-confirm", is_open = False ),

    html.Div( id='p3-tagcat-card-errormsg' ),
	dcc.Store( id='p3-tagcat-card-store' )
] )


@callback(
    Output("p3-tagcat-form-name", "valid"), 
	Output("p3-tagcat-form-name", "invalid"),
    Input("p3-tagcat-form-name", "value")
)
def checkTagcatCreateValidity( name ):
	""" 
	Tag category create error checking 
	"""

	if name:
		if name=="":
			return False, True
		else:
			return True, False
		
	return False, True


@callback(
    Output("p3-tagcat-card-update-btn", "disabled"), 
    Input("p3-tagcat-card-select", "value")
)
def setTagcattUpdateDisable( value ):
	""" update button is disabled if no tag is selected """
	return True if value is None else False


@callback(
    Output("p3-tagcat-card-delete-btn", "disabled"), 
    Input("p3-tagcat-card-select", "value")
)
def setTagcattDeleteDisable( value ):
	""" delete button is disabled if no tag is selected """
	return True if value is None else False


@callback(
	Output( 'p3-tagcat-card-select', 'options' ),
	Output( 'p3-tagcat-card-select', 'value' ),
	Output( 'p3-tagcat-card-content', 'children' ),

	Output( 'p3-tagcat-form', 'is_open' ),
	Output( 'p3-tagcat-form-title', 'children' ),
	Output( 'p3-tagcat-form-confirm-btn', 'children' ),
	Output( 'p3-tagcat-form-name', 'value' ),
	Output( 'p3-tagcat-form-comment', 'value' ),

	Output( 'p3-tagcat-card-delete-confirm', 'is_open' ), 
	Output( 'p3-tagcat-card-store', 'data' ),
	Output( 'p3-tagcat-card-errormsg', 'children' ),

	Input( 'p3-tagcat-card-select', 'value' ),
	Input( 'p3-tagcat-card-create-btn', 'n_clicks' ),
	Input( 'p3-tagcat-card-update-btn', 'n_clicks' ),

    Input( 'p3-tagcat-card-delete-btn', 'n_clicks' ),
	Input( 'p3-tagcat-card-delete-cancel-btn', 'n_clicks' ),
	Input( 'p3-tagcat-card-delete-confirm-btn', 'n_clicks' ),

	Input( 'p3-tagcat-form-confirm-btn', 'n_clicks' ),
	State( 'p3-tagcat-form-name', 'value' ),
	State( 'p3-tagcat-form-comment', 'value' ),
       
	State( 'p3-tagcat-card-store', 'data' ),
	State( 'config-store', 'data' )
)
def onCategorySelectCard( tagcat_idx, create_btn, update_btn, delete_btn, delete_cancel_btnb, delete_confirm_btn, confirm_btn, name, comment, card_store, config_store ):
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

	def display_category_content( tagcat ):
		return html.Div( [
			dbc.Row( [
				dbc.Col( [
					html.P( f"Nom de la catégorie: {tagcat['name']}" ),
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

		""" Init page -> load categories from database """
		tagcats = session.load_tagcats()
		if len( tagcats ) == 0:
			raise Exception( f"Aucune catégorie enregistrée dans la base" )

		if clicked is None:
			""" Populate selector """
			tagcats_options = []
			for index, tagcat in enumerate( tagcats ):
				tagcats_options.append( {"label": tagcat['name'], "value": index} )

			return tagcats_options, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, json.dumps( store ), no_update

		elif clicked == 'p3-tagcat-card-select':
			""" A tag category has been selected -> display content """
			return (
				no_update, no_update, 
				display_category_content( tagcats[tagcat_idx] if tagcat_idx is not None else None ),
				no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update
			)

		elif clicked == 'p3-tagcat-card-create-btn':
			""" creating formular is requested by user -> launches formular in create mode """
			store['form'] = 'create'
			return no_update, no_update, no_update, True, 'Créer une nouvelle catégorie', 'Créer', no_update, no_update, no_update, json.dumps( store ), no_update

		elif clicked == 'p3-tagcat-card-update-btn':
			""" update formular is requested by user -> launches formular with its categories in update mode """
			store['form'] = 'update'
			return no_update, no_update, no_update, True, 'Mettre à jour une catégorie', 'Valider', tagcats[tagcat_idx]['name'], tagcats[tagcat_idx]['comment'], no_update, json.dumps( store ), no_update

		elif clicked == 'p3-tagcat-card-delete-btn':
			""" delete selected category -> ask for confirm """
			store['form'] = 'delete'
			store['tagcat_idx'] = tagcat_idx
			return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, True, json.dumps( store ), no_update

		elif clicked == 'p3-tagcat-card-delete-cancel-btn':
			""" cancel deleting """
			store['form'] = None
			store['tagcat_idx'] = None
			return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, False, json.dumps( store ), no_update

		elif clicked == 'p3-tagcat-card-delete-confirm-btn':
			""" delete """
			session.delete_tagcat( tagcats[tagcat_idx]['id'] )

			""" reloads tags and populates selector with """
			tagcats = session.load_tagcats()
			tagcats_options = []
			for index, tagcat in enumerate( tagcats ):
				tagcats_options.append( {"label": tagcat['name'], "value": index} )

			""" leave delete mode """
			store['form'] = None
			store['tagcat_idx'] = None

			return (
				tagcats_options, 						# populates tag selector
				None,									# unselect 
				display_category_content( None ),	# remove selected tag display
			    no_update, no_update, no_update, no_update, no_update,
				False, 									# close popup window
				json.dumps( store ), 					# save data
	       		no_update
			)

		elif clicked == "p3-tagcat-form-confirm-btn":
			""" User confirms creating/updating -> save in database and close formular """

			if store['form'] is None:
				""" No mode defined -> error """
				log.error( f"Internal error: form mode create or update not defined" )
				raise Exception( f"Internal error: form mode create or update not defined")
			
			elif store['form'] == 'create':
				""" create mode """

				""" check validity """
				if [idx for idx, _ in enumerate( tagcats ) if tagcats[idx]['name']==name]:
					raise Exception( f"La catégorie {name} existe déjà !" )

				""" save """
				response = session.create_tagcat( name, comment )

				""" reloads categories and populates selector with """
				tagcats = session.load_tagcats()
				tagcats_options = []
				for index, tagcat in enumerate( tagcats ):
					tagcats_options.append( {"label": tagcat['name'], "value": index} )

				""" leave create mode """
				store['form'] = None

				""" display the newly created category """ 
				tagcat_id = response['id']
				tagcat_idx = next( i for i, _ in enumerate( tagcats ) if tagcats[i]['id']==tagcat_id )

				return (
					tagcats_options, 			# populate tag selector
					tagcat_idx, 				# init the selector to the newley created category
					display_category_content( tagcats[tagcat_idx] ), 
					False, 						# close the popup cxreate window 
					no_update, 
					no_update, 
					'',							# reset formular name field 
					'', 						# reset formular comment field
					no_update,
					json.dumps( store ), 		# store local data
					no_update
				)

			elif store['form'] == 'update':
				""" update mode """

				session.update_tagcat( tagcats[tagcat_idx]['id'], name, comment )

				""" reloads categories, populates selector with and display updated category """
				tagcats = session.load_tagcats()
				tagcats_options = []
				for index, tagcat in enumerate( tagcats ):
					tagcats_options.append( {"label": tagcat['name'], "value": index} )

				""" leave update mode """				
				store['form'] = None

				return (
					tagcats_options, 			# populate tag selector
					no_update,
					display_category_content( tagcats[tagcat_idx]  ), 
					False, 						# close the popup update window
					no_update, 
					no_update, 
					'', 						# reset formular name 
					'', 						# reset formular comment
					no_update,
					json.dumps( store ), 		# stire local data
					no_update
				)

			else:
				raise Exception( f" Internal error: unknown return option stored in local memory: '{store['form']}'." )
			
		else:
			""" unknown entry -> nothing to do """
			return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

	except Exception as e:
		log.info( f" .Error on category select card: {e}" )
		return no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update, display_error_msg( str( e ) )



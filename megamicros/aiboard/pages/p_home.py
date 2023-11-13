import dash
from dash import html, dcc


dash.register_page( 
    __name__,
    path='/',
    title='Accueil',
    name='Accueil',
    location='sidebar',
    order=0
)


layout = html.Div(children=[
    html.H1( "Accueil" ),

    html.Div(children='''
        Home page content.
    '''),

])

"""
Tools aiming at help for components design
"""
import re
from dash import html, no_update
import dash_bootstrap_components as dbc



class Ouput:
    """
    Class that help to generate component callback output
    """
    __values = []

    def __init__( self, values=[] ) -> None:
        self.__values = values

    def generate( self, **kwargs ) -> list:
        output = []
        for value in self.__values:
            output.append( kwargs[value] if value in kwargs else no_update )

        return output


def display_empty_content( message: str ):
    """
    Display message in card content 
    """
    return [
        html.Hr(),
        html.P( [
            html.I( message )
        ] )
    ]


def display_error_msg( message: str ):
    """
    Display error message in card 
    """    
    return html.Div( [
        dbc.Modal( [ 
            dbc.ModalHeader( dbc.ModalTitle("Erreur" ) ), 
            dbc.ModalBody( message ) 
        ], is_open=True ),
    ] )


def display_success_msg( message: str ):
    """
    Display success message in card 
    """    
    return html.Div( [
        dbc.Modal( [ 
            dbc.ModalHeader( dbc.ModalTitle("Success" ) ), 
            dbc.ModalBody( message ) 
        ], is_open=True ),
    ] )

def display_info_msg( message: str ):
    """
    Display info message in card 
    """    
    return html.Div( [
        dbc.Modal( [ 
            dbc.ModalHeader( dbc.ModalTitle("Info" ) ), 
            dbc.ModalBody( message ) 
        ], is_open=True ),
    ] )



def populate_selector( data, field='name' ):
    """
    Populate dropdown selector options 
    """
    options = []
    for index, label in enumerate( data ):
        options.append( {"label": label[field], "value": index} )

    return options


def format_duration( duration:int|str ):
    """
    Display a duration data in in seconds, minutes hours, etc. 
    """
    if duration is not None:
        duration = int(duration)
        d = duration // (3600 * 24)
        h = duration // 3600 % 24
        m = duration % 3600 // 60
        s = duration % 3600 % 60
        if d > 0:
            return f"{d} days {h}:{m}:{s}"
        elif h > 0:
            return f"{h}:{m}:{s}"
        elif m > 0:
            return f"{m} min and {s} s"
        elif s > 0:
            return f"{s} seconds"
    return '-'

def add_seconds_to_formated_date( formated_date:str ):
    """ 
    Control date format by adding microseconds if needed 
    
    Parameters
    ----------
    
    * formated_date (str): date string in the form xxxTyyyZ
    * return formated_date (str) in the form: xxxTyyy.000Z
    """

    m = re.match( r"(?P<date>.+)T(?P<time>.+)Z", formated_date )
    if m is None:
        raise Exception( f"Unable to process date <{formated_date}>" )
    if m.group(2).find( '.') == -1:
        formated_date = m.group(1) + 'T' + m.group(2) + '.000Z'

    return formated_date
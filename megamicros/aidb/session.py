# megamicros.db.session.py python module for database session managing
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
Megamicros module for database session managing

MegaMicros documentation is available on https://readthedoc.biimea.io

"""


import requests
import re

from megamicros.log import log
from megamicros.aidb.exception import MuDbException


DEFAULT_TIMEOUT = 10


session = requests.Session()

class RestDBSession:
    __session: requests.Session
    __key: str = ''
    __csrftoken: str = ''
    __sessionid: str = ''
    __dbhost: str = ''
    __login: str = ''
    __email: str = ''
    __password: str = ''
    __connected_flag = False


# =============================================================================
# Properties
# =============================================================================

    @property
    def session( self ) -> requests.Session:
        return self.__session
    
    @property
    def dbhost( self ) -> str:
        return self.__dbhost
    
    @property
    def login( self ) -> str:
        return self.__login
    
    @property
    def email( self ) -> str:
        return self.__email
    
    @property
    def password( self ) -> str:
        return self.__password


# =============================================================================
# Constructor
# =============================================================================

    def __init__( self, dbhost: str|None=None, login:str|None=None, email:str|None=None, password:str|None=None ):
        """
        A Requests Aidb session.
        Provides cookie persistence, connection-pooling, and configuration.

        Basic Usage:

        >>> import megamicros_aidb.query.session
        >>> s = session.AidbSession( 'http://host.com', 'login', 'email', 'password' )
        >>> ...

        Or as a context manager:

        >>> with session.AidbSession( 'http://host.com', 'login', 'email', 'password' ) as s:
        ...
        """
        self.__dbhost = None if dbhost is None else dbhost
        self.__login = None if login is None else login
        self.__email = None if email is None else email
        self.__password = None if password is None else password
        self.__connected_flag = False


    def __enter__( self ):

        self.__session = requests.Session()
        log.info( f" .Try connecting on endpoint database {self.__dbhost + '/dj-rest-auth/login/'}..." )
        try:
            response = self.__session.post( 
                self.__dbhost + '/dj-rest-auth/login/', 
                #json={ 'username': self.__login, 'email': self.__email, 'password': self.__password },
                json={ 'username': self.__login, 'password': self.__password }, 
                timeout=DEFAULT_TIMEOUT 
            )

        except Exception as e:
            log.warning( ' .Failed to disconnect from database: {e}' )
            raise MuDbException( f"Failed to connect to database: {e}" )
        
        status_code = response.status_code
        log.info( f" .Got HTTP {status_code} status code from server" )
        if status_code!=200 and status_code!=201:
            raise MuDbException( f'Post request failed with http {status_code} status code' )

        self.__updateSessionWithTokens( response )
        self.__connected_flag = True
        log.info( f' .Successfully connected on {self.__dbhost}' )

        return self


    def open( self, dbhost: str|None=None, login:str|None=None, email:str|None=None, password:str|None=None ):
        if dbhost is not None:
            self.__dbhost = dbhost

        if login is not None:
            self.__login = login

        if email is not None:
            self.__email = email

        if password is not None:
            self.__password = password

        return self.__enter__()

    def __updateSessionWithTokens( self, response: requests.Response ):
        """Set key, crsftoken and session id for opened session"""

        self.__key = None,
        self.__csrftoken = None
        self.__sessionid = None
        cookies =  response.headers['Set-Cookie'].split( '; ' )
        response = response.json()

        """
        Check key
        """
        if 'key' in response:
            self.__key = response['key']

        """
        Check CRSF token and session id
        """
        self.__csrftoken = None
        self.__sessionid = None
        for elem in cookies:
            elem_content = elem.split( '=' )
            if len( elem_content ) > 0:
                if elem_content[0]=='csrftoken':
                    self.__csrftoken = elem_content[1]
                else:
                    try:
                        m = re.match( r"(?P<trash>.+), sessionid=(?P<sessionid>.+)", elem )
                        if m is not None:
                            self.__sessionid = m.group(2)
                        
                    except Exception as e:
                        log.info( f" .Unable to decode session id. Error: {e}" )
        
        if self.__csrftoken is None:
            log.info( f" .No CSRF token found" )
        else:
            log.info( f" .Received CSRF token: {self.__csrftoken}. Update session with" )
            self.__session.headers.update( {'X-CSRFToken': self.__csrftoken} )

        if self.__sessionid is None:
            log.info( f" .No session id found" )
        else:
            log.info( f" .Received session id: {self.__sessionid}" )


    def __exit__( self, *args ):
        """Logout from database if connected"""

        if self.__connected_flag == False:
            # not connected -> nothing to do (should never occure but...)
            return
        
        log.info( f" .Trying to disconnect from database {self.__dbhost}..." )

        try:
            response = self.__session.post( 
                self.__dbhost + '/dj-rest-auth/logout/', 
                json={}, 
                timeout=DEFAULT_TIMEOUT 
            )
            log.info( ' .Logout successful.' )
            self.__connected_flag = False

        except Exception as e:
            log.warning( ' .Failed to disconnect from database: {e}' )
            raise MuDbException( f"Failed to disconnect from database: {e}" )

    def close( self ):
        return self.__exit__( self.__dbhost, self.__login, self.__email, self.__password )

    def __del__( self ):
        if self.__connected_flag:
            self.close()


# =============================================================================
# REST commands
# =============================================================================

    def get( self, request:str, timeout:int=DEFAULT_TIMEOUT, full_url:bool=False ) -> requests.Response:
        """ The [GET] REST command

        Parameters
        ----------
        request: str
            The database request
        timeout: int, optional
            Time before abandon if server does not responds
        full_url: bool, optional
            True or False whether the host is provided or not in the url request (default is False)

        Returns
        -------
        Reponse can be either json text or binary:
        >>> get( request=some_request ).json()  # if json response
        >>> get( request=some_request ).content # if binary response
        """

        if self.__connected_flag == False:
            log.error( "Bad request on data base: connection is closed" )
            raise MuDbException( f"Cannot load data on a closed connection. Please use open() method before requesting" )

        try:
            if not full_url:
                request = f"{self.__dbhost}{request}"

            log.info( f" .Send a database request on endpoint: {request}" )
            response  = self.session.get( request, timeout=timeout )
            if not response.ok:
                log.warning( f"[GET] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )
                log.info( f" .Last request was: {request}" )
                raise MuDbException( f"[GET] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )

            return response

        except MuDbException:
            raise
        except Exception as e:
            log.error( f"[GET] request failed on database '{self.__dbhost}': {e}" )
            raise MuDbException( f"[GET] request failed on database '{self.__dbhost}': {e}" )


    def post( self, request: str, content, timeout=DEFAULT_TIMEOUT, full_url:bool=False ) -> requests.Response:
        """ Submit a POST request to the database server

        Parameters
        ----------
        request: str
            the endpoint url or the complete url (host with endpoint)
        timeout: int, optional
            time limit after which the method throw an exception
        full_url: bool, optional
            True or False whether the host is provided or not in the url request (default is False)
        """

        if self.__connected_flag == False:
            log.error( "Bad request on data base: connection is closed" )
            raise MuDbException( f"Cannot load data on a closed connection. Please use open() method before requesting" )

        try:
            if not full_url:
                request = f"{self.__dbhost}{request}"

            response = self.session.post( request, json=content, timeout=timeout )

        except Exception as e:
            log.error( f"[POST] request failed on database '{self.__dbhost}': {e}" )
            raise MuDbException( f"[POST] request failed on database '{self.__dbhost}': {e}" )

        if not response.ok:
            log.warning( f"[POST] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )
            log.info( f" .Last request was: {request}" )
            raise MuDbException( f"[POST] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )

        return response

    def put( self, request: str, content: dict, timeout=DEFAULT_TIMEOUT, full_url:bool=False ) -> requests.Response:
        """ 
        Submit a PUT request to the database server

        Parameters
        ----------
        request: str
            the endpoint url or the complete url (host with endpoint)
        timeout: int, optional
            time limit after which the method throw an exception
        full_url: bool, optional
            True or False whether the host is provided or not in the url request (default is False)
        """

        if self.__connected_flag == False:
            log.error( "Bad request on data base: connection is closed" )
            raise MuDbException( f"Cannot load data on a closed connection. Please use open() method before requesting" )

        try:
            if not full_url:
                request = f"{self.__dbhost}{request}"

            response = self.session.put( request, json=content, timeout=timeout )

        except Exception as e:
            log.error( f"[PUT] request failed on database '{self.__dbhost}': {e}" )
            raise MuDbException( f"[PUT] request failed on database '{self.__dbhost}': {e}" )

        if not response.ok:
            log.warning( f"[PUT] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )
            log.info( f" .Last request was: {request}" )
            raise MuDbException( f"[PUT] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )

        return response


    def patch( self, request: str, content: dict, timeout=DEFAULT_TIMEOUT, full_url:bool=False  ) -> requests.Response:
        """ Submit a PATCH request to the database server

        Parameters
        ----------
        request: str
            the endpoint url or the complete url (host with endpoint)
        content: dict
            dictionary of fields to be updated
        timeout: int, optional
            time limit after which the method throw an exception
        full_url: bool, optional 
            True or False whether the host is provided or not in the url request (default is False)
        """
        
        if self.__connected_flag == False:
            log.error( "Bad request on data base: connection is closed" )
            raise MuDbException( f"Cannot load data on a closed connection. Please use open() method before requesting" )

        try:
            if not full_url:
                request = f"{self.__dbhost}{request}"
            
            response = self.session.patch( request, json=content, timeout=timeout )

        except Exception as e:
            log.error( f"[PATCH] request failed on database '{self.__dbhost}': {e}" )
            raise MuDbException( f"[PATCH] request failed on database '{self.__dbhost}': {e}" )

        if not response.ok:
            log.warning( f"[PATCH] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )
            log.info( f" .Last request was: {request}" )
            raise MuDbException( f"[PATCH] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )

        return response


    def delete( self, request: str, timeout:int=DEFAULT_TIMEOUT, full_url:bool=False ) -> requests.Response:
        """ Send a delete request to database server

        Parameters
        ----------
        request: str
            a string containing the database end point 
        timeout: int, optional 
            the delay after what the session throw a timeout exception
        full_url: bool, optional
            True or False whether the host is provided or not in the url request (default is False)

        Returns
        -------
            Response object: requests.Response
        """
        if self.__connected_flag == False:
            log.error( "Bad request on data base: connection is closed" )
            raise MuDbException( f"Cannot load data on a closed connection. Please use open() method before requesting" )

        try:
            if not full_url:
                request = f"{self.__dbhost}{request}"

            response = session.delete( request, timeout=timeout )

            if not response.ok:
                log.warning( f"[DELETE] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )
                log.info( f" .Last request was: {request}" )
                raise MuDbException( f"[DELETE] request failed on database '{self.__dbhost}' with status code: {response.status_code}" )

            return response

        except MuDbException:
            raise
        except Exception as e:
            log.error( f"[DELETE] request failed on database '{self.__dbhost}': {e}" )
            raise MuDbException( f"[DElETE] request failed on database '{self.__dbhost}': {e}" )




# =============================================================================
# V1 code, just for ascending compatibility...
# =============================================================================

def updateSessionWithTokens( response: requests.Response ):

    key = None,
    csrftoken = None
    sessionid = None

    if response.status_code != 200 and response.status_code != 201:
        raise Exception( f"Cannot get tokens from response with HTTP status {response.status_code}" )

    cookies =  response.headers['Set-Cookie'].split( '; ' )
    response = response.json()

    """
    Check key
    """
    if 'key' in response:
        key = response['key']

    """
    Check CRSF token and session id
    """
    csrftoken = None
    sessionid = None
    for elem in cookies:
        elem_content = elem.split( '=' )
        if len( elem_content ) > 0:
            if elem_content[0]=='csrftoken':
                csrftoken = elem_content[1]
            else:
                try:
                    m = re.match( r"(?P<trash>.+), sessionid=(?P<sessionid>.+)", elem )
                    if m is not None:
                        sessionid = m.group(2)
                    
                except Exception as e:
                    log.info( f" .Unable to decode session id. Error: {e}" )
    
    if csrftoken is None:
        log.info( f" .No CSRF token found" )
    else:
        log.info( f" .Received CSRF token: {csrftoken}. Update session with" )
        session.headers.update( {'X-CSRFToken': csrftoken} )

    if sessionid is None:
        log.info( f" .No session id found" )
    else:
        log.info( f" .Received session id: {sessionid}" )

    return key, csrftoken, sessionid
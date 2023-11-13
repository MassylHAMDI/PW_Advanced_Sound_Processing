# megamicros.core.ws.py base class for antenna connected to a remote antenna server
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


""" Provide the class for antenna with MEMs signals extracted from a remote antenna

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
import websockets
import json
import asyncio
import threading
import time

from megamicros.log import log
from megamicros.exception import MuException
import megamicros.core.base as base


DEFAULT_MBS_SERVER_ADDRESS      = 'localhost'
DEFAULT_MBS_SERVER_PORT         = 9002
DEFAULT_H5_PASS_THROUGH         = False                     # whether server performs H5 saving or client 
DEFAULT_BACKGROUND_MODE         = False                     # whether background execution mode in on (True) or off (False)


# Megamicros dependances (should be removed)
DEFAULT_MEMS_INIT_WAIT          = 1000                      # Mems initializing time in milliseconds


# =============================================================================
# Exception dedicaced to Megamicros websocket systems
# =============================================================================

class MuWSException( MuException ):
    """Exception base class for Megamicros Winsokets systems """
    
    def __init__( self, message: str="" ):
        super().__init__( message )


# =============================================================================
# The MemsArrayWS base class
# =============================================================================


class MemsArrayWS( base.MemsArray ):
    """ MEMs array class with input stream connected to a remote megamicros server.

    """

    __server_host: str = DEFAULT_MBS_SERVER_ADDRESS
    __server_port: int = DEFAULT_MBS_SERVER_PORT
    __flag_success: bool = None
    __background_mode: bool = DEFAULT_BACKGROUND_MODE

    # H5 attributes
    __h5_pass_through: bool = DEFAULT_H5_PASS_THROUGH


    @property
    def h5_pass_through( self ) -> bool:
        """ Get the H5 compression local (False) or remote (True) flag """
        return self.__h5_pass_through
    
    @property
    def background_mode( self ) -> bool:
        """ Check if bacground mode is on (True) or off (False) """
        return self.__background_mode


    def setBackgroundMode( self ) -> None :
        """ Set the execution background mode on """
        self.__background_mode = True


    def unsetBackgroundMode( self ) -> None :
        """ Set the execution background mode off """
        self.__background_mode = False


    def setH5RecordingPassthrough( self ) -> None :
        """ Set the H5 recording passthrough mode on """
        self.__h5_pass_through = True


    def unsetH5RecordingPassthrough( self ) -> None :
        """ Set the H5 recording passthrough mode off """
        self.__h5_pass_through = False


    def __init__( self, host: str, port: int=DEFAULT_MBS_SERVER_PORT, **kwargs ):
        """ Connect the antenna input stream to a remote antenna 

        The connection to the remote server is verified. If the server is not available, an exception is raised. 

        Parameters
        ----------
        host: str
            The remote host address
        port: int, optional
            The remote port (default is 9002)
        """
        
        # Init base class
        super().__init__( kwargs=kwargs )

        # Set WS settings
        if len( kwargs ) > 0:
            self._set_settings( [], kwargs )

        self.__server_host = host
        self.__server_port = port

        # check connection to the server
        try:
            loop = asyncio.get_running_loop()
            log.info( ' .Async event loop already running. Adding coroutine to the event loop...' )
            task = loop.create_task( self.__try_connect() )
            task.add_done_callback( self.__try_connect_check_error )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__try_connect() )

            if self.__flag_success == False:
                log.error( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
                raise MuWSException( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
            else:
                log.info( ' .Starting MegamicrosWS device [ready]' ) 
                return


    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for MemsArrayWS objects 
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        args: array
            named arguments of the run function
        """

        # Check direct args
        if len( args ) != 0:
            raise MuWSException( "Direct arguments are not accepted" )
        
        try:  
            log.info( f" .Install MemsArrayWS settings" )

            if 'h5_pass_through' in kwargs:
                self.setH5RecordingPassthrough() if kwargs['h5_pass_through'] else self.unsetH5RecordingPassthrough()

            if 'background_mode' in kwargs:
                self.setBackgroundMode() if kwargs['background_mode']== True else self.unsetBackgroundMode()
            
        except Exception as e:
            raise MuWSException( f"Run failed on settings: {e}")
        

    def _check_settings( self ) -> None :
        """ Check settings values for MemsArrayWS and parents settings """

        super()._check_settings()

        if self.h5_recording and self.h5_pass_through and not self.background_mode:
            raise MuWSException( f"Remote H5 recording is only available on background execution mode. Please set the background mode on" )



    def __try_connect_check_error( self, t ):

        if t.result() == True:
            log.info( ' .Starting MegamicrosWS device [ready]' ) 
        else:
            log.error( f"Unable to connect to remote server {self.__server_host}:{self.__server_port}" )
        

    async def __try_connect( self ) -> bool :
        """ Open a connection to the server then get server settings before closing """

        self.__flag_success = False
        try:
            log.info( f" .Try connecting to ws://{self.__server_host}:{str(self.__server_port)}...") 

            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                # check server response
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed with error: {error}" )
                else:
                    log.info( f" .Received positive answer from server" )

                # get remote settings and set them
                log.info( f" .Getting settings values from remote receiver..." )
                await websocket.send( json.dumps( {'request': 'settings'} ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Unable to get settings from server: {error}" )
                log.info( f" .Received settings from server [ok]" )

                # init object with server response
                settings = response["response"]
                self.setAvailableMems( available_mems=settings['available_mems'] )
                self.setAvailableAnalogs( available_analogs=settings['available_analogs'] )
                
        except websockets.exceptions.WebSocketException as e:
            log.error( f"Server connection failed due to websocket failure: {e}" )
            return False

        except Exception as e:
            log.error( f"Server connection failed: {e}" )
            return False
        
        self.__flag_success = True
        return True


    def __check_mbs_error( self, response ) -> bool|str :
        """ Check the response from MBS server concerning the presence of errors 
        
        Parameters
        ----------
        response: dict
            Response given by the remote server after its transformation in Python object
        
        Returns
        -------
        message: str|bool 
            string error message received from server or False if no message
        """

        if response['type'] == 'status' and response['response'] == 'error':
            return response['message'] if 'message' in response else 'Unknown error'
        else:
            return False

    def halt( self ) -> None :

        try:
            # There is current event loop...
            loop = asyncio.get_running_loop()
            task = loop.create_task( self.__halt() )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__halt() )


    async def __halt( self ) -> None :
        """ Send a halt command to stop the remote current running process
        """

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send halt command to server:
                log.info( f" .Send halt command..." )  
                await websocket.send( json.dumps( {'request': 'halt'} ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Halt command failed on remote server: {error}" )
                else:
                    log.info( f" .Halt command completed" )  

        except Exception as e:
            log.error( f"Halt failed: {e}" )


    def halt_master( self ) -> None :

        try:
            # There is current event loop...
            loop = asyncio.get_running_loop()
            task = loop.create_task( self.__halt_master() )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__halt_master() )


    async def __halt_master( self ) -> None :
        """ Send a halt command to stop the remote current master running process
        """

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send halt command to server:
                log.info( f" .Send halt master command..." )  
                await websocket.send( json.dumps( {'request': 'halt_master'} ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Halt_master command failed on remote server: {error}" )
                else:
                    log.info( f" .Halt_master command completed" )  

        except Exception as e:
            log.error( f"Halt_master failed: {e}" )



    def run( self, *args, **kwargs ) :
        """ The main run method that run the remote antenna """

        if len( args ) > 0:
            raise MuWSException( f"Run() method does not accept direct arguments" )
        
        log.info( f" .Starting run execution" )
                
        # Set all settings
        # Run does not call the super().run() method so that we have to handle all settings here      
        try:
            # listen job cannot set some settings
            if 'job' in kwargs and kwargs['job'] == 'listen':
                if 'available_mems_number' in kwargs:
                    log.warning( f" .'available_mems_number' cannot be set for listen job. Removing it" )
                    kwargs.pop( 'available_mems_number')
                if 'available_analogs_number' in kwargs:
                    log.warning( f" .'available_analogs_number' cannot be set for listen job. Removing it" )
                    kwargs.pop( 'available_analogs_number')
                if 'sampling_frequency' in kwargs:
                    log.warning( f" .'sampling_frequency' cannot be set for listen job. Removing it" )
                    kwargs.pop( 'sampling_frequency')
                if 'datatype' in kwargs:
                    log.warning( f" .'datatype' cannot be set for listen job. Removing it" )
                    kwargs.pop( 'datatype')
                if 'frame_length' in kwargs:
                    log.warning( f" .'frame_length' cannot be set for listen job. Removing it" )
                    kwargs.pop( 'frame_length')

            super()._set_settings( [], kwargs=kwargs )
            self._set_settings( [], kwargs=kwargs )

        except Exception as e:
            raise MuWSException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
            
        # Check settings values
        try:
            self._check_settings()
        except Exception as e:
            raise MuWSException( f"Unable to execute run: control failure  ({type(e).__name__}): {e}" )

        # verbose
        if self.duration == 0:
            log.info( f" .Run infinite loop (duration=0)" )
        else :
            log.info( f" .Perform a {self.duration}s run loop" )

        # H5 recording
        if self.h5_recording:
            if self.h5_pass_through:
                log.info( f" .Remote H5 recording by server on (pass-through mode)" )
            else:
                log.info( f" .Local H5 recording on" )
        else:
            log.info( f" .H5 recording off" )

        # Job
        log.info( f" .Start a `{self.job}` running job on remote server" )

        # Backgound mode is deprecated
        if self.background_mode:
            log.info( f" .Background execution mode on" )
        else:
            log.info( f" .Background execution mode off" )

        # For run and master there is no need to run a timer thread even if execution time is limited.
        # Indeed, this is the remote server which performs this work.
        # We have only to wait for the remote server to end the transfer

        # Start the timer if a limited execution time is requested for listeners only
        # In this case, the timeout causes a stop command to be sent to the server
        # We have then to wait for the remote server to end the transfer
        if self.job == 'listen' and self.duration > 0 :
            self._thread_timer = threading.Timer( self.duration, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = threading.Thread( target= self.__run_thread )
        self._async_transfer_thread.start()

        #try:
        #    # There is current event loop...
        #    loop = asyncio.get_running_loop()
        #    task = loop.create_task( self.__run() )
        #
        #except RuntimeError:  
        #    # There is no current event loop...
        #    asyncio.run( self.__run() )


    def __run_thread( self ) -> None :
        """ Start run execution in asynchronous mode with asyncio.run() """

        try:
            log.info( " .Run thread execution started" )
            asyncio.run( self.__run() )
        except MuWSException as e:
            log.info( f" .Run thread halted on error: {e}" )
            self._async_transfer_thread_exception = e
                    

    async def __run( self ):
        """ Perform a run execution on Megamicros remote receiver """

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send settings to server
                # Note that 'clockdiv', and 'mems_init_wait' should be set by the remote server since they are Megamicros parameters 
                # Also notice that the 'int32' datatype is the only avaible datatype on MBS server 
                settings = {
                    'mems': self.mems,
                    'analogs': self.analogs,
                    'counter': self.counter,
                    'counter_skip': self.counter_skip,
                    'status': self.status,
                    'clockdiv': int( 500000 // self.sampling_frequency ) - 1,
                    'sampling_frequency': self.sampling_frequency,
                    'datatype': 'int32' if self.datatype==base.MemsArray.Datatype.int32 or self.datatype==base.MemsArray.Datatype.bint32 else 'float32',
                    'mems_init_wait': DEFAULT_MEMS_INIT_WAIT,
                    'duration': self.duration,
                    'datatype': 'int32',
                    'frame_length': self.frame_length
                }

                # Add H5 settings if H5_pass_through mode is on:
                if self.h5_recording and self.h5_pass_through:
                    settings.update( {
                        'h5_recording': True,
                        'h5_rootdir': self.h5_rootdir,
                        'h5_dataset_duration': self.h5_dataset_duration,
                        'h5_file_duration': self.h5_file_duration,
                        'h5_compressing': self.h5_compressing,
                        'h5_compression_algo': self.h5_compression_algo,
                        'h5_gzip_level': self.h5_gzip_level
                    } )

                if self.background_mode:
                    # Play in background mode -> no more communicatiobn with the server
                    run_command = {'request': self.job, 'settings': settings, 'origin': 'background'}
                else:
                    run_command = {'request': self.job, 'settings': settings}

                # send run command to server:
                log.info( f" .Send running job command ({self.job})" )        
                await websocket.send( json.dumps( run_command ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Run command failed on remote server: {error}" )

                # Start listening unless background mode is ON
                if self.job == 'run':
                    log.info( " .Run command accepted by server" )
                    # Start server listening 
                    await self.__remote_run( websocket )

                    # Stop H5 recording if not yet stopped
                    # The following should be done at the base level :
                    """
                    if self.h5_recording and not self.__h5_pass_through and self._h5_started:
                        self.h5_close()
                    
                    if self.__transfer_index != 0:
                        log.info( f" .Total transfers received: {self.__transfer_index}. Total lost: {self.__transfer_lost} ({self.__transfer_lost*100/self.__transfer_index:.2f}%)")
                        log.info( f" .Total elapsed time: {self.__elapsed_time:.2f} s ({self.__elapsed_time*1000/self.__transfer_index:.2f} ms / frame)" )
                        log.info( f" .Mean completion time: {self.__mean_completion_time*1000:.2f} ms")
                        log.info( f" .Data rate estimation: {self.transfer_rate/1000:.2f} Ko/s (real time is: {self.sampling_frequency*4*self.channels_number/1000:.2f} Ko/s)" )
                    else:
                        log.info( f" .No transfers received" )
                    """
                elif self.job == 'master':
                    log.info( " .Master run command accepted by server" )

                    # wait 2 seconds before halting 
                    time.sleep( 2 )
                    log.info( " .Halt connection with server and exit" )
                    return
                
                elif self.job == 'listen':
                    log.info( " .Listen run command accepted by server" )
                    
                    #set settings comming freom mserver aster if any
                    if "message" in response and "settings" in response["message"]:
                        log.info( " .Update settings comming from server master..." )
                        return_settings = response["message"]["settings"]
                        super()._set_settings( args=[], kwargs=return_settings )
                        self._set_settings( [], kwargs=return_settings )
                        log.info( " .Settings updated [ok]" )
                        log.info( f"  > sampling fequency: {self.sampling_frequency}" )
                        log.info( f"  > frame length: {self.frame_length}" )

                    # Start server listening 
                    await self.__remote_run( websocket )

                else:
                    raise MuWSException( f"Unknown running job `{self.job}`" )

        except Exception as e:
            log.error( f"Failed to connect to remote server ({type(e).__name__}): {e}" )
            if type(e).__name__=='RuntimeError':
                log.warning( f"Asynchronous mode must wait for the end of the execution thread. Did you forget to use `MemsArrayWS.wait()` in your code ?" )


    async def __remote_run( self, websocket ):
        """ Remote run command in foreground mode 
        
        Get data from server and populate the internal data queue - or call the user callback function 

        Parameters
        ----------
        websocket: 
            The open connection websocket
        """

        halt_registered: bool = False       # halt registration flag (to avoid multiple sending)
        signal_buffer = None
        transfer_index = 0                  # transfers counter
        transfer_lost = 0                   # lost transfers counter
        start_time: float = 0
        elapsed_time: float = 0
        sample_time: float = None
        mean_completion_time: float = None
        
        try:
            self.setRunningFlag( True )
            while True:
                # If running turns to False, send the stop command to the remote server
                # and wait until receiving of the completed status message
                # Notice that for `listen` run, the halt command stop only the listener job on remote server, not the master run  
                if self.running == False and halt_registered == False:
                    log.info( " .Send stop command" )
                    await websocket.send( json.dumps( {'request': 'halt'} ) )
                    halt_registered = True
        
                # wait for signal recept from network
                signal_buffer = await websocket.recv()
                sample_time = time.time()
                if start_time == 0:
                    start_time = sample_time

                if isinstance( signal_buffer, str ):
                    # If a message is received, it means that the server has experienced a problem, 
                    # or that the server decided to stop the acquisition.
                    # In both two cases we stop the transfer loop either by raising an exception or by normal exit.
                    response = json.loads( signal_buffer )
                    error = self.__check_mbs_error( response )
                    if error:
                        # Server error: throw an exception
                        raise MuWSException( f"Received error message from server: {error}" )
                    elif response['type'] == 'status' and response['response'] == 'completed':
                        # End of processing message received from server -> leave the loop
                        log.info( f" .Received end of service from server. Stop running." )
                        break
                    elif response['request'] == 'halt' and response['type'] == 'status':
                        if response['response']=="ok":
                            log.info( f" .Received aknowledgment reponse from halt request. Stop running." )
                            break
                        else:
                            raise MuException( f"Received server error or unknown response from halt request: {response['response']}" )
                    else:
                        # Unknown message reception: throw an exception
                        raise MuWSException( f"Received unexpected message from server: {response['response']}" )
                    
                else:
                    # If running status is False, the remaining data on the network are lost
                    # It's simply a matter of speeding up the end of treatment.
                    if not self.running:
                        transfer_lost += 1
                    else:
                        # Process binary data by pushing them in the queue 
                        # Thanks to the queue, data are not lost if the reading process is too slow compared to the filling speed.
                        # However, the queue introduces a latency that can become problematic.
                        # If the user accepts the loss of data, it is possible to limit the size of the queue.
                        # In this case, once the size is reached, each new entry induces the deletion of the oldest one.
                        self.signal_q.put(
                            self._run_process_data_bint32( 
                                signal_buffer,
                                h5_recording = self.h5_recording and not self.__h5_pass_through
                            )
                        )

                        # Transfers counting
                        # Note that the loop control is conducted by the remote server.
                        # The loop stops as soon as a 'completed' message is received from the server  
                        transfer_index += 1
                        elapsed_time += time.time() - sample_time


            elapsed_time = sample_time - start_time
            mean_completion_time = elapsed_time/transfer_index if transfer_index != 0 else 0


        except MuWSException as e:
            # Known exception:
            log.error( f" .Listening loop was stopped: {e}" )
        except Exception as e:
            # Uknnown exception:
            log.error( f" Listening loop stopped due to network error exception ({type(e).__name__}): {e}" )

    
    def selftest( self ) -> json:
        """ Send a selftest request to the remote server """

        try:
            # There is current event loop...
            loop = asyncio.get_running_loop()
            task = loop.create_task( self.__selftest() )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__selftest() )


    async def __selftest( self ) -> json:
       
        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send selftest command to server
                command = {'request': 'selftest' }

                log.info( f" .Send selftest command to server" )        
                await websocket.send( json.dumps( command ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Selftest command failed on remote server: {error}" )
                else:
                    # Update local settings according the antenna response
                    log.info( f" .Remote server selftest command successfull" ) 

                    settings = {
                        'available_analogs': response['response']['available_analogs'],
                        'available_mems': response['response']['available_mems'],
                        'datatype': response['response']['datatype'],
                        'frame_length': response['response']['frame_length'],
                        'mems_sensibility': response['response']['mems_sensibility'],
                        'sampling_frequency': response['response']['sampling_frequency'],
                        'system_type': response['response']['system_type'],
                    }                    

        except Exception as e:
            log.error( f"Failed to connect to remote server ({type(e).__name__}): {e}" )
            if type(e).__name__=='RuntimeError':
                log.warning( f"Asynchronous mode must wait for the end of the execution thread. Did you forget to use `MemsArrayWS.wait()` in your code ?" )

        try:
            super()._set_settings( args=[], kwargs=settings )

            log.info( f" .New settings:" )
            log.info( f"  > available_mems: {self.available_mems}" )
            log.info( f"  > available_analogs: {self.available_analogs}" )
            log.info( f"  > datatype: {str( self.datatype )}" )
            log.info( f"  > frame_length: {self.frame_length}" )
            log.info( f"  > mems_sensibility: {self.sensibility}" )
            log.info( f"  > sampling_frequency: {self.sampling_frequency} Hz" )
            log.info( f"  > system_type: {response['response']['system_type']}" )

        except Exception as e:
            log.error( f"Failed to set new settings ({type(e).__name__}): {e}" )


    def settings( self ) -> json:
        """ Send a settings request to the remote server """

        try:
            # There is current event loop...
            loop = asyncio.get_running_loop()
            task = loop.create_task( self.__settings() )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__settings() )


    async def async_settings( self, future: asyncio.Future ):
        """ Ensure public access to the async private method __settings() 
        
        Provided for users who want to get settings from their own asyncio loop  
        
        Parameters
        ----------
        future: asyncio.Future
            Future coroutine provided by client for getting results of the asynchronous call
        """ 
        await self.__settings( future )


    async def __settings( self, future = None ) -> json:    
        """ Connect to the server for getting settings 
        
        Parameters
        ----------
        future: asyncio.Future
            Result of the asynchronous operation
        """   

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send settings command to server
                command = {'request': 'settings' }

                log.info( f" .Send settings command to server" )        
                await websocket.send( json.dumps( command ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Settings command failed on remote server: {error}" )
                else:
                    # Update local settings according the antenna response
                    log.info( f" .Remote server settings command successfull" ) 

                    settings = {
                        'available_analogs': response['response']['available_analogs'],
                        'available_mems': response['response']['available_mems'],
                        'datatype': response['response']['datatype'],
                        'frame_length': response['response']['frame_length'],
                        'mems_sensibility': response['response']['mems_sensibility'],
                        'sampling_frequency': response['response']['sampling_frequency'],
                        'system_type': response['response']['system_type'],
                    }

        except Exception as e:
            log.error( f"Failed to connect to remote server ({type(e).__name__}): {e}" )
            if type(e).__name__=='RuntimeError':
                log.warning( f"Asynchronous mode must wait for the end of the execution thread. Did you forget to use `MemsArrayWS.wait()` in your code ?" )

        try:
            super()._set_settings( args=[], kwargs=settings )
            self._set_settings( [], kwargs=settings )

            log.info( f" .New settings:" )
            log.info( f"  > available_mems: {self.available_mems}" )
            log.info( f"  > available_analogs: {self.available_analogs}" )
            log.info( f"  > datatype: {str( self.datatype )}" )
            log.info( f"  > frame_length: {self.frame_length}" )
            log.info( f"  > mems_sensibility: {self.sensibility}" )
            log.info( f"  > sampling_frequency: {self.sampling_frequency} Hz" )
            log.info( f"  > system_type: {response['response']['system_type']}" )

            if future is not None:
                future.set_result( settings )

        except Exception as e:
            log.error( f"Failed to set new settings ({type(e).__name__}): {e}" )


    def shutdown( self ) -> None:
        """ Send a shutdown request to the remote server """

        try:
            # There is current event loop...
            loop = asyncio.get_running_loop()
            task = loop.create_task( self.__shutdown() )

        except RuntimeError:  
            # There is no current event loop...
            asyncio.run( self.__shutdown() )


    async def __shutdown( self ) -> None :
        """ A special command for halting the remote server """

        log.info( f" .Connecting to remote host {self.__server_host}:{str(self.__server_port)}..." )
        try:
            async with websockets.connect( f"ws://{self.__server_host}:{str(self.__server_port)}" ) as websocket:
                log.info( " .Connected" )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Connection to server failed: {error}" )        

                # send shutdown command to server
                command = {'request': 'shutdown' }

                log.info( f" .Send shutdown command to server" )        
                await websocket.send( json.dumps( command ) )
                response = json.loads( await websocket.recv() )
                error = self.__check_mbs_error( response )
                if error:
                    raise MuWSException( f"Shutdown command failed on remote server: {error}" )
                else:
                    log.info( f" .Remote server shutdown success" ) 

        except Exception as e:
            log.error( f"Failed to connect to remote server ({type(e).__name__}): {e}" )
            if type(e).__name__=='RuntimeError':
                log.warning( f"Asynchronous mode must wait for the end of the execution thread. Did you forget to use `MemsArrayWS.wait()` in your code ?" )

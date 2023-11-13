# core.base.py base class for MegaMicros receivers
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


""" Provide the base class of MEMs arrays.

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import time
from datetime import datetime
from os import path as ospath
import numpy as np
import queue
import h5py
from enum import Enum
from threading import Thread, Timer

from megamicros.log import log
from megamicros.exception import MuException
from megamicros.aidb.query import AidbSession
from megamicros.data import MuAudio


DEFAULT_FRAME_LENGTH                = 256
DEFAULT_SAMPLING_FREQUENCY          = 50000
DEFAULT_QUEUE_SIZE                  = 2			            # Queue size as the number of buffer that can be queued (0 means infinite signal queueing)
DEFAULT_QUEUE_TIMEOUT               = 2                     # The block delay until the queue is considered as empty  
DEFAULT_DATATYPE			        = "int32"	            # Default receiver incoming data type ("int32" or "float32") 
DEFAULT_SYNC_MODE                   = False                 # Default run mode is asynchronous
DEFAULT_MEMS_SENSIBILITY		    = 1/((2**(24-1))*10**(-26/20)/3.17)	    # Default MEMs sensibility factor (-26dBFS for 104 dB that is 3.17 Pa)

# Default H5 values
DEFAULT_H5_RECORDING				= False				    # Whether H5 recording is On or Off
DEFAULT_H5_SEQUENCE_DURATION		= 1					    # Time duration of a dataset in seconds
DEFAULT_H5_FILE_DURATION			= 15*60				    # Time duration of a complete H5 file in seconds
DEFAULT_H5_COMPRESSING				= False				    # Whether compression mode is On or Off
DEFAULT_H5_COMPRESSION_ALGO 		= 'gzip'			    # Compression algorithm (gzip, lzf, szip)
DEFAULT_H5_GZIP_LEVEL 				= 4					    # compression level for gzip algo (0 to 9, default 4) 
DEFAULT_H5_DIRECTORY				= './'				    # The default directory where H5 files are saved


class MemsArray:
    """ MEMs array base class.

    The MemsArray class models the operation of an antenna composed of any number of microphones
    Les microphones de l'antenne sont obligatoireement numérotés de 0 à `available_mems_number`. 
    Certains peuvent ne pas être *actifs*. `mems_number` donne le nombre de microphones actifs. 
    Les microphones sont définis par une position relative au centre de l'antenne. 
    Ces positions peuvent ne pas être connues. Il n'est alors pas possible de faire du filtrage spatial.
    Les positions des microphones peuvent ne pas être toutes déterminées. 
    C'est le cas lorsque des microphones sont devenus hors d'usage au moement de la mesure.
    Ces microphpjnes sont toujours identifiés comme *available*, mais ils doivent être désactivés dans l'antenne lorsque leurs signaux sont absents du flux entrant.

    Antenna microphones must be numbered from 0 to `available_mems_number`. 
    Some may not be *active*. `mems_number` gives the number of active microphones. 
    Microphones are defined by a position relative to the center of the antenna.
    These positions may not be known. In this case, spatial filtering is not possible.
    A problem arises when not all microphones are located.
    In this case, unlocated microphones must be placed at location (0, 0, 0) so that it can be determined which are not available.
    Calls to antenna definition parameters should follow the order: setAvailableMems(), setMemsPosition(), then setActiveMems()  
    """

    class Datatype(Enum):
        """ Antenna datatype enumeration

        Datatype decide for the output data format of the antenna

        Values
        ------
        unknown: 0
            no dataype specified
        int32: 1
            np.ndarray of 32bits integer data
        float32: 2
            np.ndarray of 32bits float data
        bint32: 3
            binary buffer of 32bits integer data
        bfloat32: 4
            binary buffer of 32bits float data
        """

        unknown = 0
        int32 = 1
        float32 = 2
        bint32 = 3
        bfloat32 = 4

        def __str__( self ):
            """ Convert a datatype integer code into its string enumeration """
            if self == self.unknown:
                return "Unknown"
            elif self == self.int32:
                return "int32"
            elif self == self.float32:
                return "float32"
            elif self == self.bint32:
                return "bint32"
            elif self == self.bfloat32:
                return "bfloat32"
            else:
                return "Unknown datatype"  

        def __int__( self ):
            """ Convert a datatype enumeration into its integer code """
            if self == self.unknown:
                return 0
            elif self == self.int32:
                return 1
            elif self == self.float32:
                return 2
            elif self == self.bint32:
                return 3
            elif self == self.bfloat32:
                return 4
            else:
                return -1
            

    class Queue( queue.Queue ):
        """ Thread safe queue adapted to the MemsArray class 
        
        Original comportment is that insertion blocks once maxsize is reached, until queue items are consumed.
        This implementation pop up the last element of the queue if maxsize is reached.
        """

        __transfert_lost: int = 0

        def __init__( self, maxsize: int = 0 ):
            super().__init__( maxsize )

        def put( self, data ):
            # pop up the last element of the queue if maxsize is reached.
            if self.maxsize > 0 and self.qsize() >= self.maxsize:
                self.get()
                self.__transfert_lost += 1

            # Let parent class do the work 
            super().put( data )


    # Antenna dimensions
    __mems: tuple = []
    __available_mems: tuple = []
    __analogs: tuple = []
    __available_analogs: tuple = []
    __mems_position: np.ndarray|None|None = None
    __counter: bool|None = None
    __counter_skip: bool|None = None
    __status: bool|None = None
    __job: str = 'run'

    # Antenna properties
    __sampling_frequency: float = DEFAULT_SAMPLING_FREQUENCY
    __sensibility: float = DEFAULT_MEMS_SENSIBILITY

    # Output buffering
    __frame_length: int = DEFAULT_FRAME_LENGTH
    __frame_duration: float = DEFAULT_FRAME_LENGTH / DEFAULT_SAMPLING_FREQUENCY
    __it: int = 0
    __max_it: int = 0
    __datatype: Datatype = getattr( Datatype, DEFAULT_DATATYPE ) 
    __signal_q = Queue( maxsize=DEFAULT_QUEUE_SIZE )

    # Running properties
    __duration: int|None = None
    
    # Internal run parameters
    _async_transfer_thread = None
    _async_transfer_thread_exception: MuException = None
    _duration_thread = None
    _thread_timer = None
    _thread_timer_flag: bool = False
    __running: bool = False

    # H5 attributes
    __h5_recording: bool = DEFAULT_H5_RECORDING
    __h5_rootdir: str = DEFAULT_H5_DIRECTORY
    __h5_dataset_duration: int = DEFAULT_H5_SEQUENCE_DURATION
    __h5_file_duration: int  = DEFAULT_H5_FILE_DURATION
    __h5_compressing: bool = DEFAULT_H5_COMPRESSING
    __h5_compression_algo: str = DEFAULT_H5_COMPRESSION_ALGO
    __h5_gzip_level: int = DEFAULT_H5_GZIP_LEVEL

    # H5 recording properties
    __h5_current_file: h5py.File = None
    __h5_dataset_length: int = int( DEFAULT_H5_SEQUENCE_DURATION * __sampling_frequency )
    __h5_dataset_index: int = 0
    __h5_dataset_number:int = int( DEFAULT_H5_FILE_DURATION // DEFAULT_H5_SEQUENCE_DURATION )
    __h5_buffer = None
    __h5_buffer_length: int = __h5_dataset_length
    __h5_buffer_index: int = 0
    __h5_timestamp = 0
    __h5_date = ''
    __h5_started: bool = False
    __h5_stopped: bool = False
    __h5_system = 0
    __h5_comment = ''



    @property
    def job( self ) -> str:
        """ Get the running job """
        return self.__job

    @property
    def running( self ) -> bool:
        """ Get the running status """
        return self.__running
    
    @property
    def sensibility( self ) -> bool:
        """ Get the MEMs sensibility factor. 
        
        Default sensibility is set to Megamicros MEMs sensibility (-26dBFS for 104 dB that is 3.17 Pa) 
        """
        return self.__sensibility

    @property
    def h5_recording( self ) -> bool:
        """ Get the H5 recording flag """
        return self.__h5_recording

    @property
    def h5_rootdir( self ) -> str:
        """ Get the H5 recording root directory """
        return self.__h5_rootdir

    @property
    def h5_dataset_duration( self ) -> int:
        """ Get the MuH5 dataset duration """
        return self.__h5_dataset_duration

    @property
    def h5_file_duration( self ) -> int:
        """ Get the time duration of a complete MuH5 file in seconds """
        return self.__h5_file_duration

    @property
    def h5_compressing( self ) -> bool:
        """ Get the H5 compression boolean flag """
        return self.__h5_compressing

    @property
    def h5_compression_algo( self ) -> str:
        """ Get the H5 compression algorithm """
        return self.__h5_compression_algo
    
    @property
    def h5_gzip_level( self ) -> int:
        """ Get the H5 gzip compression level """
        return self.__h5_gzip_level

    @property
    def mems_number( self ) -> int:
        """ Get the active MEMs number """
        return len( self.__mems )
    
    @property
    def available_mems_number( self ) -> int:
        """ Get the available MEMs number """
        return len( self.__available_mems )

    @property
    def analogs_number( self ) -> int:
        """ Get the active analogs number """
        return len( self.__analogs )
    
    @property
    def available_analogs( self ) -> tuple | None:
        """ Get the available analogs channels """
        return self.__available_analogs
    
    @property
    def available_analogs_number( self ) -> int:
        """ Get the available analogs number """
        return len( self.__available_analogs )
    
    @property
    def channels_number( self ) -> int:
        """ Get the active channels number including counter and status if any """
        return self.mems_number + self.analogs_number + ( 1 if self.counter and not self.counter_skip else 0 ) + (1 if self.status else 0 )

    @property
    def available_channels_number( self ) -> int:
        """ Get the available channels number including counter and status if any """
        return self.available_mems_number + self.available_analogs_number + ( 1 if self.counter else 0 ) + (1 if self.status else 0 )

    @property
    def mems_position( self ) -> np.ndarray|None | None:
        """ Get the antenna mems positions
        
        Returns
        -------
            mems_position : np.ndarray|None | None
                array of 3D MEMs positions  
        """
        return self.__mems_position

    @property
    def available_mems( self ) -> tuple | None:
        """ Get the available mems list """
        return self.__available_mems
    
    @property
    def mems( self ) -> tuple | None:
        """ Get the activated MEMss list """
        return self.__mems
    
    @property
    def analogs( self ) -> tuple | None:
        """ Get the activated analog channels list """
        return self.__analogs

    @property
    def counter( self ) -> bool | None:
        """ Get the counter status """
        return self.__counter
    
    @property
    def counter_skip( self ) -> bool | None:
        """ Get the counter skipping status """
        return self.__counter_skip
    
    @property
    def status( self ) -> bool | None:
        """ Get the status state """
        return self.__status
    
    @property
    def datatype( self ) -> Datatype :
        """ Get the antenna output datatype """
        return self.__datatype

    @property
    def frame_length( self ) -> int:
        """ Get the output frames length """
        return self.__frame_length

    @property
    def frame_duration( self ) -> int:
        return self.__frame_duration

    @property
    def sampling_frequency( self ) -> float:
        """ Get the antenna current sampling frequency """
        return self.__sampling_frequency
    
    @property
    def duration( self ) -> int | None:
        """ Get duration scheduled for running """
        return self.__duration

    @property
    def signal_q( self ) -> Queue:
        """ Get the default queue """
        return self.__signal_q

    @property
    def signal_q_maxsize( self ) -> int:
        """ Get the max length of the queue """
        return self.signal_q.maxsize


    #def __init__( self, available_mems_number:int|None=None, mems_position:np.ndarray|None|None=None, unit: str|None=None ):
    def __init__( self, *args, **kwargs ):

        """Create an antenna object

        Parameters:
        -----------
        available_mems_number : int | None
            The total number of MEMs composing the antenna with MEMs numbered from 0 to `available_mems_number-1`
        mems_position : np.ndarray|None | None
            The 3D positions of the MEMs relative to the center of the antenna
        unit : str | None
            The unit used for mems_position ("meters", "centimeters", "millimeters"), default is "meters"
        """
        
        # No args -> nothing to do
        if len( args ) > 0 or len( kwargs ) > 0:
            self._set_settings( args, kwargs )
                
        log.info( f" .Created a new antenna" )


    def _set_settings( self, args, kwargs ) -> None :
        """ Set settings for MemsArray constructor and run method
        
        Parameters
        ----------
        args: array
            direct arguments of the run function
        kwargs: array
            named arguments of the run function
        """
        
        if len( args ) > 0:
            print( f"args={args}" )
            raise MuException( "Direct arguments are not accepted for MemsArray objects" )

        try:
            log.info( f" .Install MemsArray settings" )

            if 'available_mems_number' in kwargs:
                self.setAvailableMems( kwargs['available_mems_number'] )

            if 'mems' in kwargs:
                self.setActiveMems( kwargs['mems'] )

            if 'available_analogs_number' in kwargs:
                self.setAvailableAnalogs( kwargs['available_analogs_number'] )

            if 'analogs' in kwargs:
                self.setActiveAnalogs( kwargs['analogs'] )

            if 'counter' in kwargs:
                self.setCounter() if kwargs['counter'] is True else self.unsetCounter()

            if 'counter_skip' in kwargs:
                self.setCounterSkip() if kwargs['counter_skip'] is True else self.unsetCounterSkip()

            if 'status' in kwargs:
                self.setStatus() if kwargs['status'] is True else self.unsetStatus()

            if 'sampling_frequency' in kwargs:
                self.setSamplingFrequency( kwargs['sampling_frequency'] )

            if 'job' in kwargs:
                self.setJob( kwargs['job'] )

            if 'datatype' in kwargs:
                log.info( f" .Set datatype to {kwargs['datatype']} " )
                if type( kwargs['datatype'] )is str:
                    try:
                        self.setDatatype( getattr( MemsArray.Datatype, kwargs['datatype'] ) )
                    except:
                        raise MuException( f"Unknown output datatype '{kwargs['datatype']}'" )
                elif type( kwargs['datatype'] ) is int:
                    try:
                        self.setDatatype( MemsArray.Datatype( kwargs['datatype'] ) )
                    except:
                        raise MuException( f"Unknown output datatype code '{kwargs['datatype']}'" )                    
                elif type( kwargs['datatype'] ) is MemsArray.Datatype :
                    self.setDatatype( kwargs['datatype'] )
                else:
                    raise MuException( f"Unknown datatype '{kwargs['datatype']}'" )

            if 'duration' in kwargs:
                self.setDuration( kwargs['duration'] )

            if 'frame_length' in kwargs:
                self.setFrameLength( kwargs['frame_length'] )

            if 'h5_recording' in kwargs:
                self.setH5Recording() if kwargs['h5_recording'] else self.unsetH5Recording()

            if 'h5_rootdir' in kwargs:
                self.setH5Rootdir( kwargs['h5_rootdir'] )

            if 'h5_dataset_duration' in kwargs:
                self.setH5DatasetDuration( kwargs['h5_dataset_duration'] )

            if 'h5_file_duration' in kwargs:
                self.setH5FileDuration( kwargs['h5_file_duration'] )

            if 'h5_compressing' in kwargs:
                if kwargs['h5_compressing'] == True:
                    algo = kwargs['h5_compression_algo'] if 'h5_compression_algo' in kwargs else DEFAULT_H5_COMPRESSION_ALGO
                    level =  kwargs['h5_gzip_level'] if 'h5_gzip_level' in kwargs else DEFAULT_H5_GZIP_LEVEL
                    self.setH5Compressing( algo=algo, level=level )
                else:
                    self.unsetH5Compressing()

            if 'signal_q_size' in kwargs:
                self.setQueueSize( kwargs['signal_q_size'] )

        except Exception as e:
            raise MuException( f"Run failed on settings: {e}")


    def _check_settings( self ) -> None :
        """ Check settings values for MemsArray """

        log.info( f" .Pre-execution checks for MemsArray.run()" )

        if self.mems is None or len( self.mems )==0:
            raise MuException( f"No activated MEMs" )
        
        if self.counter is None:
            log.info( f" .Counter was not set -> set to False" )
            self.unsetCounter()
        
        if self.counter_skip is None:
            log.info( f" .Counter skipping not set -> set to False" )
            self.unsetCounterSkip()       

        if self.status is None:
            log.info( f" .Status was not set -> set to False" )
            self.unsetStatus()         

        if self.sampling_frequency is None:
            raise MuException( f"No sampling frequency set" )

        if self.duration is None:
            raise MuException( f"No running duration set" )
        
        if self.datatype is MemsArray.Datatype.unknown:
            raise MuException( f"No datatype set" )
        
        if self.frame_length is None:
            log.info( f" .Frame length not set -> set to default" )
            self.setFrameLength( DEFAULT_FRAME_LENGTH )

        if self.job == 'run' or self.job == 'master' or self.job == 'listen':
            log.info( f" .Requested job: {self.job}" )
        else:
            raise MuException( f"Unknown requested job '{self.job}'" )


    def setRunningFlag( self, status: bool ) -> None:
        self.__running = status

    def setSensibility( self, sensibility: float ) -> None :
        """ Set MEMs sensibility value 
        
        Parameter
        ---------
        sensibility: float
            The new sensibility value
        """

        self.__sensibility = sensibility

    def setJob( self, job: str ) -> None :
        """ Set the running on """

        if job != 'run' and job != 'master' and job != 'listen':
            raise MuException( f"Unknown requested job '{self.job}'" )
        else:
            self.__job = job

    def unsetH5Recording( self ) -> None :
        """ Set the H5 recording off """
        self.__h5_recording = False

    def setH5Recording( self ) -> None :
        """ Set the H5 recording on """
        self.__h5_recording = True

    def unsetH5Recording( self ) -> None :
        """ Set the H5 recording off """
        self.__h5_recording = False

    def setH5Rootdir( self, dir: str ) -> None :
        """ Set the H5 recording root directory """
        self.__h5_rootdir = dir

    def setH5DatasetDuration( self, duration: int ) -> None :
        """ Set the H5 dataset duration in seconds """
        self.__h5_dataset_duration = duration

    def setH5FileDuration( self, duration: int ) -> None :
        """ Set the H5 file duration in seconds """
        self.__h5_file_duration = duration

    def setH5Compressing( self, algo: str=DEFAULT_H5_COMPRESSION_ALGO, level: int=DEFAULT_H5_GZIP_LEVEL ) -> None :
        """ Set the H5 recording compressing mode on """

        if str != 'gzip':
            raise MuException( f"The H5 compressing algo '{algo}' is not implemented" )
        if algo == 'gzip' and ( level <0 or level > 9 ):
            raise MuException( f"Wrong compressing level <{level}>. Accepted values are between 0 and 9" )
        
        self.__h5_compressing = True
        self.__h5_compression_algo = algo
        self.__h5_gzip_level = level

    def unsetH5Compressing( self ) -> None :
        """ Set the H5 recording compressing mode off """
        self.__h5_compressing = False
        self.__h5_compression_algo = DEFAULT_H5_COMPRESSION_ALGO
        self.__h5_gzip_level = DEFAULT_H5_GZIP_LEVEL

    def setStatus( self ) -> None :
        """ Make status channel available. Status state will be added to output signals 

        See
        ---
            MemsArray.unsetStatus()
        """
        self.__status = True

    def unsetStatus( self ) -> None :
        """ Make status unavailable.

        See
        ---
            MemsArray.setStatus()
        """
        self.__status = False

    def setCounter( self ) -> None :
        """ Make counter available. Counter state will be added to output signals 

        See
        ---
            MemsArray.unsetCounter()
        """
        self.__counter = True

    def unsetCounter( self ) -> None :
        """ Make counter unavailable.

        See
        ---
            MemsArray.setCounter()
        """
        self.__counter = False

    def setCounterSkip( self ) -> None :
        """ If counter is available, do not add counter state in output signals

        See
        ---
            MemsArray.setCounter()
            MemsArray.unsetCounterSkip()
        """
        self.__counter_skip = True

    def unsetCounterSkip( self ) -> None :
        """ If counter is available, add counter state in output signals

        See
        ---
            MemsArray.setCounter()
            MemsArray.setCounterSkip()
        """
        self.__counter_skip = False

    def setDatatype( self, datatype: Datatype ) -> None :
        """ Set the output antenna data type

        Parameters
        ----------
        datatype: MemsArray.Datatype
            the antenna output data type among int32, float32, bint32, bfloat32...
        """

        self.__datatype = datatype

    def setAvailableMems( self, available_mems: int|tuple|list|np.ndarray ) -> None :
        """Init antenna available MEMs.
        
        This funtion deactivates MEMs if some are already activated 

        Parameters
        ----------
        available_mems: int | list | tuple | np.ndarray
            Antenna available MEMs number which will be numbered from 0 to `available_mems-1`
            Or list/tuple of available MEMs
        """

        # check available_mems_number parameter type and complete
        if type( available_mems ) is int:
            if available_mems == 0:
                self.__available_mems = []
            else:
                self.__available_mems = [i for i in range( available_mems )]
        elif type( available_mems ) is list:
            self.__available_mems = available_mems
        elif type( available_mems ) is tuple:
            self.__available_mems = list( available_mems )
        elif type( available_mems ) is np.ndarray:
            self.__available_mems = list( available_mems )
        else:
            raise MuException( f"Unknown type of parameter `available_mems`: should be list, tuple or np.ndarray" )

        available_mems_number = len( self.__available_mems )

        # Deactivate MEMs
        if len( self.__mems ) > 0 and max( self.__mems ) >= available_mems_number:
            log.warning( f"Some MEMs are activated that do not match the new antenna definition: all MEMs are now unactivated" )
            self.__mems = []

        # Check positions matching if any
        if self.__mems_position is not None:
            if self.__mems_position.shape[0] != len( self.__available_mems ):
                raise MuException( f"Available_mems_number({available_mems_number}) do not match with MEMs positions ({self.__mems_position.shape[0]} MEMs)" )

        if available_mems_number > 0:
            log.info( f" .Set {available_mems_number} available MEMs numbered from 0 to {available_mems_number-1}" )
        else:
            log.info( f" .No MEMs available" )


    def setMemsPosition( self, mems_position: np.ndarray|None, unit: str="meters" ) -> None :
        """ Set MEMs physical position
        
        Parameters
        ----------
        mems_position: np.ndarray|None
            3D array of MEMs position (shape = `(mems_number, 3)`)
        """

        if mems_position.shape[1] != 3:
            raise MuException( f"Array dimensions are not correct: shape is {mems_position.shape} but should be (mems_number, 3)" )

        # Build the available MEMs list if needed or check availability 
        if len( self.__available_mems) == 0:
            log.info( f" .Setting available MEMs numbered from 0 to {mems_position.shape[0]-1}" )
            self.__available_mems = [i for i in range(mems_position.shape[0])]
        else:
            if mems_position.shape[0] != len( self.__available_mems ):
                log.warning( f"MEMs locations do not match with available MEMs: reset available MEMS from 0 to {mems_position.shape[0]-1}" )
                self.__available_mems = [i for i in range(mems_position.shape[0])]

        # Check unlocated microphones with location set to (0, 0, 0)
        unlocated_mems = []
        for i, mem in enumerate( range( mems_position ) ):
            if np.all( mem==0 ) ==  True:
                unlocated_mems.append( i )
        if len( unlocated_mems ) > 0:
            log.info( f" .Following MEMS are unlocated: {unlocated_mems}" )
        
        # check matching with activated MEMs
        if len( self.__mems ) != 0:
            unlocated_activated = list( set( self.__mems ) & set( unlocated_mems ) )
            if len( unlocated_activated ) > 0:
                log.warning( f"Some activated MEMs are not located. Please check for {unlocated_activated} MEMs" )

        self.__mems_position = mems_position
        if unit == "centimeters":
            self.__mems_position /= 100
        elif unit == "millimeters":
            self.__mems_position /= 1000

        log.info( f" .Set a {mems_position.shape[0]} activable MEMs antenna with physical positions" )


    def setActiveMems( self, mems: tuple ) -> None :
        """ Activate mems

        All activated MEMs should be available. Raise an exception if not.
        Print a warning if some activated MEMs are not located while MEMs positions are defined.
        
        Parameters:
        -----------
        mems : tuple
            list or tuple of mems number to activate
        """

        # No mems means removing current active mems
        if len( mems ) == 0:
            self.__mems = []
            return
        
        if len( self.__available_mems ) == 0:
            raise MuException( f"Cannot activate MEMs on antenna with no available MEMs" )

        # Check if activated MEMs are available. Raise an exception if not
        if False in np.isin( mems, self.__available_mems ):
            mask = np.logical_not( np.isin( mems, self.__available_mems ) )
            raise Exception( f"Some activated microphones ({np.array(mems)[mask]}) are not available on antenna.")

        # Warning if some activated MEMs are not located
        if self.__mems_position is not None:
            unlocated_mems = []
            for i, mem in enumerate( range( self.__mems_position ) ):
                if np.all( mem==0 ) ==  True:
                    unlocated_mems.append( i )
            if len( unlocated_mems ) > 0:
                unlocated_activated_mems = list( set(mems) & set(unlocated_mems) )
                if len( unlocated_activated_mems ) > 0:
                    log.warning( f"Following activated MEMs are unlocated: {unlocated_mems}" )

        self.__mems = mems
        log.info( f" .{len(mems)} MEMs were activated among 0 to {len(self.__available_mems)-1} available MEMs" )


    def setAvailableAnalogs( self, available_analogs: int|list|tuple|np.ndarray ) -> None :
        """Init antenna available analogic channels.
        
        This funtion deactivates channels if some are already activated 

        Parameters
        ----------
        available_analogs: int | list | tuple | np.ndarray
            Antenna available analogs number which will be numbered from 0 to `available_analogs-1`
            Or list/tuple of available analogs
        """

        # check available_analogs parameter type and complete
        if type( available_analogs ) is int:
            if available_analogs == 0:
                self.__available_analogs = []
            else:
                self.__available_analogs = [i for i in range( available_analogs )]
        elif type( available_analogs ) is list:
            self.__available_analogs = available_analogs
        elif type( available_analogs ) is tuple:
            self.__available_analogs = list( available_analogs )
        elif type( available_analogs ) is np.ndarray:
            self.__available_analogs = list( available_analogs )
        else:
            raise MuException( f"Unknown type of parameter `available_analogs`: should be list, tuple or np.ndarray" )

        available_analogs_number = len( self.__available_analogs )

        # Deactivate analogs
        if len( self.__analogs ) > 0 and max(self.__analogs) >= available_analogs_number:
            log.warning( f"Some analogs are activated that do not match the new antenna definition: all analogic channels are now unactivated" )
            self.__analogs = []

        if available_analogs_number > 0:
            log.info( f" .Set {available_analogs_number} available analog channels numbered from 0 to {available_analogs_number-1}" )
        else:
            log.info( f" .No analogic channels available" )


    def setActiveAnalogs( self, analogs: tuple ) -> None :
        """ Activate analogic channels

        All activated analogs should be available. Raise an exception if not.
        
        Parameters:
        -----------
        analogs : tuple
            list or tuple of analogs number to activate
        """

        # No analogs means removing current analogs
        if len( analogs ) == 0:
            self.__analogs = []
            return

        if len( self.__available_analogs ) == 0:
            raise MuException( f"Cannot activate analogs channels on antenna with no available analogs" )

        # Check if activated analogs are available. Raise an exception if not
        if False in np.isin( analogs, self.__available_analogs ):
            mask = np.logical_not( np.isin( analogs, self.__available_analogs ) )
            raise Exception( f"Some activated analogs ({np.array(analogs)[mask]}) are not available on antenna.")

        self.__analogs = analogs
        log.info( f" .{len(analogs)} analogic channels were activated among 0 to {len(self.__available_analogs)-1} available analogs" )


    def setFrameLength( self, frame_length: int ) -> None :
        """ Set the output frame length in samples number 
        
        Parameters:
        -----------
        frame_length : int
            the frame length in samples number
        """

        self.__frame_length = frame_length

        # update frame_duration
        if self.sampling_frequency != 0:
            self.__frame_duration = self.__frame_length / self.sampling_frequency


    def setSamplingFrequency( self, sampling_frequency: float ) -> None :
        """ Set the antenna sampling frequency
        
        Parameters:
        -----------
        sampling_frequency : float
            The sampling frequency (default is given by DEFAULT_SAMPLING_FREQUENCY)
        """

        if sampling_frequency==0:
            raise Exception( f"Cannot set sampling frequency to 0" )

        self.__sampling_frequency = sampling_frequency
        
        # update frame_duration
        self.__frame_duration = self.frame_length / self.__sampling_frequency


    def setDuration( self, duration ) -> None :
        """ Set the duration for next run

        Parameters
        ----------
        duration: int
            durationscheduled for next run in seconds
        """

        self.__duration = duration


    def setQueueSize( self, queue_size: int ) -> None :
        """ Set the signal queue size. Beware that the current queue elements are lost
        
        Parameters
        ----------
        queue_size: int
            The new queue size value. 0 means no size
        """
        self.__signal_q = None
        self.__signal_q = MemsArray.Queue( maxsize=queue_size )


    def run( self, *args, **kwargs ) :
        """ The main run method that run the antenna """

        log.info( f" .Starting run execution" )
                
        # Set base settings      
        try:
            self._set_settings( args, kwargs )
        except Exception as e:
            raise MuException( f"Cannot run: settings loading failed ({type(e).__name__}): {e}" )
            
        # Check settings values
        try:
            self._check_settings()
        except Exception as e:
            raise MuException( f"Unable to execute run: control failure ({type(e).__name__}): {e}" )

        # verbose
        if self.duration == 0:
            log.info( f" .Run infinite loop (duration=0)" )
        else :
            log.info( f" .Perform a {self.duration}s run loop" )

        if self.h5_recording:
            log.info( f" .Local H5 recording" )

        # Start the timer if a limited execution time is requested 
        if self.duration > 0:
            self._thread_timer = Timer( self.duration, self._run_endding )
            self._thread_timer_flag = True
            self._thread_timer.start()

        # Start run thread
        self._async_transfer_thread = Thread( target= self.__run_thread )
        self._async_transfer_thread.start()


    def wait( self ) -> None :
        """ Wait for the end of the thread execution """
        
        if self._async_transfer_thread is not None:
            self._async_transfer_thread.join()
            self._async_transfer_thread = None

        if self._async_transfer_thread_exception is not None:
            thread_exception = MuException( f"Thread exception ({type(self._async_transfer_thread_exception).__name__}): {self._async_transfer_thread_exception}" )
            self._async_transfer_thread_exception = None
            raise thread_exception
        

    def stop( self ) -> None :
        """ Stop current running """

        log.info( " .Request for stopping thread execution" )

        if self.running:
            log.info( " .Stopping current run thread execution..." )
            self.setRunningFlag( False )
        else:
            log.warning( "Failed to stop: No current thread running" )


    def _run_endding( self ) -> None:
        """ Timer callback for running stop """

        log.info( f" .Thread timer started for {self.duration}s duration" )
        self.setRunningFlag( False )
        self._thread_timer_flag = False


    def __run_thread( self ) -> None :
        """ Start run execution

        Generates random data
        """

        try:
            log.info( " .Run thread execution started" )
            
            transfer_lost: int = 0
            self.setRunningFlag( True )
            while self.running:
                # generates random data
                if self.counter is None or ( self.counter == False or ( self.counter == True and self.counter_skip==True ) ):
                    # send data without counter state
                    data = np.random.rand( self.frame_length, self.mems_number ) * 2 - 1
                else:
                    # add counter values
                    counter = np.array( [[i for i in range(self.frame_length)]] ).T + self.__it * self.frame_length
                    data = np.concatenate( ( counter, ( np.random.rand( self.frame_length, self.mems_number ) * 2 - 1 ) ), axis=1 )
                if self.status is not None and self.status == True:
                    # add status values
                    status =np.zeros( ( self.frame_length, 1 ) )
                    data = np.concatenate(( data, status ), axis=1 )

                # post them in the internal queue as float32 array
                self.signal_q.put(
                    self._run_process_data_float32( 
                        data, 
                        h5_recording = self.h5_recording
                    )
                )

            log.info( " .Running stopped: normal thread termination" )

        except Exception as e:
            log.error( f" .Error resulting in thread termination ({type(e).__name__}): {e}" )
            self._async_transfer_thread_exception = e


    def __iter__( self ) :
        """ Init iterations over the antenna data """

        if self.datatype == self.Datatype.bint32:
            log.info( f" .Starting iterations: will produce data as binary buffer of int32" )
        elif self.datatype == self.Datatype.int32:
            log.info( f" .Starting iterations: will produce data as numpy array of int32 ({self.frame_length} x {self.channels_number} size)" )
        elif self.datatype == self.Datatype.bfloat32:
            log.info( f" .Starting iterations: will produce data as binary buffer of float32" )
        elif self.datatype == self.Datatype.float32:
            log.info( f" .Starting iterations: will produce data as numpy array of float32 ({self.frame_length} x {self.channels_number} size)" )
        else:
            raise MuException( f"Bad or unknown datatype. May be a bug" )

        self.__it = 0
        return self


    def __next__( self ) -> np.ndarray|StopIteration :
        """ next iteration over the antenna data """
        
        try:
            data = self.signal_q.get( timeout=DEFAULT_QUEUE_TIMEOUT )
            self.__it += 1
            return data
        
        except queue.Empty:
            raise StopIteration


    def _run_process_data_float32( self, data: bytes, h5_recording: bool=False ) -> any :
        """ Process data in the right format before sending it to the internal queue.
        Data are also saved in H5 file if requested.
        
        Parameter
        ---------
        data: np.ndarray
            input data. Format is two dimensional int32 np.ndarray (frame_length, channels_number) 
        Return: bytes|np.ndarray
            output data in the format required by the user
        """

        # convert to int32 if requested
        if self.datatype == self.Datatype.bint32 or self.datatype == self.Datatype.int32:
            data = ( data / self.sensibility ).astype(np.int32)

        # Save in H5 format if requested
        if h5_recording and self.__h5_started :
            try:
                # Transpose to shape (channels_number, samples_number)
                input_data = data.T

                # If the counter is ON but skipping is ON, it means that incoming data include counter state.
                # Remove the counter state from data  
                if self.counter and self.counter_skip:
                    input_data = input_data[1:,:]

                # convert to int32 if not already done
                if self.datatype != self.Datatype.bint32 and self.datatype != self.Datatype.int32:
                    input_data = ( input_data / self.sensibility ).astype(np.int32)

                # save at the time it was at the transfer starting
                self.__h5_write_mems( input_data, time.time() - self.frame_duration )

            except Exception as e:
                raise MuException( f"H5 writing process failed: {e}. Stop running." )


        # User wants data as binary buffer of int32 -> converts
        if self.datatype == self.Datatype.bint32:
            data = np.ndarray.tobytes( data )

        # User wants data as numpy array of int32 -> nothing to do
        elif self.datatype == self.Datatype.int32:
            pass

        # User wants data as numpy array of float32 -> nothing to do
        elif self.datatype == self.Datatype.float32:
            pass

        # User wants data as binary buffer of float32
        else:
            data = np.ndarray.tobytes( data )


    def _run_process_data_bint32( self, data: bytes, h5_recording: bool=False ) -> any :
        """ Process data in the right format before sending it to the internal queue.
        Data are also saved in H5 file if requested.
        
        Parameter
        ---------
        data: bytes
            input data. Format is int32 binary encoded data as bytes
        Return: bytes|np.ndarray
            output data in the format required by the user
        """

        # Save in H5 format if requested
        if h5_recording and self.__h5_started :
            try:
                # Reshape incoming data using C-like index order
                # Read/write the elements with the last axis index changing fastest (microphones),
                # back to the first axis index changing slowest (samples) 
                                    
                input_data = np.reshape( 
                    np.frombuffer( data, dtype=np.int32 ), 
                    ( self.frame_length, self.channels_number ) 
                ).T

                # If the counter is ON but skipping is ON, it means that incoming data include counter state.
                # Remove the counter state from data  
                if self.counter and self.counter_skip:
                    input_data = input_data[1:,:]

                # save at the time it was at the transfer starting
                self.__h5_write_mems( input_data, time.time() - self.frame_duration )

            except Exception as e:
                raise MuException( f"H5 writing process failed: {e}. Stop running." )
                

        # User wants data as binary buffer of int32 -> nothing to do
        if self.datatype == self.Datatype.bint32:
            pass

        # User wants data as numpy array of int32 
        elif self.datatype == self.Datatype.int32:
            # build np array from binary buffer and eshape MEMs signals column wise
            data = np.reshape( 
                np.frombuffer( data, dtype=np.int32 ), 
                ( self.frame_length, self.channels_number ) 
            )

        # User wants data as numpy array of float32 
        elif self.datatype == self.Datatype.float32:
            # build np array from binary buffer and reshape MEMs signals column wise
            data = np.reshape( 
                np.frombuffer( data, dtype=np.int32 ).astype(np.float32) * self.sensibility, 
                ( self.frame_length, self.channels_number ) 
            )

        # User wants data as binary buffer of float32
        else:
            data = np.frombuffer( data, dtype=np.int32 ).astype(np.float32) * self.sensibility
            data = np.ndarray.tobytes( data )

        return data


    def h5_start( self ):
        """ Start H5 recording (init the H5 recording file) """

        if not self.h5_recording:
            raise MuException( "Cannot start H5 recording: H5 recording mode is OFF" )

        if self.__h5_started:
            log.warning( "Cannot start h5 recording: recording is already started. Please stop recording and restart" )
        else:
            # Create H5 file and set the started floag ON 
            self.__h5_init()
            self.__h5_started = True
            log.info( " .H5 recording started..." )


    def h5_stop( self ):
        """ Stop H5 recording (close the H5 file) """

        if not self.h5_recording:
            raise MuException( "Cannot stop H5 recording: H5 recording mode is OFF" )        

        if not self.__h5_started:
            log.warning( "Cannot stop h5 recording: recording is not running. Please restart before" )
        else:
            self.__h5_close()
            self.__h5_started = False
            log.info( " .H5 recording stopped" )


    def __h5_init( self ):
        """
        Init H5 file system.
        Organization of H5 file is as follows (fs of 50000Hz with 32 MEMs are values taken as reference):

        * incoming transfer buffers are saved into dataset of ``_h5_dataset_duration`` duration
        * datasets are stored into h5 files of '_h5_file_duration' duration
        * counter and status are saved as additional channels if they are set ON in settings 

        These h5 parameters are MegaMicro parameters that have default values (1 second datasets, 15 minutes files,
        see ``core_base.DEFAULT_H5_SEQUENCE_DURATION`` and ``core_base.DEFAULT_H5_FILE_DURATION`` parameters).
        With buffers of 512 samples each, it means that a complete file stores about one minute data (22Go at 50000Hz).
        Files can be fractionned into subfiles to ensure safe network transfer. 
        Internal organization is performed so as to rebuild bigger file from those subfiles.
        H5 files are stored in the H5 root directory which default value is the current working directory

        H5 recording is performed at the Megamicros base class level, provided _h5_recording is set to true.
        When starting, the recording process set the flag '_h5_started' to true, meaning that a H5 file has been created and that it is currently opened.  
        """

        # Create the H5 buffer and init first H5 file 
        # Beware that the counter is never saved in the H5 file
        log.info( ' .H5 init recording process...' )
        try:
            self.__h5_dataset_number = int( self.h5_file_duration // self.h5_dataset_duration )
            self.__h5_dataset_length = int( self.h5_dataset_duration * self.sampling_frequency )
            self.__h5_buffer = np.zeros( shape=( self.channels_number -int( self.counter and self.counter_skip ), self.__h5_dataset_length), dtype=np.int32 )
            self.__h5_buffer_index = 0
            self.__h5_init_file()
        except Exception as e:
            log.fatal( f"H5 init process failed: {e}" )
            raise


    def __h5_close( self ):
        """
        Nothing to do but closing the current opened H5 file
        """
        self.__h5_current_file.close()


    def __h5_init_file( self ):
        """
        Define the H5 file name (form is muh5-YYYYMMDD-hhmmss.h5), and open it in create/write mode
        Set the H5 file internal structure by setting the 'muh5' root group attributes
        Dataset are stored as 2-dimensional np.ndarray with shape (mems_number, samples_number)
        """

        # get current datetime and process file name creation
        date = datetime.now()
        timestamp0 = date.timestamp()
        date0str = datetime.strftime(date, '%Y-%m-%d %H:%M:%S.%f')
        abs_path = ospath.abspath( self.h5_rootdir )
        filename = ospath.join( abs_path, 'mu5h-' + f"{date.year}{date.month:02}{date.day:02}-{date.hour:02}{date.minute:02}{date.second:02}" + '.h5' )

        # open file in write mode
        self.__h5_current_file = h5py.File( filename, "w" )
        
        # Create the root group muh5 and set its attributes
        self.__h5_current_group = self.__h5_current_file.create_group( 'muh5' )
        
        #self.__h5_current_group.attrs['system'] = int( self.__system )
        self.__h5_current_group.attrs['system'] = 0
        self.__h5_current_group.attrs['date'] = self.__h5_date = date0str
        self.__h5_current_group.attrs['timestamp'] = self.__h5_timestamp = timestamp0
        self.__h5_current_group.attrs['dataset_number'] = 0
        self.__h5_current_group.attrs['dataset_duration'] = self.h5_dataset_duration
        self.__h5_current_group.attrs['dataset_length'] = self.__h5_dataset_length
        self.__h5_current_group.attrs['channels_number'] = self.channels_number - int( self.counter and self.counter_skip )
        self.__h5_current_group.attrs['sampling_frequency'] = self.sampling_frequency
        self.__h5_current_group.attrs['duration'] = 0
        self.__h5_current_group.attrs['datatype'] = str( self.datatype )
        self.__h5_current_group.attrs['mems'] = np.array( self.mems )
        self.__h5_current_group.attrs['mems_number'] = self.mems_number
        self.__h5_current_group.attrs['analogs'] = np.array( self.analogs )
        self.__h5_current_group.attrs['analogs_number'] = self.analogs_number
        self.__h5_current_group.attrs['counter'] = self.counter
        self.__h5_current_group.attrs['counter_skip'] = self.counter_skip
        self.__h5_current_group.attrs['comment'] = self.__h5_comment
        if self.h5_compressing:
            self.__h5_current_group.attrs['compression'] = self.h5_compression_algo
            if self.h5_compression_algo == 'gzip':
                self.__h5_current_group.attrs['compression_gzip_level'] = self.h5_gzip_level
        else:
            self.__h5_current_group.attrs['compression'] = False

        self.__h5_dataset_index = 0
        log.info( f" .Created new H5 file [{filename}]" )


    def __h5_write_mems( self, signal, timestamp ):
        """
        Write transfer buffer in local cache and tranfer local to H5 file 
        ! Beware that this function is not thread safe !
        ! it should be re-writen or writen outside the acquisition thread ! 

        Parameters
        ----------
        signal: np.ndarray
            2 dimensional array with microphones as line (0 axis) and samples as columns (1 axis) 
        timestamp: 
            Signal first sample timestamp
        """

        if self.__h5_buffer_index + self.frame_length < self.__h5_dataset_length:
            """
            Buffer is not yet completed -> transfer whole signal in buffer
            """
            if self.__h5_buffer_index == 0:
                self.__h5_timestamp = timestamp
            self.__h5_buffer[:,self.__h5_buffer_index:self.__h5_buffer_index+self.__frame_length] = signal
            self.__h5_buffer_index += self.__frame_length
            
        else:
            """
            Not enough remainning place in buffer -> transfer first part of signal and save
            """
            transf_samples_number = self.__h5_dataset_length - self.__h5_buffer_index
            self.__h5_buffer[:, self.__h5_buffer_index:self.__h5_buffer_index+self.__h5_dataset_length] = signal[:,:transf_samples_number]

            """
            Save dataset. Create new file if dataset max number is reached
            """
            if self.__h5_dataset_index >= self.__h5_dataset_number:
                self.__h5_close()
                self.__h5_init_file()

            seq_group = self.__h5_current_group.create_group( str( self.__h5_dataset_index ) )
            seq_group.attrs['ts'] = self.__h5_timestamp
            if self.__h5_compressing:
                if self.__h5_compression_algo == 'gzip':
                    seq_group.create_dataset( 'sig', data=self.__h5_buffer, compression=self.__h5_compression_algo, compression_opts=self.__h5_gzip_level )
                else:
                    seq_group.create_dataset( 'sig', data=self.__h5_buffer, compression=self.__h5_compression_algo )
            else:
                seq_group.create_dataset( 'sig', data=self.__h5_buffer )
            self.__h5_dataset_index += 1
            self.__h5_current_group.attrs['dataset_number'] = self.__h5_dataset_index
            self.__h5_current_group.attrs['duration'] = self.__h5_dataset_index * self.__h5_dataset_duration

            """ 
            Transfer remaining part of signal in buffer, reset index and set the new dataset timestamp
            Marie Elise Mercuis
            """
            self.__h5_buffer[:, :self.__frame_length-transf_samples_number] = signal[:,transf_samples_number:self.__frame_length]
            self.__h5_buffer_index = self.__frame_length-transf_samples_number
            self.__h5_timestamp = timestamp + transf_samples_number / self.__sampling_frequency




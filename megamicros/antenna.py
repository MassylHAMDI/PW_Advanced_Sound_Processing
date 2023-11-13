# Megamicros_ailab.antenna.py
#
# Copyright (c) 2023 Sorbonne Université
# Author: bruno.gas@sorbonne-universite.fr, françois.ollivier@sorbonne-universite.fr,
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
Define antenna class for beamforming
"""

import numpy as np
from .exception import MuException
from .log import log

DEFAULT_FRAME_LENGTH = 256
SOUND_SPEED = 340.29

class Antenna:
    __mems: np.ndarray
    __position: np.ndarray

            
    @property
    def mems_number( self ) -> int:
        return len( self.__mems )
    
    @property
    def position( self ) -> np.ndarray:
        return self.__position

    def __init__( self, mems: tuple=(), unit='meters', position=(0, 0, 0) ):
        """
        Build an antenna object from a tuple of MEMs 3D positions
        Default unit is meters. If position is given, the antenna is built relative to this position.
        Default position is assumed null (0, 0, 0)

        Parameters
        ----------
        * mems: tuple tuple of MEMs 3D positions
        * unit: str metric used ('meters', 'centimeters', 'millimeters', default is 'meters'
        * position: tuple antenna position. DEfayult is (0, 0, 0)  
        """
        self.__mems = np.array( mems )
        self.__position = np.array( position )
        self.__mems += self.__position

        if unit == 'centimeters':
            self.__mems /= 100
        elif unit == 'millimeters':
            self.__mems /= 1000

        log.info( f" .Build antenna with {self.mems_number} MEMs at position {self.position}" )


    def set_position( self, position: tuple ) -> None:
        """
        Update the antenna current position. Old is removed and MEMs positions are all updated

        Paraleters
        ----------
        * position: tuple new antenna position
        """

        self.__mems = self.__mems - self.__position + np.array( position )
        self.__position = np.array( position )
    

    def mems( self, number:int|None=None, position: tuple|None = None ) -> np.ndarray:
        """
        Return 3D position of the MEMs which rank in antenna is given as argument.
        If position is given, the MEMs positions are given relative to this position.
        If number is not given, MEMs array is return 
        """

        if position is None:
            # Return actual positions
            mems = self.__mems
        else:
            # Return MEMS position relative to the given antenna position given as argument
            mems = self.__mems - self.__position + np.array( position )

        if number is None:
            return mems
        else:
            return mems[number]


"""
Declare the square antenna of 32 mems used for the Mosellerie and Le Prehaut POCs 

vue de dessus


                  (back)
      24  25  26  27  28  29  30  31

                    F3
     --x---x---x---x---x---x---x---x--
7    x(0) (1) (...)              (0) x    16
     |                               | 
6    x                           (1) x    17
     |                               |
5    x                         (...) x    18
     |                               |
4    x                               x    19
  F0 |                               |  F2
3    x                               x    20
     |                               |
2    x (...)                         x    21
     |                               |
1    x (1)                           x    22
     |                               |
0    x (0)              (...) (1) (0)x    23
     --x---x---x---x---x---x---x---x--
  (0,0)             F1

       15  14  13  12  11  10  9   8              
                    !
                    !
                    !
              vers la porte (front)

MEMs numbering:
F0: 0,1,2,3,4,5,6,7
F1: 8, 9, 10, 11, 12, 13, 14, 15
F2: 16, 17, 18, 19, 20, 21, 22, 23
F3: 24, 25, 26, 27, 28, 29, 30, 31
"""

Mu32_Mems32_JetsonNano_0001: Antenna = Antenna( 
    mems=(
        (0, 3.82, 0), (0, 9.82, 0), (0, 15.82, 0), (0,  21.82, 0), (0,  27.82, 0), (0, 33.82, 0), (0, 39.82, 0), (0, 45.82, 0),
        (45.81, 0, 0), (39.81, 0, 0), (33.81, 0, 0), (27.81, 0, 0), (21.81, 0, 0), (15.81, 0, 0), (9.81, 0, 0) , (3.81, 0, 0),
        (49.63, 45.82, 0), (49.63, 39.82, 0), (49.63, 33.82, 0), (49.63,  27.82, 0), (49.63,  21.82, 0), (49.63, 15.82, 0), (49.63, 9.82, 0), (49.63, 3.82, 0),
        (3.81, 49.63, 0), (9.81, 49.63, 0), (15.81, 49.63, 0), (21.81, 49.63, 0), (27.81, 49.63, 0), (33.81, 49.63, 0), (39.81, 49.63, 0), (45.81, 49.63, 0)
    ),
    unit='centimeters'
)


class BufferedAntenna( Antenna ):
    """
    Antenna with data buffer inside which can be iterated
    """

    __data: np.ndarray
    __it: int = 0
    __frame_length: int = DEFAULT_FRAME_LENGTH
    __frame_number: int = 0


    @property
    def frame_length( self ) -> int:
        return self.__frame_length
    
    @property
    def frame_number( self ) -> int:
        return self.__frame_number
    
    @property
    def index( self ) -> int:
        return self.__it
    

    def __init__( self, mems: tuple=(), unit='meters', position=(0, 0, 0), data:np.ndarray|None = None, frame_length=DEFAULT_FRAME_LENGTH ):
        super().__init__( mems=mems, unit=unit, position=position )

        if data is None:
            self.__data = None
            self.__frame_number = 0
            self.__frame_length = frame_length

        else:
            if data.shape[0] != self.mems_number:
                raise MuException( f" Signal dimensions ({data.shape[0]} x {data.shape[1]}) does not match with antenna mems number ({self.mems_number}) " )
            
            self.__data = data
            self.__frame_length = frame_length
            self.__frame_number = self.__data.shape[1] // self.__frame_length

        log.info( f" .Buffered antenna set with frames of length {self.frame_length} samples" )


    def __iter__( self ):
        if self.__frame_number == 0:
            raise Exception( f"Cannot iterate: empty object with no frame to iterate on" ) 
        
        self.__it = 0
        return self


    def __next__( self ) -> np.ndarray :
        if self.__it >= self.__frame_number:
            raise StopIteration
        
        offset = self.__it * self.__frame_length
        result = self.__data[:,offset:offset+self.__frame_length]
        self.__it += 1
        return result


    def set_frame_length( self, frame_length: int ):
        self.__frame_length = frame_length
        if self.__data is not None:
            self.__frame_number = self.__data.shape[1] // self.__frame_length


    def set_data( self, data: np.ndarray ) -> None:
        """
        Fill the internal buffer with signals comming from MEMs
        
        Parameters
        ----------
        * data: np.ndarray, numpy array of signals (mems_number x samples_number)
        """
        if data.shape[0] != self.mems_number:
            raise MuException( f" Signal dimensions ({data.shape[0]} x {data.shape[1]}) does not match with antenna mems number ({self.mems_number}) " )
        
        self.__data = data
        self.__frame_number = self.__data.shape[1] // self.__frame_length


    def _index_inc( self ):
        self.__it += 1


class BmfAntenna( BufferedAntenna ):
    """
    Antenna which embed a beamformer for sound space filtering
    Default beamformer is the Delay and Sum algorithm ('das')

    Parameters
    ----------
    * space_q: np.ndarray space quantization, a matrix of 3D vectors listing all space locations to be filtered
    * sampling_frequency: float, sampling frequency
    * cutoff_frequency: float, cutoff frequency for beamformer
    * bmf: str a string denoting the beamformer algorithm to use (defalt is 'das' for Delay And Sum algorithm)
    """

    _space_quantization: np.ndarray = None
    _sampling_frequency: float = None

    __sampling_period: float             # sampling period
    __n_freqs: int                       # FFT frequencies number
    __n_locations: int                   # space locations number
    __cutoff: float                      # cutoff frequency
    __n_freqs_cutoff: int

    __D: np.ndarray                      # Distance matrix between space locations and microphones
    __H: np.ndarray                      # Beamformer matrix

    @property
    def sampling_frequency( self ) -> float:
        return self._sampling_frequency
    
    @property
    def cutoff_frequency( self ) -> float:
        return self.__cutoff
    

    def __init__( self, mems: tuple=(), unit='meters', position=(0, 0, 0), data:np.ndarray|None=None, frame_length: int=DEFAULT_FRAME_LENGTH, space_q:np.ndarray|list|tuple=None, sampling_frequency: float=16000, bmf='das', cutoff_frequency=None ):
        super().__init__( mems=mems, unit=unit, position=position, data=data, frame_length=frame_length )

        # check space quantization
        if space_q is None:
            raise MuException( f"No space quantization given. Cannot init antenna beamformer" )

        if type(space_q) is list or type(space_q) is tuple:
            self._space_quantization = np.array( space_q )
        else:
            self._space_quantization = space_q

        if self._space_quantization.shape[1] != 3:
            raise MuException( f"Wrong space quantization matrix ({self._space_quantization.shape[0]} x {self._space_quantization.shape[1]}): space dimension should be 3, but not {self._space_quantization.shape[1]}" )

        self.__n_locations = self._space_quantization.shape[0]

        if bmf != 'das':
            raise MuException( f"Unknow '{bmf}' beamformer algorithm" )

        self._sampling_frequency = sampling_frequency
        self.__sampling_period = 1/self._sampling_frequency
        self.__n_freqs = np.fft.rfftfreq( self.frame_length, 1/self.sampling_frequency ).size
        self.__cutoff = self._sampling_frequency if cutoff_frequency is None else cutoff_frequency
        if self.__cutoff == self._sampling_frequency:
            self.__n_freqs_cutoff = self.__n_freqs
        else:
            self.__n_freqs_cutoff = int( self.__n_freqs * self.__cutoff / self._sampling_frequency )

        # time axis in seconds
        t = np.arange( self.frame_length )/self.sampling_frequency

        # frequency axis in Hz
        f = np.fft.rfftfreq( self.frame_length, 1/self.sampling_frequency )

        # install/init the beamformer
        log.info( f" .Beamformer2D Initilization:" )
        log.info( f"  > Found antenna with {self.mems_number} mems microphones at position {self.position}" )
        log.info( f"  > Frame length is {self.frame_length}" )
        log.info( f"  > Time range: [0, {t[-1]}] s" )
        log.info( f"  > Frequency range: [0, {f[-1]}] Hz ({self.__n_freqs} beams)" )
        log.info( f"  > Space quantization: {self.__n_locations} locations requested" )

        # Init distance matrix
        log.info( f"  > Build distances matrix D ({self.__n_locations} x {self.mems_number})" ) 
        self._D = np.ndarray( (self.__n_locations, self.mems_number), dtype=float )
        for s in range( self.__n_locations ):
            for m in range( self.mems_number ):
                self._D[s, m] = np.linalg.norm( np.array( self.mems( m ) ) - self._space_quantization[s] )

        # Allocate and build the H complex transfer function matrix (preformed channels)
        log.info( f"  > Build preformed channels matrix H ({self.__n_freqs} x {self.__n_locations} x {self.mems_number})" ) 
        self._H = np.outer( f, self._D ).reshape( self.__n_freqs, self.__n_locations, self.mems_number )/SOUND_SPEED
        self._H = np.exp( 1j*2*np.pi*self._H ) 


    def __iter__( self ):
        """
        Init iteration
        """
        BufferedAntenna.__iter__( self )
        return self


    def __next__( self ) -> np.ndarray :
        """
        Next iteration
        """
        return self._beamform( BufferedAntenna.__next__( self ) )


    def beamform( self, signal: np.ndarray ):
        """
        Process beamforming on signal given as argument (mems_number x samples_number)
        
        Parameters
        ----------
        * signal: np.ndarray signal (mems_number x samples_number)

        Return 
        ------
        BFE: np.ndarray, the beamforming energy array
        """
        
        if signal.shape[0] != self.mems_number:
            raise MuException( f"Signal shape [{signal.shape[0]} x {signal.shape[1]}] does not match with the antenna mems number ({self.mems_number})" )

        if signal.shape[1] != self.frame_length:
            raise MuException( f"Signal shape [{signal.shape[0]} x {signal.shape[1]}] does not match with the frame length ({self.mems_number} samples)" )

        return self._beamform( signal )
    

    def _beamform( self, signal: np.ndarray ):
        """
        Process beamforming
        """
        signal = signal.T
        Spec = np.fft.rfft( signal, axis=0 )
        SpecH = Spec[:, None, :]*self._H
        BFSpec = np.sum( SpecH, -1 ) / self.mems_number
        #BFE = np.sum( ( np.abs( BFSpec )**2 ), 0 ) / self.__n_freqs
        BFE = np.sum( ( np.abs( BFSpec )**2 )[0:self.__n_freqs_cutoff,:], 0 ) / self.__n_freqs_cutoff

        return BFE


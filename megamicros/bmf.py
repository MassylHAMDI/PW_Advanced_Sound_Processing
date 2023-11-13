# megamicros.bmf.py
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

"""Define beamformer classes for beamforming

Usage
-----
import megamicros.bmf

Attributes
----------

__mems_position: np.ndarray()
    3D MEMs positions from the antenna center
    
__sampling_frequency: float
    Sampling frequency

__area: np.ndarray | tuple
    working space size

__area_quantization: float
    locations number per meters (space frequency)

__area_position: np.ndarray
    position of the area center from the antenna center (default is (0, 0, 0))

__window_size: int
    samples number for FFT estimation

__band_width: tuple
    frequencies interval for beamforming expressed in relative frequencies (1 means fe/2).
    Default is [0, 1]
    

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import numpy as np
from megamicros.log import log
from megamicros.exception import MuException

SOUND_SPEED = 340.29

class MuBmfException( MuException ):
    """ Exception for beamformers """
    pass


class Beamformer:
    """ Base class for beamformers"""

    # bmf properties
    __mems_position: np.ndarray | None          = None  # 3D MEMs positions from the antenna center
    __area_quantization: np.ndarray | None      = None  # locations number per meters (space frequency)
    __area: np.ndarray | None                   = None
    __area_position: np.ndarray                 = np.array([[0, 0, 0]])
    __sampling_frequency: float | None          = None
    __fft_win_size: int | None                  = None
    __band_width: tuple                         = [0, 1]

    # for internal purpose
    __freq_number: int                                  # spectral bands number
    __loc_number: int                                   # Total space locations number
    __locations: np.ndarray | None              = None
    __D: np.ndarray | None                      = None  # Distance matrix between area locations and microphones
    __H: np.ndarray | None                      = None  # Beamformer matrix
    __mems_number: int | None                   = None  # MEMs number according the mems_position array
    __bw_range_start: int | None                = None  # Bandwidth start frequency range
    __bw_range_end: int | None                  = None  # Bandwidth end frequency range 
    __bw_length: int | None                     = None  # Bandwidth length in samples number

    def setMemsPosition( self, mems_position: np.ndarray ) -> None:

        if np.shape( mems_position )[1] != 3:
            raise MuBmfException( f"bad dimensions ({np.shape( mems_position )}). Mems positions should be a 3D data array (shape=(mems_number, 3))" )
        
        log.info( f' .Set beamformer on a {np.shape( mems_position )[0]} MEMs antenna' )

        self.__mems_position = mems_position
        self.__mems_number = mems_position.shape[0]


    def setSamplingFrequency( self, sr: float ) -> None:
        
        log.info( f' .Set beamformer sampling rate on {sr} Hz' )
        self.__sampling_frequency = sr


    def setFftWindowSize( self, ws: int ) -> None:
        
        log.info( f' .Set beamformer FFT window size to {ws} samples' )
        self.__fft_win_size = ws


    def setAreaQuantization( self, sq: np.ndarray | tuple ) -> None:
        
        if type( sq ) is tuple or type( sq ) is list:
            if len( sq ) != 3:
                raise MuBmfException( f"Incorrect quantization dimensions ({len( sq )}). Should be 3 (sq_x, sq_y, sq_z)" )
            else:
                self.__area_quantization = np.array( [sq] )
        elif np.shape( sq ) != (1,3):
            raise MuBmfException( f"Incorrect array dimensions ({np.shape( sq )}). Should be (1, 3)" )
        else:
            self.__area_quantization = sq
            
        log.info( f' .Set beamformer space quantization to {sq} locations/meter' )


    def setBandWidth( self, bandwidth: tuple, unit: str="normalized" ) -> None:
        """
        Set the frequency bandwidth for beamforming computing

        Parameters:
        -----------
        bw: tuple
            The 2 values tuple that set the bandwidth ([fmin, fmax]) expressed in frequency or in normalized values

        unit: str
            The unit used: `normalized` ([0, 1/3]) or `frequency` ([0,2000])  
        """

        if len( bandwidth ) != 2:
            raise MuBmfException( f"Bad bandwidth tuple dimension ({len(bandwidth)}). Should be 2 " )

        if unit == "frequency" and self.__sampling_frequency is None:
            raise MuBmfException( "Cannot understand bandwidth in frequency as long as sampling frequency is not defined. Please define it or use the `normalized` unit" )

        if unit == "normalized":
            self.__band_width = bandwidth
        else:
            self.__band_width = tuple( np.array( bandwidth )/(self.__sampling_frequency/2) ) 

        log.info( f' .Set beamformer band width to {self.__band_width}' )


    def setArea( self, ss: np.ndarray|tuple ) -> None:
        """ Set the beamformer working space dimensions 
        
        Note that the working space has nothing to do with the room space. 
        The working space is the area where the beamformer perfoms the source localization.
        Its definition is relative to the antenna center. 
        Use the `Beamformer.moveAntenna()` method to stop centering of the working space.
        """
        
        if type( ss ) is tuple or type( ss ) is list:
            if len( ss ) != 3:
                raise MuBmfException( f"Incorrect space dimensions ({len( ss )}). Should be 3 (dx, dy, dz)" )
            else:
                self.__area = np.array( [ss] )
        elif np.shape( ss ) != (1,3):
            raise MuBmfException( f"Incorrect array dimensions ({np.shape( ss )}). Should be (1, 3)" )
        else:
            self.__area = ss
            
        log.info( f' .Set beamformer space size to {ss} meters' )
        

    def getLocations( self ) -> np.ndarray:
        """ Get the locations matrix
        
        The locations matrix is a 3D array of 3D points coverring the beamformer working space
        """

        if self.__locations is None:
            raise MuBmfException( f"No locations found. The beamformer seems not initialized. Please use the `Beamformer.init()` method before." )

        return self.__locations 


    def getLocationsNumber( self ) -> tuple:
        """ Get the locations number among x, y and z axis
        
        The locations matrix is a 3D array of 3D points coverring the beamformer working space
        """

        if self.__locations is None:
            raise MuBmfException( f"No locations found. The beamformer seems not initialized. Please use the `Beamformer.init()` method before." )

        # locations number
        loc_number_x = int( self.__area[0,0] * self.__area_quantization[0,0] )
        loc_number_y = int( self.__area[0,1] * self.__area_quantization[0,1] )
        loc_number_z = int( self.__area[0,2] * self.__area_quantization[0,2] )

        return [loc_number_x, loc_number_y, loc_number_z] 
    

    def getMems( self ) -> np.ndarray:
        """ Get the array of positions of all antenna MEMs 
        
        Throw an exception if MEMs are not defined

        Return
        ------
        mems_position: np.ndarray
            array of MEMs 3D position

        """

        if self.__mems_position is None:
            raise MuBmfException( f"No MEMs position defined. Please use `Beamformer.setMemsPosition()` before" )
        
        return self.__mems_position


    def getMemsNumber( self ) -> int:
        """ Get the antenna MEMs number according the dimension of the MEMs positions array """

        if self.__mems_position is None:
            return 0
        else:
            return self.__mems_position.shape[0]
        

    def moveArea( self, delta: np.ndarray | tuple ) -> np.ndarray:
        """ Move the area center from the antenna center 
        
        Parameters:
        -----------
        delta: np.ndarray | tuple
            3D array or tuple that gives the moving vector value.
            New position is the current area position added to the delta vector
        """

        if type( delta ) is tuple or type( delta ) is list:
            if len( delta ) != 3:
                raise MuBmfException( f"Incorrect array or tuple dimensions ({len( delta )}). Should be 3 (dx, dy, dz)" )
            else:
                log.info( f" .Move area from {self.__area_position[0]} to {(self.__area_position+np.array( [delta] ))[0]}" )
                self.__area_position += np.array( [delta] )
                if self._check( verbose=False ):
                    self._build_locations()

        elif np.shape( delta ) != (1,3):
            raise MuBmfException( f"Incorrect array dimensions ({np.shape( delta )}). Should be (1, 3)" )
        
        else:
            log.info( f" .Move area from {self.__area_position[0]} to {(self.__area_position+delta)[0]}" )
            self.__area_position += delta
            if self._check( verbose=False ):
                self._build_locations()



    def __init__( self, mems_position: np.ndarray|None=None, sampling_frequency: float|None=None, window_size:int|None=None, area:float|None=None, area_quantization:float|None=None ):

        if mems_position is not None:
            self.setMemsPosition( mems_position )
        if sampling_frequency is not None:
            self.setSamplingFrequency( sampling_frequency )
        if window_size is not None:
            self.setFftWindowSize( window_size )
        if area is not None:
            self.setArea( area )
        if area_quantization is not None:
            self.setAreaQuantization( area_quantization )

    def _check( self, verbose=True ) -> bool:

        if verbose:
            log.info( f' .Checking beamformer parameters...' )
        result: bool = True
        if self.__mems_position is None:
            log.info( f' > MEMs position should be set.' )
            result = False
        if self.__area_quantization is None:
            log.info( f' > Space quantization should be set.' )
            result = False
        if self.__area is None:
            log.info( f' > Space size should be set.' )
            result = False
        if self.__sampling_frequency is None:
            log.info( f' > Sampling should be set.' )
            result = False
        if self.__fft_win_size is None:
            log.info( f' > FFT window size not set.' )
            result = False

        if verbose:
            log.info( f' .[Ready]' )

        return result


    def _build_locations( self ) -> None:

        # check for parameters
        if not self._check():
            raise MuBmfException( f'Some parameters are not set. Cannot build locations matrix of the working space' )
        
        # space size
        dimx = self.__area[0,0]
        dimy = self.__area[0,1]
        dimz = self.__area[0,2]

        # locations number
        loc_number_x = int( dimx * self.__area_quantization[0,0] )
        loc_number_y = int( dimy * self.__area_quantization[0,1] )
        loc_number_z = int( dimz * self.__area_quantization[0,2] )

        self.__loc_number = loc_number_x * loc_number_y * loc_number_z

        # width, depth, height quantizations in meters
        dx: float = 1/self.__area_quantization[0,0]
        dy: float = 1/self.__area_quantization[0,1]
        dz: float = 1/self.__area_quantization[0,2]

        log.info( f" .Found {self.__loc_number} locations ({loc_number_x} x {loc_number_y} x {loc_number_z})")
        log.info( f" .Space quantum size is ({dx:.2f} x {dy:.2f} x {dz:.2f}) meters")

        self.__locations = np.ndarray( ( loc_number_x*loc_number_y*loc_number_z, 3 ) )
        for x in range( loc_number_x ):
            for y in range( loc_number_y):
                for z in range( loc_number_z):
                    i = x * loc_number_y * loc_number_z + y * loc_number_z + z
                    self.__locations[i] = np.array( [x*dx+dx/2-dimx/2, y*dy+dy/2-dimy/2, z*dz+dz/2-dimz/2] ) + self.__area_position



    def init( self ) -> None:
        
        """ Init beamformer. All parameters should be set before 
        
        Check antenna parameters, then build the distance matrix
        """

        # check for parameters
        if not self._check():
            raise MuBmfException( f'Some parameters are not set. Cannot perform beamforming' )

        # time axis in seconds
        t = np.arange( self.__fft_win_size )/self.__sampling_frequency

        # frequency axis in Hz
        f = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency )

        # frequencies number
        self.__freq_number = np.fft.rfftfreq( self.__fft_win_size, 1/self.__sampling_frequency ).size

        # frequency step
        frequency_step = self.__sampling_frequency / self.__freq_number / 2


        # bandwidth range
        self.__bw_range_start = int( self.__sampling_frequency * self.__band_width[0] / frequency_step / 2 )
        self.__bw_range_end = int( self.__sampling_frequency * self.__band_width[1] / frequency_step / 2 ) - 1
        self.__bw_length = self.__bw_range_end - self.__bw_range_start + 1

        # print info
        log.info( f" .Beamformer2D Initilization:" )
        log.info( f"  > Found antenna with {self.__mems_number} MEMs microphones" )
        log.info( f"  > FFT window size is {self.__fft_win_size} samples" )
        log.info( f"  > Time range: [0, {t[-1]}] s" )
        log.info( f"  > Sampling frequency: {self.__sampling_frequency} Hz" )
        log.info( f"  > Frequency range: [0, {f[-1]}] Hz ({self.__freq_number} beams)" )
        log.info( f"  > frequency step: {frequency_step:.2f} Hz" )
        log.info( f"  > Space quantization: {self.__area_quantization} locations/meter" )
        log.info( f"  > Beamforming frequency bandwidth: {self.__band_width} ({self.__bw_length} samples, [{self.__bw_range_start}, {self.__bw_range_end}])" )
        log.info( f"  > Beamforming bandwidth starting at: {(self.__bw_range_start * frequency_step):.2f} Hz" )
        log.info( f"  > Beamforming bandwidth endding at: {((self.__bw_range_end+1)* frequency_step):.2f} Hz" )

        # Build the locations 3D (centered) coordinates
        self._build_locations()
        
        # Init distance matrix
        log.info( f" .Build distances matrix D ({self.__loc_number} x {self.__mems_number})" ) 
        self._D = np.ndarray( (self.__loc_number, self.__mems_number), dtype=float )
        for s in range( self.__loc_number ):
            for m in range( self.__mems_number ):
                self._D[s, m] = np.linalg.norm( np.array( self.__mems_position[m] ) - self.__locations[s] )

        # Allocate and build the H complex transfer function matrix (preformed channels)
        log.info( f" .Build preformed channels matrix H ({self.__freq_number} x {self.__loc_number} x {self.__mems_number})" ) 
        self._H = np.outer( f, self._D ).reshape( self.__freq_number, self.__loc_number, self.__mems_number )/SOUND_SPEED
        self._H = np.exp( 1j*2*np.pi*self._H )
        

    def beamform( self, signal: np.ndarray ) -> np.ndarray:
        """ Process beamforming on input signals
        
        If the signal length is smaller than the `__fft_win_size` parameter, the input is cropped. 
        If it is larger, the input signal is padded with zeros
        
        Parameters
        ----------
        signal: np.ndarray
            the MEMs signal line wise (samples_number X mems_number)

        Return
        ------
        BFE: np.ndarray
            The beamformed energy channels (location_number x 1)
        """
        
        Spec = np.fft.rfft( signal, n=self.__fft_win_size, axis=0 )
        SpecH = Spec[:, None, :] * self._H
        BFSpec = np.sum( SpecH, -1 ) / self.__mems_number
        BFE = np.sum( ( np.abs( BFSpec )**2 )[self.__bw_range_start:self.__bw_range_end+1,:], 0 ) / self.__bw_length

        return BFE

"""
antenna= {'positions': np.array(
[[-0.2261063,  -0.2217998,   0.        ],
[-0.2231343,  -0.16230868,  0.        ],
[-0.23502814,  0.01106646,  0.        ],
[-0.23505722,  0.07143718,  0.        ],
[-0.23869585,  0.13492614,  0.        ],
[-0.241065,    0.19720244,  0.        ],
[-0.20675762,  0.23860315,  0.        ],
[-0.14724884,  0.23868911,  0.        ],
[-0.08815056,  0.23800337,  0.        ],
[-0.02524838,  0.23605316,  0.        ],
[ 0.03711273,  0.23184893,  0.        ],
[ 0.09778664,  0.22929929,  0.        ],
[ 0.20982932,  0.21545461,  0.        ],
[ 0.25022585,  0.17556075,  0.        ],
[ 0.24945468,  0.11548598,  0.        ],
[ 0.2482488,   0.05719138,  0.        ],
[ 0.25352816,  0.00069583,  0.        ],
[ 0.25355045, -0.17305451,  0.        ],
[ 0.26728441, -0.23428049,  0.        ],
[ 0.23313417, -0.27617064,  0.        ],
[ 0.16906521, -0.27623144,  0.        ],
[-0.01177931, -0.2639107,   0.        ],
[-0.0767392,  -0.26609785,  0.        ],
[-0.13061677, -0.26229372,  0.        ],
[-0.18359293, -0.25536996,  0.        ]] ),
'mems':[0,1,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,22,23,24,25,28,29,30,31],
'available_mems': [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31]
}
np.save( 'Antenna-square-JetsonNano-0001.npy', antenna )
"""


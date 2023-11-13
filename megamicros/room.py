# Megamicros_ailab.room.py
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
Define beamformer class for beamforming
"""
import numpy as np
from .log import log
from .exception import MuException
from .antenna import Antenna

DEFAULT_FRAME_LENGTH = 256
DEFAULT_SAMPLING_RATE = 50000

SOUND_SPEED = 340.29

def arrange_2D( room_size:list , sq_x: float, sq_y: float, ground_elevation: float=0 ):
    """
    Build an array of 3D coordinates points which brows the 2D space

    Parameters
    ----------
    * room_size: list space dimensions in meters
    * sq_x: float quantization along x axis (in points per meters)
    * sq_y: float quantization along y axis (in points per meters)
    * ground_elevation: float z coordinate (the same for all points)

    Return
    ------
    * The array of 3D coordinates points. np.reshape(arrange_2D, ny, nx, 3)[x][y] gives the vector (x,y,z) coordinates
    """

    width, depth, height = room_size
    nx: int = int( width * sq_x )
    ny: int = int( depth * sq_y )

    # width quantization in meters
    dx: float = 1/sq_x

    # depth quantization in meters
    dy: float = 1/sq_y

    SQ = np.ndarray( ( nx*ny, 3 ) )
    for x in range(nx):
        for y in range(ny):
            i = x * ny + y
            SQ[i] = np.array( [x*dx+dx/2, y*dy+dy/2, ground_elevation] )

    return SQ



class Room:
    __dim: list

    @property
    def antenna( self ) -> list:
        return self.__dim
    
    @property
    def dimx( self ) -> float:
        return self.__dim[0]
    
    @property
    def dimy( self ) -> float:
        return self.__dim[1]
    
    @property
    def dimz( self ) -> float:
        return self.__dim[2]
    
    @property
    def width( self ) -> float:
        return self.__dim[0]
    
    @property
    def depth( self ) -> float:
        return self.__dim[1]
    
    @property
    def height( self ) -> float:
        return self.__dim[2]

    def __init__( self, dim: list=(0, 0, 0) ):
        self.__dim = dim        

    def __str__(self) -> str:
        return str( self.__dim  )
        
    def dim( self, dim_x, dim_y, dim_z ):
        self.__dim = list( (dim_x, dim_y, dim_z ) )

    

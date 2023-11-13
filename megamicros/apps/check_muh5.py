# check_muh5.py python program example for MegaMicros devices 
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
Check MuH5 file content. Please use the more precise 'h5dump' command from HDF5 tools instead

MegaMicros documentation is available on https://readthedoc.biimea.io
"""

welcome_msg = '-'*20 + '\n' + 'check_muh5 program\n \
Copyright (C) 2023  Sorbonne University\n \
This program comes with ABSOLUTELY NO WARRANTY; for details see the source code\'.\n \
This is free software, and you are welcome to redistribute it\n \
under certain conditions; see the source code for details.\n' + '-'*20

import argparse
import numpy as np
import h5py

H5_FILENAME = ''


def arg_parse() -> tuple:

    parser = argparse.ArgumentParser()
    parser.add_argument( "-f", "--filename", help=f"H5 filename to check" )
    args = parser.parse_args()

    filename = H5_FILENAME
    if args.filename:
        filename = args.filename

    return filename


def main():
    
    filename = arg_parse()

    print( welcome_msg )

    try:
        with h5py.File( filename, 'r' ) as h5_file:
            if 'muh5' in h5_file:
                group = h5_file['muh5']
                print( f"Found 'muh5' group with following attributes: " )
                
                # Print attributes
                att = dict( zip( group.attrs.keys(), group.attrs.values() ) )
                for key in att.keys():
                    print( f" > {key}: {att[key]}" )
                
                # Compute total duration
                dataset_duration = dataset_number = 0
                if "dataset_duration" in att:
                    dataset_duration = int( att["dataset_duration"])
                if "dataset_number" in att:
                    dataset_number = int( att["dataset_number"])
                
                print( '-'*20 )
                print( f"Total duration: {dataset_duration * dataset_number}s" )

            else:
                raise Exception( f"No muh5 group find in h5 file {filename}" )


    except Exception as e:
        print( f'Failed to check H5 file: {e}' )
        exit()

if __name__ == "__main__":
	main()

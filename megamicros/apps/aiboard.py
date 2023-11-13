# megamicros.apps.aiboard.py Megamicros Aiboard launcher
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
apps/version.py

Launch the Aiboard application

@author: bruno.gas@sorbonne-universite.fr

Documentation
-------------
MegaMicros documentation is available on https://readthedoc.biimea.io
"""

import argparse
import megamicros.aiboard.main as aiboard_main
from megamicros.log import log, logging, formats_str

DEFAULT_LOGGER_MODE = logging.DEBUG

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument( "-v", "--verbose", help=f"set the verbose level (debug, info, warning, error, fatal)" )
    args = parser.parse_args()
    
    """ set default logger level """
    verbose_mode = DEFAULT_LOGGER_MODE
    log.setLevel( DEFAULT_LOGGER_MODE )

    log.info( f"Starting Aiboard..." )

    """ process logger level command line argument """
    if args.verbose:
        """ user has set the verbose argument """
        verbose_arg : str = args.verbose
        verbose_mode = formats_str( verbose_arg )
        if verbose_mode is None:
            log.warning( f"Unknown verbose mode '{verbose_arg}'. Set to default 'info' mode. Please correct the command line argument 'verbose'" )
            verbose_mode = DEFAULT_LOGGER_MODE
    else:
        verbose_mode = DEFAULT_LOGGER_MODE

    log.setLevel( verbose_mode )
    verbose_arg = formats_str( verbose_mode )
    log.info( f" .Set verbose level to [{verbose_arg}]" )
 
    aiboard_main.app.run_server(debug=True)



if __name__ == '__main__':
    main()



#===============================================================================
# OpenDigitalRadio - RadioDNS Bridge - Resolver Code
# 
# Copyright (C) 2016 Nick Piggott
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#===============================================================================

from __future__ import print_function
import sys
from pyradiodns.rdns import RadioDNS 
from spi import DabBearer
from odr.radiodns.resolver import *
import argparse
import logging


def main():

    parser = argparse.ArgumentParser(description='Resolves RadioDNS services from an ODR Dabmux file')
    parser.add_argument('f',  nargs=1, help='multiplex configuration file')
    parser.add_argument('-X', dest='debug', action='store_true', help='turn debug on')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('odr.radiodns.bridge')

    filename = args.f[0]

    check_warnings(resolve_dns(parse_mux_config(filename)))
    print("\nSlideshow Services:")
    resolve_slideshow(filename,printServices)
    print("\nEPG Services:")
    resolve_epg(filename,printServices)
    
def printServices(services):
    if len(services):
        print(services)
    return
    
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)    

        
if __name__ == '__main__':
    main()

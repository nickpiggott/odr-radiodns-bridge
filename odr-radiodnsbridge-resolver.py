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
from boost_info_parser import BoostInfoParser
from pyradiodns.rdns import RadioDNS 
from spi import DabBearer


def main():
	try:
		filename = sys.argv[1]

	except:
		print("You need to provide the filename of an odr-dabmux configuration file as a parameter")
		return

	
	configurationWarnings(resolveDNS(parseMuxConfig(filename)))
	print("\nSlideshow Services:")
	slideshowServices(filename,printServices)
	print("\nEPG Services:")
	EPGServices(filename,printServices)
	
def printServices(services):
	if len(services):
		print(services)
	return
	
def parseMuxConfig(filename):
	parser = BoostInfoParser()
	parser.read(filename)
	root = parser.getRoot()
	ensemble_ecc = int(root["ensemble"][0]["ecc"][0].getValue(), 16)
	ensemble_id = int(root["ensemble"][0]["id"][0].getValue(), 16)

	subchannels=[] 
	for subchannel in root["subchannels"][0].subTrees:
		type =  root["subchannels"][0][subchannel][0]["type"][0].getValue()
		if type == "packet" or type == "enhancedpacket":
			subchannels.append(
				{
					"subchannel" : subchannel,
					"type" : type,
					"bitrate" : root["subchannels"][0][subchannel][0]["bitrate"][0].getValue(),
					"inputuri" : root["subchannels"][0][subchannel][0]["inputuri"][0].getValue()
				})
					
	components=[]		
	for component in root["components"][0].subTrees:
		try:
			figtype = int(root["components"][0][component][0]["figtype"][0].getValue(), 16)
		except KeyError:
			figtype = None
			
	
		if figtype == 2: # Slideshow
			components.append(
				{
					"service" : root["components"][0][component][0]["service"][0].getValue(),
					"figtype" : figtype
				})		
				
		if figtype == 7: # EPG
			if int(root["components"][0][component][0]["type"][0].getValue()) == 60:
				components.append(
					{
						"service" : root["components"][0][component][0]["service"][0].getValue(),
		 				"subchannel" : root["components"][0][component][0]["subchannel"][0].getValue(),
						"figtype" : figtype,
						"address" : int(root["components"][0][component][0]["address"][0].getValue(), 16)
					})			
	
	services=[]
	for service in root["services"][0].subTrees:

		hasEPG = False
		hasSlideshow = False
		EPGpacketSize = None
		EPGinputURI = None
		EPGpacketAddress = None
	
		for component in components:
			if component["service"] == service:
				if component["figtype"] == 2:
					hasSlideshow = True
				if component["figtype"] == 7:
					hasEPG = True
					for subchannel in subchannels:
						if subchannel["subchannel"] == component["subchannel"]:
							EPGpacketAddress = int(component["address"])
							EPGpacketSize = int(subchannel["bitrate"])*3
							EPGinputURI = subchannel["inputuri"]
									
	
		services.append(
			{
				"service" : service,
				"label" : root["services"][0][service][0]["label"][0].getValue(),
				"bearer" : DabBearer(ensemble_ecc, ensemble_id, int(root["services"][0][service][0]["id"][0].getValue(), 16)),
				"hasEPG" : hasEPG,
				"hasSlideshow" : hasSlideshow,
				"EPGpacketSize" : EPGpacketSize,
				"EPGinputURI" : EPGinputURI,
				"EPGpacketAddress" : EPGpacketAddress
			})
		
	
	return services
				
def resolveDNS(services):
	radiodns = RadioDNS()
	for service in services:
		bearer = service["bearer"]
		try: 
			result = radiodns.lookupDABService("%X" % ((bearer.eid >> 4 & 0xf00) + bearer.ecc), "%X" % bearer.eid, "%X" % bearer.sid, "%X" % bearer.scids)
		except:
			result = None
		service["dns"] = result
	return services
	
def slideshowServices(filename,callback):
	services = resolveDNS(parseMuxConfig(filename))
	slideshowServices = []
	
	for service in services:

		try:
			radiovis = service["dns"]["applications"]["radiovis"]["supported"]
		except:
			radiovis = []

		try:
			radiovis_http = service["dns"]["applications"]["radiovis-http"]["supported"]
		except:
			radiovis_http = []
	
		if service["hasSlideshow"] and (radiovis or radiovis_http):
			slideshowServices.append(
				{ "fqdn" : service["dns"]["authorative_fqdn"],
				"bearer" : service["bearer"],
				"radiovis" : radiovis,
				"radiovis-http" : radiovis_http
				})
			
	callback(slideshowServices)
	return

def EPGServices(filename,callback):
	services = resolveDNS(parseMuxConfig(filename))

	radioepg_fqdn_list = []

	
	for service in services:
		radioepg_fqdn = ""
	
		try:
			radioepg_fqdn = service["dns"]["authorative_fqdn"]
		except:
			pass

		if radioepg_fqdn:
				# check to see if we already have that FQDN
				adding = True
				for s in radioepg_fqdn_list:
					if radioepg_fqdn == s["fqdn"]:
						adding = False
						continue

				if adding:
						EPGBearer = []
						EPGServer = []					
						
						for s in services:
							if not s.has_key("dns"): continue
							if not s["dns"]: continue
							if not s["dns"].has_key("authorative_fqdn"): continue
							if radioepg_fqdn == s["dns"]["authorative_fqdn"]:
								EPGBearer.append(s["bearer"])
								EPGServer = (s["dns"]["applications"]["radioepg"]["servers"])
						radioepg_fqdn_list.append({"fqdn" : radioepg_fqdn,
								"bearers": EPGBearer,
								"servers" : EPGServer })


	callback(radioepg_fqdn_list)
	return
	
def configurationWarnings(services):

	EPGtempURI = []
	
	for service in services:

		try:
			radiovis = len(service["dns"]["applications"]["radiovis"]["supported"])>0
		except:
			radiovis = False

		try:
			radiovis_http = len(service["dns"]["applications"]["radiovis-http"]["supported"])>0
		except:
			radiovis_http = False
			
		if not service["hasSlideshow"] and (radiovis or radiovis_http):
			eprint("WARNING:" + service["service"] + " '" + service["label"] + "' has hybrid visual slideshow service but no figtype = 0x02 definition in its component definition.")
		
		if service["hasSlideshow"] and not radiovis and not radiovis_http:
			eprint("WARNING:" + service["service"] + " '" + service["label"] + "' is configured to send DAB Slideshow with a figtype = 0x02 defined in its component definition, but has no hybrid visual source available.")
			
		if service["hasEPG"] == True:
			EPGtempURI.append(service["EPGinputURI"])
		
	EPGtempURI = set(EPGtempURI)
	
	if len(EPGtempURI) > 1 :
		eprint("WARNING: More than one EPG subchannel input file is defined." , EPGtempURI)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)	

		
if __name__ == '__main__':
    main()
	

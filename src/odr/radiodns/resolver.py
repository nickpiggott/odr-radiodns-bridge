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

# BoostInfoParser
# Copyright (C) 2014 Regents of the University of California.
# Author: Adeola Bannis 
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
# A copy of the GNU General Public License is in the file COPYING.

import logging
import shlex
from pyradiodns.rdns import RadioDNS 
from spi import DabBearer
from collections import OrderedDict

log = logging.getLogger('odr.radiodns')

class BoostInfoTree(object):
    def __init__(self, value = None, parent = None):
        super(BoostInfoTree, self).__init__()
        self.subTrees = OrderedDict()
        self.value = value
        self.parent = parent

        self.lastChild = None

    def createSubtree(self, treeName, value=None ):
        newTree = BoostInfoTree(value, self)
        if treeName in self.subTrees:
            self.subTrees[treeName].append(newTree)
        else:
            self.subTrees[treeName] = [newTree]
        self.lastChild = newTree
        return newTree

    def __getitem__(self, key):
        # since there can be repeated keys, we may have to get creative
        found = self.subTrees[key]
        return list(found)

    def getValue(self):
        return self.value

    def _prettyprint(self, indentLevel=1):
        prefix = " "*indentLevel
        s = ""
        if self.parent is not None:
            if self.value is not None and len(self.value) > 0:
                s += "\"" + str(self.value) + "\""
            s+= "\n" 
        if len(self.subTrees) > 0:
            if self.parent is not None:
                s += prefix+ "{\n"
            nextLevel = " "*(indentLevel+2)
            for t in self.subTrees:
                for subTree in self.subTrees[t]:
                    s += nextLevel + str(t) + " " + subTree._prettyprint(indentLevel+2)
            if self.parent is not None:
                s +=  prefix + "}\n"
        return s

    def __str__(self):
        return self._prettyprint()


class BoostInfoParser(object):
    def __init__(self):
        self._reset()

    def _reset(self):
        self._root = BoostInfoTree()
        self._root.lastChild = self

    def read(self, filename):
        with open(filename, 'r') as stream:
            ctx = self._root
            for line in stream:
                ctx = self._parseLine(line.strip(), ctx)

    def write(self, filename):
        with open(filename, 'w') as stream:
            stream.write(str(self._root))

    def _parseLine(self, string, context):
        # skip blank lines and comments
        commentStart = string.find(";")
        if commentStart >= 0:
           string = string[:commentStart].strip()
        if len(string) == 0:
           return context

        # ok, who is the joker who put a { on the same line as the key name?!
        sectionStart = string.find('{')
        if sectionStart > 0:
            firstPart = string[:sectionStart]
            secondPart = string[sectionStart:]

            ctx = self._parseLine(firstPart, context)
            return self._parseLine(secondPart, ctx)

        #if we encounter a {, we are beginning a new context
        # TODO: error if there was already a subcontext here
        if string[0] == '{':
            context = context.lastChild 
            return context

        # if we encounter a }, we are ending a list context
        if string[0] == '}':
            context = context.parent
            return context

        # else we are expecting key and optional value
        strings = shlex.split(string)
        key = strings[0]
        if len(strings) > 1:
            val = strings[1]
        else:
            val = None
        newTree = context.createSubtree(key, val)

        return context

    def getRoot(self):
        return self._root

    def __getitem__(self, key):
        ctxList = [self._root]
        path = key.split('/')
        foundVals = []
        for k in path:
            newList = []
            for ctx in ctxList:
                try:
                    newList.extend(ctx[k])
                except KeyError:
                    pass
            ctxList = newList
        
        return ctxList

def parse_mux_ensemble(filename):

        parser = BoostInfoParser()
        parser.read(filename)
        root = parser.getRoot()
        
        ecc = int(root["ensemble"][0]["ecc"][0].getValue(), 16)
        eid = int(root["ensemble"][0]["id"][0].getValue(), 16)
        label = root["ensemble"][0]["label"][0].getValue()
        shortlabel = root["ensemble"][0]["shortlabel"][0].getValue()

        return ecc,eid,label,shortlabel
        
def parse_mux_config(filename):
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
		service_id = int(root["services"][0][service][0]["id"][0].getValue(), 16)

		if service_id>65535: 	# this is a long SId which contains ECC (first two nibbles)
			service_ecc = (service_id >> 24)
		else: 			# this is a short SId which does not contain the ECC
			try:
				service_ecc = (int(root["services"][0][service][0]["ecc"][0].getValue(),16))
			except KeyError:
				service_ecc = ensemble_ecc
			
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
				"bearer" : DabBearer(service_ecc, ensemble_id, service_id),
				"hasEPG" : hasEPG,
				"hasSlideshow" : hasSlideshow,
				"EPGpacketSize" : EPGpacketSize,
				"EPGinputURI" : EPGinputURI,
				"EPGpacketAddress" : EPGpacketAddress
			})
		
	
	return services
				
def resolve_dns(services):
	radiodns = RadioDNS()
	for service in services:
		bearer = service["bearer"]
		
		if bearer.sid>65535: # this is a long SId which contains both ECC (first two nibbles) and CC (third nibble)
			gcc = (bearer.sid >> 12 & 0xf00) + (bearer.sid >> 24)
		else: # this is a short SId which contains only the CC (first nibble)
			gcc = (bearer.sid >> 4 & 0xf00) + bearer.ecc
			
		try: 
			result = radiodns.lookup_dab("%X" % gcc, "%X" % bearer.eid, "%X" % bearer.sid, "%X" % bearer.scids)
		except:
			result = None
		service["dns"] = result
	return services
	
def resolve_slideshow(filename,callback):
	services = resolve_dns(parse_mux_config(filename))
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

def resolve_epg(filename,callback):
	services = resolve_dns(parse_mux_config(filename))

	radioepg_fqdn_list = []

	for service in services:
		radioepg_fqdn = ""
		hasEPG = False
		hasSPI = False
		app = ""

		try:
			radioepg_fqdn = service["dns"]["authorative_fqdn"]
		except:
			pass

		try:
			hasEPG = service["dns"]["applications"]["radioepg"]["supported"]
			app = "radioepg"
		except:
			pass

		try:
			hasSPI = service["dns"]["applications"]["radiospi"]["supported"]
			app = "radiospi"
		except:
			pass

		if radioepg_fqdn and (hasEPG or hasSPI):
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
							if "dns" not in s: continue
							if not s["dns"]: continue
							if "authorative_fqdn" not in s["dns"]: continue
							if not s["dns"]["applications"][app]["supported"]: continue
							if radioepg_fqdn == s["dns"]["authorative_fqdn"]:
								EPGBearer.append(s["bearer"])
								EPGServer = (s["dns"]["applications"][app]["servers"])
						radioepg_fqdn_list.append({"fqdn" : radioepg_fqdn,
								"bearers": EPGBearer,
								"servers" : EPGServer,
								"app" : app })


	callback(radioepg_fqdn_list)
	return
	
def check_warnings(services):

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
			log.error("WARNING:" + service["service"] + " '" + service["label"] + "' has hybrid visual slideshow service but no figtype = 0x02 definition in its component definition.")
		
		if service["hasSlideshow"] and not radiovis and not radiovis_http:
			log.error("WARNING:" + service["service"] + " '" + service["label"] + "' is configured to send DAB Slideshow with a figtype = 0x02 defined in its component definition, but has no hybrid visual source available.")
			
		if service["hasEPG"] == True:
			EPGtempURI.append(service["EPGinputURI"])
		
	EPGtempURI = set(EPGtempURI)
	
	if len(EPGtempURI) > 1 :
		log.error("WARNING: More than one EPG subchannel input file is defined: %s", EPGtempURI)

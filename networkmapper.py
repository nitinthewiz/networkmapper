''' 
AUTHOR: Nitin Khanna

Reason this module was made: for Network Management Lecture

Thanks to: Jochen from network-forum.com at http://networking-forum.com/viewtopic.php?t=17635

for?? - His file at http://dl.dropbox.com/u/7491662/cdpwalker.py

which was a big inspiration for this program
'''

''' 
NOTE: Please run this code as Admin since it needs to run a tftp library, a system process and pySNMP
'''

#!/usr/bin/env python
# Dependencies: pysnmp
# http://www.oidview.com/mibs/9/CISCO-CDP-MIB.html

import sys
import re
import os
import socket
import logging
import tftpy
import struct
from subprocess import check_call
try:
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    from pysnmp.proto import rfc1902
except ImportError:
    print "pySNMP module missing, please install it else this program will not work"
    sys.exit(0)
try:
    from configwalker import nettools as print_gns_file
except ImportError:
    print "ConfigWalker File missing from folder where network mapper is stored. Please download a full copy from SourceForge.net under the title networkmapper"

logger = logging.getLogger("networkmapper")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)

OID_SYSNAME = '1.3.6.1.2.1.1.5.0'
OID_SYSDESCR = '1.3.6.1.2.1.1.1.0'
OID_CDP_CACHE_ENTRY = '1.3.6.1.4.1.9.9.23.1.2.1.1'
OID_CDP_CACHE_DEVICEID = '1.3.6.1.4.1.9.9.23.1.2.1.1.6.'
OID_CDP_CACHE_DEVICEPORT = '1.3.6.1.4.1.9.9.23.1.2.1.1.7.'
OID_CDP_CACHE_ADDRESS = '1.3.6.1.4.1.9.9.23.1.2.1.1.4.'
OID_FLASH_GET = '1.3.6.1.4.1.9.2.10.9'
OID_RUN_CONF = '1.3.6.1.4.1.9.2.1.55'
OID_FLASH_STATUS = '1.3.6.1.4.1.9.2.10.17.1.1.1'
OID_CDP_DEVICE_PLATFORM = '1.3.6.1.4.1.9.9.23.1.2.1.1.8.'


NEIGHBOR_TABLE = []
DEVICES = {}

class SnmpSession(object):
    """SNMP Session object
        This object is used to get the information from the router
        using OIDs defined by Cisco at http://www.oidview.com/mibs/9/CISCO-CDP-MIB.html
        The simplest initialization of the an SnmpSession object is as

        >>> snmp = SnmpSession()
        >>> snmp.host = "198.0.0.2"

        By doing so, you are passing the router's IP address to the SNMP object.

        I have simplified the process of accessing the internal variables of the Class for current use
        but further changes to the code will bring better Class definitions.
    """

    def __init__(self):
        self.host = "198.0.0.2"
        self.port = 161
        self.community = "public"
        self.version = "2c"


    def get_config(self):
        """
        This function returns the configuration required for the router according to the version
        of SNMP being used.We have assumed an SNMP version 2c for our program but this can be changed easily.

        A sample code is :

        >>> snmp.version = "2c"
        >>> snmp_config = self.get_config()

        This function is used internally only.
        """
        if self.version == "1":
            return  cmdgen.CommunityData('test-agent', self.community, 0),

        elif self.version == "2c":
            return cmdgen.CommunityData('test-agent', self.community)

        elif self.version == "3":
            return cmdgen.UsmUserData('test-user', 'authkey1', 'privkey1'),

    def oidstr_to_tuple(self, s):
        """ This function removes the '.' (dots) from the OID specified in the program
        and returns it in the form of a tuple, which is used by pySNMP to get info from the router.
        
        Error in Function - remove trailing dot if there is one

        Sample Implementation -

        >>> oid = self.oidstr_to_tuple(oid)
        """

        return tuple([int(n) for n in s.split(".")])

    def snmp_get(self, oid):
        """
        This function gets a single data from the router, such as the router name or
        the system description.For lists of data such as a list of interfaces or a
        list of neighbors of the router, a different function called snmp_getnext is used.

        Example:

        >>> sys_descr = snmp.snmp_get(OID_SYSDESCR)[1]

        This function returns a tuple of data back and the useful datum from that is the 2nd part,
        hence the use of the [1] in the function.
        """
        r = ()

        oid = self.oidstr_to_tuple(oid)
        snmp_config = self.get_config()

        errorIndication, errorStatus, \
            errorIndex, varBinds = cmdgen.CommandGenerator().getCmd(
            snmp_config, cmdgen.UdpTransportTarget((self.host, self.port)), oid)

        if errorIndication:
            print errorIndication
            print errorStatus
            print errorIndex
        else:
            if errorStatus:
                print '%s at %s\n' % (
                    errorStatus.prettyPrint(), varBinds[int(errorIndex)-1])
            else:
                for name, val in varBinds:
                    return (name.prettyPrint(), val.prettyPrint())

    def snmp_getnext(self, oid):
        """ This function is used to get a list of data from the router, such as
        a list of interfaces or neighbors the router has. This information must then
        be parsed through with a for loop to go through all the returned data.

        Sample -

        >>> r = snmp.snmp_getnext(OID_CDP_CACHE_ENTRY)
        >>> for e in r:
        >>>     snmpoid, value = e[0], e[1]
        
        """

        r = []

        oid = self.oidstr_to_tuple(oid)

        snmp_config = self.get_config()

        errorIndication, errorStatus, errorIndex, \
            varBindTable = cmdgen.CommandGenerator().nextCmd(
            snmp_config, cmdgen.UdpTransportTarget((self.host, self.port)), oid)

        if errorIndication:
            print errorIndication
            print errorStatus
            print errorIndex
        else:
            if errorStatus:
                print '%s at %s\n' % (
                    errorStatus.prettyPrint(), varBindTable[-1][int(errorIndex)-1])
            else:
                for varBindTableRow in varBindTable:
                    for name, val in varBindTableRow:
                        r.append((name.prettyPrint(), val.prettyPrint()))

        return r



class CdpDevice(object):
    """
    This Class is used to define a single CDP neighbor of a router. It is currently
    the simplest implementation of the class as can be. It just holds -
    1. Device ID - The name of the neighboring router
    2. Device Port - The interface of the neighbor which connects to the current router being queried
    3. Address - IP address of the router.
    4. Device Platform - The platform of the device (Cisco 3700, Cisco 3640) -- This is essential for the creation of the .NET file since
    GNS3 does not work without knowledge of the device platform

    Sample -

    >>> neighbors[ifindex] = CdpDevice()
    """
    deviceid = ""
    deviceport = ""
    address = ""
    deviceplatform = ""

def get_cache_ifindex(snmpoid):
    """ This function returns the interface of the router being accessed in relation to the neighbor whose details we are accessing.
    For Example - If router R1 has connections to R2 and R3 on interfaces Fa1/0 and Fa2/0 then this function returns the corresponding
    ifIndices for Fa1/0 and Fa2/0

    Sample -

    >>> ifindex = get_cache_ifindex(snmpoid)
    """
    return int(snmpoid.split(".")[-2])

def get_cdp_neighbors(host):
    """
    This is the core of the program. This function accesses the router (whose IP address is specified as hot)
    and runs through the list of the OID labelled OID_CDP_CACHE_ENTRY to access details about the router's
    neighbors. It also accesses the router for it's IOS via tftp and for this, please ensure that the program is running under
    Admin and the routers are configured to upload the contents of their flash to a tftp client.

    Sample Code -

    >>> h, rel = get_cdp_neighbors(host)
    
    Once again, this function returns a tuple of the neighbor and it's relation with the current router.

    The planning of the program is in such a format that every link between 2 routers is defined as a relationship
    which defines the routers which are connected, the platforms of these routers, the interfaces used by that link
    and the IOS files of each router which is stored by the program in the tmp folder.
    
    """
    neighbors = {}
    neighbor_relations = []
    hostname = ""
    hostplatform = ""
    snmpversion = "2c"
    snmpcommunity = "public"

    snmp = SnmpSession()
    snmp.host = host
    r = snmp.snmp_getnext(OID_CDP_CACHE_ENTRY)
    if r == []:
        l.warn("failed to query %s by snmp" % host)
        return [], []

    for e in r:
        snmpoid, value = e[0], e[1]
        ifindex = get_cache_ifindex(snmpoid)
        if not ifindex in neighbors:
            neighbors[ifindex] = CdpDevice()

        if hostplatform == "":
            hostplatform = re.search("(.*)(?<=C)(\d\d\d\d)(.*)", snmp.snmp_get(OID_SYSDESCR)[1]).group(2)
        if hostname == "":
            hostname = snmp.snmp_get(OID_SYSNAME)[1]
        if snmpoid.startswith(OID_CDP_CACHE_ADDRESS):
            neighbors[ifindex].address = "%i.%i.%i.%i" % \
                    (struct.unpack("BBBB", value))
        elif snmpoid.startswith(OID_CDP_CACHE_DEVICEID):
            neighbors[ifindex].deviceid = value
        elif snmpoid.startswith(OID_CDP_CACHE_DEVICEPORT):
            neighbors[ifindex].deviceport = value
        elif snmpoid.startswith(OID_CDP_DEVICE_PLATFORM):
            neighbors[ifindex].deviceplatform = re.search('(.*)(\d\d\d\d)(.*)',value).group(2)

            ifname = snmp.snmp_get("1.3.6.1.2.1.2.2.1.2.%i" % ifindex)[1]
            
            hostOS = get_flash(host)
            if hostplatform != neighbors[ifindex].deviceplatform:
                neighOS = get_flash(neighbors[ifindex].address)
            else:
                neighOS = hostOS
    
            var1 = (hostOS, hostplatform, hostname, ifname, neighOS, neighbors[ifindex].deviceplatform, neighbors[ifindex].deviceid, neighbors[ifindex].deviceport)
            var2 = (neighOS, neighbors[ifindex].deviceplatform, neighbors[ifindex].deviceid, neighbors[ifindex].deviceport, hostOS, hostplatform, hostname, ifname)
            print "Received configurations for the link "+hostname+" to "+neighbors[ifindex].deviceid
            
            if not var1 in neighbor_relations and not var2 in neighbor_relations:
                neighbor_relations.append(var1)
    
    return [neighbors[neigh] for neigh in neighbors], neighbor_relations

def print_relations(relations, filename='a.dot'):
    """ This function is responsible for saving the DOT file which can be viewed in GraphViz.
    Sample Code -

    >>> print_relations(relations, filename)
    """
    with file(filename, "w") as f:
        f.write("digraph G {\n")
        f.write("rankdir=LR;")
        f.write("size=\"8.5\";")

        for relation in relations:
            if "Gigabit" in relation[1] and "Gigabit" in relation[3]:
                linkcolor = "green"
            else:
                linkcolor = "blue"
                        
            f.write("\"%s\"->\"%s\" [ label=\"(%s - %s)\",color=%s ];\n" % \
                            (relation[2], relation[6], relation[3], relation[7], linkcolor))

        f.write("}")
        print "\nPrinted the GraphViz DOT file\n"

def print_png(dotfile='a.dot', pngfile='a.png'):
    """
    This function prints out a PNG file from the DOT file so that you can view the network as a map if you do not have GraphViz
    or other similar software.

    Sample code -

    >>> print_png(filename, pngfile)
    """
    check_call(['dot','-Tpng',dotfile,'-o',pngfile])
    print "\nPrinted PNG file", pngfile
    print "\n"
    

def get_flash(host):
    """ This function gets the IOS of the routers. It uses the tftpy library
    and it is nesessary that the router is setup as a tftp server serving up it's IOS file from the flash.
    The config in the router is as follows -
    R1(config)tftp-server flash:c3640-jk9o3s-mz.124-16a.bin

    A Sample code -

    >>> hostOS = get_flash(host)
    """
    snmpversion = "2c"
    snmpcommunity = "public"

    snmp = SnmpSession()
    snmp.host = host
    try:
        r = snmp.snmp_get(OID_FLASH_STATUS)[1]
    except TypeError:
        print host+" is not responding or does not have SNMP Enabled"
        return
    if r == []:
        logger.warn("failed to query %s by snmp" % host)
    client = tftpy.TftpClient(host, 69)
    try:
        client.download(r, '/tmp/'+r)
    except:
        print "There has been an error in accessing the router at IP: ", host
    return r
    

def merge_relations(relations, relations2):
    """
    This function adds the relation of 2 routers to a total list of relations. A router relation looks a lot like -
    ('c3640-jk9o3s-mz.124-16a.bin','R1','FastEthernet1/0','c3640-jk9o3s-mz.124-16a.bin','R2','FastEthernet0/0')
    As you can see, each relation is a tuple. And the ending list holds a list of tuples.

    Sample code -

    >>> relations = merge_relations(relations, rel)
        
    """
    for relation in relations2:
        relation_var2 = (relation[4], relation[5], relation[6], relation[7], relation[0], relation[1], relation[2], relation[3])
        if not relation in relations and not relation_var2 in relations:
            relations.append(relation)

    return relations


def read_config(filename):
    """ This function retrives the configuration of the router and stores it in a file.
    It is currently not being used by the program but will be available in further versions. :)
    """
    hosts = []

    with file(filename, "r") as f:
        for l in f:
            l = l.strip()
            if not l in hosts:
                hosts.append(l)
            else:
                logger.warn("host %s already seen in config file" % l)

    return hosts

if __name__ == "__main__":
    print "Welcome to NetworkMapper v0.7 by Nitin Khanna"
    print "This program allows you to traverse a real network of routers and create a .NET file from it"
    print "That .NET file can be used to emulate the real network in GNS3 or Dynagen. Yay!"
    print "We also create a .DOT file which can be opened in GraphViz"
    print "and a corresponding .PNG which is a pretty good image of the network :)"
    print "\n"
    
    relations = []
    filename = raw_input("Enter the name for dot file(default = a.dot) ")
    if filename == "":
        filename = 'a.dot' ##### Default

    pngfile = raw_input("Enter the name of the image file(default = a.png) ")
    if pngfile == "":
        pngfile = 'a.png' #### Default
    hosts = []
    hostsdone = []

    host = raw_input("Enter the first router IP(default = 198.0.0.1) ")
    if host == "":
        host = '198.0.0.2'  ##### Default
    hosts.append(host)

    print "\n"

    while hosts != []:
        host = hosts.pop()

        h, rel = get_cdp_neighbors(host)
        relations = merge_relations(relations, rel)
        
        hostsdone.append(host)
        for host in h:
            if host.address == "127.0.0.1":
                print "host %s has 127.0.0.1 as it's neighbor?!" % hostsdone[-1]
            elif not host.address in hostsdone:
                hosts.append(host.address)

    print_relations(relations, filename)
    print_png(filename, pngfile)
    
    netfile = raw_input("Please Enter the name of the GNS File(default = abc.net) ")
    if netfile == "":
        netfile = 'abc.net'         ### Default
    print_gns_file(relations, netfile)



from cli import *
from cisco import *
from cisco.system import *
from cisco.ospf import *
from cisco.bgp import *

from params import *

import pprint
import re
import sys
import json
import ipaddress
import time

intIdReg = re.compile("\d+\/(\d+)")

def findIf ():
    reg = re.compile('[Ee]thernet\d+\/\d+')
    for a in sys.argv[1:]:
        if reg.match (a):
            return a
    return None

def pp (content):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(content)

def setInterface(if_name, ip_address = None):
    interface = Interface(if_name)
    interface.set_description("Configured by AutoBGP Python")
    commands = [
        "interface %s" % if_name,
        "no switchport",
        "mtu 9216"
    ]
    if ip_address is None:
        commands.append("medium p2p")
        commands.append("ip unnumbered loopback0")
        
    configure_array(commands)
    if ip_address is not None:
        interface.set_ipaddress(ip_address, 30)
    interface.set_state('up')

def getAdminState(intf):
    result = json_clid("show interface %s" % intf)["TABLE_interface"]["ROW_interface"]["admin_state"]

    if result == "up":
        return True
    else:
        return None
    
def getLeafID():
    hostname = System().get_hostname()
    match = re.match(r'[Ll]eaf(\d+)', hostname)
    if match:
        return int(match.group(1))
    else:
        return None

def getSpineID(intf):
    if_index = parsePortNumber(intf)
        
    if if_index not in uplink_ports:
        print('Not uplink port')
        exit()
    return uplink_ports.index(if_index) + 1

def parsePortNumber(intf):
    search = intIdReg.search(intf)
    if_index = 0
    if search:
        if_index = int(search.group(1))

    return if_index

def calcIP(leaf, spine):
    ip_address = ipaddress.ip_address(unicode(start_ip))
    ip_address += (leaf - 1) * (4 * spine_num) + (spine - 1) * 4 + 1
    return str(ip_address)

def setOSPFInterface(intf):
    ospf_session = OSPFSession(ospf_process_tag)
    ospf_interface = ospf_session.OSPFInterface(intf, str(ospf_area))
    ospf_interface.cfg_ospf_priority(0)
    ospf_interface.add()
    commands = [
        "interface %s" % intf,
        "ip ospf network point-to-point"
    ]
    configure_array(commands)

def waitOSPFAllFull(intf):
    timeout = 60
    command = "show ip ospf neighbor %s" % intf
    for _ in range(timeout):
        time.sleep(1)
        ospf_neighbor = json_clid(command)

        if ospf_neighbor is None:
            continue
        ospf_neighbor = ospf_neighbor["TABLE_ctx"]["ROW_ctx"]
        if int(ospf_neighbor["nbrcount"]) > 0 \
           and ospf_neighbor["TABLE_nbr"]["ROW_nbr"]["state"] == "FULL":
            return True
    return None

def setBGPNeighbor(neighbor_addr):
    bgp_session = BGPSession(bgp_as)
    neighbor = bgp_session.BGPNeighbor(neighbor_addr, ASN=bgp_as)
    neighbor.cfg_update_source("lo0")
    commands = [
        "router bgp %i" % bgp_as,
        "neighbor %s" % neighbor_addr,
        "address-family l2vpn evpn",
        "send-community both"
    ]
    configure_array(commands)

def getBGPNeighbors():
    neighbors = []
    results = json_clid("show bgp l2vpn evpn summary")["TABLE_vrf"]["ROW_vrf"]

    if "TABLE_af" not in results:
        return []
    results = results["TABLE_af"]["ROW_af"]["TABLE_saf"]["ROW_saf"]

    if "TABLE_neighbor" not in results:
        return []
    results = results["TABLE_neighbor"]["ROW_neighbor"]
    
    if type(results) is dict:
        results = [results]

    for result in results:
        neighbors.append(result["neighborid"])
    return neighbors

def getOSPFNeighbors():
    neighbors = []
    results = json_clid("show ip ospf neighbor")
    if results is None:
        return []

    results = results["TABLE_ctx"]["ROW_ctx"]["TABLE_nbr"]["ROW_nbr"]
    if type(results) is dict:
        results = [results]

    for result in results:
        neighbors.append(result["rid"])
    return neighbors
    
def removeUnusedBGPNeighbor():
    #nextHopLoopbacks = getNextHopLoopback()
    ospfNeighbors = getOSPFNeighbors()
    bgpNeighbors = getBGPNeighbors()

    bgp_session = BGPSession(bgp_as)

    for neighbor_addr in list_diff(bgpNeighbors, ospfNeighbors):
        neighbor = bgp_session.BGPNeighbor(neighbor_addr)
        neighbor.remove()
    
def configure_array(commands):
    commands.insert(0, "conf t")
    cli(" ; ".join(commands))

def json_clid(command):
    try:
        result = clid(command)
        if result is None:
            return None
        return json.loads(clid(command))
    except:
        return None

def list_diff(a, b):
    return list(set(a) - set(b))

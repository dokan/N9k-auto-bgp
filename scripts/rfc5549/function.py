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

def setInterface(if_name):
    interface = Interface(if_name)
    interface.set_description("Configured by AutoBGP Python")
    commands = [
        "interface %s" % if_name,
        "no switchport",
        "mtu 9216",
        "ipv6 address use-link-local-only"
    ]
    configure_array(commands)
    interface.set_state('up')
    
def getAdminState(intf):
    result = json_clid("show interface %s" % intf)["TABLE_interface"]["ROW_interface"]["admin_state"]

    if result == "up":
        return True
    else:
        return None
    
def getPodID(hostname = None):
    if hostname is None:
        hostname = System().get_hostname()
        
    match = re.search(r'[Pp]od(\d+)', hostname)
    if match:
        return int(match.group(1))
    else:
        return 0

def getRole():
    hostname = System().get_hostname()

    match = re.search(r'([Ll]eaf|[Ss]pine)', hostname)
    if match:
        return match.group(1).lower()
    else:
        return None

def getSwitchID():
    hostname = System().get_hostname()

    match = re.search(r'([Ll]eaf|[Ss]pine)(\d+)', hostname)
    if match:
        return int(match.group(2))
    else:
        return 0

def createRouterID():
    ip_address = ipaddress.ip_address(unicode(base_router_id))
    ip_address +=  256 * getPodID() + getSwitchID()
    return str(ip_address)

def setBGPNeighbor(neighbor_addr, self_as, remote_as, if_name):
    config_asn = getASN()
    new_asn = False
    if config_asn is not None and self_as != config_asn:
        new_asn = True
        commands = ["no router bgp %i" % config_asn]
        configure_array(commands)
        
    bgp_session = BGPSession(self_as)
    if new_asn or config_asn is None:
        bgp_session.cfg_router_id(createRouterID())
        
    neighbor = bgp_session.BGPNeighbor(neighbor_addr, ASN=remote_as)
    neighbor.cfg_update_source(if_name)
    neighbor.set_addr_family("ipv4", "unicast")
    neighbor.send_community()
    neighbor.send_community_extended()

def getBGPNeighbors():
    neighbors = []
    results = json_clid("show bgp ipv4 unicast summary")["TABLE_vrf"]["ROW_vrf"]

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

def getIPv6Neighbors():
    neighbors = []
    results = json_clid("show ipv6 neighbor")["TABLE_vrf"]["ROW_vrf"]["TABLE_afi"]["ROW_afi"]
    if "TABLE_adj" not in results:
        return []
    results = results["TABLE_adj"]["ROW_adj"]

    if type(results) is dict:
        results = [results]

    for result in results:
        neighbors.append(result["ipv6-addr"])
    return neighbors

def getASN():
    result = json_clid("show bgp ipv4 unicast summary")

    if result is None:
        return None
    
    return int(result["TABLE_vrf"]["ROW_vrf"]["vrf-local-as"])

def removeUnusedBGPNeighbor():
    self_as = getASN()
    ipv6Neighbors = getIPv6Neighbors()
    bgpNeighbors = getBGPNeighbors()

    bgp_session = BGPSession(self_as)
    for neighbor_addr in list_diff(bgpNeighbors, ipv6Neighbors):
        neighbor = bgp_session.BGPNeighbor(neighbor_addr)
        neighbor.remove()
        
def getIPv6Neighbor(if_name):
    timeout = 10
    command = "show ipv6 neighbor %s" % if_name
    for _ in range(timeout):
        cli("ping6 multicast ff02::1 source-interface %s count 1 timeout 1" % if_name)
        results = json_clid(command)["TABLE_vrf"]["ROW_vrf"]["TABLE_afi"]["ROW_afi"]

        if "TABLE_adj" in results:
            return results["TABLE_adj"]["ROW_adj"]["ipv6-addr"]
    return None

def getCDPNeighbor(if_name):
    result = json_clid("show cdp neighbor interface %s detail" % if_name)
    if result is None:
        return None

    return result["TABLE_cdp_neighbor_detail_info"]["ROW_cdp_neighbor_detail_info"]["sysname"]
    
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

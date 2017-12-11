from function import *

if __name__ == '__main__':
    leaf = getLeafID()
    if leaf is None:
        print('This is not leaf switch')
        exit()

    intf = findIf()
    if intf is None:
        print('Not Interface Related log')
        exit()
        
    spine = getSpineID(intf)
    
    ip_address = calcIP(leaf, spine)
    setInterface(intf, ip_address)
    setOSPFInterface(intf)
    
    if waitOSPFAllFull(intf):
        bgpNeighbors = getBGPNeighbors()
        ospfNeighbors = getOSPFNeighbors()

        for neighbor_addr in list_diff(ospfNeighbors, bgpNeighbors):
            setBGPNeighbor(neighbor_addr)
            
        print("Done BGP Configuration")
    else:
        print("OSPF didn't converge")

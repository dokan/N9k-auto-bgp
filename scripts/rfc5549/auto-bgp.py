from function import *

if __name__ == '__main__':
    intf = findIf()
    if intf is None:
        print('Not Interface Related log')
        exit()

    role = getRole()
    if role is None:
        print("Wrong hostname")
        exit()
    
    setInterface(intf)
    neighbor_addr = getIPv6Neighbor(intf)

    if neighbor_addr is None:
        print("No IPv6 neighbor found")
        exit()
    
    self_as = bgp_as
    remote_as = bgp_as
    
    if role == "spine":
        neighbor = getCDPNeighbor(intf)
        neighbor_podID = getPodID(neighbor)
        remote_as += neighbor_podID
    else:
        podID = getPodID()
        self_as += podID
        
    setBGPNeighbor(neighbor_addr, self_as, remote_as, intf)

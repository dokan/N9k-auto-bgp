from function import *

if __name__ == '__main__':
    intf = findIf()
    if intf is None:
        print('Not Interface Related log')
        exit()

    adminState = getAdminState(intf)
    
    commands = [
        "default interface %s" % intf,
    ]
    configure_array(commands)

    if adminState:
        interface = Interface(intf)
        interface.set_state('up')

    removeUnusedBGPNeighbor()

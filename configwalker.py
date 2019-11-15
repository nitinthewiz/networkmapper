""" 
Author: Nitin Khanna

Reason: Part of networkmapper module

Awesome Thanks to: GNS3

why??? - Because they use the ConfigObj module to save the .NET file for the config we create in GNS3, so I'm also using the same!
"""
import re
from configobj import ConfigObj
from configobj import Section

def nettools(relations="", filename='abc.net'):
    """
    This is the core function of this module. It accepts the relations created by the networkmapper module and converts them into a .NET
    file for use with GNS3. The file created is a striped down version of an actual .NET file and thus the topology created will look funny
    when opened in GNS3.(because no x and y co-ordinates are specified by this module)
    It's best to simply rearrange your routers and save the file again, specially since you might want to add a cloud of other components to
    the topology.

    Usage -

    >>> from configwalker import nettools as print_gns_file
    >>> print_gns_file(relations, netfile)

    I've created this file with the name of the module as nettools but it just seems more logical to name
    the function as print_gns_fie()
    """
    config = ConfigObj(configspec='configspec')    
    config.indent_type = '    '
    config.filename = filename
    config['autostart'] = 'False'
    config['127.0.0.1:7200'] = {}
    config['127.0.0.1:7200']['workingdir'] = '/tmp'
    config['127.0.0.1:7200']['udp'] = 10000
    
    router_config = ConfigObj(configspec='configspec')
    for count in range (0,len(relations)):
        a0 = relations[count][0]
        a1 = relations[count][1]
        a2 = relations[count][2]
        a3 = relations[count][3]
        begin = re.search("(^.)(.*)",a3).group(1)
        a3 = re.sub('(.*)[^(\d\/\d)]',begin,a3)         # s = re.sub(" \d+", " ", s) from http://stackoverflow.com/questions/817122/delete-digits-in-python-regex
        a4 = relations[count][4]
        a5 = relations[count][5]
        a6 = relations[count][6]
        a7 = relations[count][7]
        begin = re.search("(^.)(.*)",a7).group(1)
        a7 = re.sub('(.*)[^(\d\/\d)]',begin,a7)         # s = re.sub(" \d+", " ", s) from http://stackoverflow.com/questions/817122/delete-digits-in-python-regex
        router_config['127.0.0.1:7200'] = {}
        router_config['127.0.0.1:7200'][a1] = {}
        router_config['127.0.0.1:7200'][a1] = {'image':'/tmp/'+a0}
        router_config['127.0.0.1:7200']['ROUTER '+a2] = {}
        router_config['127.0.0.1:7200']['ROUTER '+a2] = {'model': a1 , a3 : a6+" "+a7}
        router_config['127.0.0.1:7200'][a5] = {}
        router_config['127.0.0.1:7200'][a5] = {'image':'/tmp/'+a4}
        router_config['127.0.0.1:7200']['ROUTER '+a6] = {}
        router_config['127.0.0.1:7200']['ROUTER '+a6] = {'model': a5 , a7 : a2+" "+a3}
        config.merge(router_config)
    config.write()
    print ".NET File written to - ", filename

if __name__ == "__main__":
    nettools()

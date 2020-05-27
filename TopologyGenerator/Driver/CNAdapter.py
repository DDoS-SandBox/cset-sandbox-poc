from typing import Dict, List
from mininet.net import Containernet
from mininet.node import Controller, Docker, OVSBridge

from Topology.AutonomousSystem import AutonomousSystem
from Topology.Node import Host, Router, BoringRouter, Switch, NetworkInterface
from QuaggaConfigGenerator.QuaggaConfigGenerator import QuaggaConfigGenerator

"""
TODO: many LoC in the init() should be relocated
"""


class CNAdapter:
    # create containernet instance
    # net = Containernet(controller=Controller)
    net = Containernet()
    # add a default sdn controller for OVS switches to switch end host traffic
    # net.addController('c0')

    #########################
    # router-related vars
    #########################
    sandbox_routers: List['Router'] = []

    sb_router_to_container: Dict['Router', 'Docker'] = {}
    # track how many interfaces of a sandbox router has been processed
    # we need this index to build the interface name
    sb_router_to_container_if_index: Dict['Router', int] = {}
    # we map 'logical' interface obj to the absolute interface name in a container
    # we can use it to build absolute interface name to IPv4Interface string mapping
    # this way, we can build bgpd.conf and zebra.conf for each router container
    sb_router_if_to_container_if_name: Dict['NetworkInterface', str] = {}

    #########################
    # switch-related vars
    #########################
    sandbox_switches: List['Switch'] = []
    # as for now, we do not use Docker containers to implement switches/bridges
    # unless there is an absolute perf-related issue, we will continue to not use Docker for switches/bridges
    sb_switch_to_OVSBridge: Dict['Switch', 'OVSBridge'] = {}
    sb_switch_to_OVSBridge_index: Dict['Switch', int] = {}
    sb_switch_if_to_OVSBridge_if_name: Dict['NetworkInterface', str] = {}

    #########################
    # end-host-related vars
    #########################
    sandbox_end_hosts: List['Host'] = []
    sb_host_to_container: Dict['Host', 'Docker'] = {}
    sb_host_to_container_index: Dict['Host', int] = {}
    sb_host_if_to_container_if_name: Dict['NetworkInterface', str] = {}

    def __init__(self, as_list: List['AutonomousSystem']):
        #########################
        # router-router linking
        #########################
        # get all routers from all sandbox ASes
        self.sandbox_routers = [router for router in [as_obj.routers[0] for as_obj in as_list]]
        # prepare boring router docker containers
        self.sb_router_to_container = {}
        for sandbox_router in self.sandbox_routers:
            container = self.net.addDocker(sandbox_router.get_node_id(), ip="",
                                           dimage=sandbox_router.docker_image,
                                           cap_add=sandbox_router.docker_caps)
            # add the sandbox router to its container mapping
            self.sb_router_to_container[sandbox_router] = container

        # iterate through each sandbox router, link containers
        for local_router in self.sandbox_routers:
            local_router_interfaces = local_router.router_to_router_net_interfaces
            for local_interface in local_router_interfaces:
                # get remote router info
                remote_interface = local_interface.get_paired_interface()
                remote_router = remote_interface.get_owner_node()

                # check if each router is already in sandbox_router_to_container_interface_index
                if local_router not in self.sb_router_to_container_if_index:
                    self.sb_router_to_container_if_index[local_router] = 0
                if remote_router not in self.sb_router_to_container_if_index:
                    self.sb_router_to_container_if_index[remote_router] = 0

                # get each router's current container interface index
                local_router_int_i = self.sb_router_to_container_if_index[local_router]
                remote_router_int_i = self.sb_router_to_container_if_index[remote_router]
                # generate the container interface name for each router
                local_router_int_name = CNAdapter.get_interface_name_in_containernet(
                    local_router.get_node_id(), local_router_int_i)
                remote_router_int_name = CNAdapter.get_interface_name_in_containernet(
                    remote_router.get_node_id(), remote_router_int_i)

                # save the sandbox network interface to container interface name mapping
                if (local_interface not in self.sb_router_if_to_container_if_name) and (
                        remote_interface not in self.sb_router_if_to_container_if_name):
                    self.sb_router_if_to_container_if_name[local_interface] = local_router_int_name
                    self.sb_router_if_to_container_if_name[remote_interface] = remote_router_int_name
                    # now we can safely link two router containers together
                    local_router_container = self.sb_router_to_container[local_router]
                    remote_router_container = self.sb_router_to_container[remote_router]
                    self.net.addLink(local_router_container, remote_router_container)
                    # increment container interface index for both routers
                    self.sb_router_to_container_if_index[local_router] += 1
                    self.sb_router_to_container_if_index[remote_router] += 1
                else:
                    print('redundant interface mapping process, skip')
                    pass

        for network_if, container_if in self.sb_router_if_to_container_if_name.items():
            print("sb ip if: {}, container if: {}".format(network_if.get_ip_interface(), container_if))

        # TODO: we create end host boxes and attach them to the corresponding routers via OVSBridges

        #########################
        # switch-router linking
        #########################
        # populate the sandbox switch list
        for r in self.sandbox_routers:
            r_to_s_ifs = r.router_to_switch_net_interfaces
            for r_to_s_if in r_to_s_ifs:
                self.sandbox_switches.append(r_to_s_if.get_paired_interface().get_owner_node())

        # create ovs bridges in mininet
        # and link them to routers in mininet
        for s in self.sandbox_switches:
            ovs_br = self.net.addSwitch(name=s.get_node_id(), cls=OVSBridge)
            self.sb_switch_to_OVSBridge[s] = ovs_br

            # find the linked sandbox router
            linked_sb_router = None
            linked_sb_router_if = None
            switch_net_if_linked_to_router = None
            for n_if in s.net_interfaces:
                paired_if = n_if.get_paired_interface()
                paired_node = paired_if.get_owner_node()
                if isinstance(paired_node, Router):
                    linked_sb_router = paired_node
                    linked_sb_router_if = paired_if
                    switch_net_if_linked_to_router = n_if
                    break
            assert linked_sb_router is not None

            # retrieve the corresponding router container
            router_container = self.sb_router_to_container[linked_sb_router]
            # link the ovs bridge and router container
            self.net.addLink(ovs_br, router_container)

            # first let's check if s has an index; create one if not
            if s not in self.sb_switch_to_OVSBridge_index:
                self.sb_switch_to_OVSBridge_index[s] = 0

            # bind net_if with its actual eth str name
            self.sb_switch_if_to_OVSBridge_if_name[switch_net_if_linked_to_router] = \
                CNAdapter.get_interface_name_in_containernet(
                    s.get_node_id(),
                    self.sb_switch_to_OVSBridge_index[s]
                )
            self.sb_router_if_to_container_if_name[linked_sb_router_if] = \
                CNAdapter.get_interface_name_in_containernet(
                    linked_sb_router.get_node_id(),
                    self.sb_router_to_container_if_index[linked_sb_router]
                )

            # increment if indexes
            self.sb_switch_to_OVSBridge_index[s] += 1
            self.sb_router_to_container_if_index[linked_sb_router] += 1

        #########################
        # host-switch linking
        #########################
        # populate the end host list
        for s in self.sandbox_switches:
            for sif in s.net_interfaces:
                n = sif.get_paired_interface().get_owner_node()
                if isinstance(n, Host):
                    self.sandbox_end_hosts.append(n)

        # create end host containers and
        # link them to the corresponding switches (ovs bridges)
        for h in self.sandbox_end_hosts:
            end_host_container = self.net.addDocker(
                h.get_node_id(), ip="",
                dimage=h.docker_image,
                cap_add=h.docker_caps
            )
            self.sb_host_to_container[h] = end_host_container
            # get the connected sb switch
            # TODO: we assume each end host has only one net_interface which is directly connected to the switch
            sb_switch = h.net_interfaces[0].get_paired_interface().get_owner_node()
            assert type(sb_switch) is Switch
            # get the OVS bridge
            ovs_bridge = self.sb_switch_to_OVSBridge[sb_switch]
            # link ovs_bridge with the end host container
            self.net.addLink(end_host_container, ovs_bridge)

            # create an index for the host
            if h not in self.sb_host_to_container_index:
                self.sb_host_to_container_index[h] = 0

            # bind net_if to actual eth name in containernet
            self.sb_host_if_to_container_if_name[h.net_interfaces[0]] = CNAdapter.get_interface_name_in_containernet(
                h.get_node_id(), self.sb_host_to_container_index[h]
            )
            self.sb_switch_if_to_OVSBridge_if_name[h.net_interfaces[0].get_paired_interface()] = \
                CNAdapter.get_interface_name_in_containernet(
                    sb_switch.get_node_id(),
                    self.sb_switch_to_OVSBridge_index[sb_switch]
                )

            # increment indexes
            self.sb_host_to_container_index[h] += 1
            self.sb_switch_to_OVSBridge_index[sb_switch] += 1

        # start net
        self.net.start()

        # config runtime
        self.runtime_config()

    #def __del__(self):
    #    self.net.stop()

    def runtime_config(self):
        #########################
        # router config
        #########################
        # create a Quagga config generator
        qcg: 'QuaggaConfigGenerator' = QuaggaConfigGenerator()

        # go through each router container and create zebra and bgpd config files
        for r, c in self.sb_router_to_container.items():
            net_ifs = []
            neighbors = []  # neighbor: {"ip": str, "asn": int}
            networks = [p.with_prefixlen for p in r.owner_as.prefixes]
            for net_if in r.router_to_router_net_interfaces:
                net_if_dict = {'name': self.sb_router_if_to_container_if_name[net_if],
                               'ip': net_if.get_ip_interface().ip.compressed,
                               'prefix_len': net_if.get_ip_interface().network.prefixlen}
                net_ifs.append(net_if_dict)

                # now build neighbor
                remote_if = net_if.get_paired_interface()
                # such jump much wow
                remote_if_ip = remote_if.get_ip_interface().ip.compressed
                remote_if_asn = remote_if.get_owner_node().owner_as.asn
                neighbor = {"ip": remote_if_ip, "asn": remote_if_asn}
                neighbors.append(neighbor)

            # turn off default nat interface provided by docker
            c.cmd("ifconfig eth0 0")

            # install zebra config
            zebra_conf_str = qcg.generate_zebra_config(r.node_id, net_ifs)
            cmd_install_zebra_conf = 'echo "{}" > /etc/quagga/zebra.conf'.format(zebra_conf_str)
            c.cmd(cmd_install_zebra_conf)
            c.waitOutput()
            # run zebra!
            c.cmd("zebra -f /etc/quagga/zebra.conf -d -i /tmp/zebra.pid -z /tmp/zebra.sock")

            # install bgpd config
            bgpd_config_str = qcg.generate_bgpd_config(node_id=r.node_id, asn=r.owner_as.asn,
                                                       networks=networks, neighbors=neighbors)
            cmd_install_bgpd_conf = 'echo "{}" > /etc/quagga/bgpd.conf'.format(bgpd_config_str)
            c.cmd(cmd_install_bgpd_conf)
            c.waitOutput()
            # run bgpd!
            c.cmd("bgpd -f /etc/quagga/bgpd.conf -d -i /tmp/bgpd.pid -z /tmp/zebra.sock")

            # now we set up the ips for end-host-facing interfaces
            for net_if in r.router_to_switch_net_interfaces:
                # we only run ifconfig if the interface has been created
                if net_if in self.sb_router_if_to_container_if_name:
                    ip_if = net_if.get_ip_interface()
                    eth_name = self.sb_router_if_to_container_if_name[net_if]
                    c.cmd("ip addr add {} dev {}".format(ip_if.with_prefixlen, eth_name))

        #########################
        # end host config
        #########################
        for net_if, eth_name in self.sb_host_if_to_container_if_name.items():
            sb_host = net_if.get_owner_node()
            host_container = self.sb_host_to_container[sb_host]
            # turn off default eth provided by docker
            host_container.cmd("ifconfig eth0 0")
            # add host ip to the right eth
            host_container.cmd("ip addr add {} dev {}".format(
                net_if.get_ip_interface().with_prefixlen,
                eth_name)
            )
            # set the default gateway for the end host
            # the gateway ip is end host's ip interface's network's second IP
            # e.g., an end host ip_interface: 1.1.1.200/25, the network is 1.1.1.128/25,
            # the second ip of the network is 1.1.1.129.
            # therefore, the gateway for the end host is 1.1.1.129
            host_container.cmd("ip route add default via {}".format(net_if.get_ip_interface().network[1]))


    @staticmethod
    def get_interface_name_in_containernet(node_id: str, container_interface_index: int):
        interface_template = "{}-eth{}"
        return interface_template.format(node_id, container_interface_index)

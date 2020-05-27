from typing import Dict, List
from ipaddress import ip_network, ip_address, ip_interface, IPv4Interface
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid cyclic import but we want type hinting
    from Topology.AutonomousSystem import AutonomousSystem


class NetworkInterface:
    _owner_node: 'Node'
    _paired_with: 'NetworkInterface'

    # e.g., 1.1.1.1/24, it contains both ip_address and some additional info, e.g., netmask
    # TODO: abstract it to support IPv6 in the future
    _ip_interface: 'IPv4Interface'

    # host_facing_interface: bool  # what is this good for?

    def __init__(self, owner: 'Node'):
        self._owner_node = owner

    def set_ip_interface(self, ip: 'IPv4Interface'):
        self._ip_interface = ip

    def get_ip_interface(self):
        return self._ip_interface

    def set_paired_interface(self, interface: 'NetworkInterface'):
        self._paired_with = interface

    def get_paired_interface(self):
        return self._paired_with

    def get_owner_node(self):
        return self._owner_node


class Node:
    node_id: str  # for managing nodes w/o IPs; using docker exec instead (linux namespace)
    owner_as: 'AutonomousSystem' = None  # the AS that owns this node
    net_interfaces: List['NetworkInterface']

    docker_image: str  # the docker image name to pull
    docker_cmds_to_run: List[str]
    docker_caps: List[str]  # assign container cap permissions

    def __init__(self, owner_as):
        self.owner_as = owner_as
        self.net_interfaces = []
        self.docker_caps = []

    def set_node_id(self, node_id: str):
        self.node_id = node_id

    def get_node_id(self):
        return self.node_id

    def add_network_interface(self, net_if: 'NetworkInterface'):
        self.net_interfaces.append(net_if)

    def is_ready(self):
        print("[ERROR] node class: {} has not implemented its is_ready function yet.".format(
            self.__class__.__name__))
        exit(-1)  # TODO: we should have some meaningful error code assignment


class Switch(Node):
    # TODO: before we understand how to control OVS from a docker container,
    # let's just implement switches by using the in-kernel OVSBridge in mininet.
    def __init__(self, owner_as):
        super().__init__(owner_as)


class Router(Node):
    router_to_router_net_interfaces: List['NetworkInterface']
    router_to_switch_net_interfaces: List['NetworkInterface']

    def __init__(self, owner_as):
        super().__init__(owner_as)
        self.docker_caps = ["ALL"]  # just give router nodes all cap permissions.
        self.router_to_router_net_interfaces = []
        self.router_to_switch_net_interfaces = []

    def add_router_to_router_network_if(self, net_if):
        self.add_network_interface(net_if)
        self.router_to_router_net_interfaces.append(net_if)

    def add_router_to_switch_network_if(self, net_if):
        self.add_network_interface(net_if)
        self.router_to_switch_net_interfaces.append(net_if)


class BoringRouter(Router):
    docker_image = "ddos-sandbox:quagga-ubuntu"

    def __init__(self, belong_to_as):
        super().__init__(belong_to_as)

    def _populate_quagga_bgpd_conf(self):
        pass

    def _populate_quagga_zebra_conf(self):
        pass


class Host(Node):
    _ready: bool = False
    docker_image = "ddos-sandbox:endhost-ubuntu"

    def __init__(self, owner_as):
        super().__init__(owner_as)
        self.docker_caps = ["NET_ADMIN"]
        # create one interface per host

        # init cmds to execute in docker container

    def is_ready(self):
        # a list of state to check before calling the containernet
        pass

    def execute(self):
        cmds_to_execute = []
        pass


class TMAgent(Host):
    docker_image = "ddos-sandbox:endhost-tmagent-ubuntu"

    def __init__(self, owner_as):
        super().__init__(owner_as)


class TMDispatcher(Host):
    _ready: bool = False
    docker_image = "ddos-sandbox:dispatcher"

    def __init__(self, owner_as):
        super().__init__(owner_as)

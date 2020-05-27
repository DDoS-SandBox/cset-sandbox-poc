from typing import Set, Dict, List, Type
from ipaddress import ip_network, IPv4Interface, IPv4Network

from .Config import ASTopoGenMode
from .Node import Router, BoringRouter, Host, NetworkInterface, Switch


class AutonomousSystem:
    asn: int  # the ASN of this AS
    prefixes: List['ip_network']  # what are the prefixes belong to this AS
    routers: List['Router']  # maintain a list of routers that this AS owns
    neighbor_to_router: Dict[int, 'Router']  # to check whether a neighbor has been connected via a router link
    neighbors: Dict[int, 'AutonomousSystem']  # asn: as obj

    # we must further split the ownership of the AS's prefixes down to router level
    __end_host_prefix_to_router_map: Dict['IPv4Network', 'Router']

    # IP prefixes from the prefixes owned by this AS and use them for end-host-facing connections
    end_host_network_pool: List['IPv4Network']
    # put used up end host networks here
    __used_end_host_network_pool: List['IPv4Network']
    # put used end host IPs here
    __used_end_host_ip_pool: Set[str]
    # save current end host network index
    __curr_end_host_network_index: int
    __curr_end_host_network: 'IPv4Network'

    # IP prefixes from the prefixes owned by this AS and use them for router-to-router connections
    router_network_pool: List['IPv4Network']

    topo_gen_mode: 'ASTopoGenMode'  # how to generate internal router-level topology

    # router_to_router_IPs = Dict[str, bool]  # key: IP, value: whether it has been assigned

    # TODO: need better ways to handle end host creation
    end_hosts: List['Host']
    switches: List['Switch']

    def __init__(self, asn: int, prefixes: List[str], topo_gen_mode: ASTopoGenMode):
        """
        Do not use the default constructor unless you know what you are doing.
        See the definition of each var below above
        """
        self.asn = asn
        self.prefixes: List['IPv4Network'] = [IPv4Network(p) for p in prefixes]
        self.topo_gen_mode = topo_gen_mode
        self.routers = []
        self.end_hosts = []
        self.switches = []
        self.neighbors = {}
        self.neighbor_to_router = {}
        self.end_host_network_pool = []
        self.__used_end_host_network_pool = []
        self.__used_end_host_ip_pool = set()
        self.__curr_end_host_network_index = 2
        self.__curr_end_host_network = None
        self.router_network_pool = []
        self.__end_host_prefix_to_router_map = {}

        # TODO: ADDRESS ALL THE ASSUMPTIONS BELOW!!!
        # keep track of where we are in IP assignment
        # I am not sure if all linux support .0 IPs
        # arbitrary skipping here. not all subnets start with .0 IPs
        # also, not taking into broadcasting .255 IPs into account (assume it does not happen)
        # skip .0 and .1 IPs; assign .1 as the gateway IP
        # self.end_host_ip_index = 2
        # again, skip .0 and .1,
        self.router_ip_index = 2

    @classmethod
    def create_one_router_as(cls, asn: int, prefixes: List[str]):
        """
        Construct an AS with one router only

        @rtype: AutonomousSystem
        """
        autonomous_system = cls(asn, prefixes, ASTopoGenMode.ONE_ROUTER)
        return autonomous_system

    @classmethod
    def create_with_real_topology(cls, asn: int, prefixes: List[str], topo):
        """
        Construct an AS with real topology information --- make sure your input topology has no loopholes.

        @rtype: AutonomousSystem
        """
        # TODO

    @classmethod
    def create_with_partial_knowledge(cls, asn: int, prefixes: List[str], partial_topo):
        """
        Construct an AS with partial topo knowledge

        @rtype: AutonomousSystem
        """
        # TODO

    def allocate_network_prefix_pool(self):
        # WE ALLOCATE SUFFICIENT AMOUNT OF IPS FOR ROUTER-TO-ROUTER CONNS
        # AND THE REST OF THE IPS BELONG TO END HOSTS

        # Step 1: we get the number of router-to-router links this as has
        # TODO: the following method will over allocate IPs but it is better than nothing
        #       THE FUNC. COULD BE BETTER STILL
        rr_link_num = 0
        for router in self.routers:
            rr_link_num += len(router.router_to_router_net_interfaces)
        rr_link_num += len(self.neighbors)

        # Step 2: we pick a prefix that this AS owns that is large enough to cover rr_link_num,
        # we then split the prefix into smaller subnets that is just enough to cover rr_link_num.
        prefix_to_split = None
        for p in self.prefixes:
            # check how many pairs of IPs that p has
            if (p.num_addresses / 2) > rr_link_num:
                prefix_to_split = p
                break

        # We assume there is A prefix that is large enough to cover rr_link_num
        # If not, the program ends
        assert prefix_to_split is not None

        # Step 3: we add all prefixes except prefix_to_split to endhost_network_pool
        for p in self.prefixes:
            if p != prefix_to_split:
                self.end_host_network_pool.append(p)

        # Step 4: we split prefix_to_split when each of its two children prefixes
        # are still enough to cover rr_link_num, which is (prefix_to_split.num_addresses / 4)
        while (prefix_to_split.num_addresses / 4) > rr_link_num:
            l_subnet, r_subnet = prefix_to_split.subnets()
            # add the left subnet to endhost prefix pool
            self.end_host_network_pool.append(l_subnet)
            # set the right subnet as the new prefix_to_split
            prefix_to_split = r_subnet

        # Step 5: add prefix_to_split to router_network_pool
        self.router_network_pool.append(prefix_to_split)

        # Step 6: populate the initial iter for end host networks
        self.__new_end_host_network_to_use()

    def assign_end_host_prefixes_to_router(self):
        if self.topo_gen_mode == ASTopoGenMode.ONE_ROUTER:
            router = self.routers[0]  # since only one router per as, the router gets all the prefixes
            for e_n in self.end_host_network_pool:
                self.__end_host_prefix_to_router_map[e_n] = router
        else:  # TODO: implement other topogen modes
            print("only one router topo mode is implemented right now.  quitting.")
            exit(-1)
            pass

    def __new_end_host_network_to_use(self):
        for n in self.end_host_network_pool:
            # for now, let's ignore all the small networks such as /30, /31...
            if n.num_addresses <= 8:
                self.__used_end_host_network_pool.append(n)
                continue
            if n not in self.__used_end_host_network_pool:
                self.__curr_end_host_network = n
                self.__used_end_host_network_pool.append(n)
                # to avoid .0 IPs
                # even if the first ip is not .0, we want to reserve the second IP as the end host gateway IP
                # e.g., we don't use 1.1.1.0 as an IP, we use 1.1.1.1 as an end host's gateway IP
                # so really, end host IP range starts from 1.1.1.2 in this example.
                self.__curr_end_host_network_index = 2
                break

    def get_an_available_end_host_ip_interface(self) -> 'IPv4Interface':
        # check if we need to get a new end host network to use
        curr_end_host_network_size = self.__curr_end_host_network.num_addresses
        if self.__curr_end_host_network_index + 1 >= curr_end_host_network_size:
            self.__new_end_host_network_to_use()
        end_host_ip = self.__curr_end_host_network[self.__curr_end_host_network_index]
        end_host_ip_interface = IPv4Interface("{}/{}".format(end_host_ip.compressed,
                                                             self.__curr_end_host_network.prefixlen))
        self.__used_end_host_ip_pool.add(end_host_ip.compressed)
        self.__curr_end_host_network_index += 1
        return end_host_ip_interface

    def add_end_host(self, ip: str = None, host: Type[Host] = Host):
        # STEP 0: generate an IP if ip == None
        host_ip_if = None
        if ip is None:
            host_ip_if = self.get_an_available_end_host_ip_interface()
        elif ip in self.__used_end_host_ip_pool:
            print("end host ip was already assigned.  check your input.")
            exit(-1)
        else:
            # TODO: handle how to use user provided IPs
            print("end host ip was provided but the code is not implemented to handle this.")
            exit(-1)

        # STEP 1: find the router that owns the host_ip
        router = None
        for p, r in self.__end_host_prefix_to_router_map.items():
            if host_ip_if in p:
                router = r
        assert router is not None

        # STEP 2: get the corresponding switch to connect the end host
        switch = None
        # try to find a switch that is responsible for the host_ip
        for local_if in router.router_to_switch_net_interfaces:
            ip_if = local_if.get_ip_interface()
            # if we find a router's interface is the gateway for this host_ip
            # we return it's connected switch
            if host_ip_if in ip_if.network:
                paired_if = local_if.get_paired_interface()
                # the owner of this paired interface must be a switch
                switch = paired_if.get_owner_node()
                assert type(switch) is Switch
                break

        # if we cannot find a switch, we create one
        if switch is None:
            switch = Switch(self.asn)
            switch.set_node_id("a{}s{}".format(self.asn, len(self.switches)))
            self.switches.append(switch)
            # create a pair of interfaces; one for switch, one for router
            router_interface = NetworkInterface(owner=router)
            switch_interface = NetworkInterface(owner=switch)
            # pair two interfaces
            router_interface.set_paired_interface(switch_interface)
            switch_interface.set_paired_interface(router_interface)
            # add the interfaces to their corresponding owner
            router.add_router_to_switch_network_if(router_interface)
            switch.add_network_interface(switch_interface)

            # set ip interface for router_interface
            # we always use the second IP of an end-host-facing prefix as the end host's gateway
            host_ip_network = host_ip_if.network
            router_ip_interface = IPv4Interface("{}/{}".format(
                host_ip_network[1].compressed, host_ip_network.prefixlen))
            router_interface.set_ip_interface(router_ip_interface)

        # STEP 3: create a host and attach it to the switch
        end_host = host(self.asn)
        # set node id: asn+len(end_hosts)
        end_host.set_node_id("a{}h{}".format(self.asn, len(self.end_hosts)))
        # create a pair of interfaces; one for switch, one for end host
        switch_interface = NetworkInterface(owner=switch)
        end_host_interface = NetworkInterface(owner=end_host)
        # pair two interfaces
        switch_interface.set_paired_interface(end_host_interface)
        end_host_interface.set_paired_interface(switch_interface)
        # add the interfaces to their corresponding owner
        end_host.add_network_interface(end_host_interface)
        switch.add_network_interface(switch_interface)
        # set ip interface of end_host net interface
        end_host_interface.set_ip_interface(host_ip_if)

        # STEP 4: add end host to end host list
        self.end_hosts.append(end_host)

    def link_neighbors(self):
        # TODO: decide how to create internal topology
        # TODO: THINK! How to decide which router connects to which router at which AS
        # TODO: need a place to set which router class to use
        #       let's just be lazy for now
        for asn, as_obj in self.neighbors.items():
            self._ask_as_for_router_to_connect_to(as_obj)

    def _get_router_network_interface_pair(self) -> ('IPv4Interface', 'IPv4Interface'):
        # TODO: IPV6?

        # STEP 1: find the right ip_network obj to use in the router_network_pool (which is a list)

        router_ip_coverage = 0
        prefix_to_use = None
        for p in self.router_network_pool:
            router_ip_coverage += p.num_addresses
            if self.router_ip_index + 2 <= router_ip_coverage:
                prefix_to_use = p

        assert prefix_to_use is not None

        # STEP 2: now we create an ip_interface pair
        ip_interface_1 = IPv4Interface('{}/31'.format(prefix_to_use[self.router_ip_index - router_ip_coverage]))
        ip_interface_2 = IPv4Interface('{}/31'.format(prefix_to_use[self.router_ip_index + 1 - router_ip_coverage]))

        # STEP 3: increment AS's router ip assignment index by 2
        self.router_ip_index += 2

        # And we return the ip interfaces
        return ip_interface_1, ip_interface_2

    def _ask_as_for_router_to_connect_to(self, as_to_request: 'AutonomousSystem'):
        # we assume there is no loops in AS paths
        # only ask an as to connect once
        if as_to_request.asn in self.neighbor_to_router:
            return
        # call the neighboring AS for a router to connect with
        router_to_connect_with = as_to_request._return_as_a_router_for_it_to_connect(self)
        assert router_to_connect_with is not None

        if self.topo_gen_mode == ASTopoGenMode.ONE_ROUTER:
            if not len(self.routers):
                r = BoringRouter(self)  # create a router with self.asn
                self.routers.append(r)
                r.set_node_id("a{}r{}".format(self.asn, len(self.routers) - 1))
            self.neighbor_to_router[as_to_request.asn] = router_to_connect_with
            # make network interface pair for the two routers
            local_router_interface = NetworkInterface(owner=self.routers[0])
            remote_router_interface = NetworkInterface(owner=router_to_connect_with)
            # pair the two router (eth) interfaces together
            local_router_interface.set_paired_interface(remote_router_interface)
            remote_router_interface.set_paired_interface(local_router_interface)
            # get ip interfaces for the two router (eth) interfaces
            local_router_ip_interface, remote_router_ip_interface = self._get_router_network_interface_pair()
            local_router_interface.set_ip_interface(local_router_ip_interface)
            remote_router_interface.set_ip_interface(remote_router_ip_interface)
            # add the net interfaces to routers
            self.routers[0].add_router_to_router_network_if(local_router_interface)
            router_to_connect_with.add_router_to_router_network_if(remote_router_interface)
        else:  # TODO: implement other topo gen mode
            print("Other topology generation modes have not been implemented yet")
            exit(-1)

    def _return_as_a_router_for_it_to_connect(self, requesting_as: 'AutonomousSystem') -> 'Router':
        requesting_asn = requesting_as.asn
        # check who's requesting; do not make redundant requests pls.
        if requesting_asn in self.neighbor_to_router:
            return None

        # if no router obj yet, create one.
        # TODO: get the appropriate router using partial or custom info
        #       (done) if it's one router topo, return the only router
        if self.topo_gen_mode == ASTopoGenMode.ONE_ROUTER:
            if not len(self.routers):
                r = BoringRouter(self)  # create a router with self.asn
                self.routers.append(r)
                r.set_node_id("a{}r{}".format(self.asn, len(self.routers) - 1))
                self.neighbor_to_router[requesting_asn] = self.routers[0]
            return self.routers[0]
        else:
            print("Other topology generation modes have not been implemented yet")
            exit(-1)

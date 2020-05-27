from typing import Dict, List, Type
from Topology.AutonomousSystem import AutonomousSystem
from Topology.Node import Host
from Topology.Config import ASTopoGenMode
from Driver.CNAdapter import CNAdapter
import time
import json
import signal
import sys

####################################################
# feed the following info from
#   the script output we implemented.
####################################################
with open('topology-data/as_path_list.json', 'r') as f:
    as_level_paths = json.load(f)

with open('topology-data/as_to_prefix.json', 'r') as f:
    as_to_prefixes = json.load(f)

class TopoGenerator:
    as_dict: Dict[int, 'AutonomousSystem']

    def __init__(self, as_paths: List[List[int]],
                 as_to_prefixes: Dict[int, List],
                 topo_gen_mode: 'ASTopoGenMode'):

        self.as_paths = as_paths
        self.as_to_prefixes = as_to_prefixes
        self.topo_gen_mode = topo_gen_mode
        self.as_dict = {}

        # create all ASes and feed each AS the basic prefix and neighboring relationships: 90%
        self.__create_as_topo()

        # assign router(s) to each AS: 70%
        self.__populate_routers_at_each_as()

        # assign end hosts(s) to each AS: 80%
        self.__assign_end_host_prefixes_to_routers_at_each_as()

        # push the logic into containernet: 60%

        # run each node's start script: 30%

        # done.

    @classmethod
    def create_via_trace(cls, trace, topo_gen_mode: 'ASTopoGenMode'):
        # TODO: process trace to infer and generate as_paths and as_to_prefixes.
        pass

    def __create_as_topo(self):
        # Iterate through all AS paths
        for as_path in self.as_paths:
            # Construct and link ASes
            as_path_len = len(as_path)
            assert as_path_len > 1  # each as path should be at least 2-node long

            for a_i in range(0, as_path_len):
                asn_1 = int(as_path[a_i])
                asn_2 = int(as_path[a_i + 1])

                if self.topo_gen_mode == ASTopoGenMode.ONE_ROUTER:
                    if asn_1 not in self.as_dict:
                        prefix_1 = self.__get_as_prefixes(asn_1)
                        self.as_dict[asn_1] = AutonomousSystem.create_one_router_as(asn_1, prefix_1)
                    if asn_2 not in self.as_dict:
                        prefix_2 = self.__get_as_prefixes(asn_2)
                        self.as_dict[asn_2] = AutonomousSystem.create_one_router_as(asn_2, prefix_2)
                elif self.topo_gen_mode == ASTopoGenMode.PARTIAL_INFO:
                    # TODO: handle partial topo
                    pass
                elif self.topo_gen_mode == ASTopoGenMode.CUSTOM:
                    # TODO: handle custom topo
                    pass

                # make sure both ASes have each other as its own neighbor
                if self.as_dict[asn_1].asn not in self.as_dict[asn_2].neighbors:
                    self.as_dict[asn_2].neighbors[self.as_dict[asn_1].asn] = self.as_dict[asn_1]
                if self.as_dict[asn_2].asn not in self.as_dict[asn_1].neighbors:
                    self.as_dict[asn_1].neighbors[self.as_dict[asn_2].asn] = self.as_dict[asn_2]

                # break the loop if we have processed all ASes in the path; we have a runner pointer
                if (a_i + 1 + 1) == as_path_len:
                    break

        # now ask each AS to allocate network prefixes
        for asn, as_obj in self.as_dict.items():
            as_obj.allocate_network_prefix_pool()

    def __populate_routers_at_each_as(self):
        for as_obj in self.as_dict.values():
            as_obj.link_neighbors()

    def __assign_end_host_prefixes_to_routers_at_each_as(self):
        for as_obj in self.as_dict.values():
            as_obj.assign_end_host_prefixes_to_router()

    def add_end_host(self, asn: int, ip: str, end_host_cls: Type['Host']):
        as_obj = self.as_dict[asn]
        assert (as_obj is not None)
        as_obj.add_end_host(ip, end_host_cls)

    def __get_as_prefixes(self, asn: int) -> List:
        # Fow now, use a toy example for lookup as prefixes.
        # TODO: get prefixes from actual as to prefix database
        #       we probably need to filter out unrelated prefixes for the experiment
        #       if they are not related to the network in interest
        # had to turn asn to str as python's json keys are strings
        return as_to_prefixes[asn]


if __name__ == '__main__':
    # a simple test: we feed 20 AS paths
    tg = TopoGenerator(as_level_paths[0:20], as_to_prefixes, ASTopoGenMode.ONE_ROUTER)
    as_12145 = tg.as_dict[12145]
    as_12145.add_end_host()

    start_time = time.time()
    adapter = CNAdapter(list(tg.as_dict.values()))
    print("Spent {} seconds to create the sandbox environment".format(time.time() - start_time))
    print("Emulation environment instantiated. There are {} ASes".format(len(tg.as_dict)))
    print("To exit the program, press Ctrl+D.")

    from mininet.cli import CLI
    CLI(adapter.net)

    print("Exiting the program... please wait.")
    adapter.net.stop()


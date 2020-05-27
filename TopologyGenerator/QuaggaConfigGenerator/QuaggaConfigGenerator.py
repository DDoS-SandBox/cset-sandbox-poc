from typing import Dict, List
import inspect
import os
import jinja2


class QuaggaConfigGenerator:
    zebra_template_filename = "zebra.conf.j2"
    bgpd_template_filename = "bgpd.conf.j2"

    def __init__(self):
        file_path = inspect.getfile(self.__class__)
        dir_path = os.path.dirname(file_path)
        self.env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=dir_path))
        self.zebra_template = self.env.get_template(self.zebra_template_filename)
        self.bgpd_template = self.env.get_template(self.bgpd_template_filename)

    def generate_zebra_config(self, node_id: str, net_ifs: List):
        zebra_config = {'hostname': node_id, 'password': "leet", 'interfaces': net_ifs, 'log_file': None}
        # print("Rendering zebra.conf template...")
        return self.zebra_template.render(zebra_config)

    def generate_bgpd_config(self, node_id: str, asn: int, networks: List, neighbors: List):
        bgpd_config = {'hostname': node_id, 'password': "leet",
                       'asn': asn, 'networks': networks, 'neighbors': neighbors}
        return self.bgpd_template.render(bgpd_config)

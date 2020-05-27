# THIS PROGRAM TAKES THE INFERRED AS TOPOLGY FROM MINGWEI'S PROGRAM.
# THERE ARE MULTIPLE AS PATHS FROM ONE ASN TO ANOTHER, WE SELECT THE SHORTEST AS PATH.
# WE THEN OUTPUT THE AS-LEVEL TOPOLGOY AND PREFIXES OWNED BY EACH AS.

import pyasn
import json

# INITIALIZE MODULE AND LOAD IP TO ASN DATABASE
ip_asn_data_path = "data/rib.20200518.0000.ipasn_db"
# THE SAMPLE DATABASE CAN BE DOWNLOADED OR BUILT - SEE BELOW
print("loading ipasn db")
asndb = pyasn.pyasn(ip_asn_data_path)
print("ipasn db loaded")

# READ RAW AS PATHS
as_topo_path = "output/relevent-as-paths.txt"
shortest_path_dict = dict() # {"123,456": [123,1,2,3,456], "123, 888": [123,1,7,888],...}

with open(as_topo_path) as as_topo_file:
    as_path_list = as_topo_file.read().splitlines()
    for as_path_str in as_path_list:
        as_path = list(map(int, as_path_str.split(",")))
        asn_local = as_path[0]
        asn_remote = as_path[-1]
        #print(as_path)
        #print("local:{}, remote:{}".format(asn_local, asn_remote))
        lookup_key = "{},{}".format(asn_local, asn_remote)

        # KEEP ONLY THE SHORTEST VERSION OF EACH ASN-to-ASN
        if lookup_key in shortest_path_dict:
            if len(shortest_path_dict[lookup_key]) > len(as_path):
                shortest_path_dict[lookup_key] = as_path
        else:
            shortest_path_dict[lookup_key] = as_path

#print(shortest_path_dict["12145,10000"])

# KEEP only as paths that are at most n hops
max_as_len = 6
filtered_shortest_path_list = list() # {"123,456": [123,1,2,3,456], "123, 888": [123,1,7,888],...}
for key, as_path in shortest_path_dict.items():
    if len(as_path) <= max_as_len:
        filtered_shortest_path_list.append(as_path)
print("num of as paths after filtering:{}".format(len(filtered_shortest_path_list)))

# GET THE PREFIXES FOR EACH ASN
as_to_prefix_dict = dict() # {123: [[1.1.1.0/24, 1.1.2.0/24]], 1: [[2.2.2.0/24, 8.0.0.0/8]], ...}
for as_path in filtered_shortest_path_list:
    for asn_str in as_path:
        asn = int(asn_str)
        if asn not in as_to_prefix_dict and asndb.get_as_prefixes(asn) is not None:
            as_to_prefix_dict[asn] = list(asndb.get_as_prefixes(asn))

# NOW WE OUTPUT THE DISTILLED RESULT
# OUTPUT filtered_shortest_path_list
with open('output/as_path_list.json', 'w', encoding='ascii') as f:
    json.dump(filtered_shortest_path_list, f, ensure_ascii=True)

# OUTPUT as_to_prefix_dict
with open('output/as_to_prefix.json', 'w', encoding='ascii') as f:
    json.dump(as_to_prefix_dict, f, ensure_ascii=True)


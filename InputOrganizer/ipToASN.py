import sys
import pandas as pd
import ipaddress

# Sometimes an IP can be within the range of two ASes (possibly some bug in the IP to AS database)
# This function chooses one of the ASes (the one that advertises the smallest IP prefix range)
def pick_smallest(asn):
    if isinstance(asn, pd.Series) == True:
        return asn.to_string().split(" ")[-1]
    else:
        return asn

# Removes unnecessary characters from AS name
def beautify(name):
    if isinstance(name, pd.Series) == True:
        name = name.to_string()
        listname = name.split(" - ")
    else:
        listname = name.split(" - ")
        listname = listname[-1].split("-BKB ")
        listname = listname[-1].split("-KR ")
        listname = listname[-1].split("-AP ")
        listname = listname[-1].split("-AS ")
    return listname[-1]

# Check arguments
if len(sys.argv) <= 3 or len(sys.argv) > 4:
    print("Error: Need to specify correct parameters -> iptoAS.py [IP_to_AS_database] [input_list_of_IPs] [output]")
    exit(1)

# First argument is the IP to AS database
# Second argument is the list of IPs
# Third argument is the output file (IP | ASN | AS Name)
databaseFile = sys.argv[1]
inputFile = sys.argv[2]
outputFile = sys.argv[3]

# Use pandas to read in files
ipasnDB = pd.read_csv(databaseFile, sep='\t', header=None, engine="python")
#ipInput = pd.read_csv(inputFile, sep=',', header=None, engine="python")
ipInput = pd.read_csv(inputFile, sep='\n', header=None, engine="python")

# Only works for ip2asn-v4.tsv file from https://iptoasn.com/
# Need to change this if you are using another IP-to-ASN database
ipasnDB["IP Range Start"] = ipasnDB[0]
ipasnDB["IP Range End"] = ipasnDB[1]
ipasnDB["ASN"] = ipasnDB[2]
ipasnDB["Region"] = ipasnDB[3]
ipasnDB["AS Name"] = ipasnDB[4]
# Convert IPs into integers to easily check if an IP is within the range
ipasnDB["int start"] = ipasnDB["IP Range Start"].map(ipaddress.ip_address).map(int)
ipasnDB["int end"] = ipasnDB["IP Range End"].map(ipaddress.ip_address).map(int)

# Set up output table and convert input IPs into integers
ips = ipInput
ips.columns = ["IP"]
ips.drop_duplicates(inplace=True)
ips["int"] = ips["IP"].map(ipaddress.ip_address).map(int)
ips["ASN"] = ""
ips["AS Name"] = ""

# Check if input IP is within an IP prefix range of an AS in the database
# If so, set ASN and AS Name of input IP to match the AS
ipasnDB.index = pd.IntervalIndex.from_arrays(ipasnDB["int start"], ipasnDB["int end"], closed='both')
ips["ASN"] = ips["int"].apply(lambda x: ipasnDB.iloc[ipasnDB.index.get_loc(x)]["ASN"])
ips["AS Name"] = ips["int"].apply(lambda x: ipasnDB.iloc[ipasnDB.index.get_loc(x)]["AS Name"])
ips.drop(columns=["int"], inplace=True)
ips["ASN"] = ips["ASN"].apply(pick_smallest)
ips["AS Name"] = ips["AS Name"].apply(beautify)

# Write output file
sep = ","
header = True
ips.to_csv(outputFile, sep=sep, header=header, index=None, columns=['ASN'])


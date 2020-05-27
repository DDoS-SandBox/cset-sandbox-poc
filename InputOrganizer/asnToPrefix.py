import pyasn

ip_asn_data_path = "data/ipasn_20200416.dat"

# Initialize module and load IP to ASN database
# the sample database can be downloaded or built - see below
print("loading ipasn db")
asndb = pyasn.pyasn(ip_asn_data_path)
print("ipasn db loaded")

print(asndb.get_as_prefixes(12145))
print(type(asndb.get_as_prefixes(12145)))


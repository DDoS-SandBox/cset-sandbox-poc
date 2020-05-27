#!/bin/bash

dataFolder="data"
outputFolder="output"

# STEP 1
# define the ASN for generating an inferred AS-level topology
asn=""
# define the local network that you want to monitor and emulate.
ip_range_regex="" # e.g., 192\.168\.[0-9]*\.[0-9]*
# define sflow agent listening port
sflow_port=8777

# STEP 2
# the following cmd outputs time, s_ip, and d_ip of a local net to a file
# note that the latest sflowtool should be used
step2out_tmp=$outputFolder"/step2out-tmp.txt"
step2out=$outputFolder'/step2out.txt'
monitor_time_sec=60
timeout $monitor_time_sec sflowtool -p $sflow_port -L unixSecondsUTC,srcIP,dstIP | grep -w $ip_range_regex > $step2out_tmp
sed '$d' $step2out_tmp > $step2out
rm -f $step2out_tmp

# STEP 3
# the following cmd pipe the content of above output, filters out all local netnetwork IPs, outputs non local network IPs to a file
step3out=$outputFolder'/step3out.txt'
cat $step2out | awk -F',' '{print $2;}{print $3;}' | grep -w $ip_range_regex -v | sort | uniq > $step3out

# STEP 4
# now, we 'reduce' the unique IPs from the above step to the unique ASNs
# SLACK ALERT: the following process is not the best approach.
step4_1out=$outputFolder'/step4-1out.txt'
step4_2out=$outputFolder'/step4-2out.txt'
python3 ipToASN.py $dataFolder"/ip2asn-v4.tsv" $step3out $step4_1out
cat $step4_1out | sort | uniq > $step4_2out

# STEP 5
# infer all paths towards $asn
# note that the asTopology program outputs all possible path from src asn to dest asn
# inferASTopo is a binary compiled from asTopology code; it applies valley-free routing
step5out=$outputFolder'/relevent-as-paths.txt'
./asTopology_mac -data "$dataFolder/20200101.as-rel.txt.bz2" $asn
# unzip the gzip file
gzip -d "paths/$asn""-paths.txt.gz"
while read src_asn; do cat "paths/$asn""-paths.txt" | grep ",$src_asn$"; done < $step4_2out > $step5out

# STEP 6
# output filtered as topology and network prefix information
python3 distill.py 

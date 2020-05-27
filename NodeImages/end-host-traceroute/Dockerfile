FROM ubuntu:bionic

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    telnet telnetd \
    iperf netcat \ 
    python3 python3-pip traceroute\
    vim tmux tcpdump

CMD /bin/bash


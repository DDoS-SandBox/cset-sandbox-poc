FROM ubuntu:bionic

RUN apt-get update && apt-get install -y \
    net-tools \
    iputils-ping \
    iproute2 \
    telnet telnetd \
    iperf  traceroute \ 
    quagga \
    vim tmux tcpdump

# a workaround for quagga to create vtysh sock
RUN mkdir -p /run/quagga && chown quagga:quagga /run/quagga

CMD /bin/bash


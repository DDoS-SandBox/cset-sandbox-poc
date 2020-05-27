# DDoS SandBox Proof of Concept

To set up a basic emulation environment with reference routers and end hosts,
please take the following steps:

* Install containernet, https://containernet.github.io/
* Build both end host and router node images in the NodeImages folder.
* cd to TopologyGenerator folder, and type `sudo python3 TopoGenerator.py`.
* You should have a mini BGP network running with 30 ASes.

InputOrganizer folder contains a bunch of small programs for generating AS-level topology and prefix information.
You do not need to run them for the above test.


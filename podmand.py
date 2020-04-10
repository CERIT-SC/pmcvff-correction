#!/usr/bin/env python3

import os
import socket
import sys

socket_path = "work/podmand.sock"
orca = os.environ['HOME'] + "/magicforcefield-pipeline/orca-docker"
gromacs = os.environ['HOME'] + "/magicforcefield-pipeline/gromacs-plumed-docker/gromacs/gmx-docker"

server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
	os.remove(socket_path)
except FileNotFoundError:
	pass

server.bind(socket_path)
server.listen()

while True:
    conn,_addr = server.accept()
    cmd = conn.recv(1024).decode('utf-8')
    if not cmd:
            break
    else:
        parsed_cmd = cmd.split(" ", 3)
        print(parsed_cmd)
        if parsed_cmd[0] == "gromacs":
            os.system("cd /tmp; " + gromacs + " ".join(parsed_cmd[1:]))
        elif parsed_cmd[0] == "orca":
            if parsed_cmd[1] == "am1" or parsed_cmd[1] == "bp86":
                #tst = "cd /tmp; " + orca + " " + " ".join(parsed_cmd[3:]) + " > " + os.environ['WORK'] + "/orca_output/{}/orca_output{}.log ".format(parsed_cmd[1], parsed_cmd[2])
                #print(tst)
                
                os.system("cd /tmp; " + orca + " " + " ".join(parsed_cmd[3:]) + " > " + os.environ['WORK'] + "/orca_output/{}/orca_output{}.log ".format(parsed_cmd[1], parsed_cmd[2]))
        else:
            conn.send("error choosing between containers".encode('utf-8'))
        conn.send("done".encode('utf-8'))
		

server.close()
os.remove(socket_path)


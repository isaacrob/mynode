#! /usr/bin/env python

import socket, sys, select, time, paramiko
import netifaces as ni
from subprocess import call

bport=5555

def findtornodes():
	config=paramiko.SSHConfig()
	config.parse(open("/root/.ssh/config"))

	myonionfile=open("/var/lib/tor/cluster/hostname","r")
	myonion=myonionfile.read().split("\n")[0]
	myonionfile.close()
	print("I am: "+myonion)
	
	otheronionsfile=open("/root/scripts/known_nodes","ra")
	otheronions=otheronionsfile.read().split("\n")
	if '' in otheronions:
		otheronions.pop(otheronions.index(''))
	totalonionlist=set(otheronions+[myonion])
	onionstocheck=otheronions
	newonions=[]
	workingonions=[]
	while len(onionstocheck)>0:
		for onion in onionstocheck:
			if len(onion)>3:
				print("connecting to: "+onion)
				c=paramiko.SSHClient()
				c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
				proxy=paramiko.ProxyCommand(config.lookup(onion)["proxycommand"])
				try:
					c.connect(onion,username="root",password="raspberry",sock=proxy,banner_timeout=10.0)
					workingonions.append(onion)
				except paramiko.ssh_exception.SSHException:
					print("error connecting to onion, moving on")
					continue
				print("success")
				totalonionlist.add(onion)
				trans=c.get_transport()
				sftp=paramiko.SFTPClient.from_transport(trans)
				#sftp=c.open_sftp()
				print("getting remote onions")
				remoteonionsfile=sftp.open("/root/scripts/known_nodes")
				remoteonions=remoteonionsfile.read().split("\n")
				remoteonionsfile.close()
				sftp.close()
				for newonion in remoteonions:
					if not newonion in totalonionlist and not newonion=='':
						newonions.append(newonion)
						print("found new onion: "+newonion)
				c.close()
			else:
				break
		onionstocheck=newonions
		newonions=[]
	print("found all available onions")
	print("onions found: "+str(totalonionlist))
	#will only write found onions for the next search
	#this is because some onions may simply cease to be part of the system
	#this allows for a more dynamic system, albiet with the chance of missing a fringe node
	#remember this only appends so this stops duplicates
	for onion in totalonionlist:
		if onion not in otheronions:
			otheronionsfile.write(onion+"\n")
	otheronionsfile.close()

	#copy file to other nodes
	source="/root/scripts/known_nodes"
	destination="/root/scripts/known_nodes"
	for onion in workingonions:
		c=paramiko.SSHClient()
		c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                proxy=paramiko.ProxyCommand(config.lookup(onion)["proxycommand"])
		c.connect(onion,username="root",password="raspberry",sock=proxy,banner_timeout=10.0)
		trans=c.get_transpot()
		sftp=paramiko.SFTPClient.from_transport(trans)
		sftp.put(source,destination)
		sftp.close()
		c.close()

	return totalonionlist

def fixcloneproblems():
	#now irrelevant from bash script "startup"
	ifaces=ni.interfaces()
	if "eth1" in ifaces:
		print("this node needs to be reformatted")
		call(['rm','/etc/udev/rules.d/70-persistent-net.rules'])
		call(['rm','-rf','/var/lib/tor/cluster'])
		call(['rm','-rf','/var/lib/tor/virtcluster'])
		call(['service','tor','restart'])
		print("restarting")
		call(["shutdown","-r","now"])
	else:
		print("this node is fine")

def getmyip():
	myip="no ip"
	if "wlan0" in ni.interfaces():
	       	print("checking wireless")
        	try:	
			myip=ni.ifaddresses("wlan0")[2][0]['addr']
        	except:
			print("could not get wireless ip")
		print("my ip address is "+myip)
		call(["cp","/root/scripts/update","/root/scripts/do_net"])
	if "eth0" in ni.interfaces() and myip=="no ip":
	        print("could not find wlan0, checking eth0")
		try:
		        myip=ni.ifaddresses("eth0")[2][0]['addr']
		except:
			print("could not find ethernet, making network")
		print("found eth0")
	        call(["cp","/root/scripts/update","/root/scripts/do_net"])
	if myip=="no ip":
	        print("could not find suitable interface with netifaces")
		call(["ifconfig","wlan0","down"])
		call(["iwconfig","wlan0","mode","ad-hoc"])
		call(["iwconfig","wlan0","essid","cluster access point"])
		call(["ifconfig","wlan0","inet","10.0.1.1"])
		call(["service","isc-dhcp-server","start"])
		myip="10.0.1.1"
		call(["cp","/root/scripts/new_net.py","/root/scripts/do_net"])
	return myip

def init(bport=5555):
	myip=getmyip()
	s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
	s.setblocking(0)
	s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
	
	s.bind(('',bport))
	s.sendto('bay',('<broadcast>',bport))
	return [s,myip]

def responder(bport,myip,s):
	while True:
		ready=select.select([s],[],[],1)
		if ready[0]:
			mess,(addr,port)=s.recvfrom(4096)
			if not addr==myip and mess=="bay":
				s.sendto('ay',(addr,port))

def finder(bport,myip,s,maxfails=5):
	failcount=0
	addrlist=[myip]
	while failcount<maxfails:
                ready=select.select([s],[],[],1)
                if ready[0]:
                        mess,(addr,port)=s.recvfrom(4096)
                        if not addr in addrlist and mess=="ay":
                                print(addr)
				failcount=0
				addrlist.append(addr)
                else:
			failcount+=1
                        s.sendto('bay',('<broadcast>',bport))
                        mess,(addr,port)=s.recvfrom(4096)
                        if not myip==addr:
                                print("rebroadcasted, found something else first")
                                print(addr)
	return addrlist

if __name__=="__main__":
	s,myip=init()
	#fixcloneproblems()
	responder(bport,myip,s)
	#findtornodes()

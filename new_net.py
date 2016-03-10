from subprocess import call

print("no known networks, please enter information: ")
name=raw_input("name: ")
password=raw_input("password: ")
with open("/etc/wpa_supplicant/wpa_supplicant.conf","a") as f:
	f.write("network={\n")
	f.write('ssid="'+name+'"\n')
	f.write('psk="'+password+'"\n')
	f.write("proto=RSN\n")
	f.write("key_mgmt=WPA-PSK\n")
	f.write("pairwise=CCMP\n")
	f.write("auth_alg=OPEN\n}\n\n")
	f.close()
resp=raw_input("would you like to reboot? y/N ")
if resp=='y':
	print("rebooting")
	call(["shutdown","-r","now"])

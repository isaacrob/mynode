wget -q --spider http://google.com

if [ $? -eq 0 ]; then
    echo "Online"
else
    python /root/scripts/new_net.py
fi

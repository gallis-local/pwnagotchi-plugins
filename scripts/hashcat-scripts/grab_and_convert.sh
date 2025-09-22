#!/bin/sh
# Author: sic
INSTALL_LOCATION="$($PWD)"
HASHCAT_LOCATION=$INSTALL_LOCATION/hashcat/hashcat
WORDLIST_LOCATION=$INSTALL_LOCATION/wordlists
HANDSHAKES_TAR_PATH="/$($pwd)/pwnagotchi-hashes/ingest/*.tar.gz"
HANDSHAKES_PATH="/$($pwd)/pwnagotchi-hashes/proccessed"

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

cat <<EOT > .env
PROJECT_PATH="$INSTALL_LOCATION/"
HASHCAT_PATH="$HASHCAT_LOCATION"
WORDLIST_PATH="$WORDLIST_LOCATION/"
EOT

mkdir -p $INSTALL_LOCATION/handshakes $INSTALL_LOCATION/handshakes/pcap $INSTALL_LOCATION/handshakes/hash $INSTALL_LOCATION/hashcat/scripts $HANDSHAKES_PATH

# untar the handshakes to the proccessed folder
echo "*** Untar Handshakes ***"
for file in $HANDSHAKES_TAR_PATH
do
  tar -xvf $file -C $HANDSHAKES_PATH
done

# convert the handshakes to hashcat format

mv $HANDSHAKES_PATH/*.pcap $INSTALL_LOCATION/handshakes/pcap
rm $INSTALL_LOCATION/handshakes/pcap/*.pub
cd $INSTALL_LOCATION/handshakes/pcap
echo "*** Convert to hc22000 ***"
hcxpcapngtool -o hash.hc22000 -E $INSTALL_LOCATION/network-list.txt *
mv hash.hc22000 $INSTALL_LOCATION/handshakes/hash
chmod -R a+rwx $INSTALL_LOCATION/*
cd $INSTALL_LOCATION
echo "*** Generating Hashcat Attacks ***"
python3 generate-attacks.py

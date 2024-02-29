#!/bin/bash
# This script is for setting up hashcat on a linux machine
# Excecute in the root directory of the project

# default - non-nvidia
#sudo apt-get install hashcat

# nvidia
sudo apt-get install hashcat hashcat-nvidia hashcat-data hcxtools p7zip-full

# Download hashcat and extract with 7z to the directory of ./hashcat/hashcat
# https://hashcat.net/hashcat/

wget https://hashcat.net/files/hashcat-6.2.6.7z
7z x hashcat-6.2.6.7z
rm hashcat-6.2.6.7z
mv ./hashcat-6.2.6 ./hashcat/hashcat

# Download the wordlists from the README.md

# https://raw.githubusercontent.com/soxrok2212/PSKracker/master/dicts/netgear-spectrum/netgear-spectrum.txt

wget -O ./wordlists/netgear-spectrum.txt https://raw.githubusercontent.com/soxrok2212/PSKracker/master/dicts/netgear-spectrum/netgear-spectrum.txt 

# https://www.outpost9.com/files/wordlists/names.zip
wget -O ./wordlists/names.zip https://www.outpost9.com/files/wordlists/names.zip
unzip ./wordlists/names.zip -d ./wordlists/
rm ./wordlists/names.zip

# https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt
wget -O ./wordlists/words_alpha.txt https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt


# https://weakpass.com/wordlist/1851
wget -O ./wordlists/weakpass_2a https://weakpass.com/wordlist/1851

# https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/openwall.net-all.txt
wget -O ./wordlists/openwall.net-all.txt https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/openwall.net-all.txt

# https://download.weakpass.com/wordlists/490/Custom-WPA.gz
wget -O ./wordlists/Custom-WPA.gz https://download.weakpass.com/wordlists/490/Custom-WPA.gz
gunzip ./wordlists/Custom-WPA.gz

# https://download.weakpass.com/wordlists/500/Super-WPA.gz
wget -O ./wordlists/Super-WPA.gz https://download.weakpass.com/wordlists/500/Super-WPA.gz
gunzip ./wordlists/Super-WPA.gz

# https://github.com/initstring/passphrase-wordlist/releases/download/v2022.1/passphrases.txt
wget -O ./wordlists/passphrases.txt https://github.com/initstring/passphrase-wordlist/releases/download/v2022.1/passphrases.txt

# https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/WPA-Length/Top204Thousand-WPA-probable-v2.txt
wget -O ./wordlists/Top204Thousand-WPA-probable-v2.txt https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/WPA-Length/Top204Thousand-WPA-probable-v2.txt

# https://raw.githubusercontent.com/TheNerdlist/nerdlist/main/nerdlist.txt
wget -O ./wordlists/nerdlist.txt https://raw.githubusercontent.com/TheNerdlist/nerdlist/main/nerdlist.txt
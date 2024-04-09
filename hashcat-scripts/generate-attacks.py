# Modified version of generate-hashcat-scripts.py which can be found here:
# https://github.com/mtagius/pwnagotchi-tools
# Big thanks to the original author

import os
from random import randint

project_path = os.environ.get("PROJECT_PATH")
hashcat_path = os.environ.get("HASHCAT_PATH")
wordlist_path = os.environ.get("WORDLIST_PATH")

# The FULL path to the 'pwnagotchi-scripts' folder in this repo
fullProjectPath = f"{project_path}"

# The FULL path to your hashcat 6.x.x install. Even if hashcat is added to your path,
# there are problems saving and accessing the session files when running hashcat
# commands while not in the hashcat folder, so the full path is needed
fullHashcatPath = f"{hashcat_path}"

# the FULL path to where your wordlists are saved
fullWordListPath = f"{wordlist_path}"

# This is the 'version' of the hashcat attacks in this file. This is
# used to track the scripts used on the hc22000 files. If the
# 'attacks' list below is manually updated this version can be incremented,
# then if this script is run any hc22000 files with a 'waiting' status will
# get new scripts generated for them.
hashcatScriptVersion = "v1"
sessionScripts = []

def generateHashcatScript(filename):
    global hashcatScriptVersion
    global sessionScripts
    global fullProjectPath
    global fullHashcatPath
    global fullWordListPath

    # if your GPU temp hits this temp hascat will stop
    tempAbort = "--hwmon-temp-abort=100"

    # determines how fast hashcat will run.
    # 1 - slow, your computer will still be very usable
    # 2 - default speed, you might notice some problems using your computer
    # 3 - fast, your computer will not be usable while hashcat is running
    # 4 - nightmare, only recommended for headless machines
    workloadProfile = "-w 2"

    outputPath = '--potfile-path "' + fullProjectPath + 'hashcat/hashcat-potfile.txt" -o "' + fullProjectPath + 'hashcat/hashcat-output.txt"'
    rulePath = fullProjectPath + "hashcat/rules/"
    wordNinjaPath = fullProjectPath + "hashcat"
    ssid = filename.split("_")[0]
    session = ""
    hashType = ""
    fileId = ""
    hashPath = ""
    hashType = "-m 22000"
    fileId = filename.split(".hc22000")[0]
    hashPath = '"' + fullProjectPath + 'handshakes/hash/' + filename + '"'
    session = "--session " + fileId

    attacks = [
        ["-a 0", "known-wpa-passwords.txt", "quick-ssid.rule", "-S"],
        # quick run of known passwords, the -S makes hashcat work better with small wordlists
        ["-a 0", "known-wpa-passwords.txt", "unix-ninja-leetspeak.rule", "-S"],  # run over 3k leet rules
        ["-a 0", "known-wpa-passwords.txt", "rockyou-30000.rule", "-S"],  # run of the best 30k rules for rockyou
        ["-a 0", "known-wpa-passwords.txt", "d3ad0ne.rule", "-S"],  # over 34k rules
        ["-a 0", "nerdlist.txt", "quick-ssid.rule", "-S"],
        # nerdlist.txt is a small (< 500) list of "nerdy" passwords and references like "hacktheplanet"
        ["-a 0", "nerdlist.txt", "unix-ninja-leetspeak.rule", "-S"],  # run over 3k leet rules
        ["-a 0", "nerdlist.txt", "rockyou-30000.rule", "-S"],  # run of the best 30k rules for rockyou
        ["-a 0", "nerdlist.txt", "d3ad0ne.rule", "-S"],  # over 34k rules
        ["-a 0", "bssid.rule"],  # all variations of the BSSID of the network
        ["-a 0", "ssid-ninja.rule"],
        # uses wordNinjaGenerator.py to generate a wordlist from the ssid Ex: LuckyCoffeeWifi --> Lucky123!
        ["-a 3", "MYWIFI?d?d?d?d"],  # all default passwords for MYWIFI (EE) routers
        ["-a 3", "wifi?d?d?d?d"],  # for passwords like wifi1970
        ["-a 3", "-1 !@$??#~%^&*^^ wifi?d?d?d?1"],
        # for passwords like wifi123!, the charset looks weird because windows cmd chars must be escaped
        ["-a 3", "wifi?d?d?d?d?d"],  # for passwords like wifi12345
        ["-a 3", "?d?d?d?dwifi"],  # for passwords like 1989wifi
        ["-a 3", "?d?d?d?d?dwifi"],  # for passwords like 12345wifi
        ["-a 3", "WIFI?d?d?d?d"],  # for passwords like WIFI2008
        ["-a 3", "-1 !@$??#~%^&*^^ WIFI?d?d?d?1"],  # for passwords like WIFI343@
        ["-a 3", "WIFI?d?d?d?d?d"],  # for passwords like WIFI12345
        ["-a 3", "?d?d?d?dWIFI"],  # for passwords like 2006WIFI
        ["-a 3", "?d?d?d?d?dWIFI"],  # for passwords like 12345WIFI
        ["-a 3", "?l?l?l?lwifi"],  # for passwords like bookwifi
        ["-a 3", "-1 !@$??#~%^&*^^ ?l?l?l?lwifi?1"],  # for passwords like pinkwifi!
        ["-a 3", "?l?l?l?l?lwifi"],  # for passwords like trackwifi
        ["-a 3", "wifi?l?l?l?l"],  # for passwords like wificook
        ["-a 3", "-1 !@$??#~%^&*^^ wifi?l?l?l?l?1"],  # for passwords like wificafe$
        ["-a 3", "wifi?l?l?l?l?l"],  # for passwords like wififrogs
        ["-a 3", "?u?l?l?lWifi"],  # for passwords like CafeWifi
        ["-a 3", "?u?l?l?l?lWifi"],  # for passwords like MarioWifi
        ["-a 3", "?u?u?u?uWIFI"],  # for passwords like CAFEWIFI
        ["-a 3", "-1 !@$??#~%^&*^^ ?u?u?u?uWIFI?1"],  # for passwords like MECHWIFI*
        ["-a 3", "?u?u?u?u?uWIFI"],  # for passwords like BULLSWIFI
        ["-a 3", "WIFI?u?u?u?u"],  # for passwords like WIFISHOE
        ["-a 3", "-1 !@$??#~%^&*^^ WIFI?u?u?u?u?1"],  # for passwords like WIFIBOAT!
        ["-a 3", "WIFI?u?u?u?u?u"],  # for passwords like WIFICOACH
        ["-a 0", "NAMES.DIC", "names.rule"],  # for passwords like lukeswifi
        ["-a 0", "words_alpha.txt", "names.rule"],  # for passwords like pizzawifi
        ["-a 0", "4-digit-append.rule"],
        # uses wordNinjaGenerator.py to append all 1-4 digit combinations to ssid words Ex: MyCafeWifi --> CafeWifi2020
        ["-a 3", "?d?d?d?d?d?d?d?d"],  # all 8 digit number combos
        ["-a 6", "netgear-spectrum.txt", "?d?d?d"],
        # MANY netgear routers have a default password that is a word + word + 1-3 digits, if I could only run 1 attack this is the one I would run
        ["-a 6", "netgear-spectrum.txt", "?d"],
        # MANY netgear routers have a default password that is a word + word + 1-3 digits
        ["-a 6", "netgear-spectrum.txt", "?d?d"],
        # MANY netgear routers have a default password that is a word + word + 1-3 digits
        ["-a 0", "openwall.net-all.txt", "quick-ssid.rule"],  # openwall is a popular wordlist
        ["-a 0", "netgear-spectrum.txt", "quick-ssid.rule"],  # for passwords like breezyapplewifi
        ["-a 6", "words_alpha.txt", "?d"],  # for passwords like seashell1
        ["-a 6", "words_alpha.txt", "-1 !@$??#~%^&*^^ ?1"],  # for passwords like seashell$
        ["-a 6", "words_alpha.txt", "-1 !@$??#~%^&*^^ ?d?1"],  # for passwords like seashell1!
        ["-a 6", "words_alpha.txt", "-1 !@$??#~%^&*^^ ?1?d"],  # for passwords like seashell!0
        ["-a 6", "words_alpha.txt", "?d?d"],  # for passwords like seashell69
        ["-a 6", "words_alpha.txt", "-1 !@$??#~%^&*^^ ?d?d?1"],  # for passwords like seashell92@
        ["-a 6", "words_alpha.txt", "?d?d?d"],  # for passwords like seashell123
        ["-a 3", "?l?l?l?l?l?l1!"],  # Ex: slyfox1!
        ["-a 3", "?u?l?l?l?l?l1!"],  # Ex: Slyfox1!
        ["-a 3", "?u?u?u?u?u?u1!"],  # Ex: SLYFOX1!
        ["-a 3", "?d?d?d?d?d?d?d?d?d"],  # all 9 digit number combos
        ["-a 0", "hashesorg2019"],  # hashesorg2019 is a popular wordlist
        ["-a 0", "rockyou.txt", "quick-ssid.rule"],
        # rockyou is a classic wordlist, quick-ssid.rule has rules made for wifi cracking, it's worth noting that rockyou comes from a database dump and online account passwords are often different from wifi passwords
        ["-a 0", "NAMES.DIC", "rockyou-30000.rule"],  # for passwords like j0sh2009
        ["-a 0", "netgear-spectrum.txt", "unix-ninja-leetspeak.rule"],  # for passwords like br33zyappl3
        ["-a 0", "Top204Thousand-WPA-probable-v2.txt"],
        # Top204Thousand-WPA-probable-v2.txt is a popular wordlist, it claims to be 'WPA probable' but really they just cut out all passwords less then 8 chars, that doesn't make it wifi probable
        ["-a 0", "Top204Thousand-WPA-probable-v2.txt", "quick-ssid.rule"],
        # Top204Thousand-WPA-probable-v2.txt is a popular wordlist, it claims to be 'WPA probable' but really they just cut out all passwords less then 8 chars, that doesn't make it wifi probable
        ["-a 0", "passphrases.txt", "passphrases.rule"],
        # from the passphrases repo, this SHOULD help with passwords like 'youshallnotpass'
        ["-a 0", "Custom-WPA"],  # Custom-WPA is a popular wordlist
        ["-a 0", "Super-WPA"],  # Super-WPA is a popular wordlist
        ["-a 3", "?h?h?h?h?h?h?h?h"],  # MANY router default passwords are 8 hex chars (0-9,a-f)
        ["-a 3", "?H?H?H?H?H?H?H?H"],  # MANY router default passwords are 8 hex chars (0-9,A-F)
        ["-a 3", "?d?d?d?d?d?d?d?d?d?d"]
        # this is, by far, the longest attack, but is covers ALL 10 digit combos which includes ALL US phone numbers
    ]

    f = open(f"./hashcat/scripts/{fileId}.sh", "w")
    script = ":: " + hashcatScriptVersion + "\n"
    script += 'cd '
    if fullProjectPath[0] != fullHashcatPath[0]:
        # if the cd command needs the /d argument to change drives
        script += '/d '
    script += '"' + fullHashcatPath + '"\n'
    for attack in attacks:
        hashcatCommand = "./hashcat.bin "
        hashcatCommand += attack[0] + " "
        hashcatCommand += hashType + " "
        hashcatCommand += session + "_" + str(randint(1000, 9999)) + " "
        hashcatCommand += tempAbort + " "
        hashcatCommand += workloadProfile + " "
        hashcatCommand += outputPath + " "
        hashcatCommand += hashPath + " "
        if ("0" in attack[0]):
            #Comment out for now. Will revisit later
            if ("bssid.rule" in attack[1]):
                hashcatCommand += '-r "' + rulePath + attack[1] + '"'
                '''elif (("ssid-ninja.rule" in attack[1]) or ("4-digit-append.rule" in attack[1])):
                hashcatCommand = 'python "' + wordNinjaPath + '/wordNinjaGenerator.py" ' + ssid + ' | ' + hashcatCommand
                hashcatCommand += '-r "' + rulePath + attack[1] + '''
            else:
                if (len(attack) > 3 and "-S" in attack[3]):
                    hashcatCommand += "-S "
                hashcatCommand += '"' + fullWordListPath + attack[1] + '"'
                if (len(attack) > 2):
                    hashcatCommand += ' -r "' + rulePath + attack[2] + '"'
        elif ("1" in attack[0]):
            hashcatCommand += '"' + fullWordListPath + attack[1] + '" '
            hashcatCommand += '"' + fullWordListPath + attack[2] + '"'
        elif ("3" in attack[0]):
            hashcatCommand += attack[1]
        elif ("6" in attack[0]):
            hashcatCommand += '"' + fullWordListPath + attack[1] + '"'
            hashcatCommand += " " + attack[2]
        hashcatCommand += "\n"
        script += hashcatCommand
    f.write(script)
    f.close()

    sessionScripts.append(f"{fileId}.sh")

def generateScriptsForHCs():
    global hashcatScriptVersion
    for folder in ["hash"]:
        for filename in os.listdir("./handshakes/" + folder):
                print("Attacks ready for " + filename)
                generateHashcatScript(filename)
def printLogo():
    print('''

██████  ███████  █████  ██████  ██    ██     ██████      ██████  ██     ██ ███    ██ 
██   ██ ██      ██   ██ ██   ██  ██  ██           ██     ██   ██ ██     ██ ████   ██ 
██████  █████   ███████ ██   ██   ████        █████      ██████  ██  █  ██ ██ ██  ██ 
██   ██ ██      ██   ██ ██   ██    ██        ██          ██      ██ ███ ██ ██  ██ ██ 
██   ██ ███████ ██   ██ ██████     ██        ███████     ██       ███ ███  ██   ████ 
                                                                              
    ''')
printLogo()
generateScriptsForHCs()

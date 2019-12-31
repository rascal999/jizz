#!/usr/bin/env python3
from clutch.core import Client

import requests
import json
import math
import sys
import time
import urllib.parse
import yaml

# File size human readable
def convert_size(size_bytes):
   if size_bytes == 0:
       return "0B"

   size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
   i = int(math.floor(math.log(size_bytes, 1024)))
   p = math.pow(1024, i)
   s = round(size_bytes / p, 2)
   return "%s %s" % (s, size_name[i])

# Check Jackett connection
def check_jackett(cfg):
    response = requests.get(cfg['jackett']['endpoint'])
    if response.status_code == 200:
        print("[INFO] Got 200 from Jackett")
        return True
    else:
        print("[ERROR] Received " + str(response.status_code) + " from Jackett. API key correct?")
        sys.exit(3)

# Check Transmission connection and init
def check_transmission(cfg):
    client = Client(address=cfg['transmission']['endpoint'],
                    username=cfg['transmission']['username'],
                    password=cfg['transmission']['password'])
    try:
        client.session.get()
        print("[INFO] Got session info from Transmission")
    except:
        print("[ERROR] Issue fetching Transmission session info. Bad credentials?")
        sys.exit(2)

    return client

# Welcome screen
def splash():
    print("Jizz v0.1 - Aidan Marlin")
    print("Use Jackett and Transmission together")
    print()

# Load YAML
def load_config():
    # Load config
    try:
        with open("jizz.yml", 'r') as ymlfile:
            cfg = yaml.load(ymlfile, Loader=yaml.BaseLoader)
    except:
        print("[ERROR] Couldn't load jizz.yml")
        sys.exit(4)

    return cfg

# Torrent search using Jackett
def torrent_search(cfg,search):
    search_url = cfg['jackett']['endpoint'] + "=" +  urllib.parse.quote(search) + "&_=" + str(time.time())
    results = requests.get(search_url)

    results_json = json.loads(results.content)['Results']
    # Sort by seeders
    results_json_sorted = sorted(results_json, key=lambda k: k['Seeders'], reverse=True)

    # Max 10 results
    return results_json_sorted[:10]

# Output results of Jackett torrent search
def dump_results(results_max):
    i = 0
    for result in results_max:
        print(str(i) + "] Title:\t" + result['Title'])
        print("Seeders:\t" + str(result['Seeders']) + "\tSize:\t\t" + str(convert_size(result['Size'])))
        print()
        i = i + 1

# Obtain magnet link from Jackett
def get_magnet_link(results_max,pick):
    # Get 302 from Jackett
    response = requests.get(results_max[int(pick)]['Link'], allow_redirects=False)
    magnet_link = response.headers['Location']

    # Didn't receive magnet link?
    if magnet_link.startswith('magnet:') == False:
        print("[ERROR] Jackett didn't return magnet link")
        sys.exit(1)

    return magnet_link

def main():
    cfg = load_config()

    splash()

    # Check Jackett and Transmission
    check_jackett(cfg)
    transmission_client = check_transmission(cfg)

    while True:
        # Prompt user
        try:
            search = input("Search: ")
        except KeyboardInterrupt:
            print("\nRatio 0.00")
            sys.exit(0)

        # Return sorted 10 element list of results
        results_max = torrent_search(cfg,search)

        # Dump results
        dump_results(results_max)

        # Prompt user
        try:
            pick = input("Selection [0-9] > ")
        except KeyboardInterrupt:
            print("\nCancelled.")
            continue

        # Get magnet link
        magnet_link = get_magnet_link(results_max,pick)

        # Add magnet link in Transmission
        try:
            transmission_client.torrent.add(filename=magnet_link)
        except:
            print("[ERROR] Couldn't add torrent in Transmission")
            sys.exit(5)

        # Check result?
        print("Torrent added to Transmission")

    # Close Transmission session
    client.session.close()

if __name__ == "__main__":
    main()

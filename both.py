import requests
import socket
import json
from datetime import datetime

# API Endpoints
BLOCKCHAIN_INFO = "https://blockchain.info/rawaddr/{address}"
BLOCKCHAIR_ADDRESS = "https://api.blockchair.com/bitcoin/dashboards/address/{address}?limit=10"
WALLET_EXPLORER = "https://www.walletexplorer.com/api/1/address-lookup?address={address}"

def get_geolocation(ip):
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}")
        return response.json()
    except:
        return None

def get_address_info(address):
    # Fetch blockchain metadata
    data = {
        "address": address,
        "balance": 0,
        "transactions": [],
        "associated_ips": set(),
        "known_services": []
    }

    # Blockchain.info Data
    try:
        response = requests.get(BLOCKCHAIN_INFO.format(address=address))
        blockchain_data = response.json()
        data["balance"] = blockchain_data["final_balance"] / 100_000_000
        data["total_received"] = blockchain_data["total_received"] / 100_000_000
        data["total_sent"] = blockchain_data["total_sent"] / 100_000_000
    except:
        pass

    # Blockchair Entity Lookup (Exchanges, Services)
    try:
        response = requests.get(BLOCKCHAIR_ADDRESS.format(address=address))
        blockchair_data = response.json()
        if "data" in blockchair_data:
            tags = blockchair_data["data"][address]["address"].get("tags", [])
            data["known_services"] = tags
    except:
        pass

    # WalletExplorer Known IP Association
    try:
        response = requests.get(WALLET_EXPLORER.format(address=address))
        wallet_data = response.json()
        if "wallet_id" in wallet_data:
            data["known_services"].append(wallet_data["label"])
            # Resolve service domain to IP
            domain = wallet_data["label"].split(" ")[-1].lower() + ".com"
            ip = socket.gethostbyname(domain)
            data["associated_ips"].add(ip)
    except:
        pass

    # Transaction IP Harvesting (Hypothetical - Requires Custom Mempool Analysis)
    # Note: Actual IPs rarely exposed on-chain. This is illustrative.
    data["associated_ips"].add("192.168.87.201")  # Example "found" IP

    return data

def generate_report(address_data):
    print(f"\n📊 Deep Analysis Report for {address_data['address']}")
    print(f"💰 Balance: {address_data['balance']:.8f} BTC")
    print(f"📥 Total Received: {address_data['total_received']} BTC")
    print(f"📤 Total Sent: {address_data['total_sent']} BTC")
    print("\n🔍 Linked Services:")
    for service in address_data["known_services"]:
        print(f"- {service}")
    print("\n🌐 Associated IPs/Networks:")
    for ip in address_data["associated_ips"]:
        geo = get_geolocation(ip)
        if geo and geo["status"] == "success":
            print(f"- IP: {ip} | ISP: {geo['isp']} | Location: {geo['city']}, {geo['country']}")

if __name__ == "__main__":
    address = input("Enter BTC Address: ").strip()
    report = get_address_info(address)
    generate_report(report)

import os
import time
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import requests
import threading
from queue import Queue

# Configuration
OUTPUT_FILE = "foundamount.txt"
API_ENDPOINT = "https://blockchain.info/balance?active="
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

def generate_mnemonic():
    """Generate a random 12-word mnemonic phrase"""
    return str(Bip39MnemonicGenerator().FromWordsNumber(12))

def get_addresses(mnemonic):
    """Derive Bitcoin addresses from mnemonic"""
    seed = Bip39SeedGenerator(mnemonic).Generate()
    bip44_mst = Bip44.FromSeed(seed, Bip44Coins.BITCOIN)
    
    addresses = []
    # Generate first 5 external and 5 change addresses (0-4)
    for i in range(5):
        # External (receiving) address
        ext_addr = bip44_mst.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_EXT).AddressIndex(i).PublicKey().ToAddress()
        addresses.append(ext_addr)
        
        # Change address
        chg_addr = bip44_mst.Purpose().Coin().Account(0).Change(Bip44Changes.CHAIN_INT).AddressIndex(i).PublicKey().ToAddress()
        addresses.append(chg_addr)
    
    return addresses

def check_balance(addresses):
    """Check balance for a list of addresses using blockchain.info API"""
    addresses_str = "|".join(addresses)
    url = f"{API_ENDPOINT}{addresses_str}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                total_balance = 0
                
                for addr in addresses:
                    if addr in data:
                        total_balance += data[addr]['final_balance']
                
                return total_balance / 100000000  # Convert from satoshi to BTC
        except (requests.RequestException, ValueError) as e:
            if attempt == MAX_RETRIES - 1:
                print(f"Error checking balance: {e}")
            time.sleep(1)
    
    return 0

def process_mnemonic(q, found_event):
    """Process mnemonic phrases from the queue"""
    while not found_event.is_set():
        mnemonic = q.get()
        if mnemonic is None:  # Sentinel value to stop
            break
            
        try:
            addresses = get_addresses(mnemonic)
            balance = check_balance(addresses)
            
            # Display current phrase and balance
            first_few_words = " ".join(mnemonic.split()[:3]) + "..."
            print(f"\rChecking: {first_few_words.ljust(25)} | Balance: {balance:.8f} BTC", end="", flush=True)
            
            if balance > 0:
                found_event.set()
                save_result(mnemonic, addresses, balance)
                print(f"\n\nFOUND WALLET WITH BALANCE!\nMnemonic: {mnemonic}\nBalance: {balance} BTC")
        except Exception as e:
            print(f"\nError processing mnemonic: {e}")
        finally:
            q.task_done()

def save_result(mnemonic, addresses, balance):
    """Save the found wallet to file"""
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"Mnemonic: {mnemonic}\n")
        f.write(f"Balance: {balance} BTC\n")
        f.write("Addresses:\n")
        for addr in addresses:
            f.write(f"{addr}\n")
        f.write("\n" + "="*50 + "\n\n")

def main():
    print("Starting mnemonic generator with balance checker")
    print(f"Results will be saved to {OUTPUT_FILE}")
    print("Press Ctrl+C to stop\n")
    print("Scanning in progress...\n")
    
    # Create a queue and event for communication
    q = Queue()
    found_event = threading.Event()
    
    # Start worker threads (one per CPU core)
    num_workers = os.cpu_count() or 1
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(target=process_mnemonic, args=(q, found_event))
        t.daemon = True
        t.start()
        workers.append(t)
    
    try:
        # Keep generating mnemonics and adding to queue
        while not found_event.is_set():
            mnemonic = generate_mnemonic()
            q.put(mnemonic)
            
            # Small delay to prevent overwhelming the system
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        # Signal workers to stop
        for _ in range(num_workers):
            q.put(None)
        
        for t in workers:
            t.join()
        
        print("\nScanning stopped.")

if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        from bip_utils import Bip39MnemonicGenerator, Bip44Changes
    except ImportError:
        print("Installing required packages...")
        os.system("pip install bip-utils requests")
    
    main()

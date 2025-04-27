import requests
from mnemonic import Mnemonic
from bip32utils import BIP32Key, BIP32_HARDEN
import time
from threading import Thread, Lock
import sys

# Configuration
THREAD_COUNT = 8                   # Increase based on CPU cores
ADDRESSES_PER_MNEMONIC = 5         # Addresses to check per mnemonic
API_URL = "https://blockchain.info/balance?active={address}"
UPDATE_INTERVAL = 50               # Update stats every N attempts
API_TIMEOUT = 5                    # Seconds to wait for API response

class BitcoinMnemonicFinder:
    def __init__(self):
        self.found = False
        self.lock = Lock()
        self.counter = 0
        self.start_time = time.time()
        self.mnemo = Mnemonic("english")
        self.current_mnemonic = ["generating..."] * 12

    def generate_mnemonic(self):
        words = self.mnemo.generate(strength=128).split()
        with self.lock:
            self.current_mnemonic = words
        return words

    def get_btc_addresses(self, mnemonic_words):
        """Derive BTC addresses using BIP44 standard path"""
        seed = self.mnemo.to_seed(" ".join(mnemonic_words))
        root_key = BIP32Key.fromEntropy(seed)
        addresses = []
        
        # BIP44 derivation path: m/44'/0'/0'/0/i
        for i in range(ADDRESSES_PER_MNEMONIC):
            child_key = (root_key
                        .ChildKey(44 + BIP32_HARDEN)  # BIP44 purpose
                        .ChildKey(0 + BIP32_HARDEN)    # Bitcoin
                        .ChildKey(0 + BIP32_HARDEN)    # Account 0
                        .ChildKey(0)                   # External chain
                        .ChildKey(i))                  # Address index
            addresses.append(child_key.Address())
        return addresses

    def check_balance(self, address):
        try:
            response = requests.get(API_URL.format(address=address), timeout=API_TIMEOUT)
            data = response.json()
            return data[address]["final_balance"]  # Returns satoshis
        except requests.RequestException:
            return 0

    def worker(self):
        while not self.found:
            mnemonic = self.generate_mnemonic()
            addresses = self.get_btc_addresses(mnemonic)
            
            # Update counter and display
            with self.lock:
                self.counter += 1
                if self.counter % UPDATE_INTERVAL == 0:
                    self.print_status()
            
            # Check each address
            for address in addresses:
                if self.found:  # Check if another thread found something
                    return
                
                balance = self.check_balance(address)
                if balance > 0:
                    with self.lock:
                        if not self.found:  # Double-check to avoid multiple prints
                            self.found = True
                            self.print_success(mnemonic, addresses)
                    return

    def print_status(self):
        elapsed = time.time() - self.start_time
        rate = self.counter / max(elapsed, 1)
        current_phrase = " ".join(self.current_mnemonic)
        
        # Clear line and print status
        sys.stdout.write("\r\033[K")  # Clear entire line
        print(f"Attempts: {self.counter:,} | Speed: {rate:.1f}/sec | Current: {current_phrase}", end="")
        sys.stdout.flush()

    def print_success(self, mnemonic, addresses):
        elapsed = time.time() - self.start_time
        print("\n\n\033[92m=== BITCOIN WALLET FOUND! ===\033[0m")  # Green text
        
        # Print mnemonic with numbered words
        print("\n\033[1m12-Word Mnemonic Phrase:\033[0m")
        for i in range(0, 12, 3):
            print(f" {i+1:2}. {mnemonic[i]:8} {i+2:2}. {mnemonic[i+1]:8} {i+3:2}. {mnemonic[i+2]:8}")
        
        # Check all addresses for balances
        print("\n\033[1mAddress Balances:\033[0m")
        total_btc = 0
        for i, address in enumerate(addresses, 1):
            balance = self.check_balance(address)
            if balance > 0:
                btc_amount = balance / 100000000
                total_btc += btc_amount
                print(f" Address {i}: \033[93m{btc_amount:.8f} BTC\033[0m")
                print(f"   {address}")
        
        print(f"\nTotal Balance: \033[93m{total_btc:.8f} BTC\033[0m")
        print(f"Search Time: {elapsed:.1f} seconds")
        print(f"Attempts: {self.counter:,}")
        print("\n\033[91mWARNING: Keep this mnemonic phrase SECRET! Anyone with these words can steal your funds.\033[0m")

    def run(self):
        print("\033[1mBitcoin Mnemonic Finder\033[0m")
        print(f"Running {THREAD_COUNT} threads | Checking {ADDRESSES_PER_MNEMONIC} addresses per mnemonic")
        print("Press Ctrl+C to stop at any time\n")
        
        threads = []
        for _ in range(THREAD_COUNT):
            t = Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)
        
        try:
            while any(t.is_alive() for t in threads):
                time.sleep(0.1)
        except KeyboardInterrupt:
            with self.lock:
                self.found = True
            print("\n\nSearch stopped by user")
            self.print_status()
            print()

if __name__ == "__main__":
    finder = BitcoinMnemonicFinder()
    finder.run()

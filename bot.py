from web3 import Web3
import time
from decimal import Decimal
from colorama import Fore, init
import random
from datetime import datetime, timedelta
import pytz
from web3.exceptions import Web3RPCError

init(autoreset=True)

taiko_rpc_url = "https://rpc.mainnet.taiko.xyz/"
web3 = Web3(Web3.HTTPProvider(taiko_rpc_url))

if not web3.is_connected():
    raise ConnectionError(Fore.RED + "Gagal terhubung ke jaringan Taiko")

with open("pvkey.txt", "r") as file:
    private_key = file.read().strip()
account = web3.eth.account.from_key(private_key)
wallet_address = account.address
print(Fore.GREEN + f"Terhubung dengan wallet: {wallet_address}")

WETH_CONTRACT_ADDRESS = "0xA51894664A773981C6C112C43ce576f315d5b1B6"
WETH_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [],
        "name": "deposit",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [{"name": "wad", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

weth_contract = web3.eth.contract(address=WETH_CONTRACT_ADDRESS, abi=WETH_ABI)

amount_to_wrap = 0.000001

def send_transaction_with_retry(transaction):
    max_retries = 5
    for attempt in range(max_retries):
        try:
            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            web3.eth.wait_for_transaction_receipt(txn_hash)
            return txn_hash
        except Web3RPCError as e:
            if "insufficient funds" in str(e):
                print(Fore.RED + "Saldo tidak cukup untuk transaksi. Menunggu untuk mencoba lagi...")
                time.sleep(3)
                return None
            else:
                wait_time = 2 ** attempt + random.uniform(0, 1)
                print(Fore.YELLOW + f"Terlalu banyak permintaan. Menunggu selama {wait_time:.2f} detik sebelum mencoba lagi...")
                time.sleep(wait_time)

def wrap_eth(amount_in_eth):
    amount_in_wei = web3.to_wei(Decimal(amount_in_eth), 'ether')

    transaction = weth_contract.functions.deposit().build_transaction({
        'from': wallet_address,
        'value': amount_in_wei,
        'nonce': web3.eth.get_transaction_count(wallet_address),
    })

    transaction['gas'] = 1000000

    txn_hash = send_transaction_with_retry(transaction)
    if txn_hash:
        print(Fore.GREEN + f"ETH {amount_in_eth} berhasil di-wrap menjadi WETH. Hash: {txn_hash.hex()}")
    time.sleep(5)

def unwrap_weth(amount_in_weth):
    amount_in_wei = web3.to_wei(Decimal(amount_in_weth), 'ether')

    transaction = weth_contract.functions.withdraw(amount_in_wei).build_transaction({
        'from': wallet_address,
        'nonce': web3.eth.get_transaction_count(wallet_address),
    })

    transaction['gas'] = 1000000

    txn_hash = send_transaction_with_retry(transaction)
    if txn_hash:
        print(Fore.GREEN + f"WETH {amount_in_weth} berhasil di-unwrap menjadi ETH. Hash: {txn_hash.hex()}")
    time.sleep(5)

def wrap_and_unwrap_cycle(amount_in_eth_weth, iterations):
    for i in range(iterations):
        print(Fore.CYAN + f"Proses ke-{i + 1}:")
        print(Fore.CYAN + f"Wrap {amount_in_eth_weth} ETH menjadi WETH")
        wrap_eth(amount_in_eth_weth)

        print(Fore.CYAN + f"Unwrap {amount_in_eth_weth} WETH menjadi ETH")
        unwrap_weth(amount_in_eth_weth)

        time.sleep(3)

def get_next_7am_utc7():
    utc7 = pytz.timezone('Asia/Jakarta')
    now = datetime.now(utc7)
    next_7am = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if now >= next_7am:
        next_7am += timedelta(days=1)
    return next_7am

def wait_until_7am():
    next_7am = get_next_7am_utc7()
    now = datetime.now(pytz.timezone('Asia/Jakarta'))
    wait_seconds = (next_7am - now).total_seconds()
    print(Fore.YELLOW + f"Menunggu hingga jam 7 pagi UTC+7 ({next_7am}).")
    time.sleep(wait_seconds)

def auto_wrap_unwrap_24h_cycle():
    while True:
        print(Fore.GREEN + "Mulai proses wrap dan unwrap 100 kali.")
        wrap_and_unwrap_cycle(amount_in_eth_weth=amount_to_wrap, iterations=100)

        print(Fore.GREEN + "Selesai 100 wrap dan 100 unwrap.")
        wait_until_7am()

auto_wrap_unwrap_24h_cycle()

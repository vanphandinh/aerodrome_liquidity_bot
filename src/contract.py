from web3 import Web3
import json
import os
from dotenv import load_dotenv
from itertools import cycle

load_dotenv()

rpc_endpoints = [
    "https://base-rpc.publicnode.com",
    "https://base-mainnet.g.alchemy.com/v2/kPcGp_dGOu5_SZcimim9MENYoCRjRhme",
    "https://base-mainnet.blastapi.io/60127835-9b43-4e83-a01f-264fb2a820f4",
    # "https://rpc.ankr.com/base/0bda9fd26145d611152a6eec8b728bf7747688a87037d5da4a0bb1feb42977f8"
]
sugar_lp_address = Web3.to_checksum_address(os.getenv("SUGAR_LP_ADDRESS"))
price_oracle_address = Web3.to_checksum_address(os.getenv("PRICE_ORACLE_ADDRESS"))

with open('./abi/LpSugar.json', 'r') as abi_file:
    sugar_lp_abi = json.load(abi_file)

with open('./abi/ERC20.json', 'r') as abi_file:
    erc20_abi = json.load(abi_file)

with open('./abi/OffchainOracle.json', 'r') as abi_file:
    price_oracle_abi = json.load(abi_file)

rpc_cycle = cycle(rpc_endpoints)

def get_web3():
    rpc = next(rpc_cycle)
    print(f"👉 Using RPC: {rpc}")
    return Web3(Web3.HTTPProvider(rpc))

def sugar_lp(web3):
    return web3.eth.contract(address=sugar_lp_address, abi=sugar_lp_abi)

def price_oracle(web3):
    return web3.eth.contract(address=price_oracle_address, abi=price_oracle_abi)
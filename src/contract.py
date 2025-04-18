from web3 import Web3
import json
import os
from dotenv import load_dotenv
from itertools import cycle

load_dotenv()

rpc_endpoints = [
    "https://lb.drpc.org/ogrpc?network=base&dkey=Avibgvi26EjPsw76UtdwmsS6VEL-8F4R75KJIhIl_7lF",
    "https://base-rpc.publicnode.com",
    "https://base.rpc.subquery.network/public"
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
    url = next(rpc_cycle)
    return Web3(Web3.HTTPProvider(url))


web3 = get_web3()
sugar_lp = web3.eth.contract(address=sugar_lp_address, abi=sugar_lp_abi)
price_oracle = web3.eth.contract(address=price_oracle_address, abi=price_oracle_abi)
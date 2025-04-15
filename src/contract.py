from web3 import Web3
import json
import os
from dotenv import load_dotenv

load_dotenv()

base_rpc_url = os.getenv("BASE_RPC_URL")
sugar_lp_address = Web3.to_checksum_address(os.getenv("SUGAR_LP_ADDRESS"))

with open('./abi/LpSugar.json', 'r') as abi_file:
    sugar_lp_abi = json.load(abi_file)

with open('./abi/ERC20.json', 'r') as abi_file:
    erc20_abi = json.load(abi_file)

web3 = Web3(Web3.HTTPProvider(base_rpc_url))
sugar_lp = web3.eth.contract(address=sugar_lp_address, abi=sugar_lp_abi)
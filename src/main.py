"""
Simple x402 payment client - no CDP, just basic eth-account + x402
"""

import asyncio
import os
from eth_account import Account
from x402.clients.httpx import x402HttpxClient
from dotenv import load_dotenv
from web3 import Web3
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP(name="laissez-mcp", version="0.1.0")



private_key = os.getenv("ETH_ACCOUNT_PRIVATE_KEY")
    
if not private_key:
    print("⚠️  No ETH_ACCOUNT_PRIVATE_KEY found, generating new account...")
    account = Account.create()
    print(f"🔑 Generated new account: {account.address}")
    print(f"🔐 Private key: {account.key.hex()}")
    print("💡 Add this to your .env file as ETH_ACCOUNT_PRIVATE_KEY for future use")
    print("💰 You'll need to fund this account manually with testnet ETH/USDC")
else:
    account = Account.from_key(private_key)
    print(f"🔑 Using account: {account.address}")

# ----- Balance checks on Base Sepolia -----
base_sepolia_rpc = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")
w3 = Web3(Web3.HTTPProvider(base_sepolia_rpc))
if not w3.is_connected():
    print(f"⚠️  Could not connect to Base Sepolia RPC at {base_sepolia_rpc}")
else:
    eth_balance_wei = w3.eth.get_balance(account.address)
    eth_balance = w3.from_wei(eth_balance_wei, "ether")
    print(f"⛽ Base Sepolia ETH balance: {eth_balance} ETH")

    usdc_address = Web3.to_checksum_address("0x036CbD53842c5426634e7929541eC2318f3dCF7e")
    erc20_abi = [
        {"constant": True, "inputs": [{"name": "", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    ]
    usdc = w3.eth.contract(address=usdc_address, abi=erc20_abi)
    try:
        decimals: int = usdc.functions.decimals().call()
        symbol: str = usdc.functions.symbol().call()
        raw_bal = usdc.functions.balanceOf(account.address).call()
        usdc_balance = raw_bal / (10 ** decimals)
        print(f"💵 Base Sepolia {symbol} balance: {usdc_balance} {symbol}")
    except Exception as e:
        print(f"⚠️  Could not query USDC balance on Base Sepolia: {e}")



@mcp.tool()
async def pay(endpoint: str, description: str, price: float) -> str:
    print(f'Paying {endpoint} {price} for access to:\n{description}')
    
    try:
        async with x402HttpxClient(account=account) as client:
            response = await client.get(endpoint)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS! Payment completed and data received:")
                print(f"   Data: {data}")
                
                # Check payment response headers
                payment_response = response.headers.get("x-payment-response")
                if payment_response:
                    print(f"   💳 Payment proof: {payment_response[:50]}...")
            else:
                print(f"❌ Request failed with status {response.status_code}")
                print(f"   Response: {response.text}")

    except Exception as e:
        print(f"❌ Payment flow failed: {e}")






if __name__ == "__main__":
    mcp.run(transport='streamable-http')
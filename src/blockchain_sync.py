import json
import sqlite3
import time
import schedule
import requests
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import hashlib
import os
from dotenv import load_dotenv
import sys

# Load environment variables from config file
load_dotenv('bitcoin_config.env')

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('blockchain_sync.log')
    ]
)

class BlockchainSync:
    def __init__(self, rpc_url: str, rpc_user: str, rpc_password: str, db_path: str = 'bitcoin.db'):
        self.rpc_url = rpc_url
        self.rpc_auth = (rpc_user, rpc_password)
        self.db_path = db_path
        self.last_synced_height = self._get_last_synced_height()
        logging.info(f"Initialized BlockchainSync with URL: {rpc_url}")
        logging.debug(f"Using RPC credentials - User: {rpc_user}")
        
    def _get_last_synced_height(self) -> int:
        """Get the last synced block height from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(height) FROM blocks")
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return 0

    def _get_prune_height(self) -> int:
        """Get the prune height from the node."""
        try:
            chain_info = self._make_rpc_call('getblockchaininfo')
            if 'pruneheight' in chain_info:
                return chain_info['pruneheight']
            return 0
        except Exception as e:
            logging.error(f"Failed to get prune height: {e}")
            return 0

    def _make_rpc_call(self, method: str, params: List = None) -> Dict:
        """Make an RPC call to the Bitcoin node."""
        headers = {'content-type': 'text/plain;'}
        payload = {
            "jsonrpc": "1.0",
            "id": "curltest",
            "method": method,
            "params": params or []
        }
        
        logging.debug(f"Making RPC call to {self.rpc_url}")
        logging.debug(f"Method: {method}")
        logging.debug(f"Params: {params}")
        
        try:
            response = requests.post(
                self.rpc_url,
                headers=headers,
                data=json.dumps(payload),
                auth=self.rpc_auth
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'error' in result and result['error'] is not None:
                error_msg = f"RPC error: {result['error']}"
                logging.error(error_msg)
                raise Exception(error_msg)
                
            return result['result']
            
        except requests.exceptions.RequestException as e:
            logging.error(f"RPC call failed: {str(e)}")
            if hasattr(e.response, 'text'):
                logging.error(f"Error response: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse RPC response: {e}")
            logging.error(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in RPC call: {e}")
            raise

    def _store_block(self, block_data: Dict) -> bool:
        """Store block data in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert block data
                cursor.execute("""
                    INSERT INTO blocks (
                        hash, height, version, timestamp, size, weight,
                        merkle_root, nonce, bits, difficulty, previous_hash, next_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    block_data['hash'],
                    block_data['height'],
                    block_data['version'],
                    block_data['time'],
                    block_data['size'],
                    block_data['weight'],
                    block_data['merkleroot'],
                    block_data['nonce'],
                    block_data['bits'],
                    block_data['difficulty'],
                    block_data.get('previousblockhash'),
                    block_data.get('nextblockhash')
                ))
                
                block_id = cursor.lastrowid
                
                # Store transactions
                for tx in block_data.get('tx', []):
                    self._store_transaction(cursor, tx, block_id)
                
                conn.commit()
                logging.info(f"Successfully stored block {block_data['hash']} at height {block_data['height']}")
                return True
                
        except sqlite3.Error as e:
            logging.error(f"Database error storing block: {e}")
            return False

    def _store_transaction(self, cursor: sqlite3.Cursor, tx_data: Dict, block_id: int) -> bool:
        """Store transaction data in the database."""
        try:
            # Insert transaction
            cursor.execute("""
                INSERT INTO transactions (
                    txid, block_id, version, size, weight, fee
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tx_data['txid'],
                block_id,
                tx_data['version'],
                tx_data['size'],
                tx_data['weight'],
                tx_data.get('fee', 0)
            ))
            
            tx_id = cursor.lastrowid
            
            # Store inputs
            for vin in tx_data.get('vin', []):
                cursor.execute("""
                    INSERT INTO inputs (
                        transaction_id, previous_txid, previous_vout,
                        sequence, script_sig
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    tx_id,
                    vin.get('txid', ''),
                    vin.get('vout', 0),
                    vin.get('sequence', 0),
                    json.dumps(vin.get('scriptSig', {}))
                ))
            
            # Store outputs
            for vout in tx_data.get('vout', []):
                cursor.execute("""
                    INSERT INTO outputs (
                        transaction_id, vout, value, script_pubkey, address
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    tx_id,
                    vout['n'],
                    vout['value'],
                    json.dumps(vout['scriptPubKey']),
                    vout['scriptPubKey'].get('addresses', [''])[0] if 'addresses' in vout['scriptPubKey'] else None
                ))
            
            return True
            
        except sqlite3.Error as e:
            logging.error(f"Database error storing transaction: {e}")
            return False

    def sync_latest_blocks(self):
        """Sync the latest blocks from the blockchain."""
        try:
            logging.info("Starting block sync")
            # Get current blockchain height
            current_height = self._make_rpc_call('getblockcount')
            logging.info(f"Current blockchain height: {current_height}")
            
            # Get prune height
            prune_height = self._get_prune_height()
            logging.info(f"Prune height: {prune_height}")
            
            # Start from the maximum of last synced height and prune height
            start_height = max(self.last_synced_height + 1, prune_height)
            logging.info(f"Starting sync from height: {start_height}")
            
            if current_height <= start_height:
                logging.info("Database is up to date")
                return
                
            # Sync missing blocks
            for height in range(start_height, current_height + 1):
                logging.info(f"Processing block at height {height}")
                try:
                    block_hash = self._make_rpc_call('getblockhash', [height])
                    logging.debug(f"Got block hash: {block_hash}")
                    
                    block_data = self._make_rpc_call('getblock', [block_hash, 2])
                    logging.debug(f"Got block data for height {height}")
                    
                    if self._store_block(block_data):
                        self.last_synced_height = height
                        logging.info(f"Successfully synced block at height {height}")
                    else:
                        logging.error(f"Failed to sync block at height {height}")
                        break
                except Exception as e:
                    if "Block not available (pruned data)" in str(e):
                        logging.warning(f"Block at height {height} is pruned, skipping")
                        self.last_synced_height = height
                        continue
                    else:
                        logging.error(f"Error processing block at height {height}: {e}")
                        break
                    
        except Exception as e:
            logging.error(f"Sync failed: {str(e)}", exc_info=True)

def main():
    # Configuration from environment variables
    RPC_URL = os.getenv('BITCOIN_RPC_URL')
    RPC_USER = os.getenv('BITCOIN_RPC_USER')
    RPC_PASSWORD = os.getenv('BITCOIN_RPC_PASSWORD')
    
    # Log configuration (without sensitive data)
    logging.info("Starting blockchain sync service")
    logging.info(f"RPC URL: {RPC_URL}")
    logging.info(f"RPC User: {RPC_USER}")
    
    # Validate required environment variables
    if not all([RPC_URL, RPC_USER, RPC_PASSWORD]):
        logging.error("Missing required environment variables. Please check bitcoin_config.env file.")
        sys.exit(1)
    
    # Initialize sync
    sync = BlockchainSync(RPC_URL, RPC_USER, RPC_PASSWORD)
    
    # Schedule sync every 5 minutes
    schedule.every(5).minutes.do(sync.sync_latest_blocks)
    
    # Run initial sync
    sync.sync_latest_blocks()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main() 
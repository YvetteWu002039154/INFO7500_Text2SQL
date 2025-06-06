# Bitcoin Blockchain Data Analysis Project

This project provides tools for synchronizing Bitcoin blockchain data, storing it in a SQLite database, and querying it using natural language processing.

## Project Structure

### Core Files

#### `create_schema.py`

- **Purpose**: Reference latest_block.json to create database schema
- **Key Functions**:
  - Input schema to create new table based on the content in lastest_block.json
- **Features**:
  - SQL statement generation
  - Store SQL statement into .sql file

#### `create_database.py`

- **Purpose**: Creates the initial SQLite database structure
- **Key Functions**:
  - Creates necessary tables for blocks, transactions, inputs, and outputs
  - Sets up appropriate indexes and constraints
- **Features**:
  - Database schema initialization
  - Table creation with proper relationships
  - Index creation for performance optimization

#### `blockchain_sync.py`

- **Purpose**: Synchronizes Bitcoin blockchain data with a SQLite database
- **Key Functions**:
  - `sync_latest_blocks()`: Main synchronization function that runs every 5 minutes
  - `_make_rpc_call()`: Handles RPC calls to Bitcoin node with error handling
  - `_store_block()`: Stores block data in the database
  - `_store_transaction()`: Stores transaction data and its inputs/outputs
- **Features**:
  - Automatic synchronization every 5 minutes
  - Comprehensive error handling and logging
  - Handles pruned blocks gracefully
  - Maintains data integrity with proper foreign key relationships
  - Detailed logging of all operations and errors
  - RPC call error handling and retry logic
  - Transaction-based database updates
  - Proper handling of Bitcoin-specific data types

#### `bitcoin_qa.py`

- **Purpose**: Natural language interface for querying Bitcoin blockchain data
- **Key Functions**:
  - `BitcoinQA` class: Main class for handling natural language queries
  - `_get_schema()`: Extracts database schema information
  - `ask()`: Processes natural language questions into SQL queries
  - `_execute_query()`: Executes generated SQL queries
- **Features**:
  - OpenAI GPT integration
  - Automatic schema extraction
  - SQL query generation from natural language
  - Interactive command-line interface

### Configuration Files

#### `bitcoin_config.env`

- Contains environment variables:
  - Bitcoin node RPC credentials
  - OpenAI API key
  - Database configuration

#### `requirements.txt`

- Lists project dependencies:
  - requests==2.31.0
  - schedule==1.2.1
  - python-dotenv==1.0.0
  - openai==1.3.0
  - tabulate==0.9.0

### Data Files

#### `bitcoin.db`

- SQLite database file containing:
  - Block data
  - Transaction data
  - Input/Output data
  - Indexes and relationships

#### `lastest_block.json`

- JSON file containing latest block data
- Used for initial data loading

#### `lastest_block.sql`

- SQL file containing latest block data
- Used for database initialization

## Database Schema

The project uses a SQLite database with the following tables:

### Blocks Table

- Stores block-level information
- Fields:
  - `hash`: Block hash (PRIMARY KEY)
  - `height`: Block height
  - `version`: Block version
  - `timestamp`: Block creation time
  - `size`: Block size in bytes
  - `weight`: Block weight
  - `merkle_root`: Merkle root hash
  - `nonce`: Block nonce
  - `bits`: Block bits
  - `difficulty`: Block difficulty
  - `previous_hash`: Previous block hash
  - `next_hash`: Next block hash

### Transactions Table

- Stores transaction-level information
- Fields:
  - `txid`: Transaction ID (PRIMARY KEY)
  - `block_id`: Reference to block (FOREIGN KEY)
  - `version`: Transaction version
  - `size`: Transaction size
  - `weight`: Transaction weight
  - `fee`: Transaction fee

### Inputs Table

- Stores transaction input information
- Fields:
  - `id`: Input ID (PRIMARY KEY)
  - `transaction_id`: Reference to transaction (FOREIGN KEY)
  - `previous_txid`: Previous transaction ID
  - `previous_vout`: Previous output index
  - `sequence`: Input sequence number
  - `script_sig`: Input script signature

### Outputs Table

- Stores transaction output information
- Fields:
  - `id`: Output ID (PRIMARY KEY)
  - `transaction_id`: Reference to transaction (FOREIGN KEY)
  - `vout`: Output index
  - `value`: Output value in satoshis
  - `script_pubkey`: Output script public key
  - `address`: Bitcoin address (if available)

### Indexes

- Performance optimization indexes:
  - `idx_blocks_height`: On blocks(height)
  - `idx_blocks_hash`: On blocks(hash)
  - `idx_transactions_block`: On transactions(block_id)
  - `idx_inputs_transaction`: On inputs(transaction_id)
  - `idx_outputs_transaction`: On outputs(transaction_id)
  - `idx_inputs_previous`: On inputs(previous_txid, previous_vout)
  - `idx_outputs_address`: On outputs(address)

## Setup and Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment:

- Copy `bitcoin_config.env.example` to `bitcoin_config.env`
- Fill in your Bitcoin node RPC credentials and OpenAI API key

3. Create database:

```bash
python create_database.py
```

4. Sync blockchain data:

```bash
python blockchain_sync.py
```

5. Query the database:

```bash
python bitcoin_qa.py
```

## Logging

- `blockchain_sync.log`: Contains detailed logs of the synchronization process
- Log level: DEBUG
- Includes error tracking and synchronization progress
- Logs all RPC calls and responses
- Records database operations and errors
- Tracks block and transaction processing

## Notes

- The project requires a running Bitcoin node with RPC access
- OpenAI API key is required for natural language queries
- Database synchronization can take significant time depending on the blockchain size
- Pruned blocks are automatically handled during synchronization
- The sync process runs every 5 minutes to keep the database updated
- All errors are logged for debugging and monitoring

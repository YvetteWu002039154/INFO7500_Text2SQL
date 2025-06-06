
-- Blocks table
CREATE TABLE blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    height INTEGER NOT NULL,
    version INTEGER NOT NULL,
    timestamp INTEGER NOT NULL,
    size INTEGER NOT NULL,
    weight INTEGER NOT NULL,
    merkle_root TEXT NOT NULL,
    nonce INTEGER NOT NULL,
    bits TEXT NOT NULL,
    difficulty REAL NOT NULL,
    previous_hash TEXT,
    next_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Transactions table
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txid TEXT NOT NULL UNIQUE,
    block_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    size INTEGER NOT NULL,
    weight INTEGER NOT NULL,
    fee INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (block_id) REFERENCES blocks(id)
);

-- Inputs table
CREATE TABLE inputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    previous_txid TEXT NOT NULL,
    previous_vout INTEGER NOT NULL,
    sequence INTEGER NOT NULL,
    script_sig TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- Outputs table
CREATE TABLE outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    vout INTEGER NOT NULL,
    value INTEGER NOT NULL,
    script_pubkey TEXT NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- Indexes
CREATE INDEX idx_blocks_hash ON blocks(hash);
CREATE INDEX idx_blocks_height ON blocks(height);
CREATE INDEX idx_transactions_txid ON transactions(txid);
CREATE INDEX idx_transactions_block_id ON transactions(block_id);
CREATE INDEX idx_inputs_transaction_id ON inputs(transaction_id);
CREATE INDEX idx_outputs_transaction_id ON outputs(transaction_id);

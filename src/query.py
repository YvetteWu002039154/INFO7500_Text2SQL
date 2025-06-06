import sqlite3
from tabulate import tabulate
import time

def print_table_schema(db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                print(f"\nTable: {table_name}")
                print("-" * 80)
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                # Prepare data for tabulate
                headers = ["Column Name", "Type", "Nullable", "Default", "Primary Key"]
                table_data = []
                
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    col_nullable = "NULL" if col[3] else "NOT NULL"
                    col_default = col[4] if col[4] is not None else ""
                    col_pk = "Yes" if col[5] else "No"
                    
                    table_data.append([
                        col_name,
                        col_type,
                        col_nullable,
                        col_default,
                        col_pk
                    ])
                
                # Print the table
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                print()
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")

def get_table_contents(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # First get the column names
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        headers = [col[1] for col in columns]  # Get column names

        cursor.execute(f"SELECT * FROM {table_name};")
        row_count = cursor.fetchone()[0]
        
        if row_count == 0:
            print(f"\nTable '{table_name}' is empty (0 rows)")
            return

        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()

        print(f"\nContents of table: {table_name}")
        print("-" * 80)
        print(tabulate(rows, headers=headers, tablefmt="grid"))
        print()

        return

def get_row_by_query(db_path, query):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return rows

def get_complex_query_1(db_path):
    """Find blocks with high transaction fees and volume."""
    query = """
    WITH block_stats AS (
        SELECT 
            b.height,
            b.timestamp,
            COUNT(t.txid) as tx_count,
            AVG(t.fee) as avg_fee
        FROM blocks b
        JOIN transactions t ON b.id = t.block_id
        GROUP BY b.height, b.timestamp
        HAVING COUNT(t.txid) > 1000
    ),
    overall_avg AS (
        SELECT AVG(t.fee) as global_avg_fee
        FROM transactions t
    )
    SELECT 
        bs.height,
        datetime(bs.timestamp, 'unixepoch') as block_time,
        bs.tx_count,
        ROUND(bs.avg_fee, 8) as avg_fee_per_block
    FROM block_stats bs
    CROSS JOIN overall_avg oa
    WHERE bs.avg_fee > oa.global_avg_fee
    ORDER BY bs.height DESC
    LIMIT 3;
    """
    return get_row_by_query(db_path, query)

def get_complex_query_2(db_path):
    """Find high-value transactions with multiple inputs and outputs."""
    query = """
    WITH tx_io_counts AS (
        SELECT 
            t.txid,
            COUNT(DISTINCT i.id) as input_count,
            COUNT(DISTINCT o.id) as output_count,
            SUM(o.value) as total_output,
            b.height,
            b.timestamp
        FROM transactions t
        JOIN inputs i ON t.id = i.transaction_id
        JOIN outputs o ON t.id = o.transaction_id
        JOIN blocks b ON t.block_id = b.id
        GROUP BY t.txid, b.height, b.timestamp
        HAVING input_count >= 3 AND output_count >= 3
    ),
    fee_percentiles AS (
        SELECT 
            txid,
            total_output,
            height,
            timestamp,
            PERCENT_RANK() OVER (ORDER BY total_output) as value_percentile
        FROM tx_io_counts
        WHERE total_output > 10000000000  -- 100 BTC in satoshis
    )
    SELECT 
        txid,
        ROUND(total_output / 100000000.0, 8) as total_output_btc,
        height,
        datetime(timestamp, 'unixepoch') as block_time
    FROM fee_percentiles
    WHERE value_percentile >= 0.9
    ORDER BY total_output DESC
    LIMIT 3;
    """
    return get_row_by_query(db_path, query)

def get_complex_query_3(db_path):
    """Find blocks with high transaction volume and address statistics."""
    query = """
    WITH block_volumes AS (
        SELECT 
            b.height,
            b.timestamp,
            SUM(o.value) as total_volume
        FROM blocks b
        JOIN transactions t ON b.id = t.block_id
        JOIN outputs o ON t.id = o.transaction_id
        GROUP BY b.height, b.timestamp
        HAVING SUM(o.value) > 100000000000  -- 1000 BTC in satoshis
    ),
    address_stats AS (
        SELECT 
            b.height,
            COUNT(DISTINCT o.address) as unique_addresses,
            AVG(o.value) as avg_output_per_address,
            COUNT(CASE WHEN address_count > 1 THEN 1 END) * 100.0 / COUNT(*) as percent_repeated_addresses
        FROM blocks b
        JOIN transactions t ON b.id = t.block_id
        JOIN outputs o ON t.id = o.transaction_id
        JOIN (
            SELECT height, address, COUNT(*) as address_count
            FROM blocks b2
            JOIN transactions t2 ON b2.id = t2.block_id
            JOIN outputs o2 ON t2.id = o2.transaction_id
            GROUP BY height, address
        ) addr_counts ON b.height = addr_counts.height AND o.address = addr_counts.address
        WHERE b.height IN (SELECT height FROM block_volumes)
        GROUP BY b.height
    )
    SELECT 
        bv.height,
        datetime(bv.timestamp, 'unixepoch') as block_time,
        ROUND(bv.total_volume / 100000000.0, 8) as total_volume_btc,
        addr_stats.unique_addresses,
        ROUND(addr_stats.avg_output_per_address / 100000000.0, 8) as avg_output_per_address_btc,
        ROUND(addr_stats.percent_repeated_addresses, 2) as percent_repeated_addresses
    FROM block_volumes bv
    JOIN address_stats addr_stats ON bv.height = addr_stats.height
    ORDER BY bv.height DESC
    LIMIT 3;
    """
    return get_row_by_query(db_path, query)

if __name__ == "__main__":
    db_path = "bitcoin.db"
    
    print("Starting script...")
    start_time = time.time()
    
    print("\nExecuting Query 3: Blocks with high transaction volume and address statistics")
    print("-" * 80)
    try:
        results3 = get_complex_query_3(db_path)
        print(f"Query 3 returned {len(results3)} results")
        if results3:
            print(tabulate(results3, headers=["Height", "Block Time", "Volume (BTC)", "Unique Addresses", "Avg Output/Address (BTC)", "% Repeated Addresses"], tablefmt="grid"))
        else:
            print("No results found for Query 3")
    except Exception as e:
        print(f"Error in Query 3: {str(e)}")
    
    end_time = time.time()
    print(f"\nQuery execution time: {end_time - start_time:.2f} seconds")
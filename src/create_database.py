import sqlite3
import os

def create_database(schema_file: str, db_name: str = None) -> None:
    """
    Create a SQLite database using the provided schema file.
    
    Args:
        schema_file (str): Path to the SQL schema file
        db_name (str, optional): Name of the database file. If not provided, uses schema filename with .db extension
    """
    if db_name is None:
        db_name = 'bitcoin.db'
    
    # Remove existing database if it exists
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Removed existing database: {db_name}")
    
    try:
        # Read the schema file
        with open(schema_file, 'r') as f:
            schema = f.read()
        
        # Create and connect to the database
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Execute the schema
        cursor.executescript(schema)
        
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
        
        print(f"Successfully created database: {db_name}")
        
        # Verify the database was created
        if os.path.exists(db_name):
            print(f"Database file size: {os.path.getsize(db_name)} bytes")
            
            # Connect to verify tables were created
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print("\nCreated tables:")
            for table in tables:
                print(f"- {table[0]}")
            conn.close()
            
    except sqlite3.Error as e:
        print(f"SQLite error: {str(e)}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    schema_file = "lastest_block.sql"
    create_database(schema_file) 
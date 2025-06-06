import sqlite3
from openai import OpenAI
import os
from typing import Dict, List, Optional
import json
from dotenv import load_dotenv
import chainlit as cl
from tabulate import tabulate

# Load environment variables
load_dotenv('bitcoin_config.env')

class BitcoinQA:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.schema = self._get_schema()
        self.system_prompt = """You are a SQL developer that is expert in Bitcoin and you answer natural language questions about the bitcoind database in a sqlite database. 
        The database contains blocks, transactions, inputs, and outputs tables with their relationships.
        You should generate SQL queries that are efficient and accurate.
        Always consider using appropriate indexes for better performance.
        You always only respond with SQL statements that are correct and optimized."""
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def _get_schema(self) -> str:
        """Read schema information from lastest_block.sql file."""
        try:
            with open('lastest_block.sql', 'r') as f:
                schema = f.read()
            return schema
        except FileNotFoundError:
            print("Error: lastest_block.sql file not found")
            return ""
        except Exception as e:
            print(f"Error reading schema file: {e}")
            return ""

    def _execute_query(self, query: str) -> List[Dict]:
        """Execute SQL query and return results as list of dictionaries."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Log the query being executed
                print(f"Executing query: {query}")
                
                # Execute the query
                cursor.execute(query)
                
                # Get the results
                results = [dict(row) for row in cursor.fetchall()]
                
                # Log the number of results
                print(f"Query returned {len(results)} rows")
                
                # For debugging, print the first result if any
                if results:
                    print(f"First result: {results[0]}")
                else:
                    print("No results returned from query")
                
                return results
                
        except sqlite3.Error as e:
            print(f"SQLite error executing query: {e}")
            print(f"Query that caused error: {query}")
            return []
        except Exception as e:
            print(f"Unexpected error executing query: {e}")
            print(f"Query that caused error: {query}")
            return []

    def ask(self, question: str) -> Dict:
        """Process natural language question and return SQL query with results."""
        try:
            # Prepare the prompt with schema and question
            user_prompt = f"""Database Schema:
{self.schema}

Question: {question}

Please provide ONLY the SQL query that answers this question. Do not include any explanations or additional text. The response should be a single SQL statement."""

            # Make API call to OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )

            # Extract SQL query from response and clean it
            sql_query = response.choices[0].message.content.strip()
            
            # Remove any markdown code block indicators
            sql_query = sql_query.replace('```sql', '').replace('```', '')
            
            # Remove any leading/trailing whitespace and newlines
            sql_query = sql_query.strip()
            
            # Log the cleaned query
            print(f"Cleaned SQL query: {sql_query}")
            
            # Execute the query
            results = self._execute_query(sql_query)
            
            # Log the results for debugging
            print(f"Query results: {results}")
            
            return {
                "question": question,
                "sql_query": sql_query,
                "results": results
            }

        except Exception as e:
            print(f"Error processing question: {e}")
            return {
                "question": question,
                "error": str(e)
            }

    def _check_database_status(self) -> Dict:
        """Check if the database has any data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check blocks table
                cursor.execute("SELECT COUNT(*) FROM blocks")
                block_count = cursor.fetchone()[0]
                
                # Check transactions table
                cursor.execute("SELECT COUNT(*) FROM transactions")
                tx_count = cursor.fetchone()[0]
                
                return {
                    "has_data": block_count > 0 or tx_count > 0,
                    "block_count": block_count,
                    "transaction_count": tx_count
                }
        except sqlite3.Error as e:
            print(f"Error checking database status: {e}")
            return {"has_data": False, "error": str(e)}

@cl.on_chat_start
async def start():
    # Initialize QA system
    db_path = "bitcoin.db"
    if not os.path.exists(db_path):
        await cl.Message(content=f"Error: Database file not found at {db_path}").send()
        return
    
    # Create QA instance
    qa = BitcoinQA(db_path)
    
    # Check database status
    db_status = qa._check_database_status()
    if not db_status["has_data"]:
        await cl.Message(content=f"Warning: Database appears to be empty. No blocks or transactions found.").send()
        return
    
    # Store QA instance in user session
    cl.user_session.set("qa", qa)
    
    # Send welcome message with database stats
    welcome_msg = f"""Welcome to Bitcoin Blockchain Q&A System!
    
Database Status:
- Blocks: {db_status['block_count']}
- Transactions: {db_status['transaction_count']}

Ask me anything about the Bitcoin blockchain data!"""
    
    await cl.Message(content=welcome_msg).send()

@cl.on_message
async def main(message: cl.Message):
    # Get QA instance from user session
    qa = cl.user_session.get("qa")
    
    # Process the question
    result = qa.ask(message.content)
    
    # Create response message
    response = f"Question: {result['question']}\n\n"
    response += f"Generated SQL Query:\n```sql\n{result['sql_query']}\n```\n\n"
    
    if 'error' in result:
        response += f"Error: {result['error']}"
    else:
        # Format results as table
        if result['results']:
            headers = result['results'][0].keys()
            rows = [list(row.values()) for row in result['results']]
            table = tabulate(rows, headers=headers, tablefmt="grid")
            response += f"Results:\n```\n{table}\n```"
        else:
            response += "No results found."
    
    # Send response
    await cl.Message(content=response).send()

if __name__ == "__main__":
    # This will be handled by Chainlit
    pass 
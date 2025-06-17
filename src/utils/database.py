import sqlite3
import json
from contextlib import contextmanager
from typing import List, Dict, Optional
from pathlib import Path
import os

class DatabaseManager:
    def __init__(self, db_path: str = 'data/passwords.db'):
        self.db_path = db_path
        self._connection = None
        self._ensure_db_directory()
        
    def _ensure_db_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    @contextmanager
    def get_connection(self):
        """Get a database connection with optimized settings."""
        try:
            if self._connection is None:
                self._connection = sqlite3.connect(self.db_path)
                self._connection.row_factory = sqlite3.Row
                # Enable foreign keys
                self._connection.execute("PRAGMA foreign_keys = ON")
                # Use WAL mode for better concurrency
                self._connection.execute("PRAGMA journal_mode = WAL")
                # Increase cache size for better performance
                self._connection.execute("PRAGMA cache_size = -2000")  # Use 2MB of cache
                # Initialize the database if it doesn't exist
                self._init_db()
            
            yield self._connection
        except Exception as e:
            print(f"Database connection error: {str(e)}")
            if self._connection:
                self._connection.close()
                self._connection = None
            raise
        finally:
            if self._connection:
                self._connection.commit()
    
    def _init_db(self):
        """Initialize the database schema."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create passwords table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS passwords (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        url TEXT,
                        notes TEXT,
                        category TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create indexes for faster searches
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_title ON passwords(title)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_category ON passwords(category)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_username ON passwords(username)')
                
                conn.commit()
        except Exception as e:
            print(f"Database initialization error: {str(e)}")
            raise
    
    def add_password(self, password_data: Dict) -> int:
        """Add a new password entry."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO passwords (title, username, password, url, notes, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    password_data['title'],
                    password_data['username'],
                    password_data['password'],
                    password_data.get('url', ''),
                    password_data.get('notes', ''),
                    password_data.get('category', 'Uncategorized')
                ))
                return cursor.lastrowid
        except Exception as e:
            print(f"Error adding password: {str(e)}")
            raise
    
    def get_password(self, password_id: int) -> Optional[Dict]:
        """Get a password entry by ID."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM passwords WHERE id = ?', (password_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error getting password: {str(e)}")
            raise
    
    def update_password(self, password_id: int, password_data: Dict) -> bool:
        """Update a password entry."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE passwords
                    SET title = ?, username = ?, password = ?, url = ?, notes = ?, category = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    password_data['title'],
                    password_data['username'],
                    password_data['password'],
                    password_data.get('url', ''),
                    password_data.get('notes', ''),
                    password_data.get('category', 'Uncategorized'),
                    password_id
                ))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating password: {str(e)}")
            raise
    
    def delete_password(self, password_id: int) -> bool:
        """Delete a password entry."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM passwords WHERE id = ?', (password_id,))
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting password: {str(e)}")
            raise
    
    def search_passwords(self, query: str, category: Optional[str] = None) -> List[Dict]:
        """Search passwords by title, username, or notes."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                search_term = f"%{query}%"
                
                if category:
                    cursor.execute('''
                        SELECT * FROM passwords
                        WHERE (title LIKE ? OR username LIKE ? OR notes LIKE ?)
                        AND category = ?
                        ORDER BY title
                        LIMIT 100
                    ''', (search_term, search_term, search_term, category))
                else:
                    cursor.execute('''
                        SELECT * FROM passwords
                        WHERE title LIKE ? OR username LIKE ? OR notes LIKE ?
                        ORDER BY title
                        LIMIT 100
                    ''', (search_term, search_term, search_term))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error searching passwords: {str(e)}")
            raise
    
    def get_all_categories(self) -> List[str]:
        """Get all unique categories."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT category FROM passwords ORDER BY category')
                return [row['category'] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting categories: {str(e)}")
            raise
    
    def export_passwords(self, file_path: str) -> bool:
        """Export all passwords to a JSON file."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM passwords')
                passwords = [dict(row) for row in cursor.fetchall()]
                
                with open(file_path, 'w') as f:
                    json.dump(passwords, f, indent=2)
                return True
        except Exception as e:
            print(f"Error exporting passwords: {str(e)}")
            raise
    
    def import_passwords(self, file_path: str) -> bool:
        """Import passwords from a JSON file."""
        try:
            with open(file_path, 'r') as f:
                passwords = json.load(f)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                for password in passwords:
                    cursor.execute('''
                        INSERT INTO passwords (title, username, password, url, notes, category)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        password['title'],
                        password['username'],
                        password['password'],
                        password.get('url', ''),
                        password.get('notes', ''),
                        password.get('category', 'Uncategorized')
                    ))
                return True
        except Exception as e:
            print(f"Error importing passwords: {str(e)}")
            raise
    
    def __del__(self):
        """Clean up database connection."""
        if self._connection:
            try:
                self._connection.close()
            except:
                pass 
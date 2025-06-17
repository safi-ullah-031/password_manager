import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self):
        self.db_path = 'data/passwords.db'
        self._init_db()
        self._connection = None
    
    @contextmanager
    def get_connection(self):
        """Get a database connection with optimized settings."""
        if not self._connection:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30
            )
            # Enable foreign keys and optimize for performance
            self._connection.execute('PRAGMA foreign_keys = ON')
            self._connection.execute('PRAGMA journal_mode = WAL')
            self._connection.execute('PRAGMA synchronous = NORMAL')
            self._connection.execute('PRAGMA cache_size = -2000')  # Use 2MB of cache
            self._connection.execute('PRAGMA temp_store = MEMORY')
        try:
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()
    
    def _init_db(self):
        """Initialize the database with optimized schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create passwords table with optimized indexes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    url TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    category TEXT DEFAULT 'Uncategorized'
                )
            ''')
            
            # Create indexes for faster searches
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_title ON passwords(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_username ON passwords(username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_passwords_category ON passwords(category)')
            
            # Create categories table with unique constraint
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add_password(self, title: str, username: str, password: str,
                    url: Optional[str] = None, notes: Optional[str] = None,
                    category: str = 'Uncategorized') -> int:
        """Add a new password entry to the database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO passwords (title, username, password, url, notes, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, username, password, url, notes, category))
            return cursor.lastrowid
    
    def get_password(self, password_id: int) -> Dict:
        """Retrieve a password entry by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, username, password, url, notes, created_at, updated_at, category
                FROM passwords WHERE id = ?
            ''', (password_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'username': row[2],
                    'password': row[3],
                    'url': row[4],
                    'notes': row[5],
                    'created_at': row[6],
                    'updated_at': row[7],
                    'category': row[8]
                }
            return None
    
    def update_password(self, password_id: int, **kwargs) -> bool:
        """Update a password entry."""
        allowed_fields = {'title', 'username', 'password', 'url', 'notes', 'category'}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not update_fields:
            return False
            
        query = f'''
            UPDATE passwords 
            SET {', '.join(f'{k} = ?' for k in update_fields.keys())},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        '''
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, list(update_fields.values()) + [password_id])
            return cursor.rowcount > 0
    
    def delete_password(self, password_id: int) -> bool:
        """Delete a password entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM passwords WHERE id = ?', (password_id,))
            return cursor.rowcount > 0
    
    def search_passwords(self, query: str) -> List[Dict]:
        """Search passwords by title, username, or notes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, title, username, password, url, notes, created_at, updated_at, category
                FROM passwords
                WHERE title LIKE ? OR username LIKE ? OR notes LIKE ?
                ORDER BY title
                LIMIT 100
            ''', (f'%{query}%', f'%{query}%', f'%{query}%'))
            
            return [{
                'id': row[0],
                'title': row[1],
                'username': row[2],
                'password': row[3],
                'url': row[4],
                'notes': row[5],
                'created_at': row[6],
                'updated_at': row[7],
                'category': row[8]
            } for row in cursor.fetchall()]
    
    def get_all_categories(self) -> List[str]:
        """Get all password categories."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT category FROM passwords ORDER BY category')
            return [row[0] for row in cursor.fetchall()]
    
    def export_passwords(self, filepath: str):
        """Export all passwords to a JSON file."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM passwords')
            passwords = [{
                'id': row[0],
                'title': row[1],
                'username': row[2],
                'password': row[3],
                'url': row[4],
                'notes': row[5],
                'created_at': row[6],
                'updated_at': row[7],
                'category': row[8]
            } for row in cursor.fetchall()]
            
            with open(filepath, 'w') as f:
                json.dump(passwords, f, indent=2)
    
    def import_passwords(self, filepath: str):
        """Import passwords from a JSON file."""
        with open(filepath, 'r') as f:
            passwords = json.load(f)
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO passwords (title, username, password, url, notes, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [(pwd['title'], pwd['username'], pwd['password'],
                  pwd.get('url'), pwd.get('notes'), pwd.get('category', 'Uncategorized'))
                 for pwd in passwords])
    
    def __del__(self):
        """Clean up database connection."""
        if self._connection:
            self._connection.close() 
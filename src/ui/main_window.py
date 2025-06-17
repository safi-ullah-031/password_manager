from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QLabel, QComboBox, QMessageBox, QMenu, QAction, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QClipboard, QColor
from .password_dialog import PasswordDialog
from .setup_wizard import SetupWizard
from utils.security import SecurityManager
from utils.database import DatabaseManager
from utils.config import ConfigManager
import pyperclip
from typing import Optional, Dict, List

class SearchWorker(QThread):
    """Worker thread for performing password searches."""
    finished = pyqtSignal(list)
    
    def __init__(self, db_manager, query: str, category: Optional[str] = None):
        super().__init__()
        self.db_manager = db_manager
        self.query = query
        self.category = category
        self._is_running = True
    
    def run(self):
        """Run the search operation."""
        try:
            if not self._is_running:
                return
            results = self.db_manager.search_passwords(self.query, self.category)
            if self._is_running:  # Check again before emitting
                self.finished.emit(results)
        except Exception as e:
            print(f"Search error: {str(e)}")
            if self._is_running:
                self.finished.emit([])
                
    def stop(self):
        """Stop the search operation."""
        self._is_running = False
        self.wait()  # Wait for the thread to finish

class MainWindow(QMainWindow):
    def __init__(self, security_manager: SecurityManager, db_manager: DatabaseManager):
        super().__init__()
        self.security_manager = security_manager
        self.db_manager = db_manager
        self.config_manager = ConfigManager()
        
        self.search_worker = None
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.perform_search)
        
        self.init_ui()
        self.setup_auto_lock()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Secure Password Manager')
        self.setMinimumSize(800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('Search passwords...')
        self.search_input.textChanged.connect(self.on_search_text_changed)
        search_layout.addWidget(self.search_input)
        
        # Create category filter
        self.category_filter = QComboBox()
        self.category_filter.addItem('All Categories')
        self.update_category_filter()
        self.category_filter.currentTextChanged.connect(self.on_category_changed)
        search_layout.addWidget(self.category_filter)
        
        # Add new password button
        add_button = QPushButton('Add Password')
        add_button.clicked.connect(self.add_password)
        search_layout.addWidget(add_button)
        
        layout.addLayout(search_layout)
        
        # Create password table
        self.password_table = QTableWidget()
        self.password_table.setColumnCount(5)
        self.password_table.setHorizontalHeaderLabels(['Title', 'Username', 'Password', 'Category', 'Actions'])
        self.password_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.password_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.password_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.password_table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.password_table)
        
        # Create buttons
        button_layout = QHBoxLayout()
        export_button = QPushButton('Export')
        export_button.clicked.connect(self.export_passwords)
        button_layout.addWidget(export_button)
        
        import_button = QPushButton('Import')
        import_button.clicked.connect(self.import_passwords)
        button_layout.addWidget(import_button)
        
        layout.addLayout(button_layout)
        
        # Load initial data
        self.load_passwords()
        self.update_categories()
        
    def setup_auto_lock(self):
        """Setup auto-lock timer."""
        self.auto_lock_timer = QTimer(self)
        self.auto_lock_timer.timeout.connect(self.check_auto_lock)
        self.auto_lock_timer.start(1000)  # Check every second
        self.last_activity = QTimer.currentTime()
        
    def check_auto_lock(self):
        """Check if auto-lock should be triggered."""
        if not self.isActiveWindow():
            return
            
        current_time = QTimer.currentTime()
        timeout = self.config_manager.get_auto_lock_timeout() * 1000  # Convert to milliseconds
        
        if current_time.msecsSinceStartOfDay() - self.last_activity.msecsSinceStartOfDay() > timeout:
            self.lock_application()
    
    def lock_application(self):
        """Lock the application and show login screen."""
        # TODO: Implement lock screen
        pass
    
    def load_passwords(self):
        """Load passwords into the table."""
        passwords = self.db_manager.search_passwords('')
        self.update_password_table(passwords)
        
    def update_password_table(self, passwords: Optional[List[Dict]] = None):
        """Update the password table with search results or all passwords."""
        if passwords is None:
            passwords = self.db_manager.search_passwords('')
            
        self.password_table.setRowCount(len(passwords))
        for row, password in enumerate(passwords):
            # Store password ID and data for later use
            self.password_table.setItem(row, 0, QTableWidgetItem(password['title']))
            self.password_table.setItem(row, 1, QTableWidgetItem(password['username']))
            
            # Create password item with copy button
            password_item = QTableWidgetItem('••••••••')
            password_item.setData(Qt.UserRole, password['password'])  # Store actual password
            self.password_table.setItem(row, 2, password_item)
            
            self.password_table.setItem(row, 3, QTableWidgetItem(password['category']))
            
            # Add action buttons
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            copy_button = QPushButton('Copy')
            copy_button.clicked.connect(lambda checked, p=password['password']: self.copy_password(p))
            actions_layout.addWidget(copy_button)
            
            edit_button = QPushButton('Edit')
            edit_button.clicked.connect(lambda checked, p=password: self.edit_password(p))
            actions_layout.addWidget(edit_button)
            
            delete_button = QPushButton('Delete')
            delete_button.clicked.connect(lambda checked, p=password: self.delete_password(p))
            actions_layout.addWidget(delete_button)
            
            self.password_table.setCellWidget(row, 4, actions_widget)
            
        # Set alternating row colors
        for row in range(self.password_table.rowCount()):
            if row % 2 == 0:
                for col in range(self.password_table.columnCount()):
                    self.password_table.item(row, col).setBackground(QColor(240, 240, 240))
        
        self.password_table.resizeColumnsToContents()
        
    def update_categories(self):
        """Update the category filter dropdown."""
        current_category = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem('All Categories')
        
        categories = self.db_manager.get_all_categories()
        self.category_filter.addItems(categories)
        
        if current_category in categories:
            self.category_filter.setCurrentText(current_category)
        
    def on_search_text_changed(self):
        """Handle search text changes with debouncing."""
        self.search_timer.start(300)  # 300ms delay
        
    def perform_search(self):
        """Perform the actual search operation."""
        # Stop any existing search
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.stop()
            
        query = self.search_input.text()
        category = self.category_filter.currentText()
        if category == 'All Categories':
            category = None
            
        # Create and start search worker
        self.search_worker = SearchWorker(self.db_manager, query, category)
        self.search_worker.finished.connect(self.update_password_table)
        self.search_worker.start()
        
    def filter_by_category(self, category):
        """Filter passwords by category."""
        if category == 'All Categories':
            self.load_passwords()
        else:
            # TODO: Implement category filtering
            pass
        
    def add_password(self):
        """Show dialog to add a new password."""
        dialog = PasswordDialog(self)
        if dialog.exec_() == 1:
            self.load_passwords()
            self.update_categories()
        
    def edit_password(self, password_data: Dict):
        """Show dialog to edit an existing password."""
        dialog = PasswordDialog(self, password_data)
        if dialog.exec_() == 1:
            self.load_passwords()
            self.update_categories()
        
    def delete_password(self, password_data: Dict):
        """Delete a password after confirmation."""
        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f"Are you sure you want to delete the password for {password_data['title']}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_password(password_data['id'])
            self.load_passwords()
            self.update_categories()
        
    def copy_password(self, password: str):
        """Copy password to clipboard with timeout."""
        pyperclip.copy(password)
        QMessageBox.information(self, 'Success', 'Password copied to clipboard!')
        
    def closeEvent(self, event):
        """Handle application close event."""
        reply = QMessageBox.question(
            self, 'Confirm Exit',
            'Are you sure you want to exit?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Clean up resources
            if self.search_worker and self.search_worker.isRunning():
                self.search_worker.stop()
            event.accept()
        else:
            event.ignore()
        
    def update_category_filter(self):
        """Update the category filter dropdown."""
        current = self.category_filter.currentText()
        self.category_filter.clear()
        self.category_filter.addItem('All Categories')
        categories = self.db_manager.get_all_categories()
        self.category_filter.addItems(categories)
        if current in categories:
            self.category_filter.setCurrentText(current)
            
    def on_category_changed(self):
        """Handle category filter changes."""
        self.perform_search()
        
    def show_context_menu(self, position):
        """Show context menu for password table."""
        menu = QMenu()
        copy_action = QAction('Copy Password', self)
        edit_action = QAction('Edit', self)
        delete_action = QAction('Delete', self)
        
        menu.addAction(copy_action)
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        
        action = menu.exec_(self.password_table.mapToGlobal(position))
        if action:
            row = self.password_table.rowAt(position.y())
            if row >= 0:
                password_data = {
                    'id': row,
                    'title': self.password_table.item(row, 0).text(),
                    'username': self.password_table.item(row, 1).text(),
                    'password': self.password_table.item(row, 2).data(Qt.UserRole),
                    'category': self.password_table.item(row, 3).text()
                }
                
                if action == copy_action:
                    self.copy_password(password_data['password'])
                elif action == edit_action:
                    self.edit_password(password_data)
                elif action == delete_action:
                    self.delete_password(password_data)
                    
    def export_passwords(self):
        """Export passwords to a file."""
        try:
            file_path = QFileDialog.getSaveFileName(
                self, 'Export Passwords', '', 'JSON Files (*.json)'
            )[0]
            if file_path:
                self.db_manager.export_passwords(file_path)
                QMessageBox.information(self, 'Success', 'Passwords exported successfully!')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to export passwords: {str(e)}')
            
    def import_passwords(self):
        """Import passwords from a file."""
        try:
            file_path = QFileDialog.getOpenFileName(
                self, 'Import Passwords', '', 'JSON Files (*.json)'
            )[0]
            if file_path:
                self.db_manager.import_passwords(file_path)
                self.update_password_table()
                self.update_categories()
                QMessageBox.information(self, 'Success', 'Passwords imported successfully!')
        except Exception as e:
            QMessageBox.critical(self, 'Error', f'Failed to import passwords: {str(e)}') 
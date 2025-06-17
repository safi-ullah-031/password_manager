from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
                             QLabel, QComboBox, QMessageBox, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QClipboard
from .password_dialog import PasswordDialog
from .setup_wizard import SetupWizard
from utils.security import SecurityManager
from utils.database import DatabaseManager
from utils.config import ConfigManager

class SearchWorker(QThread):
    """Worker thread for performing password searches."""
    finished = pyqtSignal(list)
    
    def __init__(self, db_manager, query):
        super().__init__()
        self.db_manager = db_manager
        self.query = query
    
    def run(self):
        """Run the search operation."""
        results = self.db_manager.search_passwords(self.query)
        self.finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self, security_manager: SecurityManager, db_manager: DatabaseManager):
        super().__init__()
        self.security_manager = security_manager
        self.db_manager = db_manager
        self.config_manager = ConfigManager()
        
        self.search_worker = None
        self.search_timer = QTimer()
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
        self.category_filter.currentTextChanged.connect(self.filter_by_category)
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
        self.password_table.horizontalHeader().setStretchLastSection(True)
        self.password_table.setAlternatingRowColors(True)  # For better readability
        layout.addWidget(self.password_table)
        
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
        
    def update_password_table(self, passwords):
        """Update the password table with the given passwords."""
        self.password_table.setRowCount(len(passwords))
        
        for row, pwd in enumerate(passwords):
            # Title
            title_item = QTableWidgetItem(pwd['title'])
            title_item.setData(Qt.UserRole, pwd['id'])  # Store ID for later use
            self.password_table.setItem(row, 0, title_item)
            
            # Username
            self.password_table.setItem(row, 1, QTableWidgetItem(pwd['username']))
            
            # Password (masked)
            password_item = QTableWidgetItem('••••••••')
            password_item.setData(Qt.UserRole, pwd['password'])  # Store actual password
            self.password_table.setItem(row, 2, password_item)
            
            # Category
            self.password_table.setItem(row, 3, QTableWidgetItem(pwd['category']))
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            
            copy_btn = QPushButton('Copy')
            copy_btn.clicked.connect(lambda checked, r=row: self.copy_password(r))
            actions_layout.addWidget(copy_btn)
            
            edit_btn = QPushButton('Edit')
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_password(r))
            actions_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton('Delete')
            delete_btn.clicked.connect(lambda checked, r=row: self.delete_password(r))
            actions_layout.addWidget(delete_btn)
            
            self.password_table.setCellWidget(row, 4, actions_widget)
        
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
        self.search_timer.start(300)  # Wait 300ms before searching
        
    def perform_search(self):
        """Perform the actual search operation."""
        query = self.search_input.text()
        
        # Cancel any existing search
        if self.search_worker and self.search_worker.isRunning():
            self.search_worker.terminate()
            self.search_worker.wait()
        
        # Create and start new search worker
        self.search_worker = SearchWorker(self.db_manager, query)
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
        
    def edit_password(self, row):
        """Show dialog to edit a password."""
        password_id = self.password_table.item(row, 0).data(Qt.UserRole)
        dialog = PasswordDialog(self, password_id)
        if dialog.exec_() == 1:
            self.load_passwords()
            self.update_categories()
        
    def delete_password(self, row):
        """Delete a password after confirmation."""
        password_id = self.password_table.item(row, 0).data(Qt.UserRole)
        title = self.password_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, 'Confirm Deletion',
            f'Are you sure you want to delete the password for "{title}"?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_password(password_id)
            self.load_passwords()
            self.update_categories()
        
    def copy_password(self, row):
        """Copy password to clipboard."""
        password = self.password_table.item(row, 2).data(Qt.UserRole)
        clipboard = QApplication.clipboard()
        clipboard.setText(password)
        
        # Clear clipboard after timeout
        QTimer.singleShot(
            self.config_manager.get_clipboard_timeout() * 1000,
            lambda: clipboard.clear()
        )
        
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
                self.search_worker.terminate()
                self.search_worker.wait()
            event.accept()
        else:
            event.ignore() 
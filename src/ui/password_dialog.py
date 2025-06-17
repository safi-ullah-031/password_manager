from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QComboBox, QCheckBox,
                             QSpinBox, QMessageBox)
from PyQt5.QtCore import Qt
from utils.security import SecurityManager

class PasswordDialog(QDialog):
    def __init__(self, parent=None, password_id=None):
        super().__init__(parent)
        self.password_id = password_id
        self.security_manager = parent.security_manager
        self.db_manager = parent.db_manager
        
        self.init_ui()
        if password_id:
            self.load_password()
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle('Add Password' if not self.password_id else 'Edit Password')
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Title
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel('Title:'))
        self.title_input = QLineEdit()
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # Username
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel('Username:'))
        self.username_input = QLineEdit()
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel('Password:'))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_input)
        
        generate_btn = QPushButton('Generate')
        generate_btn.clicked.connect(self.generate_password)
        password_layout.addWidget(generate_btn)
        
        show_btn = QPushButton('Show')
        show_btn.setCheckable(True)
        show_btn.toggled.connect(self.toggle_password_visibility)
        password_layout.addWidget(show_btn)
        
        layout.addLayout(password_layout)
        
        # URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel('URL:'))
        self.url_input = QLineEdit()
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Category
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel('Category:'))
        self.category_input = QComboBox()
        self.category_input.setEditable(True)
        self.update_categories()
        category_layout.addWidget(self.category_input)
        layout.addLayout(category_layout)
        
        # Notes
        notes_layout = QHBoxLayout()
        notes_layout.addWidget(QLabel('Notes:'))
        self.notes_input = QLineEdit()
        notes_layout.addWidget(self.notes_input)
        layout.addLayout(notes_layout)
        
        # Password generator options
        generator_group = QVBoxLayout()
        generator_group.addWidget(QLabel('Password Generator Options:'))
        
        # Length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel('Length:'))
        self.length_input = QSpinBox()
        self.length_input.setRange(8, 128)
        self.length_input.setValue(16)
        length_layout.addWidget(self.length_input)
        generator_group.addLayout(length_layout)
        
        # Character sets
        self.use_uppercase = QCheckBox('Use Uppercase (A-Z)')
        self.use_uppercase.setChecked(True)
        generator_group.addWidget(self.use_uppercase)
        
        self.use_lowercase = QCheckBox('Use Lowercase (a-z)')
        self.use_lowercase.setChecked(True)
        generator_group.addWidget(self.use_lowercase)
        
        self.use_numbers = QCheckBox('Use Numbers (0-9)')
        self.use_numbers.setChecked(True)
        generator_group.addWidget(self.use_numbers)
        
        self.use_special = QCheckBox('Use Special Characters (!@#$%^&*)')
        self.use_special.setChecked(True)
        generator_group.addWidget(self.use_special)
        
        layout.addLayout(generator_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton('Save')
        save_btn.clicked.connect(self.save_password)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def update_categories(self):
        """Update the category dropdown with available categories."""
        self.category_input.clear()
        categories = self.db_manager.get_all_categories()
        self.category_input.addItems(categories)
        
    def load_password(self):
        """Load password data for editing."""
        password = self.db_manager.get_password(self.password_id)
        if password:
            self.title_input.setText(password['title'])
            self.username_input.setText(password['username'])
            self.password_input.setText(password['password'])
            self.url_input.setText(password['url'] or '')
            self.notes_input.setText(password['notes'] or '')
            
            # Set category
            index = self.category_input.findText(password['category'])
            if index >= 0:
                self.category_input.setCurrentIndex(index)
            else:
                self.category_input.setCurrentText(password['category'])
        
    def generate_password(self):
        """Generate a new password using the current settings."""
        try:
            password = self.security_manager.generate_password(
                length=self.length_input.value(),
                use_uppercase=self.use_uppercase.isChecked(),
                use_lowercase=self.use_lowercase.isChecked(),
                use_numbers=self.use_numbers.isChecked(),
                use_special=self.use_special.isChecked()
            )
            self.password_input.setText(password)
        except ValueError as e:
            QMessageBox.warning(self, 'Error', str(e))
        
    def toggle_password_visibility(self, checked):
        """Toggle password visibility."""
        self.password_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        )
        
    def save_password(self):
        """Save the password entry."""
        title = self.title_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        url = self.url_input.text().strip()
        notes = self.notes_input.text().strip()
        category = self.category_input.currentText().strip()
        
        if not title or not username or not password:
            QMessageBox.warning(
                self, 'Error',
                'Title, username, and password are required fields.'
            )
            return
        
        try:
            if self.password_id:
                # Update existing password
                self.db_manager.update_password(
                    self.password_id,
                    title=title,
                    username=username,
                    password=password,
                    url=url,
                    notes=notes,
                    category=category
                )
            else:
                # Add new password
                self.db_manager.add_password(
                    title=title,
                    username=username,
                    password=password,
                    url=url,
                    notes=notes,
                    category=category
                )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, 'Error',
                f'Failed to save password: {str(e)}'
            ) 
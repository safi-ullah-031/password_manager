from PyQt5.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMessageBox,
                             QSpinBox, QCheckBox)
from PyQt5.QtCore import Qt
from utils.security import SecurityManager
from utils.config import ConfigManager

class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle('Welcome to Secure Password Manager')
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            'Welcome to the Secure Password Manager setup wizard. '
            'This wizard will help you configure your password manager '
            'and create your master password.'
        ))
        
        layout.addWidget(QLabel(
            '\nYour master password is the key to all your stored passwords. '
            'Make sure to choose a strong password and keep it safe.'
        ))

class MasterPasswordPage(QWizardPage):
    def __init__(self, security_manager: SecurityManager):
        super().__init__()
        self.security_manager = security_manager
        self.setTitle('Create Master Password')
        
        layout = QVBoxLayout(self)
        
        # Password input
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel('Master Password:'))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Confirm password
        confirm_layout = QHBoxLayout()
        confirm_layout.addWidget(QLabel('Confirm Password:'))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        confirm_layout.addWidget(self.confirm_input)
        layout.addLayout(confirm_layout)
        
        # Password strength indicator
        self.strength_label = QLabel()
        layout.addWidget(self.strength_label)
        
        # Connect signals
        self.password_input.textChanged.connect(self.check_password_strength)
        self.confirm_input.textChanged.connect(self.completeChanged)
        
        self.registerField('master_password*', self.password_input)
        self.registerField('confirm_password*', self.confirm_input)
    
    def check_password_strength(self):
        """Check the strength of the master password."""
        password = self.password_input.text()
        
        if not password:
            self.strength_label.setText('')
            return
        
        # Check password length
        if len(password) < 12:
            self.strength_label.setText('Password is too short (minimum 12 characters)')
            self.strength_label.setStyleSheet('color: red')
            return
        
        # Check for character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(not c.isalnum() for c in password)
        
        # Calculate strength
        strength = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength == 4:
            self.strength_label.setText('Strong password')
            self.strength_label.setStyleSheet('color: green')
        elif strength == 3:
            self.strength_label.setText('Good password')
            self.strength_label.setStyleSheet('color: orange')
        else:
            self.strength_label.setText('Weak password - add more character types')
            self.strength_label.setStyleSheet('color: red')
    
    def validatePage(self) -> bool:
        """Validate the master password page."""
        if self.password_input.text() != self.confirm_input.text():
            QMessageBox.warning(
                self, 'Error',
                'Passwords do not match!'
            )
            return False
        
        if len(self.password_input.text()) < 12:
            QMessageBox.warning(
                self, 'Error',
                'Password must be at least 12 characters long!'
            )
            return False
        
        return True

class SecuritySettingsPage(QWizardPage):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.setTitle('Security Settings')
        
        layout = QVBoxLayout(self)
        
        # Auto-lock timeout
        lock_layout = QHBoxLayout()
        lock_layout.addWidget(QLabel('Auto-lock timeout (minutes):'))
        self.lock_timeout = QSpinBox()
        self.lock_timeout.setRange(1, 60)
        self.lock_timeout.setValue(5)
        lock_layout.addWidget(self.lock_timeout)
        layout.addLayout(lock_layout)
        
        # Clipboard timeout
        clipboard_layout = QHBoxLayout()
        clipboard_layout.addWidget(QLabel('Clipboard timeout (seconds):'))
        self.clipboard_timeout = QSpinBox()
        self.clipboard_timeout.setRange(5, 300)
        self.clipboard_timeout.setValue(30)
        clipboard_layout.addWidget(self.clipboard_timeout)
        layout.addLayout(clipboard_layout)
        
        # Password generator settings
        layout.addWidget(QLabel('\nDefault Password Generator Settings:'))
        
        # Length
        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel('Default length:'))
        self.length_input = QSpinBox()
        self.length_input.setRange(8, 128)
        self.length_input.setValue(16)
        length_layout.addWidget(self.length_input)
        layout.addLayout(length_layout)
        
        # Character sets
        self.use_uppercase = QCheckBox('Use Uppercase (A-Z)')
        self.use_uppercase.setChecked(True)
        layout.addWidget(self.use_uppercase)
        
        self.use_lowercase = QCheckBox('Use Lowercase (a-z)')
        self.use_lowercase.setChecked(True)
        layout.addWidget(self.use_lowercase)
        
        self.use_numbers = QCheckBox('Use Numbers (0-9)')
        self.use_numbers.setChecked(True)
        layout.addWidget(self.use_numbers)
        
        self.use_special = QCheckBox('Use Special Characters (!@#$%^&*)')
        self.use_special.setChecked(True)
        layout.addWidget(self.use_special)

class SetupWizard(QWizard):
    def __init__(self, security_manager: SecurityManager, config_manager: ConfigManager):
        super().__init__()
        self.security_manager = security_manager
        self.config_manager = config_manager
        
        self.setWindowTitle('Secure Password Manager Setup')
        self.setWizardStyle(QWizard.ModernStyle)
        
        # Add pages
        self.addPage(WelcomePage())
        self.addPage(MasterPasswordPage(security_manager))
        self.addPage(SecuritySettingsPage(config_manager))
        
        # Connect signals
        self.finished.connect(self.save_settings)
    
    def save_settings(self, result):
        """Save the settings when the wizard is finished."""
        if result == 1:  # Wizard was accepted
            # Save master password
            master_password = self.field('master_password')
            self.security_manager.generate_master_key(master_password)
            
            # Save security settings
            self.config_manager.set_auto_lock_timeout(
                self.field('lock_timeout') * 60  # Convert to seconds
            )
            self.config_manager.set_clipboard_timeout(
                self.field('clipboard_timeout')
            )
            
            # Save password generator settings
            self.config_manager.set_password_generator_settings({
                'length': self.field('length_input'),
                'use_uppercase': self.field('use_uppercase'),
                'use_lowercase': self.field('use_lowercase'),
                'use_numbers': self.field('use_numbers'),
                'use_special': self.field('use_special')
            })
            
            # Mark as configured
            self.config_manager.set_configured(True) 
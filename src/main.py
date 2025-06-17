import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt
from ui.main_window import MainWindow
from utils.security import SecurityManager
from utils.database import DatabaseManager
from utils.config import ConfigManager

class PasswordManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.security_manager = SecurityManager()
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        
        # Set application style
        self.app.setStyle('Fusion')
        
        # Initialize main window
        self.main_window = MainWindow(self.security_manager, self.db_manager)
        
    def run(self):
        # Check if first run
        if not self.config_manager.is_configured():
            self.show_first_run_setup()
        
        # Show main window
        self.main_window.show()
        return self.app.exec_()
    
    def show_first_run_setup(self):
        from ui.setup_wizard import SetupWizard
        wizard = SetupWizard(self.security_manager, self.config_manager)
        if wizard.exec_() != 1:  # If setup was cancelled
            sys.exit(0)

def main():
    # Ensure the data directory exists
    os.makedirs('data', exist_ok=True)
    
    try:
        # Create and run the application
        password_manager = PasswordManager()
        sys.exit(password_manager.run())
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import json
import re
import time
import threading
from datetime import datetime
import uuid as uuid_lib  # Importiere die uuid-Bibliothek für robuste UUID-Validierung

class DataDeletionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Deletion Tool")
        self.root.geometry("800x600")
        self.processing = False
        self.deleted_count = 0
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create input frame
        input_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="10")
        input_frame.pack(fill=tk.X, pady=5)
        
        # Server input
        ttk.Label(input_frame, text="Server Address:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar()
        self.server_entry = ttk.Entry(input_frame, textvariable=self.server_var, width=40)
        self.server_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # UUID input
        ttk.Label(input_frame, text="UUID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.uuid_var = tk.StringVar()
        self.uuid_entry = ttk.Entry(input_frame, textvariable=self.uuid_var, width=40)
        self.uuid_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Start time input
        ttk.Label(input_frame, text="Start Time (dd.MM.yyyy HH:mm or UNIX timestamp):").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.start_time_var = tk.StringVar()
        self.start_time_entry = ttk.Entry(input_frame, textvariable=self.start_time_var, width=40)
        self.start_time_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # End time input
        ttk.Label(input_frame, text="End Time (dd.MM.yyyy HH:mm or UNIX timestamp):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.end_time_var = tk.StringVar()
        self.end_time_entry = ttk.Entry(input_frame, textvariable=self.end_time_var, width=40)
        self.end_time_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Max value input
        ttk.Label(input_frame, text="Max Value (xxx.xx):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_value_var = tk.StringVar()
        self.max_value_entry = ttk.Entry(input_frame, textvariable=self.max_value_var, width=40)
        self.max_value_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Start button
        self.start_button = ttk.Button(button_frame, text="Start Process", command=self.start_process)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(button_frame, text="Stop Process", command=self.stop_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=5)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var).pack(fill=tk.X)
        
        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        
        # Initialize log
        self.log("Application started", "INFO")
    
    def log(self, message, level="INFO"):
        """Add a message to the log with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        self.log_text.insert(tk.END, log_message, level)
        self.log_text.see(tk.END)
    
    def validate_inputs(self):
        """Validate all input fields"""
        # Validate server
        server = self.server_var.get().strip()
        if not server or not self.is_valid_ip_or_domain(server) or server.endswith('/'):
            self.log("Invalid server address. Please enter a valid IP or domain without trailing slash.", "ERROR")
            return False
        
        # Validate UUID
        uuid = self.uuid_var.get().strip()
        if not uuid or not self.is_valid_uuid(uuid):
            self.log("Invalid UUID format. Please enter a valid UUID.", "ERROR")
            return False
        
        # Validate start time
        start_time = self.start_time_var.get().strip()
        start_timestamp = self.convert_to_timestamp(start_time)
        if start_timestamp is None:
            self.log("Invalid start time format. Use dd.MM.yyyy HH:mm or UNIX timestamp.", "ERROR")
            return False
        
        # Validate end time
        end_time = self.end_time_var.get().strip()
        end_timestamp = self.convert_to_timestamp(end_time)
        if end_timestamp is None:
            self.log("Invalid end time format. Use dd.MM.yyyy HH:mm or UNIX timestamp.", "ERROR")
            return False
        
        # Validate max value
        max_value = self.max_value_var.get().strip()
        if not self.is_valid_decimal(max_value):
            self.log("Invalid max value format. Please use xxx.xx format.", "ERROR")
            return False
        
        return True
    
    def is_valid_ip_or_domain(self, value):
        """Check if the value is a valid IP address or domain name"""
        ip_pattern = r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"
        domain_pattern = r"^(?:(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.)+[A-Za-z]{2,6}$"
        return bool(re.match(ip_pattern, value) or re.match(domain_pattern, value))
    
    def is_valid_uuid(self, value):
        """
        Robuste Überprüfung, ob der Wert eine gültige UUID ist.
        Verwendet sowohl Regex-Muster als auch die uuid-Bibliothek für maximale Sicherheit.
        """
        # Regex-Muster für UUID-Format
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        
        # Erste Überprüfung mit Regex
        if not re.match(uuid_pattern, value):
            return False
        
        # Zweite Überprüfung mit der uuid-Bibliothek
        try:
            # Versuche, den String in ein UUID-Objekt zu konvertieren
            uuid_obj = uuid_lib.UUID(value)
            # Überprüfe, ob die String-Repräsentation mit dem Original übereinstimmt
            return str(uuid_obj) == value.lower()
        except ValueError:
            # Wenn die Konvertierung fehlschlägt, ist es keine gültige UUID
            return False
    
    def convert_to_timestamp(self, value):
        """Convert a date string to UNIX timestamp or validate existing timestamp"""
        # Check if it's already a timestamp
        if value.isdigit():
            return int(value)
        
        # Try to convert from date format
        try:
            dt = datetime.strptime(value, "%d.%m.%Y %H:%M")
            timestamp = int((dt - datetime(1970, 1, 1)).total_seconds() * 1000)
            return timestamp
        except ValueError:
            return None
    
    def is_valid_decimal(self, value):
        """Check if the value is in xxx.xx format"""
        return bool(re.match(r'^\d+\.\d{2}$', value))
    
    def get_json_data(self, url):
        """Fetch JSON data from the given URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                self.log(f"Failed to fetch data: HTTP {response.status_code}", "ERROR")
                return None
        except Exception as e:
            self.log(f"Error fetching JSON data: {str(e)}", "ERROR")
            return None
    
    def delete_data(self, url):
        """Delete data using the given URL"""
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
            else:
                self.log(f"Failed to delete data: HTTP {response.status_code}", "ERROR")
                return False
        except Exception as e:
            self.log(f"Error deleting data: {str(e)}", "ERROR")
            return False
    
    def start_process(self):
        """Start the data deletion process"""
        if not self.validate_inputs():
            return
        
        self.processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Processing...")
        
        # Prepare parameters
        params = {
            "server": self.server_var.get().strip(),
            "uuid": self.uuid_var.get().strip(),
            "start_time": self.convert_to_timestamp(self.start_time_var.get().strip()),
            "end_time": self.convert_to_timestamp(self.end_time_var.get().strip()),
            "max_value": self.max_value_var.get().strip()
        }
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_data_deletion, args=(params,), daemon=True).start()
    
    def stop_process(self):
        """Stop the data deletion process"""
        self.processing = False
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Stopped")
        self.log("Process stopped by user", "WARNING")
    
    def process_data_deletion(self, params):
        """Process data deletion based on the given parameters"""
        server = params["server"]
        uuid_value = params["uuid"]
        start_time = params["start_time"]
        end_time = params["end_time"]
        max_value = float(params["max_value"])  # Sicherstellen, dass es ein float ist
        
        base_url = f"http://{server}/data/{uuid_value}.json?from={start_time}&to={end_time}"
        self.deleted_count = 0
        
        self.log("Starting data deletion process...", "INFO")
        self.log(f"Using URL: {base_url}", "INFO")
        
        # Einfache Schleife wie im PowerShell-Skript
        while self.processing:
            json_data = self.get_json_data(base_url)
            
            if not json_data or "data" not in json_data or "max" not in json_data["data"]:
                self.log("Invalid JSON data structure", "ERROR")
                break
            
            max_entry = json_data["data"]["max"]
            timestamp = max_entry[0]
            current_max_value = float(max_entry[1])  # Sicherstellen, dass es ein float ist
            
            self.log(f"Current max value: {current_max_value}, Threshold: {max_value}", "INFO")
            
            if current_max_value > max_value:
                self.log(f"Found value exceeding threshold: [{timestamp}, {current_max_value}]", "WARNING")
                delete_url = f"http://{server}/data/{uuid_value}.json?operation=delete&ts={timestamp}"
                
                if self.delete_data(delete_url):
                    self.deleted_count += 1
                    self.log(f"Successfully deleted entry with timestamp {timestamp}", "SUCCESS")
                    self.status_var.set(f"Deleted: {self.deleted_count}")
                else:
                    self.log("Failed to delete entry. Stopping process.", "ERROR")
                    break
                
                # Pause wie im PowerShell-Skript
                time.sleep(1)
            else:
                self.log(f"Max value ({current_max_value}) is not higher than threshold ({max_value})", "INFO")
                break  # Beende die Schleife, wenn kein Wert über dem Schwellenwert liegt
        
        self.log(f"Total entries deleted: {self.deleted_count}", "INFO")
        self.status_var.set(f"Completed. Deleted: {self.deleted_count}")
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = DataDeletionApp(root)
    root.mainloop()

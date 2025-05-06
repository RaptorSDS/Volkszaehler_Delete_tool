import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import json
import re
import time
import threading
from datetime import datetime
import uuid as uuid_lib

class DataDeletionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Data Deletion Tool v0.8b")
        self.root.geometry("850x650")
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
        self.create_tooltip(self.server_entry, "Enter IP address or domain name without http:// (e.g., 192.168.1.100 or example.com)")
        
        # UUID input
        ttk.Label(input_frame, text="UUID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.uuid_var = tk.StringVar()
        self.uuid_entry = ttk.Entry(input_frame, textvariable=self.uuid_var, width=40)
        self.uuid_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.uuid_entry, "Enter UUID in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        
        # Start time input
        ttk.Label(input_frame, text="Start Time:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.start_time_var = tk.StringVar()
        self.start_time_entry = ttk.Entry(input_frame, textvariable=self.start_time_var, width=40)
        self.start_time_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.start_time_entry, "Enter start time as dd.MM.yyyy HH:mm (e.g., 01.05.2025 14:30) or UNIX timestamp in milliseconds")
        
        # End time input
        ttk.Label(input_frame, text="End Time:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.end_time_var = tk.StringVar()
        self.end_time_entry = ttk.Entry(input_frame, textvariable=self.end_time_var, width=40)
        self.end_time_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.end_time_entry, "Enter end time as dd.MM.yyyy HH:mm (e.g., 02.05.2025 14:30) or UNIX timestamp in milliseconds")
        
        # Max value input with sign selection
        max_value_frame = ttk.Frame(input_frame)
        max_value_frame.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Sign selection for max value
        self.max_value_sign_var = tk.StringVar(value="+")
        sign_combo = ttk.Combobox(max_value_frame, textvariable=self.max_value_sign_var, width=3, state="readonly")
        sign_combo["values"] = ["+", "-"]
        sign_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # Max value entry
        ttk.Label(input_frame, text="Max Value:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.max_value_var = tk.StringVar()
        self.max_value_entry = ttk.Entry(max_value_frame, textvariable=self.max_value_var, width=36)
        self.max_value_entry.pack(side=tk.LEFT)
        self.create_tooltip(max_value_frame, "Enter max value as xxx.xx or whole number (e.g., 123.45 or 30000)\nUse the sign selector for negative thresholds")
        
        # Delay selection
        ttk.Label(input_frame, text="Processing Delay:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value="1000")
        delay_combo = ttk.Combobox(input_frame, textvariable=self.delay_var, width=38, state="readonly")
        delay_combo["values"] = ["200", "500", "1000", "2000"]
        delay_combo.grid(row=5, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(delay_combo, "Select delay between operations in milliseconds:\n200ms: Local x86 systems\n500ms: Server (local or remote)\n1000ms: Raspberry Pi\n2000ms: Slow systems")
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Start button
        self.start_button = ttk.Button(button_frame, text="Start Process", command=self.start_process)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Stop button
        self.stop_button = ttk.Button(button_frame, text="Stop Process", command=self.stop_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Help button
        self.help_button = ttk.Button(button_frame, text="?", width=3, command=self.show_help)
        self.help_button.pack(side=tk.RIGHT, padx=5)
        
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
        
        # Version and author info
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=5)
        version_label = ttk.Label(version_frame, text="v0.8b | Tobias aka Raptorsds | github.com/raptorsds | Created with Claude | MIT License")
        version_label.pack(side=tk.RIGHT)
        
        # Initialize log
        self.log("Application started", "INFO")
    
    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        def enter(event):
            self.tooltip = tk.Toplevel(self.root)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")
            
            label = ttk.Label(self.tooltip, text=text, justify=tk.LEFT,
                             background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                             wraplength=300)
            label.pack(padx=5, pady=5)
        
        def leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
    
    def show_help(self):
        """Show help information"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - Data Deletion Tool")
        help_window.geometry("600x400")
        
        help_text = """
Data Deletion Tool v0.5b
By Tobias aka Raptorsds (github.com/raptorsds)
Created with Claude | MIT License

This tool helps you delete data points that exceed a specified maximum value.

Instructions:
1. Server Address: Enter the IP or domain name without http:// or https://
2. UUID: Enter the UUID of the data set you want to process
3. Start/End Time: Enter time range in dd.MM.yyyy HH:mm format or as UNIX timestamp
4. Max Value: Enter the threshold value (any data point above this will be deleted)
   - Use the +/- selector to set positive or negative thresholds
   - For negative thresholds, values below the threshold will be deleted
   - Example: With -4000, values like -6000 will be deleted, but -3990 will remain
5. Processing Delay: Select appropriate delay based on your system:
   - 200ms: Fast local x86 systems
   - 500ms: Server environments (local or remote)
   - 1000ms: Raspberry Pi or similar devices
   - 2000ms: Slow systems or high-latency connections

The tool will fetch data points and delete any that exceed the specified max value.
Progress and results will be shown in the log area.
        """
        
        help_scroll = scrolledtext.ScrolledText(help_window, wrap=tk.WORD)
        help_scroll.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        help_scroll.insert(tk.END, help_text)
        help_scroll.config(state=tk.DISABLED)
    
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
        if not self.is_valid_decimal_or_integer(max_value):
            self.log("Invalid max value format. Please use xxx.xx format or whole number.", "ERROR")
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
    
    def is_valid_decimal_or_integer(self, value):
        """Check if the value is in xxx.xx format or a whole number"""
        # Check for decimal format (xxx.xx)
        if re.match(r'^\d+\.\d{2}$', value):
            return True
        
        # Check for integer format
        if value.isdigit():
            return True
            
        return False
    
    def format_max_value(self, value):
        """Format max value to ensure it has two decimal places"""
        if value.isdigit():
            # If it's a whole number, add .00
            return f"{value}.00"
        return value
    
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
        max_value_raw = self.max_value_var.get().strip()
        max_value_formatted = self.format_max_value(max_value_raw)
        
        # Apply sign to max value
        sign = self.max_value_sign_var.get()
        if sign == "-":
            max_value_with_sign = f"-{max_value_formatted}"
        else:
            max_value_with_sign = max_value_formatted
        
        params = {
            "server": self.server_var.get().strip(),
            "uuid": self.uuid_var.get().strip(),
            "start_time": self.convert_to_timestamp(self.start_time_var.get().strip()),
            "end_time": self.convert_to_timestamp(self.end_time_var.get().strip()),
            "max_value": max_value_with_sign,
            "delay_ms": int(self.delay_var.get())
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
        max_value_str = params["max_value"]
        delay_ms = params["delay_ms"]
        
        # Convert max_value to float for comparison
        max_value = float(max_value_str)
        
        base_url = f"http://{server}/data/{uuid_value}.json?from={start_time}&to={end_time}"
        self.deleted_count = 0
        
        self.log("Starting data deletion process...", "INFO")
        self.log(f"Using URL: {base_url}", "INFO")
        self.log(f"Max value threshold: {max_value_str}", "INFO")
        self.log(f"Processing delay: {delay_ms}ms", "INFO")
        
        # Process loop
        while self.processing:
            json_data = self.get_json_data(base_url)
            
            if not json_data or "data" not in json_data or "max" not in json_data["data"]:
                self.log("Invalid JSON data structure or no data found", "ERROR")
                break
            
            max_entry = json_data["data"]["max"]
            timestamp = max_entry[0]
            current_max_value = float(max_entry[1])
            
            self.log(f"Current max value: {current_max_value}, Threshold: {max_value}", "INFO")
            
            # Check if value exceeds threshold (considering sign)
            value_exceeds_threshold = False
            if max_value >= 0:
                # For positive thresholds, delete if value is greater
                value_exceeds_threshold = current_max_value > max_value
            else:
                # For negative thresholds, delete if value is less (more negative)
                value_exceeds_threshold = current_max_value < max_value
            
            if value_exceeds_threshold:
                self.log(f"Found value exceeding threshold: [{timestamp}, {current_max_value}]", "WARNING")
                delete_url = f"http://{server}/data/{uuid_value}.json?operation=delete&ts={timestamp}"
                
                if self.delete_data(delete_url):
                    self.deleted_count += 1
                    self.log(f"Successfully deleted entry with timestamp {timestamp}", "SUCCESS")
                    self.status_var.set(f"Deleted: {self.deleted_count}")
                else:
                    self.log("Failed to delete entry. Stopping process.", "ERROR")
                    break
                
                # Pause according to selected delay
                time.sleep(delay_ms / 1000)
            else:
                self.log(f"No values exceeding threshold found. Process complete.", "INFO")
                break
        
        self.log(f"Total entries deleted: {self.deleted_count}", "INFO")
        self.status_var.set(f"Completed. Deleted: {self.deleted_count}")
        self.processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = DataDeletionApp(root)
    root.mainloop()
import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import json
import os
import queue
import re
import subprocess
import sys
import threading
from datetime import datetime
import uuid as uuid_lib

__version__ = "0.9"
APP_NAME = "Data Deletion Tool"

# Connect / read timeout in seconds for every HTTP request
HTTP_TIMEOUT = (5, 30)

# Max number of matching points listed in the log during a dry run
DRY_RUN_LIST_LIMIT = 50

# Settings and log files are stored per user (no admin rights needed)
APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config"),
                       "VZ_Delete_Tool")
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")
LOG_DIR = os.path.join(APP_DIR, "logs")

SERVER_EXAMPLES = ("Examples: 192.168.1.100 | raspberrypi | vz.example.com:8080 | "
                   "https://vz.example.com/middleware.php")

IPV4_OCTET = r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_PATTERN = rf"^{IPV4_OCTET}(\.{IPV4_OCTET}){{3}}$"
HOST_LABEL = r"(?!-)[A-Za-z0-9-]{1,63}(?<!-)"
HOSTNAME_PATTERN = rf"^{HOST_LABEL}(\.{HOST_LABEL})*$"
SERVER_PATTERN = r"^(?:(https?)://)?([^/:]+)(?::(\d{1,5}))?(/[A-Za-z0-9._~%/-]*)?$"


def is_valid_host(host):
    """Check if host is a valid IPv4 address (0-255 per octet) or host/domain name"""
    if re.fullmatch(r"[\d.]+", host):
        # Only digits and dots: must be a real IPv4 address (rejects e.g. 999.999.999.999)
        return bool(re.match(IPV4_PATTERN, host))
    return len(host) <= 253 and bool(re.match(HOSTNAME_PATTERN, host))


def parse_server(value):
    """
    Build the middleware base URL from the server input.
    Accepts [http:// or https://]host[:port][/path], e.g. 192.168.1.100,
    raspberrypi, vz.example.com:8080 or https://vz.example.com/middleware.php.
    Without scheme http:// is used. Returns None if the input is invalid.
    """
    match = re.match(SERVER_PATTERN, value.strip(), re.IGNORECASE)
    if not match:
        return None
    scheme, host, port, path = match.groups()
    if not is_valid_host(host):
        return None
    if port is not None and not 1 <= int(port) <= 65535:
        return None
    base_url = f"{(scheme or 'http').lower()}://{host}"
    if port:
        base_url += f":{int(port)}"
    return base_url + (path or "").rstrip("/")


def is_valid_uuid(value):
    """Check if the value is a valid UUID in format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"""
    if not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', value):
        return False
    try:
        return str(uuid_lib.UUID(value)) == value.lower()
    except ValueError:
        return False


def convert_to_timestamp(value):
    """Convert dd.MM.yyyy HH:mm (local time) or a UNIX timestamp in ms to a UNIX timestamp in ms"""
    value = value.strip()
    if value.isdigit():
        return int(value)
    try:
        dt = datetime.strptime(value, "%d.%m.%Y %H:%M")
        # Naive datetime -> interpreted as local time of this PC (incl. daylight saving time)
        return int(dt.timestamp() * 1000)
    except (ValueError, OverflowError, OSError):
        return None


def format_timestamp(timestamp_ms):
    """Format a UNIX timestamp in ms as local time for the log"""
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%d.%m.%Y %H:%M:%S")
    except (ValueError, OverflowError, OSError):
        return str(timestamp_ms)


def is_valid_decimal_or_integer(value):
    """Check if the value is in xxx.xx format or a whole number"""
    return bool(re.match(r'^\d+\.\d{2}$', value)) or value.isdigit()


def exceeds_threshold(value, threshold, negative):
    """
    Positive threshold: values above the threshold exceed it.
    Negative threshold: values below the threshold exceed it (e.g. -6000 < -4000).
    """
    return value < threshold if negative else value > threshold


def middleware_error(payload):
    """Return the error message if the middleware answered with an exception, else None"""
    if isinstance(payload, dict) and "exception" in payload:
        exception = payload["exception"]
        if isinstance(exception, dict):
            return exception.get("message") or exception.get("type") or str(exception)
        return str(exception)
    return None


class DataDeletionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{__version__}")
        self.root.geometry("850x720")
        self.processing = False
        self.deleted_count = 0
        self.stop_event = threading.Event()
        self.ui_queue = queue.Queue()
        self.session = requests.Session()
        self.tooltip = None
        self.log_file_error_shown = False

        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create input frame
        input_frame = ttk.LabelFrame(main_frame, text="Input Parameters", padding="10")
        input_frame.pack(fill=tk.X, pady=5)

        # Server input
        ttk.Label(input_frame, text="Server Address:").grid(row=0, column=0, sticky=tk.W, pady=(5, 0))
        self.server_var = tk.StringVar()
        self.server_entry = ttk.Entry(input_frame, textvariable=self.server_var, width=60)
        self.server_entry.grid(row=0, column=1, sticky=tk.W, pady=(5, 0))
        self.create_tooltip(self.server_entry,
                            "IP address or host name, optional with http:// or https://, port and middleware path.\n"
                            "Without http:// or https:// the tool uses http://.\n" + SERVER_EXAMPLES)

        # Info line with supported server formats
        ttk.Label(input_frame, text=SERVER_EXAMPLES, foreground="gray").grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        # UUID input
        ttk.Label(input_frame, text="UUID:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.uuid_var = tk.StringVar()
        self.uuid_entry = ttk.Entry(input_frame, textvariable=self.uuid_var, width=60)
        self.uuid_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.uuid_entry, "Enter UUID in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")

        # Start time input
        ttk.Label(input_frame, text="Start Time:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.start_time_var = tk.StringVar()
        self.start_time_entry = ttk.Entry(input_frame, textvariable=self.start_time_var, width=60)
        self.start_time_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.start_time_entry, "Enter start time as dd.MM.yyyy HH:mm in local time (e.g., 01.05.2025 14:30) or UNIX timestamp in milliseconds")

        # End time input
        ttk.Label(input_frame, text="End Time:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.end_time_var = tk.StringVar()
        self.end_time_entry = ttk.Entry(input_frame, textvariable=self.end_time_var, width=60)
        self.end_time_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(self.end_time_entry, "Enter end time as dd.MM.yyyy HH:mm in local time (e.g., 02.05.2025 14:30) or UNIX timestamp in milliseconds")

        # Max value input with sign selection
        ttk.Label(input_frame, text="Max Value:").grid(row=5, column=0, sticky=tk.W, pady=5)
        max_value_frame = ttk.Frame(input_frame)
        max_value_frame.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Sign selection for max value
        self.max_value_sign_var = tk.StringVar(value="+")
        sign_combo = ttk.Combobox(max_value_frame, textvariable=self.max_value_sign_var, width=3, state="readonly")
        sign_combo["values"] = ["+", "-"]
        sign_combo.pack(side=tk.LEFT, padx=(0, 5))

        # Max value entry
        self.max_value_var = tk.StringVar()
        self.max_value_entry = ttk.Entry(max_value_frame, textvariable=self.max_value_var, width=54)
        self.max_value_entry.pack(side=tk.LEFT)
        self.create_tooltip(max_value_frame, "Enter max value as xxx.xx or whole number (e.g., 123.45 or 30000)\n"
                                             "+ : values above the threshold are deleted\n"
                                             "- : values below the negative threshold are deleted")

        # Delay selection
        ttk.Label(input_frame, text="Processing Delay:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value="1000")
        delay_combo = ttk.Combobox(input_frame, textvariable=self.delay_var, width=58, state="readonly")
        delay_combo["values"] = ["200", "500", "1000", "2000"]
        delay_combo.grid(row=6, column=1, sticky=tk.W, pady=5)
        self.create_tooltip(delay_combo, "Select delay between operations in milliseconds:\n200ms: Local x86 systems\n500ms: Server (local or remote)\n1000ms: Raspberry Pi\n2000ms: Slow systems")

        # Dry run option
        self.dry_run_var = tk.BooleanVar(value=False)
        dry_run_check = ttk.Checkbutton(input_frame, text="Dry run (only show matching values, delete nothing)",
                                        variable=self.dry_run_var)
        dry_run_check.grid(row=7, column=1, sticky=tk.W, pady=5)

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

        # Log folder button
        self.log_folder_button = ttk.Button(button_frame, text="Open Log Folder", command=self.open_log_folder)
        self.log_folder_button.pack(side=tk.RIGHT, padx=5)

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
        version_label = ttk.Label(version_frame, text=f"v{__version__} | Tobias aka Raptorsds | github.com/raptorsds | Created with Claude | MIT License")
        version_label.pack(side=tk.RIGHT)

        # Process log/status messages from the worker thread in the GUI thread
        self.root.after(100, self.process_ui_queue)

        self.load_settings()

        # Initialize log
        self.log("Application started", "INFO")

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget"""
        def enter(event):
            self.hide_tooltip()
            self.tooltip = tk.Toplevel(self.root)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{event.x_root+15}+{event.y_root+10}")

            label = ttk.Label(self.tooltip, text=text, justify=tk.LEFT,
                             background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                             wraplength=400)
            label.pack(padx=5, pady=5)

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", lambda event: self.hide_tooltip())

    def hide_tooltip(self):
        """Destroy the currently shown tooltip, if any"""
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None

    def show_help(self):
        """Show help information"""
        help_window = tk.Toplevel(self.root)
        help_window.title(f"Help - {APP_NAME}")
        help_window.geometry("720x640")

        notebook = ttk.Notebook(help_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: usage instructions
        usage_tab = ttk.Frame(notebook)
        notebook.add(usage_tab, text="Instructions")

        help_text = f"""
{APP_NAME} v{__version__}
By Tobias aka Raptorsds (github.com/raptorsds)
Created with Claude | MIT License

This tool helps you delete data points that exceed a specified maximum value.

Requirement: the database user vz@localhost needs the DELETE privilege,
see tab "DB Permissions".

Instructions:
1. Server Address: IP address or host name of the middleware
   - Optional with http:// or https:// (default: http://)
   - Optional with port, e.g. vz.example.com:8080
   - Optional with middleware path, e.g. https://vz.example.com/middleware.php
   - {SERVER_EXAMPLES}
2. UUID: Enter the UUID of the data set you want to process
3. Start/End Time: Enter time range in dd.MM.yyyy HH:mm format (local time of this PC)
   or as UNIX timestamp in milliseconds. The start time must be before the end time.
4. Max Value: Enter the threshold value
   - "+": any data point above the threshold will be deleted
   - "-": any data point below the negative threshold will be deleted
   - Example: With -4000, values like -6000 will be deleted, but -3990 will remain
5. Processing Delay: Select appropriate delay based on your system:
   - 200ms: Fast local x86 systems
   - 500ms: Server environments (local or remote)
   - 1000ms: Raspberry Pi or similar devices
   - 2000ms: Slow systems or high-latency connections
6. Dry run: only lists the data points beyond the threshold, nothing is deleted.
   For meter channels the result is an estimate, because deleting one reading
   changes the calculated value of the following interval.

The tool repeatedly fetches the highest (or lowest) value and deletes it as long as it
exceeds the threshold. Progress and results are shown in the log area.

The log is also written to a file per day, see "Open Log Folder":
{LOG_DIR}
The last inputs are saved and restored on the next start.
        """

        help_scroll = scrolledtext.ScrolledText(usage_tab, wrap=tk.WORD)
        help_scroll.pack(fill=tk.BOTH, expand=True)
        help_scroll.insert(tk.END, help_text)
        help_scroll.config(state=tk.DISABLED)

        # Tab 2: granting the DELETE privilege to the vz database user
        permissions_tab = ttk.Frame(notebook)
        notebook.add(permissions_tab, text="DB Permissions / DB-Rechte")
        self.build_permissions_help(permissions_tab)

    def build_permissions_help(self, parent):
        """Help on granting the DELETE privilege to vz@localhost"""
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        content = ttk.Frame(canvas, padding="10")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        def text(value, bold=False):
            font = ("TkDefaultFont", 10, "bold") if bold else ("TkDefaultFont", 10)
            ttk.Label(content, text=value, font=font, wraplength=620,
                      justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 2))
        
        def command(value):
            frame = ttk.Frame(content)
            frame.pack(fill=tk.X, pady=2)
            lines = value.count("\n") + 1
            box = tk.Text(frame, height=lines, width=70, font=("Courier New", 9),
                          background="#f4f4f4", relief=tk.SOLID, borderwidth=1)
            box.insert(tk.END, value)
            box.config(state=tk.DISABLED)
            box.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Button(frame, text="Copy", width=6,
                       command=lambda: self.copy_to_clipboard(value)).pack(side=tk.LEFT, padx=5, anchor=tk.N)
        
        text("Freigabe der Daten für den Benutzer vz (DELETE-Recht)", bold=True)
        text("Um Datensätze per HTTP-Anfrage löschen zu können, benötigt der MySQL-Benutzer "
             "vz@localhost zusätzlich das DELETE-Recht. Ohne dieses Recht schlägt der "
             "Löschvorgang mit einem Fehler fehl.\n"
             "To delete data via HTTP request, the MySQL user vz@localhost needs the "
             "DELETE privilege.")
        
        text("Volkszähler Raspberry Pi Image", bold=True)
        text("Auf dem Raspberry Pi (z.B. per SSH) an MySQL anmelden "
             "(Standard-Passwort des Images: raspberry):")
        command("sudo mysql --user=root -praspberry")
        text("Danach in der MySQL-Konsole:")
        command("grant select, update, insert, delete on volkszaehler.* to vz@localhost;\n"
                "flush privileges;\n"
                "exit")
        
        text("Andere Systeme / Other systems", bold=True)
        text("DELETE-Recht vergeben / grant DELETE privilege:")
        command("grant delete on volkszaehler.* to 'vz'@'localhost';")
        text("DELETE-Recht wieder entziehen / revoke DELETE privilege:")
        command("revoke delete on volkszaehler.* from 'vz'@'localhost';")
        
        text("Hinweis: Das Recht nach dem Bereinigen wieder zu entziehen verhindert, dass "
             "Daten versehentlich über die HTTP-Schnittstelle gelöscht werden.\n"
             "Note: revoke the privilege after cleanup to prevent accidental deletion "
             "through the HTTP interface.")
    
    def copy_to_clipboard(self, value):
        """Copy a text to the clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(value)

    def open_log_folder(self):
        """Open the folder with the log files in the file explorer"""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            if sys.platform.startswith("win"):
                os.startfile(LOG_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", LOG_DIR])
            else:
                subprocess.Popen(["xdg-open", LOG_DIR])
        except Exception as e:
            self.log(f"Could not open log folder {LOG_DIR}: {e}", "ERROR")

    # --- Log and status (thread-safe) ---------------------------------------

    def log(self, message, level="INFO"):
        """Add a message to the log with timestamp (safe to call from any thread)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.ui_queue.put(("log", f"[{timestamp}] [{level}] {message}\n", level))

    def set_status(self, text):
        """Set the status text (safe to call from any thread)"""
        self.ui_queue.put(("status", text))

    def process_ui_queue(self):
        """Apply queued log/status updates in the GUI thread"""
        try:
            while True:
                item = self.ui_queue.get_nowait()
                if item[0] == "log":
                    self.log_text.insert(tk.END, item[1], item[2])
                    self.log_text.see(tk.END)
                    self.write_log_file(item[1])
                elif item[0] == "status":
                    self.status_var.set(item[1])
                elif item[0] == "done":
                    self.processing = False
                    self.start_button.config(state=tk.NORMAL)
                    self.stop_button.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.root.after(100, self.process_ui_queue)

    def write_log_file(self, line):
        """Append a log line to the log file of the current day"""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            log_file = os.path.join(LOG_DIR, f"vz_delete_tool_{datetime.now():%Y-%m-%d}.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line)
        except OSError as e:
            if not self.log_file_error_shown:
                self.log_file_error_shown = True
                self.log_text.insert(tk.END, f"Could not write log file: {e}\n", "WARNING")

    # --- Settings -------------------------------------------------------------

    def settings_vars(self):
        """Input fields that are saved and restored"""
        return {
            "server": self.server_var,
            "uuid": self.uuid_var,
            "start_time": self.start_time_var,
            "end_time": self.end_time_var,
            "max_value": self.max_value_var,
            "max_value_sign": self.max_value_sign_var,
            "delay": self.delay_var,
        }

    def load_settings(self):
        """Restore the last inputs"""
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, ValueError):
            return
        for key, var in self.settings_vars().items():
            if isinstance(settings.get(key), str):
                var.set(settings[key])
        if self.max_value_sign_var.get() not in ("+", "-"):
            self.max_value_sign_var.set("+")
        if self.delay_var.get() not in ("200", "500", "1000", "2000"):
            self.delay_var.set("1000")

    def save_settings(self):
        """Save the current inputs"""
        settings = {key: var.get() for key, var in self.settings_vars().items()}
        try:
            os.makedirs(APP_DIR, exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except OSError as e:
            self.log(f"Could not save settings: {e}", "WARNING")

    # --- Validation -----------------------------------------------------------

    def validate_inputs(self):
        """Validate all input fields"""
        if parse_server(self.server_var.get()) is None:
            self.log("Invalid server address. " + SERVER_EXAMPLES, "ERROR")
            return False

        if not is_valid_uuid(self.uuid_var.get().strip()):
            self.log("Invalid UUID format. Please enter a valid UUID.", "ERROR")
            return False

        start_timestamp = convert_to_timestamp(self.start_time_var.get())
        if start_timestamp is None:
            self.log("Invalid start time format. Use dd.MM.yyyy HH:mm or UNIX timestamp.", "ERROR")
            return False

        end_timestamp = convert_to_timestamp(self.end_time_var.get())
        if end_timestamp is None:
            self.log("Invalid end time format. Use dd.MM.yyyy HH:mm or UNIX timestamp.", "ERROR")
            return False

        if start_timestamp >= end_timestamp:
            self.log("Start time must be before end time.", "ERROR")
            return False

        if not is_valid_decimal_or_integer(self.max_value_var.get().strip()):
            self.log("Invalid max value format. Please use xxx.xx format or whole number.", "ERROR")
            return False

        return True

    # --- HTTP -----------------------------------------------------------------

    def request_json(self, url):
        """GET the URL and return (json, None) or (None, error message)"""
        try:
            response = self.session.get(url, timeout=HTTP_TIMEOUT)
        except requests.RequestException as e:
            return None, f"Connection error: {e}"
        try:
            payload = response.json()
        except ValueError:
            payload = None
        error = middleware_error(payload)
        if error:
            return None, f"Middleware error (HTTP {response.status_code}): {error}"
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        if not isinstance(payload, dict):
            return None, "Invalid response (no JSON). Check server address and middleware path."
        return payload, None

    # --- Process --------------------------------------------------------------

    def start_process(self):
        """Start the data deletion process"""
        if self.processing:
            return
        if not self.validate_inputs():
            self.status_var.set("Invalid input, see log")
            return

        self.save_settings()

        threshold = float(self.max_value_var.get().strip())
        negative = self.max_value_sign_var.get() == "-"
        params = {
            "base_url": parse_server(self.server_var.get()),
            "uuid": self.uuid_var.get().strip().lower(),
            "start_time": convert_to_timestamp(self.start_time_var.get()),
            "end_time": convert_to_timestamp(self.end_time_var.get()),
            "threshold": -threshold if negative else threshold,
            "negative": negative,
            "delay_ms": int(self.delay_var.get()),
            "dry_run": self.dry_run_var.get(),
        }

        self.processing = True
        self.stop_event.clear()
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Dry run..." if params["dry_run"] else "Processing...")

        # Start processing in a separate thread
        threading.Thread(target=self.run_worker, args=(params,), daemon=True).start()

    def stop_process(self):
        """Stop the data deletion process"""
        self.stop_event.set()
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Stopping...")
        self.log("Stop requested by user", "WARNING")

    def run_worker(self, params):
        """Worker thread: run dry run or deletion and always re-enable the buttons"""
        try:
            if params["dry_run"]:
                self.process_dry_run(params)
            else:
                self.process_data_deletion(params)
        except Exception as e:
            self.log(f"Unexpected error: {e}", "ERROR")
            self.set_status("Aborted with error")
        finally:
            self.ui_queue.put(("done",))

    def log_run_parameters(self, params, data_url):
        """Log the parameters of a run"""
        comparison = "<" if params["negative"] else ">"
        self.log(f"Using URL: {data_url}", "INFO")
        self.log(f"Time range: {format_timestamp(params['start_time'])} - {format_timestamp(params['end_time'])} "
                 f"(local time)", "INFO")
        self.log(f"Threshold: values {comparison} {params['threshold']:.2f}", "INFO")

    def process_dry_run(self, params):
        """List all data points beyond the threshold without deleting anything"""
        data_url = (f"{params['base_url']}/data/{params['uuid']}.json"
                    f"?from={params['start_time']}&to={params['end_time']}")
        self.log("Starting dry run (nothing will be deleted)...", "INFO")
        self.log_run_parameters(params, data_url)

        json_data, error = self.request_json(data_url)
        if error:
            self.log(error, "ERROR")
            self.set_status("Dry run failed")
            return

        data = json_data.get("data")
        if not isinstance(data, dict):
            self.log("Invalid JSON data structure", "ERROR")
            self.set_status("Dry run failed")
            return

        matches = []
        for row in data.get("tuples") or []:
            if len(row) >= 2 and row[1] is not None:
                if exceeds_threshold(float(row[1]), params["threshold"], params["negative"]):
                    matches.append((row[0], float(row[1])))

        for timestamp, value in matches[:DRY_RUN_LIST_LIMIT]:
            self.log(f"Would delete: [{timestamp}] {format_timestamp(timestamp)} value {value}", "WARNING")
        if len(matches) > DRY_RUN_LIST_LIMIT:
            self.log(f"... and {len(matches) - DRY_RUN_LIST_LIMIT} more", "WARNING")

        self.log(f"Dry run finished: {len(matches)} of {len(data.get('tuples') or [])} data points "
                 f"beyond the threshold.", "SUCCESS" if not matches else "INFO")
        self.set_status(f"Dry run finished. Matching data points: {len(matches)}")

    def process_data_deletion(self, params):
        """Process data deletion based on the given parameters"""
        base_url = params["base_url"]
        uuid_value = params["uuid"]
        threshold = params["threshold"]
        negative = params["negative"]
        delay_s = params["delay_ms"] / 1000
        # Positive threshold: look at the highest value, negative threshold: at the lowest value
        extreme_key = "min" if negative else "max"

        data_url = f"{base_url}/data/{uuid_value}.json?from={params['start_time']}&to={params['end_time']}"
        self.deleted_count = 0
        deleted_timestamps = set()
        result = "Completed"

        self.log("Starting data deletion process...", "INFO")
        self.log_run_parameters(params, data_url)
        self.log(f"Processing delay: {params['delay_ms']}ms", "INFO")

        while True:
            if self.stop_event.is_set():
                result = "Stopped by user"
                break

            json_data, error = self.request_json(data_url)
            if error:
                self.log(error, "ERROR")
                result = "Aborted with error"
                break

            data = json_data.get("data")
            if not isinstance(data, dict):
                self.log("Invalid JSON data structure", "ERROR")
                result = "Aborted with error"
                break

            extreme = data.get(extreme_key)
            if not extreme or len(extreme) < 2 or extreme[1] is None:
                self.log("No data found in the selected time range.", "INFO")
                break

            timestamp = extreme[0]
            current_value = float(extreme[1])
            self.log(f"Current {extreme_key} value: {current_value} at {format_timestamp(timestamp)}", "INFO")

            if not exceeds_threshold(current_value, threshold, negative):
                self.log("No values exceeding threshold found. Process complete.", "INFO")
                break

            if timestamp in deleted_timestamps:
                # The same point comes back after deleting it -> stop instead of looping forever
                self.log(f"Timestamp {timestamp} is still reported after it was deleted. "
                         f"Stopping to avoid an endless loop (aggregated data or missing DELETE privilege?).",
                         "ERROR")
                result = "Aborted with error"
                break

            self.log(f"Found value exceeding threshold: [{timestamp}, {current_value}]", "WARNING")
            delete_url = f"{base_url}/data/{uuid_value}.json?operation=delete&ts={timestamp}"
            delete_result, error = self.request_json(delete_url)
            if error:
                self.log(f"Failed to delete entry: {error}. Stopping process.", "ERROR")
                result = "Aborted with error"
                break
            if delete_result.get("rows") == 0:
                self.log(f"Middleware reports 0 deleted rows for timestamp {timestamp}. Stopping process.", "ERROR")
                result = "Aborted with error"
                break

            deleted_timestamps.add(timestamp)
            self.deleted_count += 1
            self.log(f"Successfully deleted entry with timestamp {timestamp}", "SUCCESS")
            self.set_status(f"Deleted: {self.deleted_count}")

            # Pause according to selected delay (returns early when stop is requested)
            self.stop_event.wait(delay_s)

        if result == "Stopped by user":
            self.log("Process stopped by user", "WARNING")
        self.log(f"Total entries deleted: {self.deleted_count}", "INFO")
        self.set_status(f"{result}. Deleted: {self.deleted_count}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DataDeletionApp(root)
    root.mainloop()

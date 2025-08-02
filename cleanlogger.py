from datetime import datetime
from IPython.display import clear_output

class CleanLogger:
    def __init__(self, log_path, output_widget, preset_manager=None):
        self.log_path = log_path
        self.output_widget = output_widget
        self.preset_manager = preset_manager  # Optional, bisa None
        self.log_file = None
        self.message_buffer = []

 
    def __enter__(self):
        self.log_file = open(self.log_path, 'w', encoding='utf-8')


    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.log_file:
            self.log_file.close()

    def log(self, message, show_timestamp=True, custom=None):
        timestamp = datetime.now().strftime("%H:%M:%S") if show_timestamp else ""
        log_entry = f"[{timestamp}] {message}" if timestamp else message

        if self.log_file:
            self.log_file.write(log_entry + '\n')
            self.log_file.flush()

        if custom and self.preset_manager:
            if self.preset_manager.apply(custom, message, self.output_widget):
                return  # Sudah ditampilkan oleh preset manager

        with self.output_widget:
            print(message)

    def log_separator(self):
        separator = "=" * 50
        self.log(separator, show_timestamp=False)
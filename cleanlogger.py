class CleanLogger:
    def __init__(self, log_path, output_widget, preset_manager=None):
        self.log_path = log_path
        self.output_widget = output_widget
        self.preset_manager = preset_manager  # Optional, bisa None
        self.log_file = None
        self.message_buffer = [] # Atribut ini ada di kode lama, tapi tidak pernah dipakai. Tetap disertakan untuk konsistensi.

    def __enter__(self):
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.log_file:
            self.log_file.close()

    def log(self, message, show_timestamp=True, custom=None):
        timestamp = datetime.now().strftime("%H:%M:%S") if show_timestamp else ""
        log_entry = f"[{timestamp}] {message}" if timestamp else message

        if self.log_file:
            self.log_file.write(log_entry + '\n')
            self.log_file.flush()

        # Jika ada custom tag dan preset manager disediakan
        if custom and self.preset_manager:
            if self.preset_manager.apply(custom, message, self.output_widget):
                return  # Sudah ditampilkan oleh preset manager

        # Fallback jika preset tidak tersedia atau tidak ada custom tag
        with self.output_widget:
            print(message)

    # DITAMBAHKAN KEMBALI DARI KODE LAMA
    def log_separator(self):
        """Log separator line"""
        separator = "=" * 50
        # Memanggil metode log yang sudah ada
        self.log(separator, show_timestamp=False)

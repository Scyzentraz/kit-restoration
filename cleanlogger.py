class CleanLogger:
    def __init__(self, log_path, output_widget, preset_manager=None):
        self.log_path = log_path
        self.output_widget = output_widget
        self.preset_manager = preset_manager  # Optional, bisa None
        self.log_file = None
        self.message_buffer = [] # Atribut ini ada di kode lama, tapi tidak pernah dipakai. Tetap disertakan untuk konsistensi.
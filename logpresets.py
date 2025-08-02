import yaml
from datetime import datetime
from IPython.display import display
import ipywidgets as widgets

class PresetManager:
    def __init__(self, yaml_path=None):
        self.presets = {}
        if yaml_path:
            self.load_presets(yaml_path)

    def load_presets(self, yaml_path):
        try:
            with open(yaml_path, "r") as f:
                self.presets = yaml.safe_load(f)
        except Exception as e:
                print(f"[LOG PRESET ERROR]: Gagal                       load preset - {e}")
                self.presets = {}

    def apply(self, tag, message, output_widget):
    tag = tag.lower()
    style = self.presets.get(tag)
    if not style:
        return False

    color = style.get("color", "black")
    weight = style.get("font-weight", "normal")
    emoji = style.get("emoji", "")
    prefix = style.get("prefix", "")
    show_time = style.get("timestamp", True)

    timestamp = f"[{datetime.now().strftime('%H:%M:%S')}]" if show_time else ""
    final_message = f"{timestamp} {emoji} {prefix} {message}".strip()
    html_style = f"color:{color}; font-weight:{weight};"

    with output_widget:  # ✅ gunakan konteks output widget
        display(widgets.HTML(f"<span style='{html_style}'>{final_message}</span>"), display_id=True)

    return True
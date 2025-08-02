##Cell2
# @title ⬅️ Jalankan Cell Ini Untuk Menampilkan Aplikasi Generator (VERSI QC)
# =======================================================================
# BAGIAN 0: IMPORT & SETUP UI Lanjutan
# =======================================================================
import ipywidgets as widgets
from IPython.display import display, clear_output
import sys
from contextlib import contextmanager
import threading
import queue
from cleanlogger import CleanLogger
from logpresets import PresetManager

#fungsi tambahan
# 🔁 Reload modul dan ambil class terbarunya
def reload_logger_modules():
    import importlib
    import sys
    import cleanlogger
    import logpresets

    importlib.reload(cleanlogger)
    importlib.reload(logpresets)

    from cleanlogger import CleanLogger
    from logpresets import PresetManager

    print("✅ Modul 'cleanlogger' dan 'logpresets' berhasil di-reload.")
    print(f"📦 CleanLogger: {CleanLogger} | ID: {id(CleanLogger)}")
    print(f"📦 PresetManager: {PresetManager} | ID: {id(PresetManager)}")

    print("\n📁 Status Cache di sys.modules:")
    print(f" - cleanlogger: {sys.modules.get('cleanlogger')}")
    print(f" - logpresets: {sys.modules.get('logpresets')}")

    return CleanLogger, PresetManager

# Jalankan reload dan simpan class ke variabel
#CleanLogger, PresetManager = reload_logger_modules()


# =======================================================================
# BAGIAN 1.1: CLEAN LOGGING SYSTEM - NO STDOUT MANIPULATION
# =======================================================================

#Dipindahkan ke cleanlogger.py
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

# =======================================================================
# BAGIAN 1.2: LOGGING PRESET MANAGER SYSTEM
# =======================================================================

#Dipindahkan ke logpresets.py
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


#file yaml
success:
  color: "yellow"
  font-weight: "bold"
  emoji: "✅"
  prefix: "[BERHASIL]"
  timestamp: true

error:
  color: "red"
  font-weight: "bold"
  emoji: "❌"
  prefix: "[GAGAL]"
  timestamp: true

info:
  color: "blue"
  font-weight: "normal"
  emoji: "ℹ️"
  prefix: "[INFO]"
  timestamp: true
# =======================================================================
# BAGIAN 1.2: MEMORY MANAGEMENT & VALIDATION FUNCTIONS
# =======================================================================

def validate_batch_size(jobs_list, max_batch=5):
    """Limit batch size untuk prevent OOM - Conservative untuk Colab Free"""
    if len(jobs_list) > max_batch:
        return jobs_list[:max_batch], f"⚠️ Batch dibatasi ke {max_batch} jobs untuk stabilitas Colab Free"
    return jobs_list, None

def validate_resolution(width, height):
    """Validate resolusi untuk prevent OOM"""
    if width * height > 1536 * 1536:
        return False, f"Resolusi {width}x{height} terlalu tinggi, max 1536x1536"
    if width % 8 != 0 or height % 8 != 0:
        return False, f"Resolusi harus kelipatan 8"
    return True, "OK"

def manage_preview_memory_smooth(preview_images, preview_widgets, max_images=3):
    """Smooth preview management tanpa kedip"""
    if len(preview_images) >= max_images:
        if len(preview_images) > 1:
            preview_images = preview_images[-1:]
            preview_widgets = preview_widgets[-1:]

        torch.cuda.empty_cache()

        return preview_images, preview_widgets, f"🧹 Preview cycled (showing latest {len(preview_images)} images)"

    return preview_images, preview_widgets, None

# =======================================================================
# BAGIAN 1.3: FUNGSI INTI (GENERATOR, PARSER, DAN QC LAYER)
# =======================================================================

def validate_job_params(job_dict, job_index):
    # Fungsi ini sekarang hanya digunakan untuk parsing JSON awal, validasi utama ada di QC
    if 'prompt' not in job_dict or not str(job_dict['prompt']).strip():
        return False, f"❌ ERROR di Job #{job_index+1}: 'prompt' tidak boleh kosong"
    return True, "OK"

def parse_batch_json_input(raw_text, logger):
    """Parse batch input dengan clean logging"""
    job_list = []
    if not raw_text.strip():
        return []

    try:
        all_jobs = json.loads(raw_text)
        if not isinstance(all_jobs, list):
            logger.log("❌ ERROR: Input harus berupa array JSON (diawali '[' dan diakhiri ']')")
            return []

        # Validasi awal di sini, validasi mendalam akan dilakukan oleh QC
        for i, job_dict in enumerate(all_jobs):
            if isinstance(job_dict, dict):
                job_list.append(job_dict)
            else:
                logger.log(f"❌ ERROR di Job #{i+1}: Item bukan format JSON object yang valid.")

        return job_list
    except Exception as e:
        logger.log(f"❌ ERROR saat parsing JSON: {e}")
        return []

# Quality Control Layer
def quality_control_check(jobs_list, model_id, logger):
    """
    Fungsi ini bertindak sebagai Quality Control.
    - Memfilter job yang tidak valid.
    - Menyesuaikan parameter jika memungkinkan (misal: resolusi).
    - Memberikan laporan ringkasan yang jelas.
    """
    logger.log("🕵️‍♂️ Memulai Quality Control (QC) untuk semua job...",custom="success")

    valid_jobs = []
    report_messages = []
    total_jobs = len(jobs_list)
    invalid_count = 0
    adjusted_count = 0

    # Batasi batch size di sini sebagai bagian dari QC
    jobs_list, batch_warning = validate_batch_size(jobs_list, max_batch=5)
    if batch_warning:
        logger.log(batch_warning)
        # Update total_jobs jika ada pemotongan
        if len(jobs_list) < total_jobs:
            report_messages.append(f"   - ℹ️ Info: {total_jobs - len(jobs_list)} job terakhir diabaikan karena melebihi batas batch.")
            total_jobs = len(jobs_list)


    for i, job in enumerate(jobs_list):
        job_id = f"Job #{i+1}"
        is_adjusted = False

        # 1. Validasi Prompt
        if not job.get('prompt') or not str(job.get('prompt')).strip():
            report_messages.append(f"   - ❌ {job_id}: Gagal - 'prompt' tidak boleh kosong.")
            invalid_count += 1
            continue

        # 2. Validasi & Penyesuaian Resolusi
        width = job.get('width', 1024)
        height = job.get('height', 576)

        is_res_valid, msg = validate_resolution(width, height)
        if not is_res_valid:
            # Cek apakah resolusi terlalu besar (fatal) atau hanya bukan kelipatan 8 (bisa disesuaikan)
            if "terlalu tinggi" in msg:
                report_messages.append(f"   - ❌ {job_id}: Gagal - {msg}.")
                invalid_count += 1
                continue
            else: # Bukan kelipatan 8, kita sesuaikan
                original_w, original_h = width, height
                adj_width = width - (width % 8)
                adj_height = height - (height % 8)
                job['width'] = adj_width
                job['height'] = adj_height
                report_messages.append(f"   - ⚠️ {job_id}: Disesuaikan - Resolusi diubah dari {original_w}x{original_h} menjadi {adj_width}x{adj_height} (syarat kelipatan 8).")
                is_adjusted = True
                adjusted_count += 1

        valid_jobs.append(job)

    # 3. Membuat Laporan Ringkasan
    logger.log_separator()
    valid_count = len(valid_jobs) - adjusted_count
    logger.log(f"✅ QC Selesai. Ringkasan dari {total_jobs} job yang terdeteksi:")
    logger.log(f"   - 👍 Lolos: {valid_count}", show_timestamp=False)
    logger.log(f"   - ⚠️ Disesuaikan: {adjusted_count}", show_timestamp=False)
    logger.log(f"   - ❌ Gagal/Ditolak: {invalid_count}", show_timestamp=False)

    if report_messages:
        logger.log("\n   Detail Laporan:", show_timestamp=False)
        for msg in report_messages:
            logger.log(msg, show_timestamp=False)
    logger.log_separator()

    return valid_jobs

def generate_stable_diffusion_image_clean(
    model_pipe, output_dir, prompt, negative_prompt="", seed=None,
    width=1024, height=576, num_inference_steps=35, guidance_scale=8.0,
    eta=0.0, logger=None
):
    """Fungsi generate inti, tidak ada perubahan signifikan"""

    def get_all_hashes(data):
        return {
            "image_md5": hashlib.md5(data).hexdigest(),
            "image_sha256": hashlib.sha256(data).hexdigest(),
            "image_sha512": hashlib.sha512(data).hexdigest()
        }

    if logger: logger.log(f"🎨 Memproses: \"{prompt[:50]}...\"")

    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        if logger: logger.log(f"   Seed acak: {seed}")
    else:
        try:
            seed = int(seed)
            if logger: logger.log(f"   Seed: {seed}")
        except (ValueError, TypeError):
            original_seed = seed
            seed = random.randint(0, 2**32 - 1)
            if logger: logger.log(f"   ⚠️ Seed '{original_seed}' invalid, menggunakan: {seed}")

    try:
        generator = torch.manual_seed(seed)
        start_time = time.time()

        gen_params = {
            "prompt": prompt, "generator": generator, "width": width, "height": height,
            "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta
        }

        if negative_prompt and negative_prompt.strip():
            gen_params["negative_prompt"] = negative_prompt

        image = model_pipe(**gen_params).images[0]
        generation_duration = time.time() - start_time

        if logger: logger.log(f"   ✅ Selesai dalam {generation_duration:.2f} detik")

        image_path = f"{output_dir}/images/img_{seed}.png"
        json_path = f"{output_dir}/seeds/img_{seed}.json"

        png_metadata = PngImagePlugin.PngInfo()
        png_metadata.add_text("prompt", prompt)
        png_metadata.add_text("negative_prompt", negative_prompt)
        png_metadata.add_text("seed", str(seed))

        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG', pnginfo=png_metadata)
        image_data = image_bytes.getvalue()
        hashes = get_all_hashes(image_data)

        with open(image_path, "wb") as f: f.write(image_data)

        meta_dict = {
            "prompt": prompt, "negative_prompt": negative_prompt, "seed": seed, "width": width, "height": height,
            "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta,
            "model": model_pipe.config._name_or_path, "scheduler": model_pipe.scheduler.__class__.__name__,
            "timestamp": datetime.now().isoformat(), "generation_duration_seconds": round(generation_duration, 2),
            "hashes": hashes
        }

        with open(json_path, "w") as f: json.dump(meta_dict, f, indent=2)

        if logger: logger.log(f"   💾 Tersimpan: img_{seed}.png")
        return image_path, json_path, image.copy()

    except torch.cuda.OutOfMemoryError:
        if logger: logger.log("   ❌ GPU Out of Memory! Emergency cleanup...")
        emergency_memory_cleanup()
        return None, None, None
    except Exception as e:
        if logger: logger.log(f"   ❌ Error: {e}")
        return None, None, None

# =======================================================================
# BAGIAN 2.1: MEMBUAT KOMPONEN UI UNTUK SETIAP MODE (TIDAK BERUBAH)
# =======================================================================
batch_placeholder_text = """[
  {
    "prompt": "a photorealistic image of a cat wearing a samurai armor",
    "width": 768, "height": 768, "seed": 42
  },
  {
    "prompt": "a beautiful beach at sunset, cinematic, 8k"
  }
]"""
batch_textarea = widgets.Textarea(value='', placeholder=batch_placeholder_text, layout={'width': '95%', 'height': '300px'})
batch_button = widgets.Button(description='Generate Batch', button_style='success', icon='play')
batch_ui = widgets.VBox([widgets.Label('Masukkan beberapa job dalam format JSON Array:'), batch_textarea, batch_button])
normal_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
normal_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Kosongkan jika tidak ingin menggunakan negative prompt.', layout={'width': '95%', 'height': '80px'})
aspect_ratio_dropdown = widgets.Dropdown(options=['Lanskap (16:9) - 1024x576', 'Potret (9:16) - 576x1024', 'Persegi (1:1) - 768x768', 'Lanskap Klasik (4:3) - 960x720', 'Potret Wide (2:3) - 640x960', 'Ultrawide (21:9) - 1344x576'], value='Lanskap (16:9) - 1024x576', description='Aspek Rasio:')
normal_button = widgets.Button(description='Generate Normal', button_style='success', icon='play')
normal_ui = widgets.VBox([widgets.Label('Prompt:'), normal_prompt_area, widgets.Label('Negative Prompt:'), normal_neg_prompt_area, aspect_ratio_dropdown, normal_button])
adv_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
adv_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Kosongkan jika tidak ingin menggunakan negative prompt.', layout={'width': '95%', 'height': '80px'})
adv_seed_input = widgets.Text(placeholder='Kosong = acak', description='Seed:')
adv_steps_slider = widgets.IntSlider(value=35, min=10, max=60, step=1, description='Steps:')
adv_guidance_slider = widgets.FloatSlider(value=8.0, min=1.0, max=15.0, step=0.5, description='Guidance:')
adv_width_slider = widgets.IntSlider(value=1024, min=256, max=1536, step=8, description='Width:')
adv_height_slider = widgets.IntSlider(value=576, min=256, max=1536, step=8, description='Height:')
adv_button = widgets.Button(description='Generate Advanced', button_style='success', icon='play')
adv_ui = widgets.VBox([widgets.Label('Prompt:'), adv_prompt_area, widgets.Label('Negative Prompt:'), adv_neg_prompt_area, widgets.HBox([adv_seed_input, adv_steps_slider, adv_guidance_slider]), widgets.HBox([adv_width_slider, adv_height_slider]), adv_button])
upload_button = widgets.FileUpload(accept='.json', multiple=False, description='Pilih File JSON')
upload_generate_button = widgets.Button(description='Generate dari JSON', button_style='success', icon='play')
upload_ui = widgets.VBox([widgets.Label('Upload file .json yang berisi array of jobs:'), upload_button, upload_generate_button])
all_buttons = [batch_button, normal_button, adv_button, upload_generate_button]

# =======================================================================
# BAGIAN 3.1: EXECUTION SYSTEM
# =======================================================================
text_output_area = widgets.Output()
preview_output_area = widgets.Output()
preview_images = []
preview_widgets = []

preset_admin = PresetManager("preset_styles.yaml")

# [REVISI] execute_generation_clean sekarang memanggil QC Layer
def execute_generation_clean(jobs_list, mode_name, output_dir, preview_enabled):
    """Orchestrator utama yang mengintegrasikan QC Layer."""
    global preview_images, preview_widgets

    for button in all_buttons: button.disabled = True
    preview_toggle.disabled = True

    text_output_area.clear_output(wait=True) # SATU-SATUNYA TITIK PEMBERSIHAN

    try:
        log_dir = os.path.join(output_dir, "logging")
        os.makedirs(log_dir, exist_ok=True)
        log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        log_path = os.path.join(log_dir, log_filename)

        with CleanLogger(log_path, text_output_area, preset_manager=preset_admin) as logger:
            print("DEBUG LOGGER:", logger)
            print("TYPE LOGGER:", type(logger))

       
            # Panggil QC Layer di sini!
            ready_jobs = quality_control_check(jobs_list, model_id, logger)

            # Hanya jalankan loop jika ada job yang lolos QC
            if ready_jobs:
                run_execution_loop_clean(ready_jobs, mode_name, output_dir, preview_enabled, logger)
            else:
                logger.log("\nTidak ada job yang valid untuk diproses. Proses dihentikan.")

            logger.log_separator()
            logger.log(f"📝 Log lengkap tersimpan: {log_path}")

    finally:
        for button in all_buttons: button.disabled = False
        preview_toggle.disabled = False
        if upload_button.value:
            upload_button.value.clear()
            upload_button._counter = 0

# [REVISI] run_execution_loop_clean menjadi lebih sederhana
def run_execution_loop_clean(jobs_list, mode_name, output_dir, preview_enabled, logger):
    """Loop eksekusi yang sekarang hanya menerima job yang sudah 100% valid."""
    global preview_images, preview_widgets

    preview_output_area.clear_output()
    del preview_images[:], preview_widgets[:]
    gc.collect()

    try:
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        os.makedirs(f"{output_dir}/seeds", exist_ok=True)
        negative_prompt_default = "blurry, low quality, jpeg artifacts, distorted, watermark, text, signature"

        total_jobs = len(jobs_list)
        logger.log(f"🚀 Memulai generate {mode_name} - Total: {total_jobs} gambar valid")
        if preview_enabled: logger.log("   📸 Preview: AKTIF")

        successful_jobs, failed_jobs = 0, 0

        for i, job_config in enumerate(jobs_list):
            logger.log(f"\n--- Memproses Job Valid {i+1}/{total_jobs} ---")

            if 'negative_prompt' not in job_config:
                job_config['negative_prompt'] = negative_prompt_default

            image_object = None
            try:
                _, _, image_object = generate_stable_diffusion_image_clean(
                    model_pipe=pipe, output_dir=output_dir, logger=logger, **job_config
                )
                if image_object is not None:
                    successful_jobs += 1
                    if preview_enabled:
                        preview_images, preview_widgets, cycle_msg = manage_preview_memory_smooth(
                            preview_images, preview_widgets, max_images=3
                        )
                        if cycle_msg: logger.log(f"   {cycle_msg}")
                        preview_images.append(image_object)
                        img_widget = widgets.Image(value=image_object._repr_png_(), format='png', width=200, layout={'margin': '5px'})
                        preview_widgets.append(img_widget)
                        with preview_output_area:
                            clear_output(wait=True)
                            if preview_widgets: display(widgets.HBox(preview_widgets))
                else:
                    failed_jobs += 1
            except Exception as e:
                failed_jobs += 1
                logger.log(f"   ❌ FATAL ERROR: {e}")

        logger.log_separator()
        logger.log(f"🎉 Generate {mode_name} selesai!",custom="error")
        logger.log(f"   ✅ Sukses: {successful_jobs}")
        logger.log(f"   ❌ Gagal: {failed_jobs}")

        if total_jobs > 3:
            safe_memory_cleanup()
            logger.log("   🧹 Memory cleanup selesai")

    except Exception as e:
        logger.log(f"❌ Fatal error: {e}")
        emergency_memory_cleanup()


# =======================================================================
# BAGIAN 4.1: EVENT HANDLERS - CLEANED & SIMPLIFIED
# =======================================================================

def on_batch_button_clicked(b):
    # Hanya parsing, tanpa validasi mendalam atau logging permanen
    temp_logger_widget = widgets.Output() # Logger sementara agar tidak mengganggu UI utama
    with CleanLogger("temp.log", temp_logger_widget) as temp_logger:
        jobs = parse_batch_json_input(batch_textarea.value, temp_logger)
    execute_generation_clean(jobs, "Batch", output_directory, preview_toggle.value)

def on_normal_button_clicked(b):
    # Hanya kumpulkan data, tanpa print/validasi
    aspect_map = {
        'Lanskap (16:9) - 1024x576': (1024, 576), 'Potret (9:16) - 576x1024': (576, 1024),
        'Persegi (1:1) - 768x768': (768, 768), 'Lanskap Klasik (4:3) - 960x720': (960, 720),
        'Potret Wide (2:3) - 640x960': (640, 960), 'Ultrawide (21:9) - 1344x576': (1344, 576)
    }
    width, height = aspect_map.get(aspect_ratio_dropdown.value, (1024, 576))
    job = [{"prompt": normal_prompt_area.value, "negative_prompt": normal_neg_prompt_area.value, "width": width, "height": height}]
    execute_generation_clean(job, "Normal", output_directory, preview_toggle.value)

def on_advanced_button_clicked(b):
    # Hanya kumpulkan data, tanpa print/validasi
    job = [{"prompt": adv_prompt_area.value, "negative_prompt": adv_neg_prompt_area.value,
            "num_inference_steps": adv_steps_slider.value, "guidance_scale": adv_guidance_slider.value,
            "width": adv_width_slider.value, "height": adv_height_slider.value,
            "seed": adv_seed_input.value if adv_seed_input.value else None}]
    execute_generation_clean(job, "Advanced", output_directory, preview_toggle.value)

def on_upload_button_clicked(b):
    # Hanya parsing, tanpa print/validasi
    if not upload_button.value:
        execute_generation_clean([], "JSON Upload", output_directory, preview_toggle.value)
        return
    uploaded_file = list(upload_button.value.values())[0]
    content_bytes = uploaded_file['content']
    jobs = []
    try:
        parsed_json = json.loads(content_bytes.decode('utf-8'))
        if isinstance(parsed_json, list):
            jobs = parsed_json
    except Exception:
        pass # Biarkan QC yang melaporkan error parsing jika ada
    execute_generation_clean(jobs, "JSON Upload", output_directory, preview_toggle.value)

# Connect event handlers
batch_button.on_click(on_batch_button_clicked)
normal_button.on_click(on_normal_button_clicked)
adv_button.on_click(on_advanced_button_clicked)
upload_generate_button.on_click(on_upload_button_clicked)

# =======================================================================
# BAGIAN 5.1: UI ASSEMBLY
# =======================================================================
tab_children = [batch_ui, normal_ui, adv_ui, upload_ui]
tab = widgets.Tab(children=tab_children)
tab.set_title(0, '1. Mode Batch')
tab.set_title(1, '2. Mode Normal')
tab.set_title(2, '3. Mode Advanced')
tab.set_title(3, '4. Mode Upload JSON')

preview_toggle = widgets.Checkbox(value=True, description='Tampilkan Preview Gambar', indent=False)

ui_container = widgets.VBox([
    widgets.HTML("<h2>🎨 Aplikasi Generator Multi-Mode - Versi QC 🎨</h2>"),
    preview_toggle,
    tab
])

print("✅ Aplikasi siap!")
display(ui_container, text_output_area, preview_output_area)

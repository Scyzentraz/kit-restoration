##Cell1
# @title ⬅️ Jalankan Cell Ini Dulu Untuk Setup
# Langkah 1: Install semua kebutuhan
!pip install diffusers transformers accelerate tqdm

# Langkah 2: Import semua library di satu tempat
import os
import torch
import random
import json
import time
import hashlib
import diffusers
import transformers
import gc
import io
from contextlib import redirect_stdout
from diffusers import StableDiffusionPipeline, DDIMScheduler
from PIL import Image, PngImagePlugin
from google.colab import drive
from datetime import datetime
from tqdm.notebook import tqdm

# [MODIFIKASI #10] Ganti path hardcoded dengan form Colab
# Pengguna bisa mengubah path ini sebelum menjalankan cell.
output_directory = "/content/drive/MyDrive/Stable_diff" #@param {type:"string"}

# Langkah 3: Mount Google Drive
drive.mount('/content/drive')

# Langkah 4: Konfigurasi dan load model
model_id = "runwayml/stable-diffusion-v1-5"

# =======================================================================
# MEMORY OPTIMIZATION FUNCTIONS
# =======================================================================

def safe_memory_cleanup():
    """Cleanup memory tanpa menghapus model dari GPU"""
    torch.cuda.empty_cache()
    gc.collect()

    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3  # GB
        cached = torch.cuda.memory_reserved() / 1024**3      # GB
        print(f"   🧠 GPU Memory - Allocated: {allocated:.2f}GB, Cached: {cached:.2f}GB")

def setup_memory_efficient_pipeline(pipe):
    """Setup pipeline untuk memory efficiency"""
    try:
        pipe.enable_attention_slicing()
        print("   ✅ Attention slicing enabled")
    except:
        print("   ⚠️ Attention slicing not available")

    try:
        pipe.enable_memory_efficient_attention()
        print("   ✅ Memory efficient attention enabled")
    except:
        print("   ⚠️ Memory efficient attention not available")

    return pipe

def emergency_memory_cleanup():
    """Emergency cleanup jika terjadi OOM error"""
    print("   🚨 Emergency memory cleanup...")
    torch.cuda.empty_cache()
    gc.collect()

    # Force multiple garbage collections
    for _ in range(3):
        gc.collect()
        torch.cuda.empty_cache()

    print("   ✅ Emergency cleanup completed")

# Load pipeline dan pindahkan ke GPU
try:
    pipe = StableDiffusionPipeline.from_pretrained(model_id).to("cuda")
    # Ganti scheduler ke DDIM untuk potensi hasil yang lebih baik/cepat
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)

    # Apply memory optimizations
    pipe = setup_memory_efficient_pipeline(pipe)

    print(f"✅ Setup selesai. Model '{model_id}' siap digunakan.")
    print(f"🖼️ Hasil akan disimpan di: {output_directory}")
    print("🧠 Memory optimization applied")
except Exception as e:
    print(f"❌ Gagal memuat model. Pastikan Anda menggunakan GPU runtime. Error: {e}")

#Cell2
# @title ⬅️ Jalankan Cell Ini Untuk Menampilkan Aplikasi Generator
# =======================================================================
# BAGIAN 0: IMPORT & SETUP UI Lanjutan
# =======================================================================
import ipywidgets as widgets
from IPython.display import display, clear_output
import sys
from contextlib import contextmanager
import threading
import queue

# =======================================================================
# BAGIAN 1A: CLEAN LOGGING SYSTEM - NO STDOUT MANIPULATION
# =======================================================================

class CleanLogger:
    """Clean logging system yang tidak manipulasi stdout"""
    def __init__(self, log_path, output_widget):
        self.log_path = log_path
        self.output_widget = output_widget
        self.log_file = None
        self.message_buffer = []
        
    def __enter__(self):
        self.log_file = open(self.log_path, 'w', encoding='utf-8')
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.log_file:
            self.log_file.close()
    
    def log(self, message, show_timestamp=True):
        """Log message ke file dan tampilkan di widget"""
        if show_timestamp:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
        else:
            log_entry = message
            
        # Write to file immediately
        if self.log_file:
            self.log_file.write(log_entry + '\n')
            self.log_file.flush()
        
        # Display in widget context (no stdout hijacking!)
        with self.output_widget:
            print(message)
    
    def log_separator(self):
        """Log separator line"""
        separator = "=" * 50
        self.log("", show_timestamp=False)
        self.log(separator, show_timestamp=False) 
        self.log("", show_timestamp=False)

# =======================================================================
# BAGIAN 1B: MEMORY MANAGEMENT & VALIDATION FUNCTIONS  
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
        # Keep only the latest image, clear the rest
        if len(preview_images) > 1:
            preview_images = preview_images[-1:]
            preview_widgets = preview_widgets[-1:]
        
        # Minimal cleanup
        torch.cuda.empty_cache()
        
        return preview_images, preview_widgets, f"🧹 Preview cycled (showing latest {len(preview_images)} images)"
    
    return preview_images, preview_widgets, None

# =======================================================================  
# BAGIAN 1C: FUNGSI INTI (GENERATOR & PARSER)
# =======================================================================

def validate_job_params(job_dict, job_index):
    if 'prompt' not in job_dict or not str(job_dict['prompt']).strip():
        return False, f"❌ ERROR di Job #{job_index+1}: 'prompt' tidak boleh kosong"
    
    # Validate resolution if provided
    if 'width' in job_dict and 'height' in job_dict:
        is_valid, msg = validate_resolution(job_dict['width'], job_dict['height'])
        if not is_valid:
            return False, f"❌ ERROR di Job #{job_index+1}: {msg}"
    
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
            
        for i, job_dict in enumerate(all_jobs):
            is_valid, msg = validate_job_params(job_dict, i)
            if is_valid: 
                job_list.append(job_dict)
            else: 
                logger.log(msg)
                
        return job_list
    except Exception as e:
        logger.log(f"❌ ERROR saat parsing JSON: {e}")
        return []

def generate_stable_diffusion_image_clean(
    model_pipe, output_dir, prompt, negative_prompt="", seed=None,
    width=1024, height=576, num_inference_steps=35, guidance_scale=8.0, 
    eta=0.0, logger=None
):
    """Generate function dengan clean logging"""
    
    # Validate resolution
    is_valid, msg = validate_resolution(width, height)
    if not is_valid:
        if logger: logger.log(f"❌ ERROR: {msg}. Melewati job ini.")
        return None, None, None
    
    # Adjust resolution for v1-5 compatibility
    if "v1-5" in model_id:
        original_w, original_h = width, height
        width = width - (width % 8)
        height = height - (height % 8)
        if (width, height) != (original_w, original_h):
            if logger: logger.log(f"⚠️ Resolusi disesuaikan: {original_w}x{original_h} → {width}x{height}")
    
    if width * height > 1024 * 1024:
        if logger: logger.log(f"⚠️ Resolusi tinggi {width}x{height}, proses mungkin lama")
    
    def get_all_hashes(data):
        return {
            "image_md5": hashlib.md5(data).hexdigest(),
            "image_sha256": hashlib.sha256(data).hexdigest(),
            "image_sha512": hashlib.sha512(data).hexdigest()
        }
    
    if logger: logger.log(f"🎨 Memproses: \"{prompt[:50]}...\"")
    
    # Handle seed
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
            "prompt": prompt, 
            "generator": generator, 
            "width": width, 
            "height": height, 
            "num_inference_steps": num_inference_steps, 
            "guidance_scale": guidance_scale, 
            "eta": eta
        }
        
        if negative_prompt and negative_prompt.strip():
            gen_params["negative_prompt"] = negative_prompt
        else:
            if logger: logger.log("   (Tanpa negative prompt)")
        
        # Generate image
        image = model_pipe(**gen_params).images[0]
        generation_duration = time.time() - start_time
        
        if logger: logger.log(f"   ✅ Selesai dalam {generation_duration:.2f} detik")
        
        # Save image and metadata
        image_path = f"{output_dir}/images/img_{seed}.png"
        json_path = f"{output_dir}/seeds/img_{seed}.json"
        
        png_metadata = PngImagePlugin.PngInfo()
        png_metadata.add_text("prompt", prompt)
        png_metadata.add_text("negative_prompt", negative_prompt)
        png_metadata.add_text("seed", str(seed))
        png_metadata.add_text("guidance_scale", str(guidance_scale))
        png_metadata.add_text("steps", str(num_inference_steps))
        
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG', pnginfo=png_metadata)
        image_data = image_bytes.getvalue()
        hashes = get_all_hashes(image_data)
        
        with open(image_path, "wb") as f:
            f.write(image_data)
        
        meta_dict = {
            "prompt": prompt, 
            "negative_prompt": negative_prompt, 
            "seed": seed, 
            "width": width, 
            "height": height, 
            "num_inference_steps": num_inference_steps, 
            "guidance_scale": guidance_scale, 
            "eta": eta, 
            "model": model_pipe.config._name_or_path, 
            "scheduler": model_pipe.scheduler.__class__.__name__, 
            "timestamp": datetime.now().isoformat(), 
            "generation_duration_seconds": round(generation_duration, 2), 
            "hashes": hashes
        }
        
        with open(json_path, "w") as f: 
            json.dump(meta_dict, f, indent=2)
        
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
# BAGIAN 2: MEMBUAT KOMPONEN UI UNTUK SETIAP MODE (UNCHANGED)
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
# BAGIAN 3: CLEAN EXECUTION SYSTEM
# =======================================================================
text_output_area = widgets.Output()
preview_output_area = widgets.Output()
preview_images = []
preview_widgets = []

def execute_generation_clean(jobs_list, mode_name, output_dir, preview_enabled):
    """Clean execution tanpa stdout manipulation"""
    global preview_images, preview_widgets
    
    # Disable all buttons
    for button in all_buttons: 
        button.disabled = True
    preview_toggle.disabled = True
    
    # Clear output area ONCE
    text_output_area.clear_output(wait=True)
    
    try:
        # Setup logging
        log_dir = os.path.join(output_dir, "logging")
        os.makedirs(log_dir, exist_ok=True)
        log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        log_path = os.path.join(log_dir, log_filename)
        
        # Use clean logger (no stdout manipulation!)
        with CleanLogger(log_path, text_output_area) as logger:
            run_execution_loop_clean(jobs_list, mode_name, output_dir, preview_enabled, logger)
            logger.log_separator()
            logger.log(f"📝 Log lengkap tersimpan: {log_path}")
            
    finally:
        # Re-enable buttons
        for button in all_buttons: 
            button.disabled = False
        preview_toggle.disabled = False
        if upload_button.value:
            upload_button.value.clear()
            upload_button._counter = 0

def run_execution_loop_clean(jobs_list, mode_name, output_dir, preview_enabled, logger):
    """Clean execution loop"""
    global preview_images, preview_widgets
    
    # Clear preview
    preview_output_area.clear_output()
    del preview_images[:], preview_widgets[:]
    gc.collect()
    
    try:
        # Create directories
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        os.makedirs(f"{output_dir}/seeds", exist_ok=True)
        negative_prompt_default = "blurry, low quality, jpeg artifacts, distorted, watermark, text, signature"
        
        if not jobs_list:
            logger.log("⚠️ Tidak ada job yang valid. Proses dihentikan.")
            return
        
        # Apply batch size limit
        jobs_list, batch_warning = validate_batch_size(jobs_list, max_batch=5)
        if batch_warning:
            logger.log(batch_warning)
        
        total_jobs = len(jobs_list)
        logger.log(f"🚀 Memulai generate {mode_name} - Total: {total_jobs} gambar")
        
        if preview_enabled:
            logger.log("   📸 Preview: AKTIF")
        
        successful_jobs, failed_jobs = 0, 0
        
        # Simple progress tracking (no tqdm to avoid stdout conflicts)
        for i, job_config in enumerate(jobs_list):
            logger.log(f"\n--- Job {i+1}/{total_jobs} ---")
            
            # Add default negative prompt if not provided
            if 'negative_prompt' not in job_config:
                job_config['negative_prompt'] = negative_prompt_default
            
            # Generate image
            image_object = None
            try:
                _, _, image_object = generate_stable_diffusion_image_clean(
                    model_pipe=pipe, 
                    output_dir=output_dir, 
                    logger=logger,
                    **job_config
                )
                
                if image_object is not None:
                    successful_jobs += 1
                    
                    # Handle preview
                    if preview_enabled:
                        preview_images, preview_widgets, cycle_msg = manage_preview_memory_smooth(
                            preview_images, preview_widgets, max_images=3
                        )
                        
                        if cycle_msg:
                            logger.log(f"   {cycle_msg}")
                        
                        preview_images.append(image_object)
                        img_widget = widgets.Image(
                            value=image_object._repr_png_(), 
                            format='png', 
                            width=200,
                            layout={'margin': '5px'}
                        )
                        preview_widgets.append(img_widget)
                        
                        # Update preview (smooth, no full clear each time)
                        with preview_output_area:
                            clear_output(wait=True)
                            if preview_widgets:
                                display(widgets.HBox(preview_widgets))
                else:
                    failed_jobs += 1
                    
            except Exception as e:
                failed_jobs += 1
                logger.log(f"   ❌ FATAL ERROR: {e}")
        
        # Final summary
        logger.log_separator()
        logger.log(f"🎉 Generate {mode_name} selesai!")
        logger.log(f"   ✅ Sukses: {successful_jobs}")
        logger.log(f"   ❌ Gagal: {failed_jobs}")
        
        # Final cleanup only if batch was large
        if total_jobs > 3:
            safe_memory_cleanup()
            logger.log("   🧹 Memory cleanup selesai")
            
    except Exception as e:
        logger.log(f"❌ Fatal error: {e}")
        emergency_memory_cleanup()

# =======================================================================
# BAGIAN 4: EVENT HANDLERS - CLEAN VERSION
# =======================================================================

def on_batch_button_clicked(b):
    # Initial parsing in output area
    text_output_area.clear_output(wait=True)
    with text_output_area:
        print("⚙️ Parsing input Mode Batch...")
        
    # Create temporary logger for parsing
    log_dir = os.path.join(output_directory, "logging")
    os.makedirs(log_dir, exist_ok=True)
    temp_log = os.path.join(log_dir, "temp_parse.txt")
    
    with CleanLogger(temp_log, text_output_area) as logger:
        jobs = parse_batch_json_input(batch_textarea.value, logger)
        if jobs: 
            logger.log(f"✅ Berhasil parsing {len(jobs)} job")
    
    # Execute if jobs found
    if jobs:
        execute_generation_clean(jobs, mode_name="Batch", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_normal_button_clicked(b):
    text_output_area.clear_output(wait=True)
    with text_output_area:
        print("⚙️ Mempersiapkan Mode Normal...")
        
        aspect_map = {
            'Lanskap (16:9) - 1024x576': (1024, 576), 
            'Potret (9:16) - 576x1024': (576, 1024), 
            'Persegi (1:1) - 768x768': (768, 768), 
            'Lanskap Klasik (4:3) - 960x720': (960, 720), 
            'Potret Wide (2:3) - 640x960': (640, 960), 
            'Ultrawide (21:9) - 1344x576': (1344, 576)
        }
        
        width, height = aspect_map.get(aspect_ratio_dropdown.value, (1024, 576))
        job = {
            "prompt": normal_prompt_area.value, 
            "negative_prompt": normal_neg_prompt_area.value, 
            "width": width, 
            "height": height
        }
        
        if not job["prompt"]: 
            print("❌ Prompt tidak boleh kosong")
            return
            
        print("✅ Job siap diproses")
    
    execute_generation_clean([job], mode_name="Normal", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_advanced_button_clicked(b):
    text_output_area.clear_output(wait=True)
    with text_output_area:
        print("⚙️ Mempersiapkan Mode Advanced...")
        
        job = {
            "prompt": adv_prompt_area.value, 
            "negative_prompt": adv_neg_prompt_area.value, 
            "num_inference_steps": adv_steps_slider.value, 
            "guidance_scale": adv_guidance_slider.value, 
            "width": adv_width_slider.value, 
            "height": adv_height_slider.value, 
            "seed": adv_seed_input.value if adv_seed_input.value else None
        }
        
        if not job["prompt"]: 
            print("❌ Prompt tidak boleh kosong")
            return
            
        print("✅ Parameter advanced siap")
    
    execute_generation_clean([job], mode_name="Advanced", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_upload_button_clicked(b):
    text_output_area.clear_output(wait=True)
    with text_output_area:
        print("⚙️ Parsing file JSON...")
        
        if not upload_button.value: 
            print("❌ Tidak ada file yang diupload")
            return
            
        uploaded_file = list(upload_button.value.values())[0]
        content_bytes = uploaded_file['content']
        
        try:
            jobs = json.loads(content_bytes.decode('utf-8'))
            if not isinstance(jobs, list):
                print("❌ Format JSON tidak valid. Harus berupa array.")
                return
            print(f"✅ Berhasil parsing {len(jobs)} job dari '{uploaded_file['metadata']['name']}'")
        except Exception as e:
            print(f"❌ Gagal parsing JSON: {e}")
            return
    
    execute_generation_clean(jobs, mode_name="JSON Upload", output_dir=output_directory, preview_enabled=preview_toggle.value)

# Connect event handlers
batch_button.on_click(on_batch_button_clicked)
normal_button.on_click(on_normal_button_clicked)
adv_button.on_click(on_advanced_button_clicked)
upload_generate_button.on_click(on_upload_button_clicked)

# =======================================================================
# BAGIAN 5: UI ASSEMBLY (UNCHANGED)
# =======================================================================
tab_children = [batch_ui, normal_ui, adv_ui, upload_ui]
tab = widgets.Tab(children=tab_children)
tab.set_title(0, '1. Mode Batch')
tab.set_title(1, '2. Mode Normal')
tab.set_title(2, '3. Mode Advanced') 
tab.set_title(3, '4. Mode Upload JSON')

preview_toggle = widgets.Checkbox(value=True, description='Tampilkan Preview Gambar', indent=False)

ui_container = widgets.VBox([
    widgets.HTML("<h2>🎨 Aplikasi Generator Multi-Mode - Clean Version 🎨</h2>"),
    preview_toggle,
    tab
])

print("✅ Aplikasi siap dengan sistem logging yang bersih!")
display(ui_container, text_output_area, preview_output_area)
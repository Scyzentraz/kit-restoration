eksperimental

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
import ipywidgets as widgets
from IPython.display import display, clear_output
import sys
from contextlib import contextmanager

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
    # Ganti bagian load model dengan:
    pipe = StableDiffusionPipeline.from_pretrained(
        model_id,
        torch_dtype=torch.float16,  # FP16 untuk hemat VRAM
        safety_checker=None,        # Nonaktifkan safety checker
        use_safetensors=True       # Format file lebih efisien
    ).to("cuda")

# Optimasi dasar saja
    pipe.enable_attention_slicing()
    # Ganti scheduler ke DDIM untuk potensi hasil yang lebih baik/cepat
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)

    # Apply memory optimizations
    pipe = setup_memory_efficient_pipeline(pipe)

    print(f"✅ Setup selesai. Model '{model_id}' siap digunakan.")
    print(f"🖼️ Hasil akan disimpan di: {output_directory}")
    print("🧠 Memory optimization applied")
except Exception as e:
    print(f"❌ Gagal memuat model. Pastikan Anda menggunakan GPU runtime. Error: {e}")



    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        print(f"   > Seed tidak diberikan. Menggunakan seed acak: {seed}")
    else:
        try:
            seed = int(seed)
            print(f"   > Menggunakan seed yang diberikan: {seed}")
        except (ValueError, TypeError):
            original_seed = seed
            seed = random.randint(0, 2**32 - 1)
            print(f"   > ⚠️ PERINGATAN: Seed '{original_seed}' tidak valid. Menggunakan seed acak: {seed}")

    generator = torch.manual_seed(seed)
    start_time = time.time()

    gen_params = {"prompt": prompt, "generator": generator, "width": width, "height": height, "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta}
    if negative_prompt and negative_prompt.strip():
        gen_params["negative_prompt"] = negative_prompt
    else:
        print("   > Tidak ada negative prompt yang digunakan.")

    image = model_pipe(**gen_params).images[0]
    generation_duration = time.time() - start_time
    print(f"   > Dihasilkan dalam {generation_duration:.2f} detik.")

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

    meta_dict = {"prompt": prompt, "negative_prompt": negative_prompt, "seed": seed, "width": width, "height": height, "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta, "model": model_pipe.config._name_or_path, "scheduler": model_pipe.scheduler.__class__.__name__, "timestamp": datetime.now().isoformat(), "generation_duration_seconds": round(generation_duration, 2), "hashes": hashes}
    with open(json_path, "w") as f: json.dump(meta_dict, f, indent=2)

    print(f"   ✅ Gambar & metadata disimpan ke ('{image_path}', '{json_path}')")
    return image_path, json_path, image.copy()


# =======================================================================
# BAGIAN 2: MEMBUAT KOMPONEN UI UNTUK SETIAP MODE
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
# BAGIAN 3: FUNGSI LOGIKA & EKSEKUSI
# =======================================================================
text_output_area = widgets.Output()
preview_output_area = widgets.Output()
preview_images = []
preview_widgets = []

def execute_generation(jobs_list, mode_name, output_dir, preview_enabled):
    global preview_images, preview_widgets
    
    for button in all_buttons: button.disabled = True
    preview_toggle.disabled = True
    
    text_output_area.clear_output(wait=True)
    
    try:
        with text_output_area:
            log_dir = os.path.join(output_dir, "logging")
            os.makedirs(log_dir, exist_ok=True)
            log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            log_path = os.path.join(log_dir, log_filename)
            
            with real_time_logger(log_path):
                run_execution_loop(jobs_list, mode_name, output_dir, preview_enabled)
                print(f"\n📝 Log sesi ini disimpan di: {log_path}")

    finally:
        for button in all_buttons: button.disabled = False
        preview_toggle.disabled = False
        if upload_button.value:
            upload_button.value.clear()
            upload_button._counter = 0

def run_execution_loop(jobs_list, mode_name, output_dir, preview_enabled):
    global preview_images, preview_widgets

    preview_output_area.clear_output()
    del preview_images[:], preview_widgets[:]
    gc.collect()

    try:
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        os.makedirs(f"{output_dir}/seeds", exist_ok=True)
        negative_prompt_default = "blurry, low quality, jpeg artifacts, distorted, watermark, text, signature"

        if not jobs_list:
            print("\n⚠️ Tidak ada pekerjaan yang valid ditemukan. Proses dihentikan.")
            return

        total_jobs = len(jobs_list)
        print(f"\n🚀 Memulai proses generate {mode_name}... Total {total_jobs} gambar.")
        if preview_enabled:
            print("   > Tampilan Preview: AKTIF")
        
        successful_jobs, failed_jobs = 0, 0
        
        job_iterator = jobs_list
        # [PERBAIKAN #1] Menambahkan spinner untuk efek visual aktif.
        spinner = ['/', '-', '\\', '|']
        if total_jobs > 1:
            job_iterator = tqdm(jobs_list, desc=f"Memproses {mode_name} jobs")

        for i, job_config in enumerate(job_iterator):
            if total_jobs > 1:
                # Set postfix di sini untuk mengubahnya di setiap iterasi.
                job_iterator.set_postfix_str(f"Aktivitas: {spinner[i % 4]}")
                print(f"\n--- Memproses Job {i+1}/{total_jobs} ---")
            
            if 'negative_prompt' not in job_config:
                job_config['negative_prompt'] = negative_prompt_default

            image_object = None
            try:
                _, _, image_object = generate_stable_diffusion_image(model_pipe=pipe, output_dir=output_dir, **job_config)
                successful_jobs += 1
            except Exception as e:
                failed_jobs += 1
                print(f"   ❌ FATAL ERROR pada Job #{i+1}: {e}")
                if preview_enabled:
                    with preview_output_area:
                         print(f"Job #{i+1} Gagal, preview tidak dapat ditampilkan.")
                continue
            
            if preview_enabled and image_object:
                if len(preview_images) >= 5:
                    preview_output_area.clear_output(wait=True)
                    del preview_images[:], preview_widgets[:]
                    gc.collect(); gc.collect()
                    preview_images, preview_widgets = [], []

                preview_images.append(image_object)
                img_widget = widgets.Image(value=image_object._repr_png_(), format='png', width=256)
                preview_widgets.append(img_widget)
                
                with preview_output_area:
                    clear_output(wait=True)
                    display(widgets.HBox(preview_widgets))
        
        print(f"\n🎉 Proses generate {mode_name} selesai!")
        print(f"   Hasil: {successful_jobs} sukses, {failed_jobs} gagal.")

    except Exception as e:
        print(f"\n❌ Terjadi error tak terduga pada proses eksekusi: {e}")

def on_batch_button_clicked(b):
    with text_output_area:
        clear_output(wait=True)
        print("⚙️ Mem-parsing input dari Mode Batch...")
        jobs = parse_batch_json_input(batch_textarea.value)
        if jobs: print(f"✅ Berhasil mem-parsing {len(jobs)} job untuk di-generate.")
    execute_generation(jobs, mode_name="Batch", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_normal_button_clicked(b):
    with text_output_area:
        clear_output(wait=True)
        print("⚙️ Mempersiapkan job dari Mode Normal...")
        aspect_map = {'Lanskap (16:9) - 1024x576': (1024, 576), 'Potret (9:16) - 576x1024': (576, 1024), 'Persegi (1:1) - 768x768': (768, 768), 'Lanskap Klasik (4:3) - 960x720': (960, 720), 'Potret Wide (2:3) - 640x960': (640, 960), 'Ultrawide (21:9) - 1344x576': (1344, 576)}
        width, height = aspect_map.get(aspect_ratio_dropdown.value, (1024, 576))
        job = {"prompt": normal_prompt_area.value, "negative_prompt": normal_neg_prompt_area.value, "width": width, "height": height}
        if not job["prompt"]: print("❌ Prompt tidak boleh kosong."); return
        print("✅ Berhasil mendeteksi prompt, generate siap dimulai👌")
    execute_generation([job], mode_name="Normal", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_advanced_button_clicked(b):
    with text_output_area:
        clear_output(wait=True)
        print("⚙️ Mempersiapkan job dari Mode Advanced...")
        job = {"prompt": adv_prompt_area.value, "negative_prompt": adv_neg_prompt_area.value, "num_inference_steps": adv_steps_slider.value, "guidance_scale": adv_guidance_slider.value, "width": adv_width_slider.value, "height": adv_height_slider.value, "seed": adv_seed_input.value if adv_seed_input.value else None}
        if not job["prompt"]: print("❌ Prompt tidak boleh kosong."); return
        print("✅ Berhasil mem-parsing parameter dari mode advance.")
    execute_generation([job], mode_name="Advanced", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_upload_button_clicked(b):
    with text_output_area:
        clear_output(wait=True)
        print("⚙️ Mem-parsing file JSON dari Mode Upload...")
        if not upload_button.value: print("❌ Tidak ada file yang di-upload."); return
        uploaded_file = list(upload_button.value.values())[0]
        content_bytes = uploaded_file['content']
        try:
            jobs = json.loads(content_bytes.decode('utf-8'))
            if not isinstance(jobs, list):
                print("❌ Format JSON tidak valid. File harus berisi sebuah array (diawali '[' dan diakhiri ']')."); return
            print(f"✅ Berhasil mem-parsing {len(jobs)} job dari file '{uploaded_file['metadata']['name']}'.")
        except Exception as e:
            print(f"❌ Gagal mem-parsing file JSON: {e}")
            return
    execute_generation(jobs, mode_name="JSON Upload", output_dir=output_directory, preview_enabled=preview_toggle.value)


# Menghubungkan tombol ke fungsi logikanya masing-masing
batch_button.on_click(on_batch_button_clicked)
normal_button.on_click(on_normal_button_clicked)
adv_button.on_click(on_advanced_button_clicked)
upload_generate_button.on_click(on_upload_button_clicked)

# =======================================================================
# BAGIAN 4: MERAKIT & MENAMPILKAN APLIKASI UI
# =======================================================================
tab_children = [batch_ui, normal_ui, adv_ui, upload_ui]
tab = widgets.Tab(children=tab_children)
tab.set_title(0, '1. Mode Batch'); tab.set_title(1, '2. Mode Normal')
tab.set_title(2, '3. Mode Advanced'); tab.set_title(3, '4. Mode Upload JSON')

preview_toggle = widgets.Checkbox(value=True, description='Tampilkan Preview Gambar', indent=False)

ui_container = widgets.VBox([
    widgets.HTML("<h2>🎨 Aplikasi Generator Multi-Mode 🎨</h2>"),
    preview_toggle,
    tab
])

print("✅ Aplikasi siap. Pilih mode operasi pada tab di bawah ini:")
display(ui_container, text_output_area, preview_output_area)    # [MODIFIKASI #2] Penanganan Seed yang lebih aman
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        print(f"   > Seed tidak diberikan. Menggunakan seed acak: {seed}")
    else:
        try:
            seed = int(seed)
            print(f"   > Menggunakan seed yang diberikan: {seed}")
        except (ValueError, TypeError):
            original_seed = seed
            seed = random.randint(0, 2**32 - 1)
            print(f"   > ⚠️ PERINGATAN: Seed '{original_seed}' tidak valid. Menggunakan seed acak: {seed}")

    generator = torch.manual_seed(seed)
    start_time = time.time()

    # [MODIFIKASI #3] Menghapus `negative_prompt` jika kosong
    gen_params = {"prompt": prompt, "generator": generator, "width": width, "height": height, "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta}
    if negative_prompt and negative_prompt.strip():
        gen_params["negative_prompt"] = negative_prompt
    else:
        print("   > Tidak ada negative prompt yang digunakan.")

    image = model_pipe(**gen_params).images[0]
    generation_duration = time.time() - start_time
    print(f"   > Dihasilkan dalam {generation_duration:.2f} detik.")

    # Simpan path dan metadata
    image_path = f"{output_dir}/images/img_{seed}.png"
    json_path = f"{output_dir}/seeds/img_{seed}.json"
    
    # [MODIFIKASI #6c] Proses metadata sebelum menyimpan
    png_metadata = PngImagePlugin.PngInfo()
    png_metadata.add_text("prompt", prompt)
    png_metadata.add_text("negative_prompt", negative_prompt)
    png_metadata.add_text("seed", str(seed))
    png_metadata.add_text("guidance_scale", str(guidance_scale))
    png_metadata.add_text("steps", str(num_inference_steps))

    # [MODIFIKASI #6b] Ambil hash dari data gambar
    image_bytes = io.BytesIO()
    image.save(image_bytes, format='PNG', pnginfo=png_metadata)
    image_data = image_bytes.getvalue()
    hashes = get_all_hashes(image_data)

    # Simpan gambar dari byte
    with open(image_path, "wb") as f:
        f.write(image_data)

    meta_dict = {"prompt": prompt, "negative_prompt": negative_prompt, "seed": seed, "width": width, "height": height, "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta, "model": model_pipe.config._name_or_path, "scheduler": model_pipe.scheduler.__class__.__name__, "timestamp": datetime.now().isoformat(), "generation_duration_seconds": round(generation_duration, 2), "hashes": hashes}
    with open(json_path, "w") as f: json.dump(meta_dict, f, indent=2)

    print(f"   ✅ Gambar & metadata disimpan ke ('{image_path}', '{json_path}')")
    return image_path, json_path, image.copy()


# =======================================================================
# BAGIAN 2: MEMBUAT KOMPONEN UI UNTUK SETIAP MODE
# =======================================================================
# [MODIFIKASI #5] Contoh placeholder diubah ke format JSON Array standar
batch_placeholder_text = """[
  {
    "prompt": "a photorealistic image of a cat wearing a samurai armor",
    "width": 768, "height": 768, "seed": 42
  },
  {
    "prompt": "a beautiful beach at sunset, cinematic, 8k",
    "width": 1024, "height": 576, "num_inference_steps": 40
  },
  {
    "prompt": "portrait of an old man, detailed face, studio lighting",
    "negative_prompt": "cartoon, drawing, painting",
    "width": 576, "height": 1024
  }
]"""
# --- UI Mode 1: Batch ---
batch_textarea = widgets.Textarea(value='', placeholder=batch_placeholder_text, layout={'width': '95%', 'height': '300px'})
batch_button = widgets.Button(description='Generate Batch', button_style='success', icon='play')
batch_ui = widgets.VBox([widgets.Label('Masukkan beberapa job dalam format JSON Array:'), batch_textarea, batch_button])

# --- UI Mode 2: Normal ---
normal_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
normal_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Kosongkan jika tidak ingin menggunakan negative prompt.', layout={'width': '95%', 'height': '80px'})
aspect_ratio_dropdown = widgets.Dropdown(options=['Lanskap (16:9) - 1024x576', 'Potret (9:16) - 576x1024', 'Persegi (1:1) - 768x768', 'Lanskap Klasik (4:3) - 960x720', 'Potret Wide (2:3) - 640x960', 'Ultrawide (21:9) - 1344x576'], value='Lanskap (16:9) - 1024x576', description='Aspek Rasio:')
normal_button = widgets.Button(description='Generate Normal', button_style='success', icon='play')
normal_ui = widgets.VBox([widgets.Label('Prompt:'), normal_prompt_area, widgets.Label('Negative Prompt:'), normal_neg_prompt_area, aspect_ratio_dropdown, normal_button])

# --- UI Mode 3: Advanced ---
adv_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
adv_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Kosongkan jika tidak ingin menggunakan negative prompt.', layout={'width': '95%', 'height': '80px'})
adv_seed_input = widgets.Text(placeholder='Kosong = acak', description='Seed:')
adv_steps_slider = widgets.IntSlider(value=35, min=10, max=60, step=1, description='Steps:')
adv_guidance_slider = widgets.FloatSlider(value=8.0, min=1.0, max=15.0, step=0.5, description='Guidance:')
adv_width_slider = widgets.IntSlider(value=1024, min=256, max=1536, step=8, description='Width:')
adv_height_slider = widgets.IntSlider(value=576, min=256, max=1536, step=8, description='Height:')
adv_button = widgets.Button(description='Generate Advanced', button_style='success', icon='play')
adv_ui = widgets.VBox([widgets.Label('Prompt:'), adv_prompt_area, widgets.Label('Negative Prompt:'), adv_neg_prompt_area, widgets.HBox([adv_seed_input, adv_steps_slider, adv_guidance_slider]), widgets.HBox([adv_width_slider, adv_height_slider]), adv_button])

# --- UI Mode 4: Upload JSON ---
upload_button = widgets.FileUpload(accept='.json', multiple=False, description='Pilih File JSON')
upload_generate_button = widgets.Button(description='Generate dari JSON', button_style='success', icon='play')
upload_ui = widgets.VBox([widgets.Label('Upload file .json yang berisi array of jobs:'), upload_button, upload_generate_button])

all_buttons = [batch_button, normal_button, adv_button, upload_generate_button]

# =======================================================================
# BAGIAN 3: FUNGSI LOGIKA & EKSEKUSI
# =======================================================================
text_output_area = widgets.Output()
preview_output_area = widgets.Output() # [MODIFIKASI #6h] Output terpisah untuk preview
preview_images = []
preview_widgets = []

# [MODIFIKASI #7] Fungsi untuk logging ke file
def create_log_file(log_dir, content_callable):
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    log_path = os.path.join(log_dir, log_filename)
    
    log_stream = io.StringIO()
    with redirect_stdout(log_stream):
        content_callable() # Jalankan fungsi yang menghasilkan output print
    
    log_content = log_stream.getvalue()
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    # Cetak output asli ke notebook
    print(log_content)
    print(f"\n📝 Log sesi ini disimpan di: {log_path}")


def execute_generation(jobs_list, mode_name, output_dir, preview_enabled):
    global preview_images, preview_widgets
    
    for button in all_buttons: button.disabled = True
    
    # [MODIFIKASI #6m] UI Isolation, bersihkan output sebelum mulai
    text_output_area.clear_output(wait=True)
    with text_output_area:
      # Wrapper untuk menangkap semua output ke file log
      create_log_file(os.path.join(output_dir, "logging"), lambda: run_execution_loop(jobs_list, mode_name, output_dir, preview_enabled))

    # Re-enable buttons di luar context `with`
    for button in all_buttons: button.disabled = False
    # [MODIFIKASI #14] Reset tombol upload
    if upload_button.value:
        upload_button.value.clear()
        upload_button._counter = 0 # Workaround untuk ipywidgets bug

def run_execution_loop(jobs_list, mode_name, output_dir, preview_enabled):
    """Fungsi eksekusi inti, sekarang dengan lebih banyak fitur."""
    global preview_images, preview_widgets

    # Hapus preview lama sebelum memulai sesi baru
    preview_output_area.clear_output()
    del preview_images[:], preview_widgets[:]
    gc.collect()

    try:
        os.makedirs(f"{output_dir}/images", exist_ok=True)
        os.makedirs(f"{output_dir}/seeds", exist_ok=True)
        negative_prompt_default = "blurry, low quality, jpeg artifacts, distorted, watermark, text, signature"

        if not jobs_list:
            print("\n⚠️ Tidak ada pekerjaan yang valid ditemukan. Proses dihentikan.")
            return

        total_jobs = len(jobs_list)
        print(f"\n🚀 Memulai proses generate {mode_name}... Total {total_jobs} gambar.")
        if preview_enabled:
            print("   > Tampilan Preview: AKTIF")
        
        successful_jobs, failed_jobs = 0, 0
        
        # [MODIFIKASI #9] Tambahkan TQDM untuk loop batch
        job_iterator = jobs_list
        if total_jobs > 1:
            job_iterator = tqdm(jobs_list, desc=f"Memproses {mode_name} jobs")

        for i, job_config in enumerate(job_iterator):
            if total_jobs > 1:
                print(f"\n--- Memproses Job {i+1}/{total_jobs} ---")
            
            # [MODIFIKASI #3] Set default negative prompt hanya jika tidak ada dan tidak sengaja dikosongkan
            if 'negative_prompt' not in job_config:
                job_config['negative_prompt'] = negative_prompt_default

            image_object = None
            # [MODIFIKASI #8] Penanganan error per job
            try:
                _, _, image_object = generate_stable_diffusion_image(model_pipe=pipe, output_dir=output_dir, **job_config)
                successful_jobs += 1
            except Exception as e:
                failed_jobs += 1
                print(f"   ❌ FATAL ERROR pada Job #{i+1}: {e}")
                # [MODIFIKASI #6l] Fail-safe preview
                if preview_enabled:
                    with preview_output_area:
                         print(f"Job #{i+1} Gagal, preview tidak dapat ditampilkan.")
                continue # Lanjut ke job berikutnya
            
            # [MODIFIKASI #6] Logika Preview
            if preview_enabled and image_object:
                # [MODIFIKASI #6e & #6f] Batasi preview dan kelola memori
                if len(preview_images) >= 5:
                    preview_output_area.clear_output(wait=True)
                    del preview_images[:]
                    del preview_widgets[:]
                    # [MODIFIKASI #6k] Paksa Garbage Collection
                    gc.collect(); gc.collect()
                    preview_images, preview_widgets = [], []

                preview_images.append(image_object)
                img_widget = widgets.Image(value=image_object._repr_png_(), format='png', width=256)
                preview_widgets.append(img_widget)
                
                # [MODIFIKASI #6i] Kontrol penghapusan dan tampilan yang presisi
                with preview_output_area:
                    clear_output(wait=True)
                    display(widgets.HBox(preview_widgets))
        
        print(f"\n🎉 Proses generate {mode_name} selesai!")
        print(f"   Hasil: {successful_jobs} sukses, {failed_jobs} gagal.")

    except Exception as e:
        print(f"\n❌ Terjadi error tak terduga pada proses eksekusi: {e}")

def on_batch_button_clicked(b):
    print("⚙️ Mem-parsing input dari Mode Batch...")
    jobs = parse_batch_json_input(batch_textarea.value)
    if jobs: print(f"✅ Berhasil mem-parsing {len(jobs)} job untuk di-generate.")
    execute_generation(jobs, mode_name="Batch", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_normal_button_clicked(b):
    print("⚙️ Mempersiapkan job dari Mode Normal...")
    aspect_map = {'Lanskap (16:9) - 1024x576': (1024, 576), 'Potret (9:16) - 576x1024': (576, 1024), 'Persegi (1:1) - 768x768': (768, 768), 'Lanskap Klasik (4:3) - 960x720': (960, 720), 'Potret Wide (2:3) - 640x960': (640, 960), 'Ultrawide (21:9) - 1344x576': (1344, 576)}
    width, height = aspect_map.get(aspect_ratio_dropdown.value, (1024, 576))
    job = {"prompt": normal_prompt_area.value, "negative_prompt": normal_neg_prompt_area.value, "width": width, "height": height}
    if not job["prompt"]: print("❌ Prompt tidak boleh kosong."); return
    print("✅ Berhasil mendeteksi prompt, generate siap dimulai👌")
    execute_generation([job], mode_name="Normal", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_advanced_button_clicked(b):
    print("⚙️ Mempersiapkan job dari Mode Advanced...")
    job = {"prompt": adv_prompt_area.value, "negative_prompt": adv_neg_prompt_area.value, "num_inference_steps": adv_steps_slider.value, "guidance_scale": adv_guidance_slider.value, "width": adv_width_slider.value, "height": adv_height_slider.value, "seed": adv_seed_input.value if adv_seed_input.value else None}
    if not job["prompt"]: print("❌ Prompt tidak boleh kosong."); return
    print("✅ Berhasil mem-parsing parameter dari mode advance.")
    execute_generation([job], mode_name="Advanced", output_dir=output_directory, preview_enabled=preview_toggle.value)

def on_upload_button_clicked(b):
    print("⚙️ Mem-parsing file JSON dari Mode Upload...")
    if not upload_button.value: print("❌ Tidak ada file yang di-upload."); return
    uploaded_file = list(upload_button.value.values())[0]
    content_bytes = uploaded_file['content']
    try:
        # [MODIFIKASI #4] Langsung parse JSON standar
        jobs = json.loads(content_bytes.decode('utf-8'))
        if not isinstance(jobs, list):
            print("❌ Format JSON tidak valid. File harus berisi sebuah array (diawali '[' dan diakhiri ']')."); return
        print(f"✅ Berhasil mem-parsing {len(jobs)} job dari file '{uploaded_file['metadata']['name']}'.")
        execute_generation(jobs, mode_name="JSON Upload", output_dir=output_directory, preview_enabled=preview_toggle.value)
    except Exception as e: print(f"❌ Gagal mem-parsing file JSON: {e}")

# Menghubungkan tombol ke fungsi logikanya masing-masing
batch_button.on_click(on_batch_button_clicked)
normal_button.on_click(on_normal_button_clicked)
adv_button.on_click(on_advanced_button_clicked)
upload_generate_button.on_click(on_upload_button_clicked)

# =======================================================================
# BAGIAN 4: MERAKIT & MENAMPILKAN APLIKASI UI
# =======================================================================
tab_children = [batch_ui, normal_ui, adv_ui, upload_ui]
tab = widgets.Tab(children=tab_children)
tab.set_title(0, '1. Mode Batch'); tab.set_title(1, '2. Mode Normal')
tab.set_title(2, '3. Mode Advanced'); tab.set_title(3, '4. Mode Upload JSON')

# [MODIFIKASI #6d] Tambahkan toggle untuk preview
preview_toggle = widgets.Checkbox(value=True, description='Tampilkan Preview Gambar', indent=False)

# Rakit UI lengkap
ui_container = widgets.VBox([
    widgets.HTML("<h2>🎨 Aplikasi Generator Multi-Mode 🎨</h2>"),
    preview_toggle,
    tab
])

print("✅ Aplikasi siap. Pilih mode operasi pada tab di bawah ini:")
# Tampilkan semua komponen UI
display(ui_container, text_output_area, preview_output_area)

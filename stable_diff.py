
##Cell1 Setup
# Langkah 1: Install semua kebutuhan
!pip install diffusers transformers accelerate

# Langkah 2: Import semua library di satu tempat
import os
import torch
import random
import json
import time
import hashlib
import diffusers
import transformers
from diffusers import StableDiffusionPipeline, DDIMScheduler
from PIL import Image, PngImagePlugin
from google.colab import drive
from datetime import datetime

# Langkah 3: Mount Google Drive
drive.mount('/content/drive')

# Langkah 4: Konfigurasi dan load model
model_id = "runwayml/stable-diffusion-v1-5"

# Load pipeline dan pindahkan ke GPU
pipe = StableDiffusionPipeline.from_pretrained(model_id).to("cuda")

# Ganti scheduler ke DDIM untuk potensi hasil yang lebih baik/cepat
pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)

print("✅ Setup selesai. Model siap digunakan.")





# =======================================================================
# CELL 2: APLIKASI GENERATOR MULTI-MODE
# =======================================================================

# BAGIAN 0: IMPORT KEBUTUHAN UI & LOGIKA
import ipywidgets as widgets
from IPython.display import display
import ast, json, random, time, hashlib
from PIL import Image, PngImagePlugin
from datetime import datetime

# =======================================================================
# BAGIAN 1: FUNGSI INTI (GENERATOR & PARSER)
# =======================================================================
def parse_multi_job_input(raw_text):
    """Parser untuk Mode Batch. Kini mengembalikan jumlah job yang berhasil."""
    job_list = []
    job_chunks = raw_text.split('$')
    for i, chunk in enumerate(job_chunks):
        clean_chunk = chunk.strip()
        if not clean_chunk: continue
        try:
            job_dict = ast.literal_eval("{" + clean_chunk + "}")
            job_list.append(job_dict)
        except Exception as e:
            print(f"   > ❌ ERROR saat mem-parse Job Batch #{i+1}: {e}")
    return job_list

def generate_stable_diffusion_image(
    model_pipe, output_dir, prompt, negative_prompt, seed=None,
    width=1024, height=576, num_inference_steps=35, guidance_scale=8.0, eta=0.0
):
    """Fungsi utama untuk generate, menyimpan, dan mencatat metadata gambar."""
    if "v1-5" in model_id:
      if width % 8 != 0 or height % 8 != 0:
          print(f"   ❌ ERROR: Resolusi ({width}x{height}) tidak valid. Melewati job ini."); return None, None
    def get_all_hashes(data):
        return {"image_md5": hashlib.md5(data).hexdigest(), "image_sha256": hashlib.sha256(data).hexdigest(), "image_sha512": hashlib.sha512(data).hexdigest()}
    try:
        print(f"🎨 Processing prompt: \"{prompt[:50]}...\"")
        if seed is None:
            seed = random.randint(0, 2**32 - 1); print(f"   > No seed provided. Using random seed: {seed}")
        else:
            seed = int(seed); print(f"   > Using provided seed: {seed}")
        generator = torch.manual_seed(seed)
        start_time = time.time()
        image = model_pipe(prompt=prompt, negative_prompt=negative_prompt, generator=generator, width=width, height=height, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale, eta=eta).images[0]
        generation_duration = time.time() - start_time
        print(f"   > Generated in {generation_duration:.2f}s.")
        image_path = f"{output_dir}/images/img_{seed}.png"; json_path = f"{output_dir}/seeds/img_{seed}.json"
        png_metadata = PngImagePlugin.PngInfo(); png_metadata.add_text("prompt", prompt); png_metadata.add_text("seed", str(seed)); png_metadata.add_text("guidance_scale", str(guidance_scale)); png_metadata.add_text("steps", str(num_inference_steps))
        image.save(image_path, pnginfo=png_metadata)
        with open(image_path, "rb") as f: image_data = f.read(); hashes = get_all_hashes(image_data)
        meta_dict = {"prompt": prompt, "negative_prompt": negative_prompt, "seed": seed, "width": width, "height": height, "num_inference_steps": num_inference_steps, "guidance_scale": guidance_scale, "eta": eta, "model": model_pipe.config._name_or_path, "scheduler": model_pipe.scheduler.__class__.__name__, "timestamp": datetime.now().isoformat(), "generation_duration_seconds": round(generation_duration, 2), "hashes": hashes}
        with open(json_path, "w") as f: json.dump(meta_dict, f, indent=2)
        print(f"   ✅ Image & metadata saved to ('{image_path}', '{json_path}')")
        return image_path, json_path
    except Exception as e:
        print(f"   ❌ An error occurred: {e}"); return None, None

# =======================================================================
# BAGIAN 2: MEMBUAT KOMPONEN UI UNTUK SETIAP MODE
# =======================================================================
# ATURAN 2: Contoh untuk placeholder Mode Batch
batch_placeholder_text = """$
"prompt": "a photorealistic image of a cat wearing a samurai armor",
"width": 768, "height": 768, "seed": 42

$
"prompt": "a beautiful beach at sunset, cinematic, 8k",
"width": 1024, "height": 576, "num_inference_steps": 40

$
"prompt": "portrait of an old man, detailed face, studio lighting",
"negative_prompt": "cartoon, drawing, painting",
"width": 576, "height": 1024

$
"prompt": "a synthwave city skyline"
"""
# --- UI Mode 1: Batch ---
batch_textarea = widgets.Textarea(value='', placeholder=batch_placeholder_text, layout={'width': '95%', 'height': '300px'})
batch_button = widgets.Button(description='Generate Batch', button_style='success', icon='play')
batch_ui = widgets.VBox([widgets.Label('Masukkan beberapa job dengan pemisah "$":'), batch_textarea, batch_button])

# --- UI Mode 2: Normal ---
normal_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
normal_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Masukkan negative prompt di sini...', layout={'width': '95%', 'height': '80px'})
# ATURAN 4: Opsi aspek rasio diperbanyak
aspect_ratio_dropdown = widgets.Dropdown(
    options=[
        'Lanskap (16:9) - 1024x576',
        'Potret (9:16) - 576x1024',
        'Persegi (1:1) - 768x768',
        'Lanskap Klasik (4:3) - 960x720',
        'Potret Wide (2:3) - 640x960',
        'Ultrawide (21:9) - 1344x576'
    ],
    value='Lanskap (16:9) - 1024x576', description='Aspek Rasio:')
normal_button = widgets.Button(description='Generate Normal', button_style='success', icon='play')
normal_ui = widgets.VBox([widgets.Label('Prompt:'), normal_prompt_area, widgets.Label('Negative Prompt:'), normal_neg_prompt_area, aspect_ratio_dropdown, normal_button])

# --- UI Mode 3: Advanced ---
adv_prompt_area = widgets.Textarea(placeholder='Masukkan prompt Anda di sini...', layout={'width': '95%', 'height': '150px'})
adv_neg_prompt_area = widgets.Textarea(placeholder='(Opsional) Masukkan negative prompt di sini...', layout={'width': '95%', 'height': '80px'})
adv_seed_input = widgets.IntText(value=None, placeholder='Kosong = acak', description='Seed:')
adv_steps_slider = widgets.IntSlider(value=35, min=10, max=60, step=1, description='Steps:')
adv_guidance_slider = widgets.FloatSlider(value=8.0, min=1.0, max=15.0, step=0.5, description='Guidance:')
adv_width_slider = widgets.IntSlider(value=1024, min=256, max=1536, step=8, description='Width:')
adv_height_slider = widgets.IntSlider(value=576, min=256, max=1536, step=8, description='Height:')
adv_button = widgets.Button(description='Generate Advanced', button_style='success', icon='play')
adv_ui = widgets.VBox([widgets.Label('Prompt:'), adv_prompt_area, widgets.Label('Negative Prompt:'), adv_neg_prompt_area, widgets.HBox([adv_seed_input, adv_steps_slider, adv_guidance_slider]), widgets.HBox([adv_width_slider, adv_height_slider]), adv_button])

# --- UI Mode 4: Upload JSON ---
upload_button = widgets.FileUpload(accept='.json', multiple=False, description='Pilih File JSON')
upload_generate_button = widgets.Button(description='Generate dari JSON', button_style='success', icon='play')
upload_ui = widgets.VBox([widgets.Label('Upload file .json yang berisi list of jobs:'), upload_button, upload_generate_button])

all_buttons = [batch_button, normal_button, adv_button, upload_generate_button]

# =======================================================================
# BAGIAN 3: FUNGSI LOGIKA & EKSEKUSI
# =======================================================================
output_area = widgets.Output()

def run_execution_loop(jobs_list, mode_name=""):
    """Fungsi eksekusi umum yang kini menerima nama mode untuk log kustom."""
    for button in all_buttons: button.disabled = True
    try:
        output_dir = "/content/drive/MyDrive/Stable_diff"
        os.makedirs(f"{output_dir}/images", exist_ok=True); os.makedirs(f"{output_dir}/seeds", exist_ok=True)
        negative_prompt_default = "blurry, low quality, jpeg artifacts, distorted, watermark, text, signature"
        
        if not jobs_list: print("\n⚠️ Tidak ada pekerjaan yang valid ditemukan. Proses dihentikan.")
        else:
            # ATURAN 1: Log kustom berdasarkan mode
            total_jobs = len(jobs_list)
            if mode_name in ["Normal", "Advanced"]:
                print(f"\n🚀 Memulai proses generate...")
            else: # Batch atau JSON
                print(f"\n🚀 Memulai proses generate {mode_name}... Total {total_jobs} gambar.")

            for i, job_config in enumerate(jobs_list):
                if total_jobs > 1: print(f"\n--- Job {i+1}/{total_jobs} ---")
                if 'negative_prompt' not in job_config or not job_config['negative_prompt']:
                    job_config['negative_prompt'] = negative_prompt_default
                generate_stable_diffusion_image(model_pipe=pipe, output_dir=output_dir, **job_config)
            
            if mode_name in ["Normal", "Advanced"]:
                print("\n🎉 Generate selesai!")
            else:
                print(f"\n🎉 Proses generate {mode_name} selesai!")
    finally:
        for button in all_buttons: button.disabled = False
        # ATURAN 3: Reset widget upload file
        upload_button.value.clear()

def on_batch_button_clicked(b):
    with output_area:
        output_area.clear_output(wait=True); print("⚙️ Mem-parsing input dari Mode Batch...")
        jobs = parse_multi_job_input(batch_textarea.value)
        # ATURAN 1: Log ringkasan untuk mode batch
        if jobs: print(f"✅ Berhasil mem-parsing {len(jobs)} job untuk di generate.")
        run_execution_loop(jobs, mode_name="Batch")

def on_normal_button_clicked(b):
    with output_area:
        output_area.clear_output(wait=True); print("⚙️ Mempersiapkan job dari Mode Normal...")
        aspect_map = {
            'Lanskap (16:9) - 1024x576': (1024, 576), 'Potret (9:16) - 576x1024': (576, 1024),
            'Persegi (1:1) - 768x768': (768, 768), 'Lanskap Klasik (4:3) - 960x720': (960, 720),
            'Potret Wide (2:3) - 640x960': (640, 960), 'Ultrawide (21:9) - 1344x576': (1344, 576)
        }
        width, height = aspect_map.get(aspect_ratio_dropdown.value, (1024, 576))
        job = {"prompt": normal_prompt_area.value, "negative_prompt": normal_neg_prompt_area.value, "width": width, "height": height}
        # ATURAN 1: Log tambahan untuk mode normal
        if job["prompt"]: print("✅ Berhasil mendeteksi prompt, generate siap dimulai👌")
        run_execution_loop([job], mode_name="Normal")

def on_advanced_button_clicked(b):
    with output_area:
        output_area.clear_output(wait=True); print("⚙️ Mempersiapkan job dari Mode Advanced...")
        job = {"prompt": adv_prompt_area.value, "negative_prompt": adv_neg_prompt_area.value, "num_inference_steps": adv_steps_slider.value, "guidance_scale": adv_guidance_slider.value, "width": adv_width_slider.value, "height": adv_height_slider.value}
        if adv_seed_input.value is not None: job["seed"] = adv_seed_input.value
        # ATURAN 1: Log tambahan untuk mode advanced
        if job["prompt"]: print("✅ Berhasil mem-parsing parameter dari mode advance.")
        run_execution_loop([job], mode_name="Advanced")

def on_upload_button_clicked(b):
    with output_area:
        output_area.clear_output(wait=True); print("⚙️ Mem-parsing file JSON dari Mode Upload...")
        if not upload_button.value: print("❌ Tidak ada file yang di-upload. Silakan pilih file terlebih dahulu."); return
        uploaded_file = list(upload_button.value.values())[0]
        content_bytes = uploaded_file['content']
        try:
            raw_content = content_bytes.decode('utf-8'); clean_content = raw_content.strip()
            valid_json_string = f"[{clean_content}]"
            jobs = json.loads(valid_json_string)
            print(f"✅ Berhasil mem-parsing {len(jobs)} job dari file '{uploaded_file['metadata']['name']}'.")
            run_execution_loop(jobs, mode_name="JSON")
        except Exception as e: print(f"❌ Gagal mem-parsing file JSON: {e}")

# Menghubungkan tombol ke fungsi logikanya masing-masing
batch_button.on_click(on_batch_button_clicked); normal_button.on_click(on_normal_button_clicked)
adv_button.on_click(on_advanced_button_clicked); upload_generate_button.on_click(on_upload_button_clicked)

# =======================================================================
# BAGIAN 4: MERAKIT & MENAMPILKAN APLIKASI UI
# =======================================================================
tab_children = [batch_ui, normal_ui, adv_ui, upload_ui]
tab = widgets.Tab(children=tab_children)
tab.set_title(0, '1. Mode Batch'); tab.set_title(1, '2. Mode Normal')
tab.set_title(2, '3. Mode Advanced'); tab.set_title(3, '4. Mode Upload JSON')
print("Pilih mode operasi pada tab di bawah ini:")
display(tab, output_area)

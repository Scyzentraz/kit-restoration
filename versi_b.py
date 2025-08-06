# ==============================================================================
# KOHYA LORA TRAINING - VERSI YANG DIPERBAIKI
# ==============================================================================

# ------------------------------------------------------------------------------
# Bagian 1: Setup Environment yang Lebih Stabil
# ------------------------------------------------------------------------------
import os
import shutil
import subprocess
import sys

def run_command(command, check=True):
    """Jalankan command dengan error handling yang lebih baik"""
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e.stderr}")
        if check:
            raise
        return e

print("🚀 Memulai setup lingkungan...")

# Pindah ke direktori content dan bersihkan jika ada
os.chdir('/content/')
if os.path.exists('/content/sd-scripts'):
    shutil.rmtree('/content/sd-scripts')

# Clone repository
run_command('git clone https://github.com/kohya-ss/sd-scripts.git')
os.chdir('/content/sd-scripts/')

print("\n🔧 Memasang dependensi dengan urutan yang tepat...")

# Uninstall conflicting packages dulu
run_command('pip uninstall -y peft torchaudio tensorflow', check=False)

# Install torch dan xformers dulu
run_command('pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu121')
run_command('pip install xformers==0.0.26.post1 --index-url https://download.pytorch.org/whl/cu121')

# Install dependencies satu per satu untuk kontrol yang lebih baik
dependencies = [
    'accelerate==0.30.0',
    'transformers==4.44.0', 
    'diffusers[torch]==0.25.0',
    'bitsandbytes==0.44.0',
    'safetensors==0.4.2',
    'lion-pytorch==0.0.6',
    'prodigyopt==1.0',
    'opencv-python==4.8.1.78',
    'einops==0.7.0',
    'ftfy==6.1.1',
    'tensorboard',
    'rich==13.7.0',
    'imagesize==1.4.1',
    'toml==0.10.2',
    'voluptuous==0.13.1',
    'huggingface_hub>=0.28.1'
]

for dep in dependencies:
    run_command(f'pip install {dep}')

# Install package dalam editable mode
run_command('pip install -e .')

print("\n✅ Instalasi selesai dengan sukses!")

# ------------------------------------------------------------------------------
# Bagian 2: Konfigurasi Accelerate
# ------------------------------------------------------------------------------
print("\n⚙️ Mengkonfigurasi accelerate...")

# Buat konfigurasi accelerate secara programmatic
accelerate_config = """compute_environment: LOCAL_MACHINE
deepspeed_config: {}
distributed_type: 'NO'
downcast_bf16: 'no'
gpu_ids: all
machine_rank: 0
main_training_function: main
mixed_precision: fp16
num_machines: 1
num_processes: 1
rdzv_backend: static
same_network: true
tpu_env: []
tpu_use_cluster: false
tpu_use_sudo: false
use_cpu: false
"""

# Simpan konfigurasi
os.makedirs(os.path.expanduser('~/.cache/huggingface/accelerate'), exist_ok=True)
with open(os.path.expanduser('~/.cache/huggingface/accelerate/default_config.yaml'), 'w') as f:
    f.write(accelerate_config)

print("✅ Accelerate dikonfigurasi")

# ------------------------------------------------------------------------------
# Bagian 3: Hubungkan ke Drive
# ------------------------------------------------------------------------------
print("\n🔗 Menghubungkan ke Google Drive...")
from google.colab import drive
drive.mount('/content/drive')

# ------------------------------------------------------------------------------
# Bagian 4: Validasi Setup
# ------------------------------------------------------------------------------
print("\n🔍 Memvalidasi instalasi...")

# Test import critical modules
try:
    import torch
    import transformers
    import diffusers
    import accelerate
    print(f"✅ PyTorch: {torch.__version__}")
    print(f"✅ Transformers: {transformers.__version__}")
    print(f"✅ Diffusers: {diffusers.__version__}")
    print(f"✅ Accelerate: {accelerate.__version__}")
    print(f"✅ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
        print(f"✅ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except ImportError as e:
    print(f"❌ Import error: {e}")
    
print("\n🎯 Setup selesai!")

# ------------------------------------------------------------------------------
# Bagian 5: Fungsi Training yang Diperbaiki
# ------------------------------------------------------------------------------

def setup_training_paths(project_name, instance_name=None, class_name="person", repeats=10):
    """Setup path training dengan validasi dan penamaan folder yang tepat"""
    base_model_path = "/content/drive/MyDrive/AI/models/stable-diffusion-v1-5-fp16"
    project_folder = f"/content/drive/MyDrive/AI/training/{project_name}"
    
    # Gunakan project_name sebagai instance_name jika tidak dispesifikasi
    if instance_name is None:
        instance_name = project_name.lower().replace("_", "").replace("-", "")
    
    # Format folder DreamBooth yang benar
    dreambooth_folder_name = f"{repeats}_{instance_name}_{class_name}"
    
    paths = {
        'base_model': base_model_path,
        'project_folder': project_folder,
        'train_data_dir': project_folder,  # Root project folder untuk DreamBooth
        'images_folder': f"{project_folder}/images",
        'output_dir': f"{project_folder}/model", 
        'logging_dir': f"{project_folder}/log",
        'dreambooth_folder': os.path.join(project_folder, dreambooth_folder_name),  # Langsung di root
        'instance_name': instance_name,
        'class_name': class_name,
        'repeats': repeats
    }
    
    # Validasi base model
    if not os.path.exists(paths['base_model']):
        print(f"❌ Base model tidak ditemukan: {paths['base_model']}")
        print("Pastikan model Stable Diffusion 1.5 sudah ada di Drive")
        return None
    
    # Cek struktur folder dan perbaiki jika perlu
    images_folder = paths['images_folder']  
    
    # Cek apakah menggunakan struktur DreamBooth atau dataset biasa
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    
    # Cek gambar langsung di folder images
    direct_images = []
    if os.path.exists(images_folder):
        for file in os.listdir(images_folder):
            if file.lower().endswith(image_extensions):
                direct_images.append(file)
    
    # Cek subfolder DreamBooth yang sudah ada di root project
    existing_dreambooth_folders = []
    if os.path.exists(paths['project_folder']):
        for item in os.listdir(paths['project_folder']):
            item_path = os.path.join(paths['project_folder'], item)
            if os.path.isdir(item_path) and '_' in item:
                # Cek format DreamBooth: number_name_class
                parts = item.split('_')
                if len(parts) >= 3 and parts[0].isdigit():
                    # Cek apakah folder berisi gambar
                    subfolder_images = [f for f in os.listdir(item_path) 
                                      if f.lower().endswith(image_extensions)]
                    if subfolder_images:
                        existing_dreambooth_folders.append((item, len(subfolder_images)))
    
    print(f"📊 Ditemukan {len(direct_images)} gambar di folder images")
    print(f"📁 Ditemukan {len(existing_dreambooth_folders)} folder DreamBooth yang sudah ada")
    
    # Jika ada gambar di folder images, pindahkan ke struktur DreamBooth
    if direct_images:
        print(f"🔄 Membuat folder DreamBooth: {dreambooth_folder_name}")
        os.makedirs(paths['dreambooth_folder'], exist_ok=True)
        
        # Pindahkan semua gambar ke folder DreamBooth di root project
        moved_count = 0
        for img_file in direct_images:
            src = os.path.join(images_folder, img_file)
            dst = os.path.join(paths['dreambooth_folder'], img_file)
            if not os.path.exists(dst):  # Hindari overwrite
                shutil.move(src, dst)
                moved_count += 1
                
            # Cek dan pindahkan caption file jika ada
            caption_file = os.path.splitext(img_file)[0] + '.txt'
            src_caption = os.path.join(images_folder, caption_file)
            dst_caption = os.path.join(paths['dreambooth_folder'], caption_file)
            if os.path.exists(src_caption) and not os.path.exists(dst_caption):
                shutil.move(src_caption, dst_caption)
        
        print(f"✅ Dipindahkan {moved_count} gambar ke {paths['dreambooth_folder']}")
        existing_dreambooth_folders.append((dreambooth_folder_name, moved_count))
    
    # Hitung total gambar dari semua folder DreamBooth
    total_images = sum(count for _, count in existing_dreambooth_folders)
    
    if total_images == 0:
        print("❌ Tidak ada gambar training yang ditemukan")
        print("💡 Struktur folder yang benar:")
        print(f"   📁 {project_name}/")
        print(f"   ├── 📁 {dreambooth_folder_name}/")
        print("   │   ├── 🖼️ image1.jpg")
        print("   │   ├── 📝 image1.txt (opsional)")
        print("   │   └── ...")
        print(f"   ├── 📁 model/ (output)")
        print(f"   └── 📁 log/ (logging)")
        print(f"\n🎯 Instance name: '{instance_name}' (trigger word untuk memanggil LoRA)")
        print(f"🎯 Class name: '{class_name}' (kategori umum)")
        print(f"🎯 Repeats: {repeats}x per epoch")
        return None
    
    print(f"✅ Total {total_images} gambar siap untuk training")
    print(f"🎯 Instance name: '{instance_name}' (gunakan ini sebagai trigger word)")
    print(f"🎯 Class name: '{class_name}'")
    print(f"🎯 Repeats: {repeats}x per epoch")
    print(f"📁 Folder training: {dreambooth_folder_name}")
    
    # Validasi caption files
    print("\n🔍 Memvalidasi caption files...")
    validate_caption_files(paths['dreambooth_folder'])
    
    # Buat direktori output
    os.makedirs(paths['output_dir'], exist_ok=True)
    os.makedirs(paths['logging_dir'], exist_ok=True)
    
    return paths

def start_training(project_name, instance_name=None, class_name="person", repeats=10, **kwargs):
    """Mulai training dengan parameter yang lebih optimal"""
    
    # Setup paths
    paths = setup_training_paths(project_name, instance_name, class_name, repeats)
    if not paths:
        return False
        
    # Parameter default yang sudah dioptimalkan
    default_params = {
        'max_train_epochs': 10,
        'learning_rate': 1e-4,
        'network_dim': 32,
        'network_alpha': 16,
        'train_batch_size': 1,
        'gradient_accumulation_steps': 4,
        'mixed_precision': 'fp16',
        'optimizer_type': 'AdamW8bit',
        'lr_scheduler': 'cosine_with_restarts',
        'lr_warmup_steps': 100,
        'save_every_n_epochs': 2,
        'save_model_as': 'safetensors',
        'clip_skip': 2,
        'min_bucket_reso': 256,
        'max_bucket_reso': 1024,
        'seed': 42,
        'resolution': 512
    }
    
    # Update dengan parameter yang diberikan
    default_params.update(kwargs)
    
    # Build command dengan handling boolean yang benar
    cmd_parts = [
        'python', 'train_network.py',
        f'--pretrained_model_name_or_path="{paths["base_model"]}"',
        f'--train_data_dir="{paths["train_data_dir"]}"',  # Project folder untuk DreamBooth
        f'--output_dir="{paths["output_dir"]}"',
        f'--logging_dir="{paths["logging_dir"]}"',
        f'--output_name="{project_name}"',
        '--network_module=networks.lora',
        '--enable_bucket',
        '--cache_latents',
        '--cache_latents_to_disk',
        '--caption_extension=.txt',  # PERBAIKAN: Gunakan .txt bukan .caption
        '--shuffle_caption',
        '--keep_tokens=1',
        '--bucket_reso_steps=64',
        '--console_log_simple',  # Penting untuk Colab
        '--xformers'  # Untuk memory efficiency
    ]
    
    # Tambahkan parameter dengan handling khusus untuk boolean
    for key, value in default_params.items():
        if isinstance(value, bool):
            if value:
                cmd_parts.append(f'--{key}')
            # Boolean False tidak perlu ditambahkan ke command
        else:
            cmd_parts.append(f'--{key}={value}')
    
    # Gabungkan command
    command = ' '.join(cmd_parts)
    
    print(f"\n🔥 Memulai pelatihan untuk '{project_name}'...")
    print(f"📝 Command: {command[:100]}...")
    
    try:
        # Jalankan training
        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output real-time
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
            
        process.wait()
        
        if process.returncode == 0:
            print("\n🎉 Training selesai dengan sukses!")
            return True
        else:
            print(f"\n❌ Training gagal dengan return code: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error saat training: {e}")
        return False

# ------------------------------------------------------------------------------
# Fungsi Validasi Caption Files
# ------------------------------------------------------------------------------

def validate_caption_files(dreambooth_folder):
    """Validasi dan perbaiki caption files"""
    if not os.path.exists(dreambooth_folder):
        print(f"❌ Folder tidak ditemukan: {dreambooth_folder}")
        return False
    
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    images = [f for f in os.listdir(dreambooth_folder) if f.lower().endswith(image_extensions)]
    
    caption_count = 0
    missing_captions = []
    
    for img_file in images:
        base_name = os.path.splitext(img_file)[0]
        txt_file = f"{base_name}.txt"
        txt_path = os.path.join(dreambooth_folder, txt_file)
        
        if os.path.exists(txt_path):
            caption_count += 1
            # Cek isi caption
            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    print(f"⚠️ Caption kosong: {txt_file}")
        else:
            missing_captions.append(img_file)
    
    print(f"📝 Caption files ditemukan: {caption_count}/{len(images)}")
    
    if missing_captions:
        print(f"⚠️ Missing caption files untuk:")
        for img in missing_captions[:5]:  # Show first 5
            print(f"   - {img}")
        if len(missing_captions) > 5:
            print(f"   ... dan {len(missing_captions) - 5} lainnya")
            
        # Auto-generate missing captions
        print("🔄 Membuat caption files yang hilang...")
        for img_file in missing_captions:
            base_name = os.path.splitext(img_file)[0]
            txt_file = f"{base_name}.txt"
            txt_path = os.path.join(dreambooth_folder, txt_file)
            
            # Default caption berdasarkan folder name
            folder_name = os.path.basename(dreambooth_folder)
            parts = folder_name.split('_')
            if len(parts) >= 3:
                instance_name = parts[1]
                class_name = parts[2]
                default_caption = f"a photo of {instance_name} {class_name}, high quality"
            else:
                default_caption = "a high quality photo"
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(default_caption)
            
            print(f"   ✅ Dibuat: {txt_file} -> '{default_caption}'")
    
    return True

def quick_test_training(project_name, instance_name=None, class_name="person", repeats=10):
    """Test training dengan parameter minimal untuk debugging"""
    
    paths = setup_training_paths(project_name, instance_name, class_name, repeats)
    if not paths:
        return False
    
    # Command yang sangat sederhana untuk test - menggunakan project folder sebagai train_data_dir
    cmd_parts = [
        'python', 'train_network.py',
        f'--pretrained_model_name_or_path={paths["base_model"]}',
        f'--train_data_dir={paths["train_data_dir"]}',  # Project folder yang berisi folder DreamBooth
        f'--output_dir={paths["output_dir"]}',
        f'--output_name={project_name}',
        '--network_module=networks.lora',
        '--network_dim=16',
        '--network_alpha=8', 
        '--resolution=512',
        '--train_batch_size=1',
        '--max_train_epochs=1',  # Hanya 1 epoch untuk testing
        '--learning_rate=1e-4',
        '--mixed_precision=fp16',
        '--save_model_as=safetensors',
        '--caption_extension=.txt',  # PERBAIKAN: Gunakan .txt
        '--enable_bucket',
        '--console_log_simple'
    ]
    
    command = ' '.join(cmd_parts)
    
    print(f"\n🧪 Menjalankan test training untuk '{project_name}'...")
    print(f"🎯 Trigger word: '{paths['instance_name']}'")
    print(f"📁 Training data path: {paths['train_data_dir']}")
    print(f"📝 Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=1800)  # 30 menit timeout
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        if result.returncode == 0:
            print("\n🎉 Test training berhasil!")
            print(f"💡 Untuk generate gambar, gunakan prompt: '{paths['instance_name']} {paths['class_name']}'")
            return True
        else:
            print(f"\n❌ Test training gagal dengan return code: {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n⏰ Training timeout (30 menit)")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

# ------------------------------------------------------------------------------
# Contoh Penggunaan
# ------------------------------------------------------------------------------

# Untuk memulai training, jalankan:
# start_training("Rezcty_project", max_train_epochs=15, learning_rate=5e-5)

# Untuk test training sederhana:
# quick_test_training("Rezcty_project")

print("""
🎯 PANDUAN PENAMAAN FOLDER DREAMBOOTH:

Format: [repeats]_[instance_name]_[class_name]

📖 CONTOH PENAMAAN:
1. Untuk karakter "Rezcty": 10_rezcty_person
2. Untuk karakter anime "Sakura": 15_sakura_girl  
3. Untuk objek mobil: 20_mycar_car
4. Untuk hewan "Fluffy": 12_fluffy_cat

🎯 CARA PENGGUNAAN:

1. Training dengan nama default (otomatis dari project_name):
   quick_test_training("Rezcty_project")
   # Akan membuat: 10_rezctyproject_person

2. Training dengan custom instance name:
   quick_test_training("Rezcty_project", instance_name="rezcty", class_name="person", repeats=15)
   # Akan membuat: 15_rezcty_person

3. Training penuh:
   start_training("Rezcty_project", instance_name="rezcty", class_name="person")

💡 TIPS:
- Instance name = trigger word untuk memanggil LoRA
- Gunakan nama unik, hindari kata umum
- Semakin sedikit gambar → repeats lebih tinggi
- 5-10 gambar = 15-20 repeats
- 10-20 gambar = 10-15 repeats  
- 20+ gambar = 5-10 repeats

📁 STRUKTUR FOLDER AKHIR:
/content/drive/MyDrive/AI/training/Rezcty_project/
└── images/
    └── 15_rezcty_person/
        ├── photo1.jpg
        ├── photo1.txt (opsional)
        └── ...
""")

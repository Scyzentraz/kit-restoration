CELL 0
!pip install "numpy<2.0"
Restart

# ==============================================================================
# LORA TRAINING SETUP - CLEAR RESTART GUIDANCE
# Critical: Follow restart instructions exactly to avoid dependency conflicts
# ==============================================================================

# ==============================================================================
# PHASE 1: ENVIRONMENT PREPARATION (NO RESTART NEEDED)
# Run these cells sequentially WITHOUT restart between them
# ==============================================================================

# CELL 1A: Environment Check & Cleanup
print("🔍 PHASE 1A: Environment Check & Cleanup")
print("=" * 60)
print("⚠️  DO NOT RESTART after this cell!")
print("=" * 60)

import os
import shutil
import subprocess
import sys
import time

def run_command(command, check=True, show_output=True):
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if show_output and result.stdout:
            print(result.stdout)
        if show_output and result.stderr:
            print("STDERR:", result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running command: {command}")
        print(f"Error: {e.stderr}")
        if check:
            raise
        return e

# Check if restart is needed first
restart_needed = False
try:
    import numpy
    numpy_version = numpy.__version__
    if numpy_version.startswith('2.'):
        print(f"⚠️ WARNING: numpy {numpy_version} detected (need <2.0)")
        restart_needed = True
    else:
        print(f"✅ numpy {numpy_version} (good)")
except ImportError:
    print("⚠️ numpy not found - will install correct version")

if restart_needed:
    print("\n" + "="*60)
    print("🔄 RESTART REQUIRED!")
    print("Please restart runtime NOW, then run this cell again")
    print("="*60)
    raise Exception("Restart runtime required due to numpy 2.x")

# Clean conflicting packages
print("\n🧹 Cleaning conflicting packages...")
conflicting_packages = [
    'tensorflow', 'tensorflow-gpu', 'tf-nightly',
    'torchaudio', 'peft'
]

for pkg in conflicting_packages:
    print(f"   Removing {pkg}...")
    run_command(f'pip uninstall -y {pkg}', check=False, show_output=False)

print("   Clearing pip cache...")
run_command('pip cache purge', check=False, show_output=False)

print("✅ Environment cleanup completed!")
print("\n➡️ IMMEDIATELY run CELL 1B (DO NOT RESTART)")

# ==============================================================================

# CELL 1B: Core Dependencies Installation
print("🔧 PHASE 1B: Core Dependencies Installation")  
print("=" * 60)
print("⚠️  DO NOT RESTART after this cell!")
print("=" * 60)

# CRITICAL: Install numpy <2.0 FIRST
print("📦 Installing numpy<2.0 (CRITICAL FIRST)...")
result = run_command('pip install "numpy<2.0"')
if result.returncode != 0:
    raise Exception("Numpy installation failed")

# Install PyTorch ecosystem  
print("🔥 Installing PyTorch + torchvision...")
torch_cmd = 'pip install torch==2.3.0 torchvision==0.18.0 --index-url https://download.pytorch.org/whl/cu121'
result = run_command(torch_cmd)
if result.returncode != 0:
    raise Exception("PyTorch installation failed")

# Install xformers
print("⚡ Installing xformers...")
xformers_cmd = 'pip install xformers==0.0.26.post1 --index-url https://download.pytorch.org/whl/cu121'
result = run_command(xformers_cmd)
if result.returncode != 0:
    print("⚠️ Warning: xformers install failed, continuing...")

print("✅ Core dependencies installed!")
print("\n" + "="*60)
print("🔄 MANDATORY RESTART #1")
print("REASON: PyTorch & numpy need to be loaded fresh")
print("ACTION: Restart runtime NOW, then run CELL 2A")  
print("="*60)

# ==============================================================================
# PHASE 2: ML STACK INSTALLATION (AFTER RESTART #1)
# Start here after first mandatory restart
# ==============================================================================

# CELL 2A: Verify Core Dependencies & Install ML Stack
print("🤖 PHASE 2A: ML Stack Installation (After Restart #1)")
print("=" * 60)
print("⚠️  This should be run AFTER restart #1")
print("⚠️  DO NOT RESTART after this cell!")
print("=" * 60)

# Verify core dependencies are properly loaded
try:
    import torch
    import numpy
    print(f"✅ PyTorch: {torch.__version__}")
    print(f"✅ NumPy: {numpy.__version__}")
    if torch.cuda.is_available():
        print(f"✅ CUDA: {torch.cuda.get_device_name(0)}")
    else:
        raise Exception("CUDA not available")
except ImportError as e:
    print("❌ Core dependencies not found after restart!")
    print("Please run CELL 1A and 1B again, then restart")
    raise Exception(f"Import error: {e}")

# Install ML stack in correct order
print("\n📦 Installing ML stack...")
ml_packages = [
    'accelerate==0.30.0',
    'huggingface-hub==0.24.5',  # IMPORTANT: 0.24.5 not 0.28.1+
    'transformers==4.44.0', 
    'diffusers[torch]==0.25.0',
    'safetensors==0.4.2',
    'bitsandbytes==0.44.0'
]

for pkg in ml_packages:
    print(f"   Installing {pkg}...")
    result = run_command(f'pip install {pkg}')
    if result.returncode != 0:
        raise Exception(f"Failed to install {pkg}")

print("✅ ML stack installation completed!")
print("\n➡️ IMMEDIATELY run CELL 2B (DO NOT RESTART)")

# ==============================================================================

# CELL 2B: Utilities & Kohya Setup
print("🛠️ PHASE 2B: Utilities & Kohya Setup")
print("=" * 60)
print("⚠️  DO NOT RESTART after this cell!")
print("=" * 60)

# Install utilities
print("📦 Installing utilities...")
utility_packages = [
    'opencv-python==4.8.1.78',
    'einops==0.7.0',
    'ftfy==6.1.1', 
    'tensorboard',
    'rich==13.7.0',
    'imagesize==1.4.1',
    'toml==0.10.2',
    'voluptuous==0.13.1',
    'lion-pytorch==0.0.6',
    'prodigyopt==1.0'
]

for pkg in utility_packages:
    print(f"   Installing {pkg}...")
    result = run_command(f'pip install {pkg}', check=False)
    if result.returncode != 0:
        print(f"⚠️ Warning: Failed to install {pkg}, continuing...")

# Setup Kohya scripts
print("\n📁 Setting up Kohya scripts...")
os.chdir('/content/')
if os.path.exists('/content/sd-scripts'):
    print("   Removing existing sd-scripts...")
    shutil.rmtree('/content/sd-scripts')

print("   Cloning kohya-ss repository...")
result = run_command('git clone https://github.com/kohya-ss/sd-scripts.git')
if result.returncode != 0:
    raise Exception("Repository clone failed")

os.chdir('/content/sd-scripts/')

print("   Installing kohya-ss in editable mode...")
result = run_command('pip install -e .')
if result.returncode != 0:
    raise Exception("Kohya-ss installation failed")

print("✅ Utilities & Kohya setup completed!")
print("\n" + "="*60)
print("🔄 MANDATORY RESTART #2") 
print("REASON: All ML packages need fresh import for compatibility")
print("ACTION: Restart runtime NOW, then run CELL 3A")
print("="*60)

# ==============================================================================
# PHASE 3: FINAL SETUP & VALIDATION (AFTER RESTART #2) 
# Start here after second mandatory restart
# ==============================================================================

# CELL 3A: Configuration & Validation (After Restart #2)
print("⚙️ PHASE 3A: Configuration & Validation (After Restart #2)")
print("=" * 60)
print("⚠️  This should be run AFTER restart #2")
print("⚠️  DO NOT RESTART after this cell!")
print("=" * 60)

# Configure accelerate
print("🔧 Configuring accelerate...")
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

config_dir = os.path.expanduser('~/.cache/huggingface/accelerate')
os.makedirs(config_dir, exist_ok=True)
config_path = os.path.join(config_dir, 'default_config.yaml')
with open(config_path, 'w') as f:
    f.write(accelerate_config)

print("✅ Accelerate configured!")

# Mount Google Drive
print("🔗 Mounting Google Drive...")
try:
    from google.colab import drive
    drive.mount('/content/drive')
    print("✅ Google Drive mounted!")
except Exception as e:
    raise Exception(f"Drive mount failed: {e}")

# CRITICAL: Full validation with fresh imports
print("\n🔍 Running full validation with fresh imports...")

# Test all critical imports
test_imports = [
    ('torch', 'PyTorch'),
    ('torchvision', 'TorchVision'),
    ('transformers', 'Transformers'),
    ('diffusers', 'Diffusers'), 
    ('accelerate', 'Accelerate'),
    ('huggingface_hub', 'HuggingFace Hub'),
    ('bitsandbytes', 'BitsAndBytes'),
    ('safetensors', 'SafeTensors'),
    ('cv2', 'OpenCV'),
    ('numpy', 'NumPy')
]

failed_imports = []
for module, name in test_imports:
    try:
        imported_module = __import__(module)
        version = getattr(imported_module, '__version__', 'unknown')
        print(f"✅ {name}: {version}")
    except ImportError as e:
        print(f"❌ {name}: Failed - {str(e)}")
        failed_imports.append(name)

# Test critical functionality
print("\n🎯 Testing critical functionality...")

# Test the problematic import that was causing issues
try:
    from huggingface_hub import cached_download
    print("✅ huggingface_hub.cached_download: OK")
except ImportError as e:
    print(f"❌ huggingface_hub.cached_download: FAILED - {str(e)}")
    failed_imports.append("cached_download")

try:
    from diffusers import DDPMScheduler
    print("✅ diffusers.DDPMScheduler: OK")
except ImportError as e:
    print(f"❌ diffusers.DDPMScheduler: FAILED - {str(e)}")
    failed_imports.append("DDPMScheduler")

# Test GPU
try:
    import torch
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"✅ VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    else:
        failed_imports.append("CUDA")
except Exception as e:
    print(f"❌ CUDA test failed: {e}")
    failed_imports.append("CUDA")

if failed_imports:
    print(f"\n❌ VALIDATION FAILED!")
    print(f"Failed: {', '.join(failed_imports)}")
    print("\nTROUBLESHOOTING:")
    print("1. Restart runtime")
    print("2. Run CELL 1A → CELL 1B → Restart #1")
    print("3. Run CELL 2A → CELL 2B → Restart #2") 
    print("4. Run this CELL 3A again")
    raise Exception("Validation failed")
else:
    print(f"\n🎉 VALIDATION SUCCESS!")
    print("All systems operational! Ready for training!")

print("\n➡️ IMMEDIATELY run CELL 3B for model download (optional)")

# ==============================================================================

# CELL 3B: Base Model Download (Optional)
print("📥 PHASE 3B: Base Model Download (Optional)")
print("=" * 60)
print("⚠️  NO RESTART needed after this cell")
print("=" * 60)

import torch
from diffusers import StableDiffusionPipeline

model_id = "runwayml/stable-diffusion-v1-5"
save_path = "/content/drive/MyDrive/AI/models/stable-diffusion-v1-5-fp16"

if os.path.exists(save_path):
    print(f"✅ Model already exists at: {save_path}")
else:
    print("📦 Downloading Stable Diffusion 1.5...")
    print("⏱️ This will take several minutes...")
    
    try:
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            torch_dtype=torch.float16
        )
        
        print(f"💾 Saving to: {save_path}...")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        pipe.save_pretrained(save_path)
        print("✅ Model downloaded successfully!")
    except Exception as e:
        raise Exception(f"Model download failed: {e}")

print("\n🎯 SETUP COMPLETE!")
print("➡️ Now upload images and run TRAINING CELL")

# ==============================================================================
# PHASE 4: TRAINING (NO RESTART NEEDED)
# Run this anytime after Phase 3 completion
# ==============================================================================

# TRAINING CELL: Execute Training
print("🔥 TRAINING: Execute LoRA Training")
print("=" * 60)
print("⚠️  NO RESTART needed - run anytime after Phase 3")
print("=" * 60)

def setup_training_paths(project_name, instance_name=None, class_name="person", repeats=10):
    """Setup training paths with validation"""
    base_model_path = "/content/drive/MyDrive/AI/models/stable-diffusion-v1-5-fp16"
    project_folder = f"/content/drive/MyDrive/AI/training/{project_name}"
    
    if instance_name is None:
        instance_name = project_name.lower().replace("_", "").replace("-", "")
    
    dreambooth_folder_name = f"{repeats}_{instance_name}_{class_name}"
    
    paths = {
        'base_model': base_model_path,
        'project_folder': project_folder,
        'train_data_dir': project_folder,
        'images_folder': f"{project_folder}/images",
        'output_dir': f"{project_folder}/model",
        'logging_dir': f"{project_folder}/log",
        'dreambooth_folder': os.path.join(project_folder, dreambooth_folder_name),
        'instance_name': instance_name,
        'class_name': class_name,
        'repeats': repeats
    }
    
    if not os.path.exists(paths['base_model']):
        print(f"❌ Base model not found: {paths['base_model']}")
        return None
    
    # Handle image folder structure
    image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
    
    direct_images = []
    if os.path.exists(paths['images_folder']):
        direct_images = [f for f in os.listdir(paths['images_folder']) 
                        if f.lower().endswith(image_extensions)]
    
    existing_dreambooth_folders = []
    if os.path.exists(paths['project_folder']):
        for item in os.listdir(paths['project_folder']):
            item_path = os.path.join(paths['project_folder'], item)
            if os.path.isdir(item_path) and '_' in item:
                parts = item.split('_')
                if len(parts) >= 3 and parts[0].isdigit():
                    subfolder_images = [f for f in os.listdir(item_path) 
                                      if f.lower().endswith(image_extensions)]
                    if subfolder_images:
                        existing_dreambooth_folders.append((item, len(subfolder_images)))
    
    print(f"📊 Direct images: {len(direct_images)}")
    print(f"📁 DreamBooth folders: {len(existing_dreambooth_folders)}")
    
    # Move images to DreamBooth structure if needed
    if direct_images:
        os.makedirs(paths['dreambooth_folder'], exist_ok=True)
        moved_count = 0
        for img_file in direct_images:
            src = os.path.join(paths['images_folder'], img_file)
            dst = os.path.join(paths['dreambooth_folder'], img_file) 
            if not os.path.exists(dst):
                shutil.move(src, dst)
                moved_count += 1
        print(f"✅ Moved {moved_count} images to DreamBooth structure")
        existing_dreambooth_folders.append((dreambooth_folder_name, moved_count))
    
    total_images = sum(count for _, count in existing_dreambooth_folders)
    
    if total_images == 0:
        print("❌ No training images found!")
        print(f"📁 Upload images to: {paths['images_folder']}/")
        return None
    
    print(f"✅ Total: {total_images} images ready")
    print(f"🎯 Trigger: '{instance_name}' | Class: '{class_name}' | Repeats: {repeats}")
    
    os.makedirs(paths['output_dir'], exist_ok=True)
    os.makedirs(paths['logging_dir'], exist_ok=True)
    
    return paths

def start_training(project_name, instance_name=None, class_name="person", repeats=10, **kwargs):
    """Execute training with optimal parameters"""
    
    # Make sure we're in the right directory
    os.chdir('/content/sd-scripts/')
    
    paths = setup_training_paths(project_name, instance_name, class_name, repeats)
    if not paths:
        return False
    
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
    
    default_params.update(kwargs)
    
    cmd_parts = [
        'python', 'train_network.py',
        f'--pretrained_model_name_or_path="{paths["base_model"]}"',
        f'--train_data_dir="{paths["train_data_dir"]}"',
        f'--output_dir="{paths["output_dir"]}"',
        f'--logging_dir="{paths["logging_dir"]}"',
        f'--output_name="{project_name}"',
        '--network_module=networks.lora',
        '--enable_bucket',
        '--cache_latents',
        '--cache_latents_to_disk', 
        '--shuffle_caption',
        '--keep_tokens=1',
        '--bucket_reso_steps=64',
        '--console_log_simple',
        '--xformers'
    ]
    
    for key, value in default_params.items():
        if isinstance(value, bool):
            if value:
                cmd_parts.append(f'--{key}')
        else:
            cmd_parts.append(f'--{key}={value}')
    
    command = ' '.join(cmd_parts)
    
    print(f"\n🔥 Starting training: '{project_name}'")
    print(f"📝 Command: {command[:100]}...")
    
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            print(line.strip())
        
        process.wait()
        
        if process.returncode == 0:
            print("\n🎉 Training completed successfully!")
            return True
        else:
            print(f"\n❌ Training failed with return code: {process.returncode}")
            return False
    
    except Exception as e:
        print(f"\n❌ Training error: {e}")
        return False

# =============================================================================
# CONFIGURE YOUR TRAINING HERE
# =============================================================================

PROJECT_NAME = "Rezcty_project"
INSTANCE_NAME = "rezcty"  
CLASS_NAME = "person"
REPEATS = 10

TRAINING_PARAMS = {
    'max_train_epochs': 10,
    'learning_rate': 1e-4,
    'network_dim': 32,
    'network_alpha': 16,
}

print("🎯 TRAINING CONFIGURATION:")
print(f"   Project: {PROJECT_NAME}")
print(f"   Trigger: {INSTANCE_NAME}")
print(f"   Class: {CLASS_NAME}")
print(f"   Repeats: {REPEATS}")

# Uncomment to start training:
# start_training(PROJECT_NAME, INSTANCE_NAME, CLASS_NAME, REPEATS, **TRAINING_PARAMS)

print("\n💡 Uncomment the last line to start training!")

# ==============================================================================
# RESTART SUMMARY & TROUBLESHOOTING
# ==============================================================================

print("""
📋 RESTART SUMMARY:

CORRECT EXECUTION ORDER:
1. CELL 1A (cleanup) → CELL 1B (core deps) → 🔄 RESTART #1
2. CELL 2A (ML stack) → CELL 2B (utilities) → 🔄 RESTART #2  
3. CELL 3A (config/validation) → CELL 3B (model download)
4. TRAINING CELL (anytime after step 3)

🔄 MANDATORY RESTARTS:
- Restart #1: After installing PyTorch & numpy (fresh loading required)
- Restart #2: After installing all ML packages (compatibility check)

⚠️ CRITICAL RULES:
- NEVER restart between cells in same phase
- ALWAYS restart when instructed
- If any cell fails, restart and start from Phase 1
- Don't skip phases or change order

🐛 TROUBLESHOOTING:
- Import error → Restart runtime, start from CELL 1A
- Training fails → Check images uploaded correctly  
- Dependency conflict → Follow restart sequence exactly
- GPU error → Make sure GPU runtime selected

💡 WHY RESTARTS ARE NEEDED:
- Python caches imports in memory
- New package versions need fresh import
- Dependency conflicts resolved by clean loading
- PyTorch especially sensitive to loading order
""")
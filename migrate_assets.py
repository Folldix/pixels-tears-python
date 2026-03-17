# migrate_assets.py
import shutil
from pathlib import Path

def migrate_sprites(godot_dir: str, output_dir: str):
    """Копіює PNG-спрайти, ігноруючи .import метафайли."""
    src = Path(godot_dir)
    dst = Path(output_dir)
    
    copied = 0
    for img in src.rglob('*.png'):
        # Зберігаємо структуру папок
        rel = img.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, out)
        copied += 1
    
    print(f'✓ Скопійовано {copied} спрайтів')

migrate_sprites('C:/Users/artem/Downloads/pixels-and-tears-main-fgmult-(2)-(1)/Resource/Sprite', 'C:/Homework/Pixels-and-Tears_PyGame/assets/sprite_female')
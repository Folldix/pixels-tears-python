# audit_godot_project.py
import os, json
from pathlib import Path
from collections import defaultdict

def audit(root: str):
    cats = defaultdict(list)
    ext_map = {
        '.gd':     'scripts',
        '.tscn':   'scenes',
        '.tres':   'resources',
        '.png':    'sprites',
        '.wav':    'audio_sfx',
        '.ogg':    'audio_music',
        '.import': 'import_meta',
        '.json':   'data',
        '.cfg':    'config',
        '.godot':  'project',
    }
    
    for p in Path(root).rglob('*'):
        if p.is_file():
            key = ext_map.get(p.suffix.lower(), 'other')
            cats[key].append({
                'path': str(p.relative_to(root)),
                'size_kb': round(p.stat().st_size / 1024, 1)
            })
    
    print('\n=== АУДИТ GODOT-ПРОЄКТУ ===')
    total_work = 0
    for cat in ['scripts', 'scenes', 'resources', 'sprites', 'audio_sfx', 'audio_music', 'data']:
        items = cats.get(cat, [])
        kb = sum(i['size_kb'] for i in items)
        print(f'  {cat:<14}: {len(items):>4} файлів  ({kb:>8.1f} KB)')
        if cat in ('scripts', 'scenes'):
            total_work += len(items)
    
    print(f'\n  Орієнтовний обсяг портування: {total_work} файлів GDScript/сцен')
    
    # Зберегти детальний звіт
    with open('C:/Homework/Pixels-and-Tears_PyGame/godot_audit.json', 'w', encoding='utf-8') as f:
        json.dump(dict(cats), f, ensure_ascii=False, indent=2)
    print('\n  Детальний звіт збережено у godot_audit.json')

audit('C:/Users/artem/Downloads/pixels-and-tears-main-fgmult-(2)-(1)')  # шлях до розпакованого проєкту
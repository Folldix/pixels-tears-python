from __future__ import annotations

import pygame as pg

from game.assets import Assets

DEFAULT_TARGET_W = 440
HEIGHT_SQUASH = 0.85
ACTIVE_SCALE = 0.99


def load_menu_button_pair(assets: Assets, target_w: int = DEFAULT_TARGET_W) -> tuple[pg.Surface, pg.Surface] | None:
    p_norm = assets.path("button", "MenuButton_v2.png")
    p_press = assets.path("button", "MenuButton_v2_pressed.png")
    if not p_norm.exists():
        return None
    raw_n = pg.image.load(str(p_norm)).convert_alpha()
    target_h = max(1, int(raw_n.get_height() * target_w / raw_n.get_width()))
    target_h = max(1, int(target_h * HEIGHT_SQUASH))
    size = (target_w, target_h)
    normal = pg.transform.smoothscale(raw_n, size)
    if p_press.exists():
        raw_p = pg.image.load(str(p_press)).convert_alpha()
        pressed = pg.transform.smoothscale(raw_p, size)
    else:
        pressed = normal
    return normal, pressed


def blit_textured_menu_button(
    screen: pg.Surface,
    normal: pg.Surface,
    pressed: pg.Surface,
    cx: int,
    cy: int,
    mouse_pos: tuple[int, int],
    label: str,
    font: pg.font.Font,
    *,
    keyboard_selected: bool,
    text_color_active: tuple[int, int, int],
    text_color_inactive: tuple[int, int, int],
    max_text_pad: int = 36,
) -> pg.Rect:
    bw, bh = normal.get_size()
    base_hit = normal.get_rect(center=(cx, cy))
    hovered = base_hit.collidepoint(mouse_pos)
    active = hovered or keyboard_selected

    base_surf = pressed if active else normal
    if active:
        sw = max(1, int(bw * ACTIVE_SCALE))
        sh = max(1, int(bh * ACTIVE_SCALE))
        draw_surf = pg.transform.smoothscale(base_surf, (sw, sh))
    else:
        draw_surf = base_surf

    screen.blit(draw_surf, draw_surf.get_rect(center=(cx, cy)))

    color = text_color_active if active else text_color_inactive
    surf = font.render(label, True, color)
    max_tw = bw - max_text_pad
    if surf.get_width() > max_tw:
        sc = max_tw / surf.get_width()
        surf = pg.transform.smoothscale(
            surf,
            (max(1, int(surf.get_width() * sc)), max(1, int(surf.get_height() * sc))),
        )
    if active:
        tw, th = surf.get_size()
        surf = pg.transform.smoothscale(
            surf,
            (max(1, int(tw * ACTIVE_SCALE)), max(1, int(th * ACTIVE_SCALE))),
        )
    screen.blit(surf, surf.get_rect(center=(cx, cy)))
    return base_hit

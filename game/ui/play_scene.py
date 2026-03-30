from __future__ import annotations

from dataclasses import dataclass, field
import random
from queue import Queue
from typing import Any

import pygame as pg

from game.assets import Assets
from game.constants import BASE_HEIGHT, BASE_WIDTH, WHITE
from game.state import GameState
from game.net.ws_client import WsClient

def _load_dir_frames(assets: Assets, folder: str, prefix: str) -> list[pg.Surface]:
    # Очікуємо імена на кшталт up1.png..up4.png, left1.png..left4.png і т.д.
    frames: list[pg.Surface] = []
    for i in range(1, 5):
        frames.append(assets.image(folder, f"{prefix}{i}.png"))
    return frames


@dataclass
class Player:
    assets: Assets
    state: GameState

    pos: pg.Vector2
    speed: float = 150.0

    direction: pg.Vector2 = field(default_factory=lambda: pg.Vector2(0, 0))
    anim_time: float = 0.0
    anim_idx: int = 0

    def __post_init__(self) -> None:
        folder = "sprite_male" if self.state.skin_name == "male" else "sprite_female"
        self.frames = {
            "down": _load_dir_frames(self.assets, folder, "down"),
            "up": _load_dir_frames(self.assets, folder, "up"),
            "left": _load_dir_frames(self.assets, folder, "left"),
            "right": _load_dir_frames(self.assets, folder, "right"),
        }
        self.idle = self.frames["down"][0]
        self.facing = "down"
        self.walk_sound = self._load_walk_sound()
        self._walk_playing = False
        self.hitbox = self._load_player_hit_offsets()
        
    def _load_player_hit_offsets(self) -> list[tuple[int, int]]:
        """
        Зміщення від центру до пікселів хітбоксу (як у rect(center=pos)).

        За вимогою (спрайт 80×80) колізія — прямокутник у координатах оригінального
        зображення спрайта:
        x:[30..49], y:[45..60] (включно).
        """
        w, h = 80, 80
        x1, y1 = 30, 45
        x2, y2 = 49, 60

        out: list[tuple[int, int]] = []
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                out.append((x - w // 2, y - h // 2))
        return out
    
    def _load_walk_sound(self) -> pg.mixer.Sound | None:
        # Аналог $WalkSound у Godot: пробуємо підхопити звук кроків.
        for rel in (
            ("sounds", "chelovek-bejit-po-trave-26013.mp3"),
            ("sounds", "veter-na-igrovoy-ploschadke-35870.mp3"),
        ):
            p = self.assets.path(*rel)
            if p.exists():
                try:
                    return pg.mixer.Sound(str(p))
                except pg.error:
                    return None
        return None

    def handle_keys(self) -> None:
        keys = pg.key.get_pressed()
        d = pg.Vector2(0, 0)
        if keys[pg.K_w] or keys[pg.K_UP]:
            d.y -= 1
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            d.y += 1
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            d.x -= 1
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            d.x += 1
        self.direction = d.normalize() if d.length_squared() > 0 else pg.Vector2(0, 0)

        if abs(self.direction.x) > abs(self.direction.y):
            if self.direction.x > 0:
                self.facing = "right"
            elif self.direction.x < 0:
                self.facing = "left"
        elif self.direction.y != 0:
            self.facing = "down" if self.direction.y > 0 else "up"

    def sync_facing_from_direction(self) -> None:
        """Те саме обличчя/напрям, що й у handle_keys — для керування мишею."""
        if self.direction.length_squared() == 0:
            return
        if abs(self.direction.x) > abs(self.direction.y):
            self.facing = "right" if self.direction.x > 0 else "left"
        else:
            self.facing = "down" if self.direction.y > 0 else "up"

    def tick_animation(self, dt: float) -> None:
        moving = self.direction.length_squared() > 0
        if moving:
            self.anim_time += dt
            if self.anim_time >= 0.12:
                self.anim_time = 0.0
                self.anim_idx = (self.anim_idx + 1) % 4
        else:
            self.anim_idx = 0
            self.anim_time = 0.0

        # Звук кроків
        if getattr(self, "walk_sound", None) is not None:
            if moving and not self._walk_playing:
                self.walk_sound.play(loops=-1)
                self._walk_playing = True
            elif (not moving) and self._walk_playing:
                self.walk_sound.stop()
                self._walk_playing = False

    def image(self) -> pg.Surface:
        if self.direction.length_squared() == 0:
            return self.idle
        return self.frames[self.facing][self.anim_idx]

    def rect(self) -> pg.Rect:
        img = self.image()
        r = img.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        return r

    def draw(self, screen: pg.Surface, cam: pg.Vector2) -> None:
        img = self.image()

        scale_factor = 1.2
        new_w = int(img.get_width() * scale_factor)
        new_h = int(img.get_height() * scale_factor)

        img = pg.transform.scale(img, (new_w, new_h))

        draw_x = int(self.pos.x - cam.x)
        draw_y = int(self.pos.y - cam.y)
        img_rect = img.get_rect(center=(draw_x, draw_y))
        screen.blit(img, img_rect)


@dataclass
class Enemy:
    pos: pg.Vector2
    speed: float = 100.0
    active_after_s: float = 300.0

    _timer: float = 0.0
    visible: bool = False

    def update(self, dt: float, player_pos: pg.Vector2, world_w: int, world_h: int) -> None:
        if not self.visible:
            self._timer += dt
            if self._timer >= self.active_after_s:
                self.visible = True
            return

        direction = (player_pos - self.pos)
        if direction.length_squared() > 0:
            direction = direction.normalize()
        jitter = pg.Vector2(
            (random.random() - 0.5) * 4,
            (random.random() - 0.5) * 4,
        )
        vel = direction * self.speed + jitter
        self.pos += vel * dt
        self.pos.x = max(0, min(world_w, self.pos.x))
        self.pos.y = max(0, min(world_h, self.pos.y))

    def draw(self, screen: pg.Surface, cam: pg.Vector2) -> None:
        if not self.visible:
            return
        pg.draw.circle(
            screen,
            (200, 60, 60),
            (int(self.pos.x - cam.x), int(self.pos.y - cam.y)),
            14,
        )


@dataclass
class Material:
    pos: pg.Vector2
    image: pg.Surface
    item_type: str
    visible: bool = True

    def draw(self, surface: pg.Surface, cam: pg.Vector2, player_pos: pg.Vector2, font: pg.font.Font) -> None:
        if not self.visible:
            return

        # Малюємо сам предмет
        draw_x = int(self.pos.x - cam.x)
        draw_y = int(self.pos.y - cam.y)
        rect = self.image.get_rect(center=(draw_x, draw_y))
        surface.blit(self.image, rect)

        dist = self.pos.distance_to(player_pos)
        if dist < 60:
            hint_x, hint_y = draw_x + 15, draw_y - 30

            shadow = font.render("E", True, (0, 0, 0))
            surface.blit(shadow, (hint_x + 2, hint_y + 2))

            hint_surf = font.render("E", True, (255, 255, 255))
            surface.blit(hint_surf, (hint_x, hint_y))


@dataclass
class PlayScene:
    assets: Assets
    state: GameState

    def __post_init__(self) -> None:
        self.font = self.assets.font("font/Press_Start_2P.ttf", 18)
        self.big_font = self.assets.font("font/Press_Start_2P.ttf", 28)
        self.map_frames = self._load_map_frames()
        self.map_frame_idx = 0
        self._map_anim_time = 0.0
        self.map_frame_interval = 0.2
        self.collision_mask = self._load_collision_mask()
        self.world_w, self.world_h = self.map_frames[0].get_width(), self.map_frames[0].get_height()

        self.crowns = self._load_crowns()
        spawn_pos = pg.Vector2(1500, 1300)

        self.player = Player(
            self.assets,
            self.state,
            pos=spawn_pos
        )
        self.enemy = Enemy(pos=pg.Vector2(80, 80))

        self.materials: list[Material] = []

        self.inventory = {"stick": 0, "stones": 0, "cable": 0}

        self.game_finished = False
        self.victory_timer = 5.0
        self.show_victory_msg = False

        self.basket_pos = pg.Vector2(849, 3668)

        # 2. Функція для завантаження та ЗБІЛЬШЕННЯ картинок
        def load_large_item(name, scale=2.5):  # scale=2.5 збільшить у 2.5 рази
            img = self.assets.image("items", name)
            new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
            return pg.transform.scale(img, new_size)

        stick_img = load_large_item("stick.png")
        stones_img = load_large_item("stones.png")
        cable_img = load_large_item("cable.png")

        def get_random_spawn() -> pg.Vector2:
            for _ in range(1000):
                x = random.randint(0, self.world_w)
                y = random.randint(0, self.world_h)
                pos = pg.Vector2(x, y)
                if self.is_walkable(pos):
                    return pos
            return pg.Vector2(self.world_w // 2, self.world_h // 2)

        # 3. Спавним точну кількість предметів
        for _ in range(5):  # 5 досок
            self.materials.append(Material(get_random_spawn(), stick_img, "stick"))
        for _ in range(4):  # 4 камінця
            self.materials.append(Material(get_random_spawn(), stones_img, "stones"))
        for _ in range(4):  # 4 троси
            self.materials.append(Material(get_random_spawn(), cable_img, "cable"))

        self.paused = False
        self.mouse_hold = False
        self.ws: WsClient | None = None
        self.incoming: Queue[dict[str, Any]] | None = None
        self.outgoing: Queue[dict[str, Any]] | None = None
        self.remote_players: dict[str, pg.Vector2] = {}
        if self.state.multiplayergame and self.state.join_server:
            self._start_ws()

    def _load_crowns(self) -> list[pg.Surface]:
        map_dir = self.assets.root / "map"
        frames = []
        if map_dir.exists():
            # Шукаємо всі файли з назвами crown1.png, crown2.png і т.д.
            candidates = sorted(map_dir.glob("crown*.png"),
                                key=lambda p: int(''.join(filter(str.isdigit, p.name)) or 0))
            for path in candidates:
                # convert_alpha() обов'язковий, щоб зберегти прозорий фон!
                img = pg.image.load(str(path)).convert_alpha()
                frames.append(img)
        return frames
    
    def _load_map_frames(self) -> list[pg.Surface]:
        map_dir = self.assets.root / "map"
        frames = []
        if map_dir.exists():
            # Завантажуємо всі 12 кадрів по черзі
            candidates = sorted(map_dir.glob("map*.png"), key=lambda p: int(''.join(filter(str.isdigit, p.name)) or 0))
            for path in candidates:
                img = pg.image.load(str(path)).convert()
                frames.append(img)

        if not frames:
            surf = pg.Surface((1920, 1080))
            surf.fill((24, 24, 30))
            frames.append(surf.convert())

        return frames

    def _load_collision_mask(self) -> pg.Surface | None:
        """Load collision mask where pure white means obstacle."""
        mask_dir = self.assets.root / "map_transparent"
        candidates = (
            mask_dir / "map_white_black.png",
            mask_dir / "map_transparent.png",
        )
        for path in candidates:
            if path.exists():
                return pg.image.load(str(path)).convert()
        return None

    def _start_ws(self) -> None:
        self.incoming = Queue()
        self.outgoing = Queue()
        self.ws = WsClient(url=self.state.server_url, incoming=self.incoming, outgoing=self.outgoing)
        self.ws.start()
        # Реєстрація/вхід у лобі (спрощено під протокол Godot-версії)
        if self.state.lobby_code:
            self.ws.send({"type": "join_lobby", "code": self.state.lobby_code, "player_id": self.state.player_name})
        self.ws.send({"type": "register_player", "player_id": self.state.player_name, "lobby_code": self.state.lobby_code})

    def handle_event(self, ev: pg.event.Event) -> None:
    
     if ev.type == pg.KEYDOWN and ev.key == pg.K_ESCAPE:
        self.paused = not self.paused
        if self.paused and getattr(self.player, "walk_sound", None) is not None:
            self.player.walk_sound.stop()
        return

    
     if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
        self.mouse_hold = True

     if ev.type == pg.MOUSEBUTTONUP and ev.button == 1:
        self.mouse_hold = False

    
     if self.paused and ev.type == pg.KEYDOWN:
        if ev.key == pg.K_c:
            self.paused = False

        if ev.key == pg.K_m:
            if getattr(self.player, "walk_sound", None) is not None:
                self.player.walk_sound.stop()
            from game.ui.menu_scene import _SceneChange, MenuScene
            raise _SceneChange(MenuScene(assets=self.assets, state=self.state))
        return

    # взаємодія
     if ev.type == pg.KEYDOWN and ev.key == pg.K_e:
        self._interact()

    
     if ev.type == pg.KEYDOWN and ev.key == pg.K_e:
        self._interact()

    def _interact(self) -> None:

        items_needed = {"stick": 5, "stones": 4, "cable": 4}
        all_collected = all(self.inventory[k] >= items_needed[k] for k in items_needed)

        if all_collected and self.player.pos.distance_to(self.basket_pos) < 80:
            self.show_victory_msg = True
            self.game_finished = True
            self.victory_timer = 5.0
            return

        pickup_dist = 60.0
        for mat in self.materials:
            if mat.visible and self.player.pos.distance_to(mat.pos) < pickup_dist:
                mat.visible = False
                self.inventory[mat.item_type] += 1
                break


    def is_walkable(self, pos: pg.Vector2) -> bool:
        x = int(pos.x)
        y = int(pos.y)
        if x < 0 or y < 0 or x >= self.world_w or y >= self.world_h:
            return False
        if self.collision_mask is None:
            return True
        mask_w, mask_h = self.collision_mask.get_size()
        if mask_w <= 0 or mask_h <= 0:
            return True
        mx = int(x * mask_w / self.world_w)
        my = int(y * mask_h / self.world_h)
        mx = max(0, min(mask_w - 1, mx))
        my = max(0, min(mask_h - 1, my))
        r, g, b = self.collision_mask.get_at((mx, my))[:3]
        return not (r == 255 and g == 255 and b == 255)

    def is_player_walkable(self, center: pg.Vector2) -> bool:
        """Колізія з мапою: усі непрозорі пікселі PNG хітбоксу (центр як у спрайта)."""
        cx, cy = int(center.x), int(center.y)
        for dx, dy in self.player.hitbox:
            if not self.is_walkable(pg.Vector2(cx + dx, cy + dy)):
                return False
        return True

    # fallback — центр
    #  return pg.Vector2(self.world_w // 2, self.world_h // 2)

    def find_spawn(self) -> pg.Vector2:
     for _ in range(2000):
        x = random.randint(0, self.world_w)
        y = random.randint(0, self.world_h)

        pos = pg.Vector2(x, y)

        if self.is_walkable(pos):
            return pos

    # fallback — центр
     return pg.Vector2(self.world_w // 2, self.world_h // 2)

    def update(self, dt: float) -> None:
     if self.paused:
        return
     self._map_anim_time += dt
     if self._map_anim_time >= self.map_frame_interval:
         self._map_anim_time = 0
         # Перемикаємо на наступний кадр, а після 12-го — на 1-й (індекс 0)
         self.map_frame_idx = (self.map_frame_idx + 1) % len(self.map_frames)
     if self.game_finished and self.victory_timer > 0:
         self.victory_timer -= dt
         if self.victory_timer <= 0:
             # Повернення в меню (код з твоєї паузи)
             from game.ui.menu_scene import _SceneChange, MenuScene
             raise _SceneChange(MenuScene(assets=self.assets, state=self.state))

    #керування мишкою
     if self.mouse_hold:
        mouse_x, mouse_y = pg.mouse.get_pos()
        cam = self._camera()

        target = pg.Vector2(mouse_x + cam.x, mouse_y + cam.y)
        direction = target - self.player.pos

        if direction.length_squared() > 4:
            self.player.direction = direction.normalize()
     else:
        self.player.handle_keys()

     move_step = self.player.direction * self.player.speed * dt

     # Колізія з урахуванням хітбоксу гравця (прямокутник 80×80 offsets)
     if self.is_player_walkable(pg.Vector2(self.player.pos.x + move_step.x, self.player.pos.y)):
         self.player.pos.x += move_step.x

     if self.is_player_walkable(pg.Vector2(self.player.pos.x, self.player.pos.y + move_step.y)):
         self.player.pos.y += move_step.y
     self.player.pos.x = max(0, min(self.world_w, self.player.pos.x))
     self.player.pos.y = max(0, min(self.world_h, self.player.pos.y))

     self.player.tick_animation(dt)

     self.enemy.update(dt, self.player.pos, self.world_w, self.world_h)
     self._net_tick()


    def _net_tick(self) -> None:
        if not self.ws or not self.incoming:
            return
        # Надіслати позицію
        self.ws.send(
            {
                "type": "update_position",
                "player_id": self.state.player_name,
                "position": {"x": float(self.player.pos.x), "y": float(self.player.pos.y), "r": [float(self.player.direction.x), float(self.player.direction.y)]},
                "lobby_code": self.state.lobby_code,
            }
        )
        # Прийняти оновлення (без блокування)
        while not self.incoming.empty():
            msg = self.incoming.get_nowait()
            if msg.get("type") == "position_updated":
                pid = str(msg.get("player_id", ""))
                if not pid or pid == self.state.player_name:
                    continue
                pos = msg.get("new_position") or msg.get("position") or {}
                try:
                    x = float(pos.get("x", 0))
                    y = float(pos.get("y", 0))
                except Exception:
                    continue
                self.remote_players[pid] = pg.Vector2(x, y)

    def render(self, screen: pg.Surface) -> None:
        screen.fill((0, 0, 0))
        cam = self._camera()

        game_surface = pg.Surface((960, 540))
        current_frame = self.map_frames[self.map_frame_idx]
        game_surface.blit(current_frame, (-int(cam.x), -int(cam.y)))

        for mat in self.materials:
            mat.draw(game_surface, cam, self.player.pos, self.font)

        items_needed = {"stick": 5, "stones": 4, "cable": 4}
        all_collected = all(self.inventory[k] >= items_needed[k] for k in items_needed)

        if all_collected and not self.show_victory_msg:

            if pg.time.get_ticks() % 1000 < 500:
                basket_draw_x = int(self.basket_pos.x - cam.x)
                basket_draw_y = int(self.basket_pos.y - cam.y)

                excl_shadow = self.big_font.render("!", True, (0, 0, 0))
                game_surface.blit(excl_shadow, (basket_draw_x + 2, basket_draw_y - 68))

                excl_mark = self.big_font.render("!", True, (255, 0, 0))
                game_surface.blit(excl_mark, (basket_draw_x, basket_draw_y - 70))

        self.player.draw(game_surface, cam)

        if hasattr(self, 'crowns') and self.crowns:
            crown_index = self.map_frame_idx % len(self.crowns)
            current_crown = self.crowns[crown_index]
            game_surface.blit(current_crown, (-int(cam.x), -int(cam.y)))

        self.enemy.draw(screen, cam)
        for pid, pos in self.remote_players.items():
            pg.draw.circle(screen, (80, 140, 240), (int(pos.x - cam.x), int(pos.y - cam.y)), 12)
            label = self.font.render(pid, True, WHITE)
            screen.blit(label, (int(pos.x - cam.x) + 14, int(pos.y - cam.y) - 10))

        scaled_game = pg.transform.scale(game_surface, (1920, 1080))
        screen.blit(scaled_game, (0, 0))
        hint = self.font.render("E — взаємодія, ESC — пауза", True, (255, 255, 255))
        screen.blit(hint, (18, 18))

        y_pos = 60
        for item, count in self.inventory.items():
            names = {"stick": "Дошки", "stones": "Камені", "cable": "Троси"}
            limit = {"stick": 5, "stones": 4, "cable": 4}

            txt = f"{names[item]}: {count}/{limit[item]}"
            img = self.font.render(txt, True, (255, 255, 255))
            screen.blit(img, (18, y_pos))
            y_pos += 30  # Зсуваємо наступний рядок нижче

        if self.paused:
            overlay = pg.Surface((1920, 1080), flags=pg.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            title = self.big_font.render("Пауза", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(1920 // 2, 1080 // 2)))

            cont = self.font.render("C — продовжити", True, (255, 255, 255))
            screen.blit(cont, cont.get_rect(center=(1920 // 2, 1080 // 2 + 50)))

            to_menu = self.font.render("M — в меню", True, (255, 255, 255))
            screen.blit(to_menu, to_menu.get_rect(center=(1920 // 2, 1080 // 2 + 100)))

        if all_collected and not self.show_victory_msg:
            if pg.time.get_ticks() % 1000 < 500:
                msg = self.font.render("БІЖИМО НА ПРИЧАЛ!", True, (0, 0, 0))
                screen.blit(msg, (50, 1080 // 2))

        if self.show_victory_msg:
            win_txt = self.big_font.render("ВИ ПРОЙШЛИ ГРУ!", True, (255, 255, 255))
            rect = win_txt.get_rect(center=(1920 // 2, 1080 // 2))
            pg.draw.rect(screen, (123, 151, 87, 150), rect.inflate(20, 20))
            screen.blit(win_txt, rect)

            hint_txt = self.font.render("Повернення в меню через кілька секунд...", True, (200, 200, 200))
            screen.blit(hint_txt, hint_txt.get_rect(center=(1920 // 2, 1080 // 2 + 60)))


    def _camera(self) -> pg.Vector2:
        x = self.player.pos.x - 480
        y = self.player.pos.y - 270
        return pg.Vector2(x, y)

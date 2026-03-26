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
    speed: float = 100.0

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

    def update(self, dt: float, world_w: int, world_h: int) -> None:
        self.handle_keys()
        self.pos += self.direction * self.speed * dt
        self.pos.x = max(0, min(world_w, self.pos.x))
        self.pos.y = max(0, min(world_h, self.pos.y))

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
        moving = self.direction.length_squared() > 0
        if self.walk_sound is not None:
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
        r = self.rect().move(-int(cam.x), -int(cam.y))
        screen.blit(img, r)


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
class Interactable:
    pos: pg.Vector2
    visible: bool = True

    def draw(self, screen: pg.Surface, cam: pg.Vector2) -> None:
        if not self.visible:
            return
        r = pg.Rect(0, 0, 18, 18)
        r.center = (int(self.pos.x - cam.x), int(self.pos.y - cam.y))
        pg.draw.rect(screen, (80, 200, 120), r, border_radius=4)


@dataclass
class PlayScene:
    assets: Assets
    state: GameState

    def __post_init__(self) -> None:
        self.font = self.assets.font("font/Press_Start_2P.ttf", 18)
        self.big_font = self.assets.font("font/Press_Start_2P.ttf", 28)
        self.map = self._load_map()
        self.map = self._load_map()
        self.world_w, self.world_h = self.map.get_width(), self.map.get_height()

        spawn_pos = self.find_spawn()

        self.player = Player(
    self.assets,
    self.state,
    pos=spawn_pos
)
        pos=pg.Vector2(300, 300)
        self.enemy = Enemy(pos=pg.Vector2(80, 80))
        self.interactables = [
            Interactable(pg.Vector2(self.world_w // 2 - 120, self.world_h // 2 - 60)),
            Interactable(pg.Vector2(self.world_w // 2 + 20, self.world_h // 2 + 40)),
            Interactable(pg.Vector2(self.world_w // 2 + 160, self.world_h // 2 + 80)),
        ]
        self.paused = False
        self.mouse_hold = False
        self.ws: WsClient | None = None
        self.incoming: Queue[dict[str, Any]] | None = None
        self.outgoing: Queue[dict[str, Any]] | None = None
        self.remote_players: dict[str, pg.Vector2] = {}
        if self.state.multiplayergame and self.state.join_server:
            self._start_ws()

    def _load_map(self) -> pg.Surface:
        # Беремо map1.png за замовчуванням (або будь-яку першу map*.png)
        map_dir = self.assets.root / "map"
        candidates = []
        if map_dir.exists():
            candidates = sorted(map_dir.glob("map*.png"))
        chosen = candidates[0] if candidates else None
        if chosen is None:
            # fallback — просто полотно розміру екрана
            surf = pg.Surface((BASE_WIDTH, BASE_HEIGHT))
            surf.fill((24, 24, 30))
            return surf.convert()
        img = pg.image.load(str(chosen)).convert()
        return img

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
        nearest: Interactable | None = None
        min_dist = 40.0
        for it in self.interactables:
            if not it.visible:
                continue
            d = self.player.pos.distance_to(it.pos)
            if d < min_dist:
                min_dist = d
                nearest = it
        if nearest is not None:
            nearest.visible = False

#Логіка колізії
    def is_walkable(self, pos: pg.Vector2) -> bool:
     x, y = int(pos.x), int(pos.y)

     if x < 0 or y < 0 or x >= self.world_w or y >= self.world_h:
        return False

     r, g, b = self.map.get_at((x, y))[:3]

    #Вода
     if b > r and b > g:
        return False

     if g > 150 and r < 100 and b < 100:
      return False

    #Печера
     if r < 50 and g < 50 and b < 50:
      return False 
    
    #Скеля
     if abs(r - g) < 20 and abs(g - b) < 20 and r > 100:
        return False

    #Вогнище
     if r > 200 and g > 100 and b < 100:
        return False

     return True

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

    #рух
     new_pos = self.player.pos + self.player.direction * self.player.speed * dt

     if self.is_walkable(new_pos):
      self.player.pos = new_pos
     self.player.pos.x = max(0, min(self.world_w, self.player.pos.x))
     self.player.pos.y = max(0, min(self.world_h, self.player.pos.y))

    
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
        cam = self._camera()
        screen.blit(self.map, (-int(cam.x), -int(cam.y)))
        for it in self.interactables:
            it.draw(screen, cam)
        self.player.draw(screen, cam)
        self.enemy.draw(screen, cam)
        for pid, pos in self.remote_players.items():
            pg.draw.circle(screen, (80, 140, 240), (int(pos.x - cam.x), int(pos.y - cam.y)), 12)
            label = self.font.render(pid, True, WHITE)
            screen.blit(label, (int(pos.x - cam.x) + 14, int(pos.y - cam.y) - 10))

        hint = self.font.render("E — взаємодія, ESC — пауза", True, WHITE)
        screen.blit(hint, (18, 18))

        if self.paused:
            overlay = pg.Surface((BASE_WIDTH, BASE_HEIGHT), flags=pg.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            title = self.big_font.render("Пауза", True, WHITE)
            screen.blit(title, title.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT // 2 - 60)))

            cont = self.font.render("C — продовжити", True, WHITE)
            screen.blit(cont, cont.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT // 2)))

            to_menu = self.font.render("M — в меню", True, WHITE)
            screen.blit(to_menu, to_menu.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT // 2 + 40)))

    def _camera(self) -> pg.Vector2:
        # Камера тримає гравця по центру, але не виходить за межі мапи
        x = self.player.pos.x - BASE_WIDTH / 2
        y = self.player.pos.y - BASE_HEIGHT / 2
        x = max(0, min(self.world_w - BASE_WIDTH, x))
        y = max(0, min(self.world_h - BASE_HEIGHT, y))
        return pg.Vector2(x, y)


from __future__ import annotations

from dataclasses import dataclass
import random
import pygame as pg

from game.assets import Assets
from game.constants import BASE_HEIGHT, BASE_WIDTH, WHITE
from game.state import GameState


@dataclass
class MenuScene:
    assets: Assets
    state: GameState

    def __post_init__(self) -> None:
        self.font = self._load_font()
        self.small_font = (
            self.assets.font("font/Press_Start_2P.ttf", 40)
            if (self.assets.root / "font/Press_Start_2P.ttf").exists()
            else pg.font.SysFont(None, 40)
        )

        self.screen: str = "main"
        self.selection: int = 0
        self.editing: str | None = None

        self._bg_frames: list[pg.Surface] = self._load_bg_frames()
        self._bg_timer: float = 0.0
        self.bg_anim_speed: float = 10.0

        # НОВЕ: Список для збереження клікабельних зон (хітбоксів) кнопок у поточному кадрі
        self._button_rects: list[pg.Rect] = []

        btn_path = self.assets.path("button", "MenuButton_v2.png")
        if btn_path.exists():
            raw = pg.image.load(str(btn_path)).convert_alpha()
            target_w = 440
            target_h = max(1, int(raw.get_height() * target_w / raw.get_width()))
            self._menu_btn_bg = pg.transform.smoothscale(raw, (target_w, target_h))
        else:
            self._menu_btn_bg = None
        self._menu_btn_font = (
            self.assets.font("font/Press_Start_2P.ttf", 24)
            if (self.assets.root / "font/Press_Start_2P.ttf").exists()
            else pg.font.SysFont(None, 24)
        )

    def _load_font(self) -> pg.font.Font:
        for rel in (
                "font/Press_Start_2P.ttf",
                "font/Press_Start_2P.ttf",
        ):
            try:
                return self.assets.font(rel, 32)
            except FileNotFoundError:
                continue
        return pg.font.SysFont(None, 32)

    def _load_bg_frames(self) -> list[pg.Surface]:
        frames = []
        menu_dir = self.assets.root / "menu"
        if not menu_dir.exists():
            return frames

        for i in range(1, 13):
            path = menu_dir / f"menu{i}.jpg"
            if path.exists():
                try:
                    img = pg.image.load(str(path)).convert()
                    img = pg.transform.smoothscale(img, (BASE_WIDTH, BASE_HEIGHT))
                    frames.append(img)
                except Exception:
                    continue
        return frames

    def handle_event(self, ev: pg.event.Event) -> None:
        # --- НОВЕ: Обробка кліку мишкою ---
        if ev.type == pg.MOUSEBUTTONDOWN and ev.button == 1:
            # Перевіряємо, чи клікнули по якійсь кнопці
            for index, rect in enumerate(self._button_rects):
                if rect.collidepoint(ev.pos):
                    self.selection = index
                    self._activate_selected()
                    return  # Виходимо після обробки кліку
        # -----------------------------------

        if ev.type != pg.KEYDOWN:
            return

        if ev.key == pg.K_ESCAPE:
            if self.screen == "main":
                raise SystemExit
            self.screen = "main"
            self.selection = 0
            self.editing = None
            return

        if self.editing is not None:
            if ev.key == pg.K_BACKSPACE:
                if self.editing == "player":
                    self.state.player_name = self.state.player_name[:-1]
                elif self.editing == "lobby":
                    self.state.lobby_code = self.state.lobby_code[:-1]
                return
            if ev.key in (pg.K_RETURN, pg.K_KP_ENTER):
                self.editing = None
                return
            if ev.unicode:
                ch = ev.unicode
                if self.editing == "player" and len(self.state.player_name) < 16 and ch.isprintable():
                    self.state.player_name += ch
                    return
                if self.editing == "lobby":
                    ch = ch.upper()
                    if ch.isalnum() and len(self.state.lobby_code) < 12:
                        self.state.lobby_code += ch
                    return

        if ev.key in (pg.K_UP, pg.K_w):
            self.selection = (self.selection - 1) % self._option_count()
            return
        if ev.key in (pg.K_DOWN, pg.K_s):
            self.selection = (self.selection + 1) % self._option_count()
            return

        if ev.key in (pg.K_RETURN, pg.K_KP_ENTER):
            self._activate_selected()
            return

        if self.screen == "skin":
            if ev.key == pg.K_m:
                self.state.skin_name = "male"
            if ev.key == pg.K_f:
                self.state.skin_name = "female"
            return

        if self.screen == "mp":
            if ev.key == pg.K_p:
                self.editing = "player"
            if ev.key == pg.K_l:
                self.editing = "lobby"

    def update(self, dt: float) -> None:
        if self._bg_frames:
            self._bg_timer += dt * self.bg_anim_speed

    def render(self, screen: pg.Surface) -> None:
        # Очищаємо старі хітбокси кнопок перед малюванням нового кадру
        self._button_rects.clear()

        # Отримуємо позицію мишки
        mouse_pos = pg.mouse.get_pos()

        if self._bg_frames:
            idx = int(self._bg_timer) % len(self._bg_frames)
            screen.blit(self._bg_frames[idx], (0, 0))
            overlay = pg.Surface((BASE_WIDTH, BASE_HEIGHT), flags=pg.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill((18, 18, 24))
        shadow = self._text("Pixels and Tears", 80, (20, 20, 30))
        screen.blit(shadow, shadow.get_rect(center=(BASE_WIDTH // 2 + 4, 120 + 4)))


        title = self._text("Pixels and Tears", 80, WHITE)
        screen.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 120)))

        # Передаємо mouse_pos у методи рендеру
        if self.screen == "main":
            self._render_main(screen, mouse_pos)
        elif self.screen == "skin":
            self._render_skin(screen, mouse_pos)
        elif self.screen == "mp":
            self._render_mp(screen, mouse_pos)

        esc = self._text("Esc — вихід/назад", 22)
        screen.blit(esc, esc.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT - 60)))

    def _text(self, s: str, size: int, color: tuple = WHITE) -> pg.Surface:
        font = (
            self.assets.font("font/Press_Start_2P.ttf", size)
            if (self.assets.root / "font/Press_Start_2P.ttf").exists()
            else pg.font.SysFont(None, size)
        )
        return font.render(s, True, color)

    def _render_options(self, screen: pg.Surface, options: list[str], y0: int, mouse_pos: tuple[int, int]) -> None:
        if self._menu_btn_bg is None:
            self._render_options_text_only(screen, options, y0, mouse_pos)
            return

        bw, bh = self._menu_btn_bg.get_size()
        row = bh + 14

        for i, label in enumerate(options):
            cx, cy = BASE_WIDTH // 2, y0 + i * row
            base_rect = self._menu_btn_bg.get_rect(center=(cx, cy))
            is_hovered = base_rect.collidepoint(mouse_pos)
            if is_hovered:
                self.selection = i

            selected = i == self.selection
            screen.blit(self._menu_btn_bg, base_rect)

            color = (255, 255, 240) if selected else (170, 170, 175)
            surf = self._menu_btn_font.render(label, True, color)
            max_tw = bw - 36
            if surf.get_width() > max_tw:
                scale = max_tw / surf.get_width()
                surf = pg.transform.smoothscale(
                    surf, (max(1, int(surf.get_width() * scale)), max(1, int(surf.get_height() * scale)))
                )
            text_rect = surf.get_rect(center=(cx, cy))
            screen.blit(surf, text_rect)
            self._button_rects.append(base_rect)

    def _render_options_text_only(self, screen: pg.Surface, options: list[str], y0: int, mouse_pos: tuple[int, int]) -> None:
        for i, label in enumerate(options):
            base_surf = self.small_font.render(label, True, (255, 255, 255))
            base_rect = base_surf.get_rect(center=(BASE_WIDTH // 2, y0 + i * 70)).inflate(40, 20)
            is_hovered = base_rect.collidepoint(mouse_pos)
            if is_hovered:
                self.selection = i
            selected = i == self.selection
            text = ("> " if selected else "  ") + label
            color = (255, 255, 255) if selected else (150, 150, 150)
            surf = self.small_font.render(text, True, color)
            rect = surf.get_rect(center=(BASE_WIDTH // 2, y0 + i * 70))
            screen.blit(surf, rect)
            self._button_rects.append(base_rect)

    def _option_count(self) -> int:
        if self.screen == "main":
            return 4
        if self.screen == "skin":
            return 3
        if self.screen == "mp":
            return 4
        return 0

    def _activate_selected(self) -> None:
        if self.screen == "main":
            if self.selection == 0:
                self._start_local()
            elif self.selection == 1:
                self.screen = "mp"
                self.selection = 0
            elif self.selection == 2:
                self.screen = "skin"
                self.selection = 0
            elif self.selection == 3:
                raise SystemExit
            return

        if self.screen == "skin":
            if self.selection == 0:
                self.state.skin_name = "male"
            elif self.selection == 1:
                self.state.skin_name = "female"
            elif self.selection == 2:
                self.screen = "main"
                self.selection = 0
            return

        if self.screen == "mp":
            if self.selection == 0:
                self.editing = "player"
            elif self.selection == 1:
                self._start_host()
            elif self.selection == 2:
                self.editing = "lobby"
            elif self.selection == 3:
                self._start_join()
            return

    def _render_main(self, screen: pg.Surface, mouse_pos: tuple[int, int]) -> None:
        self._render_options(
            screen,
            ["Почати локальну гру", "Грати по мережі", "Змінити вигляд персонажа", "Вийти з гри"],
            290,
            mouse_pos
        )

    def _render_skin(self, screen: pg.Surface, mouse_pos: tuple[int, int]) -> None:
        skin = self._text(f"Поточний скін: {self.state.skin_name}", 28)
        screen.blit(skin, skin.get_rect(center=(BASE_WIDTH // 2, 240)))
        self._render_options(screen, ["Чоловічий скін (M)", "Жіночий скін (F)", "Назад"], 360, mouse_pos)

    def _render_mp(self, screen: pg.Surface, mouse_pos: tuple[int, int]) -> None:
        info = self._text("Мережева гра", 28)
        screen.blit(info, info.get_rect(center=(BASE_WIDTH // 2, 230)))

        # Поля вводу (вони поки не клікабельні, активуються через меню або гарячі клавіші)
        pn = self.small_font.render(
            f"Ім'я: {self.state.player_name or '—'}" + ("  [ввід]" if self.editing == "player" else ""),
            True,
            WHITE,
        )
        screen.blit(pn, pn.get_rect(center=(BASE_WIDTH // 2, 280)))

        lc = self.small_font.render(
            f"ID/Код сервера: {self.state.lobby_code or '—'}" + ("  [ввід]" if self.editing == "lobby" else ""),
            True,
            WHITE,
        )
        screen.blit(lc, lc.get_rect(center=(BASE_WIDTH // 2, 315)))

        self._render_options(screen,
                             ["Ввести ім'я (P)", "Створити сервер", "Ввести ID сервера (L)", "Приєднатися до сервера"],
                             440, mouse_pos)

    def _start_local(self) -> None:
        self.state.multiplayergame = False
        self.state.host_server = False
        self.state.join_server = False
        from game.ui.play_scene import PlayScene

        raise _SceneChange(PlayScene(assets=self.assets, state=self.state))

    def _start_host(self) -> None:
        self.state.multiplayergame = True
        self.state.host_server = True
        self.state.join_server = True
        if not self.state.lobby_code:
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            self.state.lobby_code = "".join(random.choice(chars) for _ in range(6))
        from game.ui.play_scene import PlayScene

        raise _SceneChange(PlayScene(assets=self.assets, state=self.state))

    def _start_join(self) -> None:
        self.state.multiplayergame = True
        self.state.host_server = False
        self.state.join_server = True
        if not self.state.lobby_code:
            return
        from game.ui.play_scene import PlayScene

        raise _SceneChange(PlayScene(assets=self.assets, state=self.state))


class _SceneChange(RuntimeError):
    def __init__(self, next_scene):
        super().__init__("scene change")
        self.next_scene = next_scene
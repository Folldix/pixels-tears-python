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
            self.assets.font("font/HarreeghPoppedCyrillic.ttf", 22)
            if (self.assets.root / "font/HarreeghPoppedCyrillic.ttf").exists()
            else pg.font.SysFont(None, 22)
        )

        # Екрани згідно діаграми: головне меню / вибір скіна / мережева гра
        self.screen: str = "main"  # main | skin | mp
        self.selection: int = 0
        self.editing: str | None = None  # player | lobby

        self._bg = self._load_random_bg()

    def _load_font(self) -> pg.font.Font:
        for rel in (
            "font/alagard-12px-unicode.ttf",
            "font/HarreeghPoppedCyrillic.ttf",
        ):
            try:
                return self.assets.font(rel, 32)
            except FileNotFoundError:
                continue
        return pg.font.SysFont(None, 32)

    def _load_random_bg(self) -> pg.Surface | None:
        menu_dir = self.assets.root / "menu"
        if not menu_dir.exists():
            return None
        choices = sorted(menu_dir.glob("menu*.jpg"))
        if not choices:
            return None
        try:
            img = pg.image.load(str(random.choice(choices))).convert()
        except Exception:
            return None
        return pg.transform.smoothscale(img, (BASE_WIDTH, BASE_HEIGHT))

    def handle_event(self, ev: pg.event.Event) -> None:
        if ev.type != pg.KEYDOWN:
            return

        if ev.key == pg.K_ESCAPE:
            if self.screen == "main":
                raise SystemExit
            self.screen = "main"
            self.selection = 0
            self.editing = None
            return

        # Редагування текстових полів у мережевому меню
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

        # Гарячі клавіші на окремих екранах
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
        pass

    def render(self, screen: pg.Surface) -> None:
        if self._bg is not None:
            screen.blit(self._bg, (0, 0))
            overlay = pg.Surface((BASE_WIDTH, BASE_HEIGHT), flags=pg.SRCALPHA)
            overlay.fill((0, 0, 0, 130))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill((18, 18, 24))

        title = self._text("Pixels and Tears", 56)
        screen.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 120)))

        if self.screen == "main":
            self._render_main(screen)
        elif self.screen == "skin":
            self._render_skin(screen)
        elif self.screen == "mp":
            self._render_mp(screen)

        esc = self._text("Esc — вихід/назад", 22)
        screen.blit(esc, esc.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT - 60)))

    def _text(self, s: str, size: int) -> pg.Surface:
        font = (
            self.assets.font("font/HarreeghPoppedCyrillic.ttf", size)
            if (self.assets.root / "font/HarreeghPoppedCyrillic.ttf").exists()
            else pg.font.SysFont(None, size)
        )
        return font.render(s, True, WHITE)

    def _render_options(self, screen: pg.Surface, options: list[str], y0: int) -> None:
        for i, label in enumerate(options):
            selected = i == self.selection
            text = ("> " if selected else "  ") + label
            surf = self.small_font.render(text, True, (255, 255, 255) if selected else (220, 220, 220))
            screen.blit(surf, surf.get_rect(center=(BASE_WIDTH // 2, y0 + i * 44)))

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

    def _render_main(self, screen: pg.Surface) -> None:
        self._render_options(
            screen,
            ["Почати локальну гру", "Грати по мережі", "Змінити вигляд персонажа", "Вийти з гри"],
            290,
        )

    def _render_skin(self, screen: pg.Surface) -> None:
        skin = self._text(f"Поточний скін: {self.state.skin_name}", 28)
        screen.blit(skin, skin.get_rect(center=(BASE_WIDTH // 2, 240)))
        self._render_options(screen, ["Чоловічий скін (M)", "Жіночий скін (F)", "Назад"], 320)

    def _render_mp(self, screen: pg.Surface) -> None:
        info = self._text("Мережева гра", 28)
        screen.blit(info, info.get_rect(center=(BASE_WIDTH // 2, 230)))

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

        self._render_options(screen, ["Ввести ім'я (P)", "Створити сервер", "Ввести ID сервера (L)", "Приєднатися до сервера"], 385)

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


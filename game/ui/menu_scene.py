from __future__ import annotations

from dataclasses import dataclass
import random

import pygame as pg

from game.assets import Assets
from game.constants import BASE_HEIGHT, BASE_WIDTH, BLACK, WHITE
from game.state import GameState


@dataclass
class MenuScene:
    assets: Assets
    state: GameState

    def __post_init__(self) -> None:
        self.font = self._load_font()
        self.small_font = self.assets.font("font/HarreeghPoppedCyrillic.ttf", 22) if (self.assets.root / "font/HarreeghPoppedCyrillic.ttf").exists() else pg.font.SysFont(None, 22)
        self.editing: str | None = None

    def _load_font(self) -> pg.font.Font:
        # У Godot є 2 шрифти; підхоплюємо той, що реально є в assets.
        for rel in (
            "font/alagard-12px-unicode.ttf",
            "font/HarreeghPoppedCyrillic.ttf",
        ):
            try:
                return self.assets.font(rel, 32)
            except FileNotFoundError:
                continue
        return pg.font.SysFont(None, 32)

    def handle_event(self, ev: pg.event.Event) -> None:
        if ev.type == pg.KEYDOWN:
            if ev.key == pg.K_ESCAPE:
                raise SystemExit

            if ev.key == pg.K_TAB:
                self.editing = "player" if self.editing is None else ("lobby" if self.editing == "player" else None)
                return

            if self.editing is not None:
                if ev.key == pg.K_BACKSPACE:
                    if self.editing == "player":
                        self.state.player_name = self.state.player_name[:-1]
                    elif self.editing == "lobby":
                        self.state.lobby_code = self.state.lobby_code[:-1]
                    return
                if ev.key == pg.K_RETURN:
                    self.editing = None
                    return
                if ev.unicode:
                    ch = ev.unicode
                    if self.editing == "player" and len(self.state.player_name) < 16 and ch.isprintable():
                        self.state.player_name += ch
                    elif self.editing == "lobby":
                        ch = ch.upper()
                        if ch.isalnum() and len(self.state.lobby_code) < 12:
                            self.state.lobby_code += ch
                    return

            if ev.key == pg.K_m:
                self.state.skin_name = "male"
            if ev.key == pg.K_f:
                self.state.skin_name = "female"

            if ev.key == pg.K_p:
                self.editing = "player"
            if ev.key == pg.K_l:
                self.editing = "lobby"

            if ev.key in (pg.K_1,):
                self._start_local()
            if ev.key in (pg.K_2,):
                self._start_host()
            if ev.key in (pg.K_3,):
                self._start_join()

    def update(self, dt: float) -> None:
        pass

    def render(self, screen: pg.Surface) -> None:
        screen.fill((18, 18, 24))

        title = self._text("Pixels and Tears", 56)
        screen.blit(title, title.get_rect(center=(BASE_WIDTH // 2, 120)))

        skin = self._text(f"Скін: {self.state.skin_name} (M/F)", 28)
        screen.blit(skin, skin.get_rect(center=(BASE_WIDTH // 2, 260)))

        pn = self.small_font.render(f"Player name: {self.state.player_name}  (P щоб редагувати)", True, WHITE)
        screen.blit(pn, pn.get_rect(center=(BASE_WIDTH // 2, 330)))

        lc = self.small_font.render(f"Lobby code: {self.state.lobby_code or '—'}  (L щоб редагувати)", True, WHITE)
        screen.blit(lc, lc.get_rect(center=(BASE_WIDTH // 2, 365)))

        hint = self.small_font.render("1 — локально | 2 — host | 3 — join", True, WHITE)
        screen.blit(hint, hint.get_rect(center=(BASE_WIDTH // 2, 420)))

        tip = self.small_font.render("Tab — перемикати поле вводу, Enter — завершити ввід", True, WHITE)
        screen.blit(tip, tip.get_rect(center=(BASE_WIDTH // 2, 455)))

        esc = self._text("Esc — вихід", 22)
        screen.blit(esc, esc.get_rect(center=(BASE_WIDTH // 2, BASE_HEIGHT - 60)))

    def _text(self, s: str, size: int) -> pg.Surface:
        font = self.assets.font("font/HarreeghPoppedCyrillic.ttf", size) if (self.assets.root / "font/HarreeghPoppedCyrillic.ttf").exists() else pg.font.SysFont(None, size)
        return font.render(s, True, WHITE)

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


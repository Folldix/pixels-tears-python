from __future__ import annotations

from pathlib import Path

import pygame as pg

from game.assets import Assets
from game.constants import BASE_HEIGHT, BASE_WIDTH, FPS, WINDOW_TITLE
from game.scenes import SceneStack
from game.state import GameState
from game.ui.menu_scene import MenuScene
from game.ui.menu_scene import _SceneChange


def run() -> None:
    pg.init()
    pg.freetype.init()
    pg.mixer.init()

    screen = pg.display.set_mode((BASE_WIDTH, BASE_HEIGHT))
    pg.display.set_caption(WINDOW_TITLE)
    clock = pg.time.Clock()

    root = Path(__file__).resolve().parent.parent
    assets = Assets(root / "assets")
    state = GameState()

    scenes = SceneStack([MenuScene(assets=assets, state=state)])

    running = True
    while running:
        try:
            dt = clock.tick(FPS) / 1000.0

            for ev in pg.event.get():
                if ev.type == pg.QUIT:
                    running = False
                    continue
                scenes.top.handle_event(ev)

            scenes.top.update(dt)
            scenes.top.render(screen)
            pg.display.flip()
        except _SceneChange as ch:
            scenes.replace(ch.next_scene)
        except SystemExit:
            running = False

    pg.quit()


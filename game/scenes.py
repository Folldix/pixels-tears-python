from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pygame as pg


class Scene(Protocol):
    def handle_event(self, ev: pg.event.Event) -> None: ...
    def update(self, dt: float) -> None: ...
    def render(self, screen: pg.Surface) -> None: ...


@dataclass
class SceneStack:
    stack: list[Scene]

    def push(self, scene: Scene) -> None:
        self.stack.append(scene)

    def pop(self) -> None:
        if self.stack:
            self.stack.pop()

    def replace(self, scene: Scene) -> None:
        self.stack = [scene]

    @property
    def top(self) -> Scene:
        return self.stack[-1]


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame as pg


@dataclass(frozen=True)
class Assets:
    root: Path

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def image(self, *parts: str) -> pg.Surface:
        p = self.path(*parts)
        surf = pg.image.load(str(p))
        return surf.convert_alpha() if surf.get_alpha() is not None else surf.convert()

    def font(self, rel_path: str, size: int) -> pg.font.Font:
        p = self.path(rel_path)
        return pg.font.Font(str(p), size)


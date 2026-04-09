# -*- coding: utf-8 -*-
"""
conftest.py — спільні фікстури для всіх тестів.
Ініціалізує pygame один раз на всю сесію (без вікна та звуку).
"""
import pytest
import pygame


# ──────────────────────────────────────────────
# Ініціалізація pygame (без дисплею та аудіо)
# ──────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def pygame_init():
    """Ініціалізує pygame один раз на всю тест-сесію (headless)."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


# ──────────────────────────────────────────────
# GameState
# ──────────────────────────────────────────────
@pytest.fixture
def default_state():
    """Повертає GameState зі значеннями за замовчуванням."""
    from game.state import GameState
    return GameState()


@pytest.fixture
def mp_state():
    """GameState налаштований для мережевої гри."""
    from game.state import GameState
    return GameState(
        player_name="TestPlayer",
        lobby_code="ABC123",
        multiplayergame=True,
        host_server=False,
        join_server=True,
    )


# ──────────────────────────────────────────────
# Player (без Assets — мокуємо)
# ──────────────────────────────────────────────
@pytest.fixture
def mock_assets(tmp_path):
    """Мінімальний Assets-мок: повертає порожні поверхні та шрифти."""
    from unittest.mock import MagicMock, patch
    import pygame

    assets = MagicMock()
    assets.root = tmp_path

    dummy_surf = pygame.Surface((80, 80))
    assets.image.return_value = dummy_surf
    assets.font.return_value = pygame.font.SysFont(None, 24)
    assets.path.return_value = tmp_path / "nonexistent.png"

    return assets


@pytest.fixture
def player(mock_assets, default_state):
    """Повертає Player з мок-ресурсами (без реальних файлів)."""
    from unittest.mock import patch, MagicMock
    import pygame

    dummy_surf = pygame.Surface((80, 80))

    with patch("game.ui.play_scene._load_dir_frames", return_value=[dummy_surf] * 4), \
         patch.object(type(mock_assets.path.return_value), "exists", return_value=False):
        from game.ui.play_scene import Player
        p = Player(
            assets=mock_assets,
            state=default_state,
            pos=pygame.Vector2(100, 200),
        )
    return p


@pytest.fixture
def enemy():
    """Повертає Enemy на початковій позиції."""
    from game.ui.play_scene import Enemy
    import pygame
    return Enemy(pos=pygame.Vector2(50, 50))


# ──────────────────────────────────────────────
# SceneStack
# ──────────────────────────────────────────────
@pytest.fixture
def scene_stack():
    """Порожній SceneStack."""
    from game.scenes import SceneStack
    return SceneStack(stack=[])

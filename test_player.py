# -*- coding: utf-8 -*-
"""
test_player.py — тести для класу Player.
Охоплює: фікстури, параметризацію, мокування pygame.key / mixer.
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch, PropertyMock

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════
# Початковий стан
# ═══════════════════════════════════════════════
class TestPlayerInit:

    def test_initial_position(self, player):
        assert player.pos.x == pytest.approx(100.0)
        assert player.pos.y == pytest.approx(200.0)

    def test_initial_speed(self, player):
        assert player.speed == 150.0

    def test_initial_direction_zero(self, player):
        assert player.direction.length_squared() == 0

    def test_initial_facing_down(self, player):
        assert player.facing == "down"

    def test_initial_anim_idx(self, player):
        assert player.anim_idx == 0

    def test_hitbox_not_empty(self, player):
        """Хітбокс має містити пікселі з прямокутника x:[30..49], y:[45..60]."""
        assert len(player.hitbox) > 0

    def test_hitbox_pixel_count(self, player):
        """Очікуємо 20*16 = 320 пікселів у хітбоксі."""
        assert len(player.hitbox) == 320


# ═══════════════════════════════════════════════
# handle_keys — мокуємо pygame.key.get_pressed
# ═══════════════════════════════════════════════
class TestPlayerHandleKeys:

    def _make_keys(self, *pressed_keys):
        """Повертає масив з натиснутими клавішами."""
        keys = [False] * 400
        for k in pressed_keys:
            keys[k] = True
        return keys

    @pytest.mark.parametrize("key,expected_facing,dx,dy", [
        (pygame.K_d, "right",  1,  0),
        (pygame.K_a, "left",  -1,  0),
        (pygame.K_s, "down",   0,  1),
        (pygame.K_w, "up",     0, -1),
    ])
    def test_single_direction_keys(self, player, key, expected_facing, dx, dy):
        with patch("pygame.key.get_pressed", return_value=self._make_keys(key)):
            player.handle_keys()
        assert player.facing == expected_facing
        if dx != 0:
            assert (player.direction.x > 0) == (dx > 0)
        if dy != 0:
            assert (player.direction.y > 0) == (dy > 0)

    def test_no_keys_direction_zero(self, player):
        with patch("pygame.key.get_pressed", return_value=self._make_keys()):
            player.handle_keys()
        assert player.direction.length_squared() == 0

    def test_diagonal_direction_normalized(self, player):
        with patch("pygame.key.get_pressed",
                   return_value=self._make_keys(pygame.K_d, pygame.K_s)):
            player.handle_keys()
        length = player.direction.length()
        assert length == pytest.approx(1.0, abs=1e-5)

    def test_touch_direction_up(self, player):
        with patch("pygame.key.get_pressed", return_value=self._make_keys()):
            player.handle_keys(touch_dirs={"up"})
        assert player.direction.y < 0

    @pytest.mark.parametrize("touch_dirs,expected_facing", [
        ({"right"}, "right"),
        ({"left"},  "left"),
        ({"up"},    "up"),
        ({"down"},  "down"),
    ])
    def test_touch_facing(self, player, touch_dirs, expected_facing):
        with patch("pygame.key.get_pressed", return_value=self._make_keys()):
            player.handle_keys(touch_dirs=touch_dirs)
        assert player.facing == expected_facing

    def test_arrow_keys_work(self, player):
        with patch("pygame.key.get_pressed",
                   return_value=self._make_keys(pygame.K_RIGHT)):
            player.handle_keys()
        assert player.facing == "right"


# ═══════════════════════════════════════════════
# sync_facing_from_direction
# ═══════════════════════════════════════════════
class TestSyncFacing:

    @pytest.mark.parametrize("dx,dy,expected", [
        ( 1,  0, "right"),
        (-1,  0, "left"),
        ( 0,  1, "down"),
        ( 0, -1, "up"),
        ( 2,  1, "right"),   # горизонталь домінує
        (-2,  1, "left"),
        ( 1,  2, "down"),    # вертикаль домінує
        ( 1, -2, "up"),
    ])
    def test_facing_from_direction(self, player, dx, dy, expected):
        player.direction = pygame.Vector2(dx, dy)
        player.sync_facing_from_direction()
        assert player.facing == expected

    def test_zero_direction_does_not_change_facing(self, player):
        player.facing = "up"
        player.direction = pygame.Vector2(0, 0)
        player.sync_facing_from_direction()
        assert player.facing == "up"


# ═══════════════════════════════════════════════
# tick_animation
# ═══════════════════════════════════════════════
class TestTickAnimation:

    def test_animation_advances_when_moving(self, player):
        player.direction = pygame.Vector2(1, 0)
        player.anim_idx = 0
        # Крок 0.12 с — кадр має змінитись
        player.tick_animation(0.13)
        assert player.anim_idx == 1

    def test_animation_wraps_around(self, player):
        player.direction = pygame.Vector2(1, 0)
        player.anim_idx = 3
        player.anim_time = 0.11
        player.tick_animation(0.13)
        assert player.anim_idx == 0  # wrap 3 → 0

    def test_animation_resets_when_stopped(self, player):
        player.direction = pygame.Vector2(0, 0)
        player.anim_idx = 2
        player.anim_time = 0.08
        player.tick_animation(0.05)
        assert player.anim_idx == 0
        assert player.anim_time == 0.0

    def test_walk_sound_starts_on_move(self, player):
        mock_sound = MagicMock()
        player.walk_sound = mock_sound
        player._walk_playing = False
        player.direction = pygame.Vector2(1, 0)
        player.tick_animation(0.05)
        mock_sound.play.assert_called_once_with(loops=-1)

    def test_walk_sound_stops_on_idle(self, player):
        mock_sound = MagicMock()
        player.walk_sound = mock_sound
        player._walk_playing = True
        player.direction = pygame.Vector2(0, 0)
        player.tick_animation(0.05)
        mock_sound.stop.assert_called_once()

    def test_no_error_without_walk_sound(self, player):
        player.walk_sound = None
        player.direction = pygame.Vector2(1, 0)
        player.tick_animation(0.05)  # не має кидати виняток


# ═══════════════════════════════════════════════
# image() та rect()
# ═══════════════════════════════════════════════
class TestPlayerImage:

    def test_idle_image_when_not_moving(self, player):
        player.direction = pygame.Vector2(0, 0)
        img = player.image()
        assert img is player.idle

    def test_walking_image_differs_from_idle(self, player):
        player.direction = pygame.Vector2(1, 0)
        player.facing = "right"
        img = player.image()
        # Коли рухається — має повертати кадр з frames, не idle
        assert img is player.frames["right"][player.anim_idx]

    def test_rect_centered_on_pos(self, player):
        player.direction = pygame.Vector2(0, 0)
        r = player.rect()
        assert r.centerx == pytest.approx(int(player.pos.x), abs=1)
        assert r.centery == pytest.approx(int(player.pos.y), abs=1)

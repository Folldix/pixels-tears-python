# -*- coding: utf-8 -*-
"""
test_enemy.py — тести для класу Enemy.
Охоплює: фікстури, параметризацію, мокування random.
"""
import pytest
import pygame
from unittest.mock import patch

pytestmark = pytest.mark.unit

WORLD_W, WORLD_H = 2000, 2000


# Початковий стан
class TestEnemyInit:

     # enemy ← Fixture (fixture створюється в conftest.py автоматично через @pytest.fixture)
    def test_initial_position(self, enemy):
        assert enemy.pos.x == pytest.approx(50.0) # assert ← перевірка умови (pytest.approx ← approx, використовується для перевірки float)
        assert enemy.pos.y == pytest.approx(50.0)

    def test_initial_invisible(self, enemy):
        assert enemy.visible is False

    def test_default_speed(self, enemy):
        assert enemy.speed == 100.0

    def test_default_active_after(self, enemy):
        assert enemy.active_after_s == 300.0

    def test_timer_starts_at_zero(self, enemy):
        assert enemy._timer == pytest.approx(0.0)


# Таймер активації
class TestEnemyActivation:

    def test_not_visible_before_threshold(self, enemy):
        enemy.update(100.0, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        assert enemy.visible is False

    def test_becomes_visible_after_threshold(self, enemy):
        enemy.update(300.0, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        assert enemy.visible is True

    def test_timer_accumulates(self, enemy):
        enemy.update(100.0, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        enemy.update(100.0, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        assert enemy._timer == pytest.approx(200.0)
         #Parametrize (один тест запускається кілька разів з різними значеннями)
    @pytest.mark.parametrize("dt,visible", [
        (299.9, False),
        (300.0, True),
        (500.0, True),
    ])
    def test_activation_boundary(self, dt, visible):
        from game.ui.play_scene import Enemy
        e = Enemy(pos=pygame.Vector2(0, 0))
        e.update(dt, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        assert e.visible == visible


# Переміщення до гравця
class TestEnemyMovement:

    def _make_active_enemy(self, x=100.0, y=100.0):
        from game.ui.play_scene import Enemy
        e = Enemy(pos=pygame.Vector2(x, y), speed=100.0, active_after_s=0.0)
        return e

    def test_moves_toward_player(self):
        """Ворог має наближатися до гравця."""
        e = self._make_active_enemy(0.0, 0.0)
        player_pos = pygame.Vector2(500, 0)

        # Патчимо random щоб прибрати jitter
        with patch("random.random", return_value=0.5):
             #Patch( тимчасово замінюємо random.random())

            # Mock (мокування), тобто тут random.random() стає "фейковим"
            e.update(1.0, player_pos, WORLD_W, WORLD_H)

        assert e.pos.x > 0.0  # рухається праворуч до гравця

    def test_does_not_move_when_invisible(self):
        from game.ui.play_scene import Enemy
        e = Enemy(pos=pygame.Vector2(0, 0), speed=100.0, active_after_s=999.0)
        e.update(0.1, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
        assert e.pos.x == pytest.approx(0.0)
        assert e.pos.y == pytest.approx(0.0)

    def test_clamped_to_world_bounds(self):
        """Позиція не виходить за межі світу."""
        e = self._make_active_enemy(WORLD_W - 1, WORLD_H - 1)
        with patch("random.random", return_value=1.0):
            e.update(10.0, pygame.Vector2(WORLD_W, WORLD_H), WORLD_W, WORLD_H)
        assert e.pos.x <= WORLD_W
        assert e.pos.y <= WORLD_H

    def test_clamped_to_zero(self):
        e = self._make_active_enemy(1.0, 1.0)
        with patch("random.random", return_value=0.0):
            e.update(10.0, pygame.Vector2(0, 0), WORLD_W, WORLD_H)
        assert e.pos.x >= 0
        assert e.pos.y >= 0

    @pytest.mark.parametrize("speed", [50.0, 100.0, 200.0])
    def test_faster_enemy_moves_more(self, speed):
        """Вищий speed = більше переміщення за 1 секунду."""
        from game.ui.play_scene import Enemy
        e = Enemy(pos=pygame.Vector2(0, 0), speed=speed, active_after_s=0.0)
        player_pos = pygame.Vector2(1000, 0)
        with patch("random.random", return_value=0.5):
            e.update(1.0, player_pos, WORLD_W, WORLD_H)
        assert e.pos.x == pytest.approx(speed, abs=2.0)


# custom active_after_s
@pytest.mark.parametrize("active_after,dt,should_be_visible", [
    (0.0,   0.1,   True),
    (10.0,  5.0,   False),
    (10.0, 10.0,   True),
])
def test_custom_active_after(active_after, dt, should_be_visible):
    from game.ui.play_scene import Enemy
    e = Enemy(pos=pygame.Vector2(0, 0), active_after_s=active_after)
    e.update(dt, pygame.Vector2(500, 500), WORLD_W, WORLD_H)
    assert e.visible == should_be_visible

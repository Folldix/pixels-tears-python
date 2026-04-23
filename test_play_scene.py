# -*- coding: utf-8 -*-
"""
test_play_scene.py — тести для логіки PlayScene.
Охоплює: інвентар, _interact, is_walkable, камера.
Pygame-рендеринг НЕ тестується (unit-тести).
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch, PropertyMock

pytestmark = pytest.mark.unit


# Фікстури PlayScene (без реальних файлів)
@pytest.fixture
def play(mock_assets, default_state, tmp_path):
    """
    PlayScene з повністю замоканими pygame-залежностями.
    Колізійна маска = None (все прохідно).
    """
    dummy_surf = pygame.Surface((200, 200))
    dummy_surf.fill((0, 0, 0))   # чорний = прохідний

    with patch("pygame.image.load", return_value=dummy_surf), \
         patch("pygame.font.Font", return_value=pygame.font.SysFont(None, 24)), \
         patch("pygame.mixer.Sound", return_value=MagicMock()), \
         patch("game.ui.textured_buttons.load_menu_button_pair", return_value=None), \
         patch("game.ui.play_scene.WsClient", MagicMock()):

        from game.ui.play_scene import PlayScene
        scene = PlayScene(assets=mock_assets, state=default_state)
        # Гарантуємо чисту маску (все прохідно)
        scene.collision_mask = None
        scene.world_w = 3000
        scene.world_h = 4000
    return scene


# Інвентар — початковий стан
class TestInventory:

    def test_initial_inventory_zeros(self, play):
        assert play.inventory == {"stick": 0, "stones": 0, "cable": 0}

    def test_inventory_keys_present(self, play):
        for key in ("stick", "stones", "cable"):
            assert key in play.inventory


# _interact — підбирання предметів
class TestInteract:

    def _place_item_near_player(self, play, item_type="stick"):
        """Додає видимий предмет поруч із гравцем."""
        from game.ui.play_scene import Material
        mat = Material(
            pos=pygame.Vector2(play.player.pos.x + 10, play.player.pos.y),
            image=pygame.Surface((32, 32)),
            item_type=item_type,
            visible=True,
        )
        play.materials.append(mat)
        return mat

    def test_pickup_nearby_item(self, play):
        mat = self._place_item_near_player(play, "stick")
        play._interact()
        assert mat.visible is False
        assert play.inventory["stick"] == 1

    def test_no_pickup_far_item(self, play):
        from game.ui.play_scene import Material
        mat = Material(
            pos=pygame.Vector2(play.player.pos.x + 500, play.player.pos.y),
            image=pygame.Surface((32, 32)),
            item_type="stick",
            visible=True,
        )
        play.materials.append(mat)
        play._interact()
        assert mat.visible is True
        assert play.inventory["stick"] == 0

    def test_pickup_only_one_item_per_interact(self, play):
        self._place_item_near_player(play, "stick")
        self._place_item_near_player(play, "stick")
        play._interact()
        assert play.inventory["stick"] == 1   # лише один за раз

    def test_pickup_invisible_item_ignored(self, play):
        from game.ui.play_scene import Material
        mat = Material(
            pos=pygame.Vector2(play.player.pos.x + 5, play.player.pos.y),
            image=pygame.Surface((32, 32)),
            item_type="stones",
            visible=False,
        )
        play.materials.append(mat)
        play._interact()
        assert play.inventory["stones"] == 0

    @pytest.mark.parametrize("item_type", ["stick", "stones", "cable"])
    def test_pickup_all_item_types(self, play, item_type):
        self._place_item_near_player(play, item_type)
        play._interact()
        assert play.inventory[item_type] == 1

    def test_victory_when_all_items_collected_at_basket(self, play):
        play.inventory = {"stick": 5, "stones": 4, "cable": 4}
        play.player.pos = pygame.Vector2(play.basket_pos.x, play.basket_pos.y)
        play._interact()
        assert play.show_victory_msg is True
        assert play.game_finished is True

    def test_no_victory_when_not_at_basket(self, play):
        play.inventory = {"stick": 5, "stones": 4, "cable": 4}
        play.player.pos = pygame.Vector2(0, 0)   # далеко від причалу
        play._interact()
        assert play.show_victory_msg is False


# is_walkable
class TestIsWalkable:

    def test_no_mask_always_walkable(self, play):
        play.collision_mask = None
        assert play.is_walkable(pygame.Vector2(100, 100)) is True

    def test_out_of_bounds_not_walkable(self, play):
        assert play.is_walkable(pygame.Vector2(-1, 0)) is False
        assert play.is_walkable(pygame.Vector2(0, -1)) is False
        assert play.is_walkable(pygame.Vector2(play.world_w + 1, 0)) is False
        assert play.is_walkable(pygame.Vector2(0, play.world_h + 1)) is False

    def test_white_pixel_not_walkable(self, play):
        mask = pygame.Surface((100, 100))
        mask.fill((255, 255, 255))   # суцільно білий = стіна
        play.collision_mask = mask
        play.world_w = 100
        play.world_h = 100
        assert play.is_walkable(pygame.Vector2(50, 50)) is False

    def test_black_pixel_walkable(self, play):
        mask = pygame.Surface((100, 100))
        mask.fill((0, 0, 0))   # чорний = прохідно
        play.collision_mask = mask
        play.world_w = 100
        play.world_h = 100
        assert play.is_walkable(pygame.Vector2(50, 50)) is True

    @pytest.mark.parametrize("px,py", [
        (0, 0),
        (99, 0),
        (0, 99),
        (99, 99),
        (50, 50),
    ])
    def test_walkable_black_pixels(self, play, px, py):
        mask = pygame.Surface((100, 100))
        mask.fill((0, 0, 0))
        play.collision_mask = mask
        play.world_w = 100
        play.world_h = 100
        assert play.is_walkable(pygame.Vector2(px, py)) is True


# Камера
class TestCamera:

    def test_camera_centered_on_player(self, play):
        play.player.pos = pygame.Vector2(500, 400)
        cam = play._camera()
        assert cam.x == pytest.approx(500 - 480)
        assert cam.y == pytest.approx(400 - 270)

    @pytest.mark.parametrize("px,py", [
        (480, 270),
        (1000, 800),
        (0, 0),
    ])
    def test_camera_formula(self, play, px, py):
        play.player.pos = pygame.Vector2(px, py)
        cam = play._camera()
        assert cam.x == pytest.approx(px - 480)
        assert cam.y == pytest.approx(py - 270)


# Пауза
class TestPause:

    def test_update_skips_when_paused(self, play):
        play.paused = True
        old_timer = play._map_anim_time
        play.update(0.5)
        assert play._map_anim_time == old_timer   # таймер не рухається

    def test_handle_event_escape_toggles_pause(self, play):
        play.paused = False
        ev = MagicMock(spec=pygame.event.Event)
        ev.type = pygame.KEYDOWN
        ev.key = pygame.K_ESCAPE
        play.handle_event(ev)
        assert play.paused is True

    def test_handle_event_escape_unpauses(self, play):
        play.paused = True
        ev = MagicMock(spec=pygame.event.Event)
        ev.type = pygame.KEYDOWN
        ev.key = pygame.K_ESCAPE
        play.handle_event(ev)
        assert play.paused is False

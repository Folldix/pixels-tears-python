# -*- coding: utf-8 -*-
"""
test_scenes.py — тести для SceneStack та MenuScene (логіка без рендерингу).
Охоплює: фікстури, мокування, маркери.
"""
import pytest
import pygame
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit


# SceneStack
class TestSceneStack:

    def _make_scene(self, name="scene"):
        scene = MagicMock()
        scene.__name__ = name
        return scene

    def test_push_adds_scene(self, scene_stack):
        s = self._make_scene()
        scene_stack.push(s)
        assert scene_stack.top is s

    def test_pop_removes_top(self, scene_stack):
        s1, s2 = self._make_scene("s1"), self._make_scene("s2")
        scene_stack.push(s1)
        scene_stack.push(s2)
        scene_stack.pop()
        assert scene_stack.top is s1

    def test_pop_empty_stack_no_error(self, scene_stack):
        scene_stack.pop()  # не має кидати виняток

    def test_replace_clears_and_sets(self, scene_stack):
        s1, s2, new = self._make_scene(), self._make_scene(), self._make_scene("new")
        scene_stack.push(s1)
        scene_stack.push(s2)
        scene_stack.replace(new)
        assert scene_stack.top is new
        assert len(scene_stack.stack) == 1

    def test_top_returns_last_pushed(self, scene_stack):
        scenes = [self._make_scene(f"s{i}") for i in range(5)]
        for s in scenes:
            scene_stack.push(s)
        assert scene_stack.top is scenes[-1]

    def test_multiple_push_pop(self, scene_stack):
        s1, s2, s3 = [self._make_scene(f"s{i}") for i in range(3)]
        scene_stack.push(s1)
        scene_stack.push(s2)
        scene_stack.push(s3)
        scene_stack.pop()
        scene_stack.pop()
        assert scene_stack.top is s1


# MenuScene — логіка без рендерингу
@pytest.fixture
def menu(mock_assets, default_state, tmp_path):
    """MenuScene з замоканими ресурсами."""
    # Мокуємо всі pygame.image / font виклики
    with patch("pygame.font.Font", return_value=pygame.font.SysFont(None, 24)), \
         patch("pygame.image.load", return_value=pygame.Surface((100, 50))), \
         patch("game.ui.textured_buttons.load_menu_button_pair", return_value=None):
        from game.ui.menu_scene import MenuScene
        scene = MenuScene(assets=mock_assets, state=default_state)
    return scene


class TestMenuSceneInit:

    def test_initial_screen_is_main(self, menu):
        assert menu.screen == "main"

    def test_initial_selection_zero(self, menu):
        assert menu.selection == 0

    def test_editing_is_none(self, menu):
        assert menu.editing is None


class TestMenuOptionCount:

    @pytest.mark.parametrize("screen,expected", [
        ("main", 4),
        ("skin", 3),
        ("mp",   4),
    ])
    def test_option_count(self, menu, screen, expected):
        menu.screen = screen
        assert menu._option_count() == expected


class TestMenuActivateSelected:

    def test_main_selection_1_goes_to_mp(self, menu):
        menu.screen = "main"
        menu.selection = 1
        menu._activate_selected()
        assert menu.screen == "mp"

    def test_main_selection_2_goes_to_skin(self, menu):
        menu.screen = "main"
        menu.selection = 2
        menu._activate_selected()
        assert menu.screen == "skin"

    def test_main_selection_3_raises_exit(self, menu):
        menu.screen = "main"
        menu.selection = 3
        with pytest.raises(SystemExit):
            menu._activate_selected()

    def test_skin_male_sets_skin(self, menu):
        menu.screen = "skin"
        menu.selection = 0
        menu._activate_selected()
        assert menu.state.skin_name == "male"

    def test_skin_female_sets_skin(self, menu):
        menu.screen = "skin"
        menu.selection = 1
        menu._activate_selected()
        assert menu.state.skin_name == "female"

    def test_skin_back_returns_to_main(self, menu):
        menu.screen = "skin"
        menu.selection = 2
        menu._activate_selected()
        assert menu.screen == "main"

    def test_mp_selection_0_starts_editing_player(self, menu):
        menu.screen = "mp"
        menu.selection = 0
        menu._activate_selected()
        assert menu.editing == "player"

    def test_mp_selection_2_starts_editing_lobby(self, menu):
        menu.screen = "mp"
        menu.selection = 2
        menu._activate_selected()
        assert menu.editing == "lobby"


class TestMenuHandleEvent:

    def _key_event(self, key, unicode_char=""):
        ev = MagicMock(spec=pygame.event.Event)
        ev.type = pygame.KEYDOWN
        ev.key = key
        ev.unicode = unicode_char
        return ev

    def test_escape_on_main_raises_exit(self, menu):
        ev = self._key_event(pygame.K_ESCAPE)
        with pytest.raises(SystemExit):
            menu.handle_event(ev)

    def test_escape_on_non_main_returns_to_main(self, menu):
        menu.screen = "skin"
        ev = self._key_event(pygame.K_ESCAPE)
        menu.handle_event(ev)
        assert menu.screen == "main"

    def test_down_key_increments_selection(self, menu):
        menu.screen = "main"
        menu.selection = 0
        ev = self._key_event(pygame.K_DOWN)
        menu.handle_event(ev)
        assert menu.selection == 1

    def test_up_key_wraps_selection(self, menu):
        menu.screen = "main"
        menu.selection = 0
        ev = self._key_event(pygame.K_UP)
        menu.handle_event(ev)
        assert menu.selection == menu._option_count() - 1

    def test_typing_player_name(self, menu):
        menu.screen = "mp"
        menu.editing = "player"
        menu.state.player_name = ""
        for char in "abc":
            ev = self._key_event(pygame.K_a, unicode_char=char)
            menu.handle_event(ev)
        assert menu.state.player_name == "abc"

    def test_backspace_removes_last_char(self, menu):
        menu.editing = "player"
        menu.state.player_name = "Test"
        ev = self._key_event(pygame.K_BACKSPACE)
        menu.handle_event(ev)
        assert menu.state.player_name == "Tes"

    def test_enter_stops_editing(self, menu):
        menu.editing = "player"
        ev = self._key_event(pygame.K_RETURN)
        menu.handle_event(ev)
        assert menu.editing is None

    def test_player_name_max_length(self, menu):
        """Ім'я гравця обмежене 16 символами."""
        menu.screen = "mp"
        menu.editing = "player"
        menu.state.player_name = "A" * 16
        ev = self._key_event(pygame.K_a, unicode_char="X")
        menu.handle_event(ev)
        assert len(menu.state.player_name) == 16

    def test_lobby_code_uppercase(self, menu):
        """Код лобі перетворюється у верхній регістр."""
        menu.screen = "mp"
        menu.editing = "lobby"
        menu.state.lobby_code = ""
        ev = self._key_event(pygame.K_a, unicode_char="a")
        menu.handle_event(ev)
        assert menu.state.lobby_code == "A"


# ═══════════════════════════════════════════════
# _SceneChange
# ═══════════════════════════════════════════════
class TestSceneChange:

    def test_scene_change_carries_next_scene(self):
        from game.ui.menu_scene import _SceneChange
        mock_scene = MagicMock()
        exc = _SceneChange(mock_scene)
        assert exc.next_scene is mock_scene

    def test_scene_change_is_runtime_error(self):
        from game.ui.menu_scene import _SceneChange
        assert issubclass(_SceneChange, RuntimeError)

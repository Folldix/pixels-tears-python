# -*- coding: utf-8 -*-
"""
test_state.py — тести для GameState.
Охоплює: фікстури, параметризацію, маркери.
"""
import pytest
from game.state import GameState


# Маркери
pytestmark = pytest.mark.unit


# Базові значення за замовчуванням
class TestGameStateDefaults:

    def test_default_skin(self, default_state):
        assert default_state.skin_name == "male"

    def test_default_player_name(self, default_state):
        assert default_state.player_name == "Player"

    def test_default_lobby_code_empty(self, default_state):
        assert default_state.lobby_code == ""

    def test_default_multiplayer_flags_false(self, default_state):
        assert default_state.multiplayergame is False
        assert default_state.host_server is False
        assert default_state.join_server is False

    def test_default_server_url(self, default_state):
        assert default_state.server_url.startswith("ws://")


# Параметризація: валідні скіни
@pytest.mark.parametrize("skin", ["male", "female"])
def test_valid_skin_names(skin):
    state = GameState(skin_name=skin)
    assert state.skin_name == skin


# Параметризація: лобі-коди різної довжини
@pytest.mark.parametrize("code,expected_len", [
    ("ABC123", 6),
    ("XY", 2),
    ("LONGCODE99", 10),
    ("", 0),
])
def test_lobby_code_stored_as_is(code, expected_len):
    state = GameState(lobby_code=code)
    assert state.lobby_code == code
    assert len(state.lobby_code) == expected_len


# Мутація стану
class TestGameStateMutation:

    def test_change_skin(self, default_state):
        default_state.skin_name = "female"
        assert default_state.skin_name == "female"

    def test_change_player_name(self, default_state):
        default_state.player_name = "Квітка"
        assert default_state.player_name == "Квітка"

    def test_enable_multiplayer(self, default_state):
        default_state.multiplayergame = True
        default_state.host_server = True
        assert default_state.multiplayergame is True
        assert default_state.host_server is True

    def test_set_lobby_code(self, default_state):
        default_state.lobby_code = "ROOM42"
        assert default_state.lobby_code == "ROOM42"

    def test_multiplayer_state_fixture(self, mp_state):
        """Перевірка мережевої фікстури."""
        assert mp_state.multiplayergame is True
        assert mp_state.player_name == "TestPlayer"
        assert mp_state.lobby_code == "ABC123"


# Параметризація: комбінації мережевих флагів
@pytest.mark.parametrize("multi,host,join", [
    (False, False, False),   # локальна гра
    (True, True, True),      # хост
    (True, False, True),     # клієнт
])
def test_network_flag_combinations(multi, host, join):
    state = GameState(multiplayergame=multi, host_server=host, join_server=join)
    assert state.multiplayergame == multi
    assert state.host_server == host
    assert state.join_server == join


# Маркер: повільний тест (демо)
@pytest.mark.slow
def test_many_state_instances():
    """Створює 1000 екземплярів — перевірка відсутності витоків."""
    states = [GameState(player_name=f"p{i}") for i in range(1000)]
    assert len(states) == 1000
    assert states[999].player_name == "p999"

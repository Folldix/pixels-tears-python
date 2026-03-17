from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameState:
    skin_name: str = "male"
    lobby_code: str = ""
    player_name: str = "Player"
    multiplayergame: bool = False
    host_server: bool = False
    join_server: bool = False
    server_url: str = "ws://132.226.193.207:8765"


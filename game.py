import random

from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class Player:
    username: str
    balance: float

    @staticmethod
    def create(username: str) -> "Player":
        return Player(
            username=username,
            balance=10,
        )


@dataclass(frozen=True)
class Game:
    player: Player | None
    other_player: Player | None
    id: str
    estimate: int | None = None
    error: int | None = None
    turn: Literal["player", "other_player"] = "player"
    estimator: Literal["player", "other_player"] = "player"
    ante: int = 0
    other_ante: int = 0

    def __post_init__(self) -> None:
        if (
            self.player is not None
            and self.other_player is not None
            and self.player.username == self.other_player.username
        ):
            raise ValueError("Player can't play against themselves!")

    @staticmethod
    def create(player: Player, other_player: Player | None) -> "Game":
        assert isinstance(player, Player)
        assert isinstance(other_player, Player) or other_player is None

        if other_player is None:
            return Game(
                player=player,
                other_player=None,
                id=_generate_game_id(),
            )

        return Game(
            player=player,
            other_player=other_player,
            id=_generate_game_id(),
        )

    def get_number_of_players(self) -> int:
        if self.player is None and self.other_player is None:
            return 0

        if self.player is None or self.other_player is None:
            return 1

        return 2

    def get_turn(self) -> Player:
        if self.player is not None and self.turn == "player":
            return self.player
        
        if self.other_player is not None and self.turn == "other_player":
            return self.other_player
        
        raise ValueError("Tried to get turn of game but game has no players!")

    def is_estimator(self, username: str) -> bool:
        assert isinstance(username, str)

        if self.get_number_of_players() == 0:
            raise ValueError("Game has no players!")

        if self.get_number_of_players() == 1:
            raise ValueError("Game is waiting for another player!")

        assert self.get_number_of_players() == 2
        assert self.player is not None
        assert self.other_player is not None

        if username not in [self.player.username, self.other_player.username]:
            raise ValueError("Username not found in game!")

        if self.estimator == "player" and self.player.username == username:
            return True

        if self.estimator == "other_player" and self.other_player.username == username:
            return True

        return False

    def add_player(self, player: Player) -> "Game":
        assert isinstance(player, Player)

        if self.player is None:
            return replace(self, player=player)

        if self.other_player is None:
            return replace(self, other_player=player)

        raise ValueError("Can't add another player since the game is full!")

    def get_player(self, username: str) -> Player:
        assert isinstance(username, str)

        if self.player is not None and self.player.username == username:
            return self.player

        if self.other_player is not None and self.other_player.username == username:
            return self.other_player

        raise ValueError("Username not found in game!")

    def remove_player(self, username: str) -> "Game":
        """Removes a player from the game."""
        assert isinstance(username, str)

        if self.player is not None and self.player.username == username:
            return replace(self, player=None)

        if self.other_player is not None and self.other_player.username == username:
            return replace(self, other_player=None)

        raise ValueError("Username not found in game!")

    def swtich_estimator(self) -> "Game":
        new_estimator = "player" if self.estimator == "other_player" else "other_player"

        return replace(
            self,
            estimator=new_estimator,
            turn=new_estimator,
            estimate=None,
            error=None,
        )
    
    def switch_turns(self) -> "Game":
        new_turn = "player" if self.turn == "other_player" else "other_player"
    
        return replace(self, turn=new_turn)

    def kick_players(self) -> "Game":
        """Kicks all players from the game."""
        return replace(self, player=None, other_player=None)

    def set_estimate(self, estimate: int) -> "Game":
        assert isinstance(estimate, int)

        return replace(self, estimate=estimate)
    
    def get_estimate(self) -> int | None:
        return self.estimate

    def set_error(self, error: int) -> "Game":
        assert isinstance(error, int)

        return replace(self, error=error)
    
    def get_error(self) -> int | None:
        return self.error

    def is_players_turn(self, username: str) -> bool:
        assert isinstance(username, str)

        player = self.get_player(username)
        
        if (
            self.player is not None
            and player.username == self.player.username
            and self.turn == "player"
        ):
            return True

        if (
            self.other_player is not None
            and player.username == self.other_player.username
            and self.turn == "other_player"
        ):
            return True

        return False
    
    def get_opponent(self, username: str) -> Player | None:
        assert isinstance(username, str)
        
        if self.player is not None and self.player.username == username:
            return self.other_player

        if self.other_player is not None and self.other_player.username == username:
            return self.player

        raise ValueError("Username not found in game!")
    
    def get_ante(self, username: str) -> int:
        assert isinstance(username, str)
        
        if self.player is not None and self.player.username == username:
            return self.ante

        if self.other_player is not None and self.other_player.username == username:
            return self.other_ante

        raise ValueError("Username not found in game!")


def is_valid_game_id(game_id: str) -> bool:
    if not isinstance(game_id, str):
        return False

    if len(game_id) != 5:
        return False

    if not game_id.isalpha():
        return False

    return True


def is_valid_username(username: str) -> bool:
    if not isinstance(username, str):
        return False

    if len(username) == 0:
        return False

    return True


def _generate_game_id():
    letters = random.sample("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 5)
    return "".join(letters)

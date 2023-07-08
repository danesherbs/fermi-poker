import random

from dataclasses import dataclass, replace
from typing import Literal


@dataclass(frozen=True)
class Problem:
    description: str
    oom: int

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
    problem: str
    expected_oom: int
    actual_oom: int | None = None
    error: int | None = None
    turn: Literal["player", "other_player"] = "player"
    estimator: Literal["player", "other_player"] = "player"
    ante: int = 1
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

        problem = _generate_problem()

        if other_player is None:
            return Game(
                player=player,
                other_player=None,
                id=_generate_game_id(),
                problem=problem.description,
                expected_oom=problem.oom,
            )

        return Game(
            player=player,
            other_player=other_player,
            id=_generate_game_id(),
            problem=problem.description,
            expected_oom=problem.oom,
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
    
    def is_winner(self, username: str) -> bool:
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
        
        payout = self.get_payout()

        if self.is_estimator(username) and payout > 0:
            return True

        if not self.is_estimator(username) and payout < 0:
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
            actual_oom=None,
            error=None,
        )
    
    def switch_turns(self) -> "Game":
        new_turn = "player" if self.turn == "other_player" else "other_player"
    
        return replace(self, turn=new_turn)

    def kick_players(self) -> "Game":
        """Kicks all players from the game."""
        return replace(self, player=None, other_player=None)

    def set_estimate(self, actual_oom: int) -> "Game":
        assert isinstance(actual_oom, int)

        return replace(self, actual_oom=actual_oom)
    
    def get_estimate(self) -> int | None:
        return self.actual_oom

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
    
    def raise_ante(self) -> "Game":
        if self.player is None or self.other_player is None:
            raise ValueError("Game has no players!")

        if self.turn == "player":
            return replace(self, ante=self.other_ante + 1)
        
        return replace(self, other_ante=self.ante + 1)
    
    def call_ante(self) -> "Game":
        if self.player is None or self.other_player is None:
            raise ValueError("Game has no players!")
        
        if self.actual_oom is None or self.error is None:
            raise ValueError("Game has no estimate or error!")
        
        payout = self.get_payout()
        max_ante = max(self.ante, self.other_ante)

        if self.turn == "player":
            new_player = replace(self.player, balance=self.player.balance + payout)
            new_other_player = replace(self.other_player, balance=self.other_player.balance - payout)
            return replace(self, player=new_player, other_player=new_other_player, ante=max_ante, other_ante=max_ante)
        
        new_player = replace(self.player, balance=self.player.balance - payout)
        new_other_player = replace(self.other_player, balance=self.other_player.balance + payout, other_ante=self.ante)
        return replace(self, player=new_player, other_player=new_other_player, ante=max_ante, other_ante=max_ante)
    
    def fold(self) -> "Game":
        if self.player is None or self.other_player is None:
            raise ValueError("Game has no players!")

        if self.turn == "player":
            new_player = replace(self.player, balance=self.player.balance - self.ante)
            new_other_player = replace(self.other_player, balance=self.other_player.balance + self.ante)
            return replace(self, player=new_player, other_player=new_other_player)
        
        new_player = replace(self.player, balance=self.player.balance + self.other_ante)
        new_other_player = replace(self.other_player, balance=self.other_player.balance - self.other_ante)
        return replace(self, player=new_player, other_player=new_other_player)
    
    def get_payout(self) -> int:
        assert self.actual_oom is not None
        assert self.error is not None

        sign = 1 if self.actual_oom - self.error <= self.expected_oom <= self.actual_oom + self.error else -1

        if self.error == 0:
            return sign * 8
        elif self.error == 1:
            return sign * 5
        elif self.error == 2:
            return sign * 2
        elif self.error == 3:
            return sign * 1
        
        raise ValueError("Invalid error value!")
    

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

def _generate_problem() -> Problem:
    return Problem(
        description="How many beats will your heart make in a lifetime?",
        oom=9,
    )
import random
import pandas as pd
import dataclasses

from dataclasses import dataclass, replace
from typing import Literal

LOG_ERROR_TO_PAYOUT = {
    0: 8,
    1: 5,
    2: 2,
    3: 1,
}


@dataclass(frozen=True)
class Problem:
    question: str
    log_answer: int
    source: str


@dataclass(frozen=True)
class Prediction:
    log_answer: int
    log_error: int

    def __post_init__(self):
        if self.log_error < 0:
            raise ValueError("Log error must be non-negative!")

        if self.log_error > 3:
            raise ValueError("Log error must be less than 4!")


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
    id: str
    usernames: set[str]
    problem: Problem
    estimator: str | None
    prediction: Prediction | None
    current_player: str | None
    antes: dict[str, int]
    folded_players: set[str] = dataclasses.field(default_factory=set)
    # actual_oom: int | None = None
    # error: int | None = None
    # turn: Literal["player", "other_player"] = "player"
    # estimator: Literal["player", "other_player"] = "player"
    # ante: int = 1
    # other_ante: int = 0

    def join(self, username: str) -> "Game":
        new_usernames = set([*self.usernames, username])

        if len(new_usernames) > 2:
            raise ValueError("Can't add another player since the game is full!")

        return replace(self, usernames=new_usernames)

    def contains(self, username: str) -> bool:
        return username in self.usernames

    def leave(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't remove player since they aren't in the game!")

        if username in self.antes:
            raise ValueError("Can't remove player since they have placed an ante!")

        new_usernames = set(user for user in self.usernames if user != username)
        new_antes = {
            user: ante for user, ante in self.antes.items() if user != username
        }

        return replace(self, usernames=new_usernames, antes=new_antes)

    def get_num_players(self) -> int:
        return len(self.usernames)

    def is_full(self) -> bool:
        return self.get_num_players() == 2

    def is_player_waiting(self) -> bool:
        return self.get_num_players() == 1

    def set_estimator(self, username: str | None) -> "Game":
        if username is not None and username not in self.usernames:
            raise ValueError("Can't set estimator to a player that's not in the game!")

        return replace(self, estimator=username)

    def get_estimator(self) -> str | None:
        return self.estimator

    def is_estimator(self, username: str) -> bool:
        return self.estimator == username

    def is_ready_to_start(self) -> bool:
        return self.is_full() and self.estimator is not None

    def get_prediction(self) -> Prediction | None:
        return self.prediction

    def set_prediction(self, prediction: Prediction | None) -> "Game":
        return replace(self, prediction=prediction)

    def has_prediction(self) -> bool:
        return self.prediction is not None

    def set_current_player(self, username: str | None) -> "Game":
        if username is not None and username not in self.usernames:
            raise ValueError(
                "Can't set current player to a player that's not in the game!"
            )

        return replace(self, current_player=username)

    def get_current_player(self) -> str | None:
        return self.current_player

    def get_opponent(self, username: str) -> str:
        if not isinstance(username, str):
            raise TypeError("Username must be a string!")

        if username not in self.usernames:
            raise ValueError("Can't get opponent of a player that's not in the game!")

        if len(self.usernames) != 2:
            raise ValueError(
                "Can't get opponent of a player in a game with less than 2 players!"
            )

        username_list = list(self.usernames)

        if username == username_list[0]:
            return username_list[1]

        return username_list[0]

    def get_antes(self) -> dict[str, int]:
        return self.antes

    def set_ante(self, username: str, ante: int) -> "Game":
        assert isinstance(username, str)
        assert isinstance(ante, int)

        if username not in self.usernames:
            raise ValueError("Can't set ante of a player that's not in the game!")

        if self.has_folded(username):
            raise ValueError("Can't set ante of a player who has folded!")

        if ante < 0:
            raise ValueError("Ante must be non-negative!")

        new_antes = {**self.antes, username: ante}

        return replace(self, antes=new_antes)

    def get_ante(self, username: str) -> int:
        if username not in self.usernames:
            raise ValueError("Can't get ante of a player that's not in the game!")

        if username not in self.antes:
            raise ValueError("Can't get ante of a player who has not placed an ante!")

        return self.antes[username]

    def raise_ante(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't raise ante of a player that's not in the game!")

        opponent = self.get_opponent(username)
        oppoenents_ante = self.get_ante(opponent)
        new_game = self.set_ante(username, oppoenents_ante + 1)

        if self.get_ante(username) >= new_game.get_ante(username):
            raise ValueError(
                "Can't raise ante when opponent's ante is less than or equal to yours!"
            )

        return new_game

    def call_ante(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't call ante of a player that's not in the game!")

        opponent = self.get_opponent(username)
        oppoenents_ante = self.get_ante(opponent)
        new_game = self.set_ante(username, oppoenents_ante)

        if self.get_ante(username) >= new_game.get_ante(username):
            raise ValueError(
                "Can't call ante when opponent's ante is less than or equal to yours!"
            )

        return new_game

    def has_called_ante(self, username: str) -> bool:
        if username not in self.usernames:
            raise ValueError(
                "Can't check if a player that's not in the game has called!"
            )

        return self.get_ante(username) == max(self.antes.values())

    def fold(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't fold a player that's not in the game!")

        if self.has_folded(username):
            raise ValueError("Can't fold a player who has already folded!")

        new_folded_players = set([*self.folded_players, username])

        return replace(self, folded_players=new_folded_players)

    def has_folded(self, username: str) -> bool:
        if username not in self.usernames:
            raise ValueError(
                "Can't check if a player that's not in the game has folded!"
            )

        return username in self.folded_players

    def has_winner(self) -> bool:
        if self.prediction is None:
            return False

        return True

    def is_winner(self, username: str) -> bool:
        if username not in self.usernames:
            raise ValueError("Can't check if a player that's not in the game has won!")

        if not self.has_winner():
            return False

        if self.is_estimator(username) and self.is_prediction_correct():
            return True

        if not self.is_estimator(username) and not self.is_prediction_correct():
            return True

        return False

    def is_prediction_correct(self) -> bool:
        if self.prediction is None:
            raise ValueError(
                "Can't check if a prediction is correct if there is no prediction!"
            )

        return (
            self.prediction.log_answer - self.prediction.log_error
            <= self.problem.log_answer
            <= self.prediction.log_answer + self.prediction.log_error
        )

    def get_payout(self, username: str) -> int:
        if username not in self.usernames:
            raise ValueError("Can't get payout of a player that's not in the game!")

        prediction = self.get_prediction()

        if prediction is None:
            raise ValueError("Can't get payout if there is no prediction!")

        if prediction.log_error not in LOG_ERROR_TO_PAYOUT:
            raise ValueError(
                f"Expected log error to be between 0 and 3 but got {prediction.log_error}!"
            )

        if self.is_winner(username):
            return LOG_ERROR_TO_PAYOUT[prediction.log_error]

        return -LOG_ERROR_TO_PAYOUT[prediction.log_error]

    # def __post_init__(self) -> None:
    #     if (
    #         self.player_one is not None
    #         and self.player_two is not None
    #         and self.player_one.username == self.player_two.username
    #     ):
    #         raise ValueError("Player can't play against themselves!")

    # @staticmethod
    # def create(player: Player, other_player: Player | None) -> "Game":
    #     assert isinstance(player, Player)
    #     assert isinstance(other_player, Player) or other_player is None

    #     problem = _generate_problem()

    #     if other_player is None:
    #         return Game(
    #             player_one=player,
    #             player_two=None,
    #             id=_generate_game_id(),
    #             problem=problem,
    #         )

    #     return Game(
    #         player_one=player,
    #         player_two=other_player,
    #         id=_generate_game_id(),
    #         problem=problem,
    #     )

    #     if self.player_one is None or self.player_two is None:
    #         return 1

    #     return 2

    # def get_turn(self) -> Player:
    #     if self.player_one is not None and self.turn == "player":
    #         return self.player_one

    #     if self.player_two is not None and self.turn == "other_player":
    #         return self.player_two

    #     raise ValueError("Tried to get turn of game but game has no players!")

    # def is_estimator(self, username: str) -> bool:
    #     assert isinstance(username, str)

    #     if (
    #         self.player_one is not None
    #         and self.player_one.username == username
    #         and self.estimator == "player"
    #     ):
    #         return True

    #     if (
    #         self.player_two is not None
    #         and self.player_two.username == username
    #         and self.estimator == "other_player"
    #     ):
    #         return True

    #     return False

    # def is_winner(self, username: str) -> bool:
    #     assert isinstance(username, str)

    #     payout = self.get_payout()

    #     if self.is_estimator(username) and payout > 0:
    #         return True

    #     if not self.is_estimator(username) and payout < 0:
    #         return True

    #     return False

    # def add_player(self, player: Player) -> "Game":
    #     assert isinstance(player, Player)

    #     if self.player_one is None:
    #         return replace(self, player=player)

    #     if self.player_two is None:
    #         return replace(self, other_player=player)

    #     raise ValueError("Can't add another player since the game is full!")

    # def get_player(self, username: str) -> Player:
    #     assert isinstance(username, str)

    #     if self.player_one is not None and self.player_one.username == username:
    #         return self.player_one

    #     if self.player_two is not None and self.player_two.username == username:
    #         return self.player_two

    #     raise ValueError(f"Username '{username}' not found in game!")

    # def remove_player(self, username: str) -> "Game":
    #     """Removes a player from the game."""
    #     assert isinstance(username, str)

    #     if self.player_one is not None and self.player_one.username == username:
    #         return replace(self, player=None)

    #     if self.player_two is not None and self.player_two.username == username:
    #         return replace(self, other_player=None)

    #     raise ValueError("Username not found in game!")

    # def swtich_estimator(self) -> "Game":
    #     new_estimator = "player" if self.estimator == "other_player" else "other_player"

    #     return replace(
    #         self,
    #         estimator=new_estimator,
    #         turn=new_estimator,
    #         actual_oom=None,
    #         error=None,
    #         problem=_generate_problem(),
    #     )

    # def switch_turns(self) -> "Game":
    #     new_turn = "player" if self.turn == "other_player" else "other_player"

    #     return replace(self, turn=new_turn)

    # def kick_players(self) -> "Game":
    #     """Kicks all players from the game."""
    #     return replace(self, player=None, other_player=None)

    # def set_estimate(self, actual_oom: int) -> "Game":
    #     assert isinstance(actual_oom, int)

    #     return replace(self, actual_oom=actual_oom)

    # def get_estimate(self) -> int | None:
    #     return self.actual_oom

    # def set_error(self, error: int) -> "Game":
    #     assert isinstance(error, int)

    #     return replace(self, error=error)

    # def get_error(self) -> int | None:
    #     return self.error

    # def is_players_turn(self, username: str) -> bool:
    #     assert isinstance(username, str)

    #     player = self.get_player(username)

    #     if (
    #         self.player_one is not None
    #         and player.username == self.player_one.username
    #         and self.turn == "player"
    #     ):
    #         return True

    #     if (
    #         self.player_two is not None
    #         and player.username == self.player_two.username
    #         and self.turn == "other_player"
    #     ):
    #         return True

    #     return False

    # def get_opponent(self, username: str) -> Player | None:
    #     assert isinstance(username, str)

    #     if self.player_one is not None and self.player_one.username == username:
    #         return self.player_two

    #     if self.player_two is not None and self.player_two.username == username:
    #         return self.player_one

    #     raise ValueError("Username not found in game!")

    # def get_ante(self, username: str) -> int:
    #     assert isinstance(username, str)

    #     if self.player_one is not None and self.player_one.username == username:
    #         return self.ante

    #     if self.player_two is not None and self.player_two.username == username:
    #         return self.other_ante

    #     raise ValueError("Username not found in game!")

    # def raise_ante(self) -> "Game":
    #     if self.player_one is None or self.player_two is None:
    #         raise ValueError("Game has no players!")

    #     if self.turn == "player":
    #         return replace(self, ante=self.other_ante + 1)

    #     return replace(self, other_ante=self.ante + 1)

    # def call_ante(self) -> "Game":
    #     if self.player_one is None or self.player_two is None:
    #         raise ValueError("Game has no players!")

    #     if self.actual_oom is None or self.error is None:
    #         raise ValueError("Game has no estimate or error!")

    #     payout = self.get_payout()
    #     max_ante = max(self.ante, self.other_ante)

    #     if self.turn == "player":
    #         new_player = replace(self.player_one, balance=self.player_one.balance + payout)
    #         new_other_player = replace(
    #             self.player_two, balance=self.player_two.balance - payout
    #         )
    #         return replace(
    #             self,
    #             player=new_player,
    #             other_player=new_other_player,
    #             ante=max_ante,
    #             other_ante=max_ante,
    #         )

    #     new_player = replace(self.player_one, balance=self.player_one.balance - payout)
    #     new_other_player = replace(
    #         self.player_two, balance=self.player_two.balance + payout
    #     )
    #     return replace(
    #         self,
    #         player=new_player,
    #         other_player=new_other_player,
    #         ante=max_ante,
    #         other_ante=max_ante,
    #     )

    # def fold(self) -> "Game":
    #     if self.player_one is None or self.player_two is None:
    #         raise ValueError("Game has no players!")

    #     if self.turn == "player":
    #         new_player = replace(self.player_one, balance=self.player_one.balance - self.ante)
    #         new_other_player = replace(
    #             self.player_two, balance=self.player_two.balance + self.ante
    #         )
    #         return replace(self, player=new_player, other_player=new_other_player)

    #     new_player = replace(self.player_one, balance=self.player_one.balance + self.other_ante)
    #     new_other_player = replace(
    #         self.player_two, balance=self.player_two.balance - self.other_ante
    #     )
    #     return replace(self, player=new_player, other_player=new_other_player)

    # def get_payout(self) -> int:
    #     assert self.actual_oom is not None
    #     assert self.error is not None

    #     sign = (
    #         1
    #         if self.actual_oom - self.error
    #         <= self.expected_oom
    #         <= self.actual_oom + self.error
    #         else -1
    #     )

    #     if self.error == 0:
    #         return sign * 8
    #     elif self.error == 1:
    #         return sign * 5
    #     elif self.error == 2:
    #         return sign * 2
    #     elif self.error == 3:
    #         return sign * 1

    #     raise ValueError("Invalid error value!")

    # def reset(self) -> "Game":
    #     new_problem = _generate_problem()

    #     return Game(
    #         player_one=None,
    #         player_two=None,
    #         id=self.id,
    #         problem=new_problem,
    #         turn=self.estimator,
    #         estimator=self.estimator,
    #     )


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
    df = pd.read_csv("problems.csv").sample(n=1)

    question = df["question"].values[0]
    answer = int(df["answer"].values[0].split("^")[-1])
    source = df["source"].values[0]

    return Problem(
        question=question,
        log_answer=answer,
        source=source,
    )

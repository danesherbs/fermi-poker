import random
import pandas as pd  # type: ignore
import dataclasses

from enum import Enum, auto
from dataclasses import dataclass, replace

LOG_ERROR_TO_PAYOUT = {
    0: 8,
    1: 5,
    2: 2,
    3: 1,
}


class InvalidStateException(Exception):
    """Raised when a state transition is invalid."""

    def __init__(self, current_state, attempted_transition):
        self.current_state = current_state
        self.attempted_transition = attempted_transition

        super().__init__(
            f"Cannot transition from {self.current_state} to {self.attempted_transition}."
        )


class GameState(Enum):
    GAME_IS_EMPTY = auto()
    WAITING_FOR_ANOTHER_PLAYER = auto()
    WAITING_FOR_ESTIMATE = auto()
    ESTIMATOR_FOLDED = auto()
    ESTIMATEE_FOLDED = auto()
    WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD = auto()
    WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD = auto()
    BOTH_PLAYERS_CALLED = auto()
    A_PLAYER_WANTS_TO_PLAY_AGAIN = auto()
    GAME_OVER = auto()


VALID_TRANSITIONS: dict[GameState, tuple[GameState, ...]] = {
    GameState.GAME_IS_EMPTY: (GameState.WAITING_FOR_ANOTHER_PLAYER,),
    GameState.WAITING_FOR_ANOTHER_PLAYER: (GameState.WAITING_FOR_ESTIMATE,),
    GameState.WAITING_FOR_ESTIMATE: (
        GameState.ESTIMATOR_FOLDED,
        GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
    ),
    GameState.ESTIMATOR_FOLDED: (
        GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN,
        GameState.GAME_OVER,
    ),
    GameState.ESTIMATEE_FOLDED: (
        GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN,
        GameState.GAME_OVER,
    ),
    GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD: (
        GameState.ESTIMATEE_FOLDED,
        GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
        GameState.BOTH_PLAYERS_CALLED,
    ),
    GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD: (
        GameState.ESTIMATOR_FOLDED,
        GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
        GameState.BOTH_PLAYERS_CALLED,
    ),
    GameState.BOTH_PLAYERS_CALLED: (
        GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN,
        GameState.GAME_OVER,
    ),
    GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN: (
        GameState.WAITING_FOR_ESTIMATE,
        GameState.GAME_OVER,
    ),
    GameState.GAME_OVER: (GameState.GAME_OVER,),
}


@dataclass(frozen=True)
class Problem:
    question: str
    log_answer: int
    source: str


@dataclass(frozen=True)
class Estimate:
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
    balance: int
    was_estimator_in_last_round: bool = False

    @staticmethod
    def create(username: str) -> "Player":
        return Player(
            username=username,
            balance=10,
        )

    def set_balance(self, new_balance: int) -> "Player":
        # pre-conditions
        assert new_balance >= 0

        # body
        return replace(self, balance=new_balance)


@dataclass(frozen=True)
class Game:
    id: str
    current_state: GameState
    usernames: set[str]
    problem: Problem
    estimator: str | None
    estimate: Estimate | None
    current_player: str | None
    antes: dict[str, int]

    @staticmethod
    def create() -> "Game":
        return Game(
            id=_generate_game_id(),
            current_state=GameState.GAME_IS_EMPTY,
            usernames=set(),
            problem=_generate_problem(),
            estimator=None,
            estimate=None,
            current_player=None,
            antes={},
        )

    def join(self, username: str) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.GAME_IS_EMPTY,
            GameState.WAITING_FOR_ANOTHER_PLAYER,
        ]

        # body
        new_usernames = set([*self.usernames, username])
        old_antes = self.get_antes()
        new_antes = {**old_antes, username: 0}
        new_game = replace(self, usernames=new_usernames, antes=new_antes)

        if new_game.get_num_players() == 1:
            return (
                new_game.set_estimator(username)
                .set_ante(username, 1)
                .set_current_player(username)
                .transition_to(GameState.WAITING_FOR_ANOTHER_PLAYER)
            )

        return new_game.transition_to(GameState.WAITING_FOR_ESTIMATE)

    def contains(self, username: str) -> bool:
        return username in self.usernames

    def get_num_players(self) -> int:
        return len(self.usernames)

    def set_estimator(self, username: str | None) -> "Game":
        # pre-conditions
        assert username is None or username in self.usernames

        # body
        return replace(self, estimator=username)

    def get_estimator(self) -> str | None:
        return self.estimator

    def is_estimator(self, username: str) -> bool:
        return self.estimator == username

    def has_estimator(self) -> bool:
        return self.estimator is not None

    def get_esimate(self) -> Estimate | None:
        return self.estimate

    def is_waiting_for_players(self) -> bool:
        return self.get_state() in [
            GameState.GAME_IS_EMPTY,
            GameState.WAITING_FOR_ANOTHER_PLAYER,
        ]

    def set_estimate(self, estimate: Estimate) -> "Game":
        # pre-conditions
        assert self.get_state() == GameState.WAITING_FOR_ESTIMATE
        assert isinstance(estimate, Estimate)

        estimator = self.get_estimator()

        assert estimator is not None
        assert self.is_current_player(estimator)

        # body
        new_game = (
            replace(self, estimate=estimate)
            .switch_turns()
            .transition_to(GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD)
        )

        # post-conditions
        assert new_game.get_esimate() == estimate
        assert new_game.get_ante(estimator) == 1
        assert not new_game.is_current_player(estimator)

        return new_game

    def has_estimate(self) -> bool:
        return self.estimate is not None

    def set_current_player(self, username: str | None) -> "Game":
        # pre-conditions
        assert username is None or username in self.usernames

        # body
        return replace(self, current_player=username)

    def get_current_player(self) -> str | None:
        return self.current_player

    def is_current_player(self, username: str) -> bool:
        return self.get_current_player() == username

    def get_opponent(self, username: str) -> str:
        # pre-conditions
        assert username in self.usernames

        # body
        username_list = list(self.usernames)

        if username == username_list[1]:
            opponent = username_list[0]
        else:
            opponent = username_list[1]

        # post-conditions
        assert opponent in self.usernames
        assert opponent != username

        return opponent

    def get_antes(self) -> dict[str, int]:
        return self.antes

    def set_ante(self, username: str, new_ante: int) -> "Game":
        # pre-conditions
        assert username in self.usernames
        assert new_ante >= 0

        # body
        new_antes = {**self.antes, username: new_ante}
        new_game = replace(self, antes=new_antes)

        # post-conditions
        assert new_game.get_ante(username) == new_ante

        return new_game

    def get_ante(self, username: str) -> int:
        # pre-conditions
        assert username in self.usernames
        assert username in self.antes

        # body
        return self.antes[username]

    def raise_ante(self, username: str) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
            GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
        ]

        assert username in self.usernames

        estimator = self.get_estimator()

        assert estimator is not None

        opponent = self.get_opponent(username)

        assert opponent is not None
        assert self.get_ante(username) < self.get_ante(opponent)
        assert self.is_current_player(username)

        # body
        oppoenents_ante = self.get_ante(opponent)
        new_state = GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD

        if self.get_state() == GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD:
            new_state = GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD

        new_game = (
            self.set_ante(username, oppoenents_ante + 1)
            .switch_turns()
            .transition_to(new_state)
        )

        # post-conditions
        assert new_game.get_ante(username) == new_game.get_ante(opponent) + 1
        assert new_game.get_ante(opponent) == self.get_ante(opponent)
        assert new_game.get_state() == new_state
        assert new_game.is_current_player(
            opponent
        ), f"Expected {opponent}. Got {new_game.get_current_player()}."

        return new_game

    def call_ante(self, username: str) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
            GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
        ]

        assert username in self.usernames

        opponent = self.get_opponent(username)

        assert opponent is not None
        assert self.get_ante(username) < self.get_ante(opponent)
        assert self.is_current_player(username)

        # body
        opponent = self.get_opponent(username)
        oppoenents_ante = self.get_ante(opponent)
        new_game = (
            self.set_ante(username, oppoenents_ante)
            .switch_turns()
            .transition_to(GameState.BOTH_PLAYERS_CALLED)
        )

        # post-conditions
        assert new_game.get_ante(username) == new_game.get_ante(opponent)
        assert new_game.get_state() == GameState.BOTH_PLAYERS_CALLED
        assert new_game.is_current_player(opponent)

        return new_game

    def has_called_ante(self) -> bool:
        return self.get_state() == GameState.BOTH_PLAYERS_CALLED

    def fold(self, username: str) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.WAITING_FOR_ESTIMATE,
            GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
            GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
        ]

        assert username in self.usernames
        assert self.is_current_player(username)

        # body
        if self.get_state() == GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD:
            new_game = self.transition_to(GameState.ESTIMATEE_FOLDED)
        elif self.get_state() == GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD:
            new_game = self.transition_to(GameState.ESTIMATOR_FOLDED)
        else:
            new_game = self.transition_to(GameState.ESTIMATOR_FOLDED)

        # post-conditions
        is_esimtaor = self.is_estimator(username)

        if is_esimtaor:
            assert new_game.get_state() == GameState.ESTIMATOR_FOLDED

        if not is_esimtaor:
            assert new_game.get_state() == GameState.ESTIMATEE_FOLDED

        return new_game

    def is_winner(self, username: str) -> bool:
        # pre-conditions
        assert self.get_state() in [
            GameState.ESTIMATEE_FOLDED,
            GameState.ESTIMATOR_FOLDED,
            GameState.BOTH_PLAYERS_CALLED,
        ]

        assert username in self.usernames

        if self.get_state() == GameState.BOTH_PLAYERS_CALLED:
            assert self.estimate is not None

        # body
        if self.get_state() == GameState.ESTIMATEE_FOLDED:
            return self.is_estimator(username)

        if self.get_state() == GameState.ESTIMATOR_FOLDED:
            return not self.is_estimator(username)

        if self.is_estimator(username) and self.is_prediction_correct():
            return True

        if not self.is_estimator(username) and not self.is_prediction_correct():
            return True

        return False

    def is_prediction_correct(self) -> bool:
        # pre-conditions
        assert self.get_state() in [
            GameState.ESTIMATOR_FOLDED,
            GameState.ESTIMATEE_FOLDED,
            GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
            GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
            GameState.BOTH_PLAYERS_CALLED,
        ]

        assert self.estimate is not None

        # body
        return (
            self.estimate.log_answer - self.estimate.log_error
            <= self.problem.log_answer
            <= self.estimate.log_answer + self.estimate.log_error
        )

    def get_payout(self, username: str) -> int:
        # pre-conditions
        assert self.get_state() in [
            GameState.ESTIMATEE_FOLDED,
            GameState.ESTIMATOR_FOLDED,
            GameState.BOTH_PLAYERS_CALLED,
        ]

        if self.get_state() == GameState.BOTH_PLAYERS_CALLED:
            assert self.get_esimate() is not None

        assert username in self.usernames

        # body
        opponent = self.get_opponent(username)
        sign = 1 if self.is_winner(username) else -1

        if self.get_state() in [
            GameState.ESTIMATEE_FOLDED,
            GameState.ESTIMATOR_FOLDED,
        ]:
            return sign * max(self.get_ante(opponent), self.get_ante(username))

        estimate = self.get_esimate()
        ante = self.get_ante(username)
        payout = sign * ante * LOG_ERROR_TO_PAYOUT[estimate.log_error]  # type: ignore

        # post-conditions
        if self.is_winner(username):
            assert payout > 0

        if not self.is_winner(username):
            assert payout < 0

        return payout

    def get_problem(self) -> Problem:
        return self.problem

    def switch_turns(self) -> "Game":
        if self.current_player is None:
            raise ValueError("Can't switch turns if there is no current player!")

        new_current_player = self.get_opponent(self.current_player)

        return replace(self, current_player=new_current_player)

    def _start_new_round(self) -> "Game":
        old_estimator = self.get_estimator()
        new_estimator = self.get_next_estimator()
        new_antes = {old_estimator: 0, new_estimator: 1}
        new_game = replace(
            self,
            problem=_generate_problem(),
            estimator=new_estimator,
            current_player=new_estimator,
            antes=new_antes,
        )

        return new_game

    def get_next_estimator(self) -> str:
        if self.estimator is None:
            raise ValueError("Can't get next estimator if there is no estimator!")

        if self.estimator not in self.usernames:
            raise ValueError("Can't get next estimator if estimator is not in game!")

        assert len(self.usernames) == 2

        if self.estimator == list(self.usernames)[0]:
            return list(self.usernames)[1]

        return list(self.usernames)[0]

    def get_state(self) -> GameState:
        return self.current_state

    def transition_to(self, new_state: GameState) -> "Game":
        if not self.is_valid_transition(new_state):
            raise InvalidStateException(self.current_state, new_state)

        return replace(self, current_state=new_state)

    def is_valid_transition(self, new_state):
        return new_state in VALID_TRANSITIONS[self.current_state]

    def end(self) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.BOTH_PLAYERS_CALLED,
            GameState.ESTIMATEE_FOLDED,
            GameState.ESTIMATOR_FOLDED,
            GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN,
            GameState.GAME_OVER,
        ]

        # body
        new_game = self.transition_to(GameState.GAME_OVER)

        # post-conditions
        assert new_game.get_state() == GameState.GAME_OVER

        return new_game

    def is_game_over(self) -> bool:
        return self.get_state() == GameState.GAME_OVER

    def play_again(self, username: str) -> "Game":
        # pre-conditions
        assert self.get_state() in [
            GameState.ESTIMATOR_FOLDED,
            GameState.ESTIMATEE_FOLDED,
            GameState.BOTH_PLAYERS_CALLED,
            GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN,
            GameState.GAME_OVER,
        ]

        assert username in self.usernames

        # body
        if self.get_state() == GameState.GAME_OVER:
            return self

        if self.get_state() == GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN:
            return self._start_new_round().transition_to(GameState.WAITING_FOR_ESTIMATE)

        return self.transition_to(GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN)


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

    if not username.isalpha():
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

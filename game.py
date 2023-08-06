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
    WAITING_FOR_PLAYERS = auto()
    WAITING_FOR_ESTIMATE = auto()
    WAITING_FOR_RAISE_CALL_OR_FOLD = auto()
    ROUND_ENDED = auto()
    GAME_ENDED = auto()


VALID_TRANSITIONS: dict[GameState, tuple[GameState, ...]] = {
    GameState.WAITING_FOR_PLAYERS: (GameState.WAITING_FOR_ESTIMATE,),
    GameState.WAITING_FOR_ESTIMATE: (
        GameState.ROUND_ENDED,
        GameState.WAITING_FOR_RAISE_CALL_OR_FOLD,
    ),
    GameState.WAITING_FOR_RAISE_CALL_OR_FOLD: (GameState.ROUND_ENDED,),
    GameState.ROUND_ENDED: (
        GameState.GAME_ENDED,
        GameState.WAITING_FOR_ESTIMATE,
    ),
    GameState.GAME_ENDED: (),
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
    balance: int
    was_estimator_in_last_round: bool = False

    @staticmethod
    def create(username: str) -> "Player":
        return Player(
            username=username,
            balance=10,
        )

    def set_was_estimator_in_last_round(
        self, was_estimator_in_last_round: bool
    ) -> "Player":
        return replace(self, was_estimator_in_last_round=was_estimator_in_last_round)


@dataclass(frozen=True)
class Game:
    id: str
    current_state: GameState
    usernames: set[str]
    problem: Problem
    estimator: str | None
    prediction: Prediction | None
    current_player: str | None
    antes: dict[str, int]
    folded_players: set[str] = dataclasses.field(default_factory=set)
    want_to_play_again: set[str] = dataclasses.field(default_factory=set)

    @staticmethod
    def create() -> "Game":
        return Game(
            id=_generate_game_id(),
            current_state=GameState.WAITING_FOR_PLAYERS,
            usernames=set(),
            problem=_generate_problem(),
            estimator=None,
            prediction=None,
            current_player=None,
            antes={},
        )

    def join(self, username: str) -> "Game":
        if self.is_full():
            raise ValueError("Can't add another player since the game is full!")

        if not is_valid_username(username):
            raise ValueError(
                "Username must be a non-empty string of alphabetical characters!"
            )

        new_usernames = set([*self.usernames, username])
        old_antes = self.get_antes()
        new_antes = {**old_antes, username: 0}
        new_game = replace(self, usernames=new_usernames, antes=new_antes)

        if new_game.get_num_players() == 1:
            return new_game.set_estimator(username).set_current_player(username)

        return new_game.transition_to(GameState.WAITING_FOR_ESTIMATE)

    def contains(self, username: str) -> bool:
        return username in self.usernames

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

    def has_estimator(self) -> bool:
        return self.estimator is not None

    def get_prediction(self) -> Prediction | None:
        return self.prediction

    def set_prediction(self, prediction: Prediction | None) -> "Game":
        estimator = self.get_estimator()

        if estimator is None:
            raise ValueError("Can't set prediction if there is no estimator!")

        if not self.is_current_player(estimator):
            raise ValueError(
                "Can't set prediction if estimator is not the current player!"
            )

        return (
            replace(self, prediction=prediction)
            .set_ante(estimator, 1)
            .transition_to(GameState.WAITING_FOR_RAISE_CALL_OR_FOLD)
        )

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

    def is_current_player(self, username: str) -> bool:
        return self.get_current_player() == username

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

    def set_ante(self, username: str, new_ante: int) -> "Game":
        assert isinstance(username, str)
        assert isinstance(new_ante, int)

        if username not in self.usernames:
            raise ValueError("Can't set ante of a player that's not in the game!")

        if self.has_folded(username):
            raise ValueError("Can't set ante of a player who has folded!")

        if not self.has_prediction():
            raise ValueError("Can't set ante when no prediction has been made yet!")

        if new_ante < 0:
            raise ValueError("Ante must be non-negative!")

        if not self.is_current_player(username):
            raise ValueError("Can't set ante if it's not the player's turn!")

        opponent = self.get_opponent(username)

        if new_ante < self.get_ante(opponent):
            raise ValueError("Can't set ante to a value less than the opponent's ante!")

        new_antes = {**self.antes, username: new_ante}

        return replace(self, antes=new_antes).switch_turns()

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
        new_game = self.set_ante(username, oppoenents_ante).switch_turns()

        if self.get_ante(username) >= new_game.get_ante(username):
            raise ValueError(
                "Can't call ante when opponent's ante is less than or equal to yours!"
            )

        return new_game.transition_to(GameState.ROUND_ENDED)

    def has_called_ante(self, username: str) -> bool:
        if username not in self.usernames:
            raise ValueError(
                "Can't check if a player that's not in the game has called!"
            )

        for username in self.usernames:
            if self.has_folded(username):
                return False  # couldn't have called ante if other player folded

        antes = self.get_antes()
        values = antes.values()

        return len(set(values)) == 1

    def fold(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't fold a player that's not in the game!")

        if self.has_folded(username):
            raise ValueError("Can't fold a player who has already folded!")

        new_folded_players = set([*self.folded_players, username])
        new_game = replace(self, folded_players=new_folded_players).switch_turns()

        return new_game.transition_to(GameState.ROUND_ENDED)

    def has_folded(self, username: str) -> bool:
        if username not in self.usernames:
            raise ValueError(
                "Can't check if a player that's not in the game has folded!"
            )

        return username in self.folded_players

    def get_folded_players(self) -> set[str]:
        return self.folded_players

    def has_winner(self) -> bool:
        return (
            self.get_state() == GameState.ROUND_ENDED
            and self.get_prediction() is not None
        )

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

        if not self.has_winner():
            raise ValueError("Can't get payout if there is no winner!")

        prediction = self.get_prediction()

        assert prediction is not None

        if self.is_winner(username):
            return LOG_ERROR_TO_PAYOUT[prediction.log_error]

        return -LOG_ERROR_TO_PAYOUT[prediction.log_error]

    def get_problem(self) -> Problem:
        return self.problem

    def switch_turns(self) -> "Game":
        if self.current_player is None:
            raise ValueError("Can't switch turns if there is no current player!")

        new_current_player = self.get_opponent(self.current_player)

        return replace(self, current_player=new_current_player)

    def start_new_round(self) -> "Game":
        new_estimator = self.get_next_estimator()
        new_antes = {username: 0 for username in self.usernames}
        new_game = replace(
            self,
            problem=_generate_problem(),
            estimator=new_estimator,
            current_player=new_estimator,
            antes=new_antes,
            folded_players=set(),
            want_to_play_again=set(),
        )

        return new_game.transition_to(GameState.WAITING_FOR_ESTIMATE)

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
        return self.transition_to(GameState.GAME_ENDED)

    def is_game_over(self) -> bool:
        return self.get_state() == GameState.GAME_ENDED

    def play_again(self, username: str) -> "Game":
        if username not in self.usernames:
            raise ValueError("Can't play again if you're not in the game!")

        new_want_to_play_again = {*self.want_to_play_again, username}
        new_game = replace(self, want_to_play_again=new_want_to_play_again)

        if len(new_game.want_to_play_again) == 2:
            return new_game.start_new_round()

        return new_game


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

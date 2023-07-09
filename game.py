import random
import pandas as pd
import dataclasses

from dataclasses import dataclass, replace

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
    balance: int

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

    @staticmethod
    def create() -> "Game":
        return Game(
            id=_generate_game_id(),
            usernames=set(),
            problem=_generate_problem(),
            estimator=None,
            prediction=None,
            current_player=None,
            antes={},
        )

    def join(self, username: str) -> "Game":
        if not is_valid_username(username):
            raise ValueError(
                "Username must be a non-empty string of alphabetical characters!"
            )

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
        return self.is_full() and self.get_estimator() is not None

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
        
        return len(set(self.antes.values())) == 1

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

    def get_folded_players(self) -> set[str]:
        return self.folded_players

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

        if self.is_winner(username):
            return LOG_ERROR_TO_PAYOUT[prediction.log_error]

        return -LOG_ERROR_TO_PAYOUT[prediction.log_error]

    def start_new_round(self, new_problem: Problem) -> "Game":
        return Game(
            id=self.id,
            usernames=self.usernames,
            problem=new_problem,
            estimator=None,
            prediction=None,
            current_player=None,
            antes=dict(),
            folded_players=set(),
        )

    def get_problem(self) -> Problem:
        return self.problem

    def switch_turns(self) -> "Game":
        if self.current_player is None:
            raise ValueError("Can't switch turns if there is no current player!")

        new_current_player = self.get_opponent(self.current_player)

        return replace(self, current_player=new_current_player)
    
    def zero_antes(self) -> "Game":
        new_game = self

        for username in self.usernames:
            new_game = new_game.set_ante(username, 0)

        return new_game
    
    def reset_antes(self) -> "Game":
        estimator = self.get_estimator()

        if estimator is None:
            raise ValueError("Can't reset antes if there is no estimator!")

        return self.zero_antes().set_ante(estimator, 1)


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

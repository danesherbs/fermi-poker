import pytest

from game import Player, Game, Problem, Prediction


@pytest.fixture
def example_player_one() -> Player:
    return Player(
        username="test-player-one-id",
        balance=10,
    )


@pytest.fixture
def example_player_two() -> Player:
    return Player(
        username="test-player-two-id",
        balance=15,
    )


@pytest.fixture
def example_player_three() -> Player:
    return Player(
        username="test-player-three-id",
        balance=20,
    )


@pytest.fixture
def example_prediction() -> Prediction:
    return Prediction(
        log_answer=9,
        log_error=2,
    )


@pytest.fixture
def example_problem() -> Problem:
    return Problem(
        question="How many miles does an average commercial airplane fly in its lifetime?",
        log_answer=9,
        source="https://my-made-up-source.com",
    )


@pytest.fixture
def empty_game(example_problem: Problem) -> Game:
    return Game(
        id="test-game-id",
        usernames=set(),
        problem=example_problem,
        estimator=None,
        prediction=None,
        current_player=None,
        antes=dict(),
    )


def test_player_can_join_empty_waiting_room(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    new_game = empty_game.join(example_player_one.username)

    # Then
    assert new_game.contains(example_player_one.username)


def test_no_more_than_two_players_can_join_game(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
    example_player_three: Player,
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    with pytest.raises(ValueError):
        game_with_one_player.join(example_player_three.username)


def test_player_can_leave_game(empty_game: Game, example_player_one: Player) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)

    # When
    new_game = game_with_one_player.leave(example_player_one.username)

    # Then
    assert game_with_one_player.contains(example_player_one.username)
    assert not new_game.contains(example_player_one.username)


def test_player_cant_leave_game_if_they_are_not_in_it(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.leave(example_player_one.username)


def test_can_get_the_number_of_players_in_the_game(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)

    # When
    num_players = game_with_one_player.get_num_players()

    # Then
    assert num_players == 1


def test_can_get_if_game_is_full(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    is_full = game_with_two_players.is_full()

    # Then
    assert is_full


def test_can_get_if_player_is_waiting_for_another_player_to_join(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_two_players = game_with_one_player.join(example_player_two.username)

    # When / Then
    assert not empty_game.is_player_waiting()
    assert game_with_one_player.is_player_waiting()
    assert not game_with_two_players.is_player_waiting()


def test_can_set_the_estimator(empty_game: Game, example_player_one: Player) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)

    # When
    new_game = game_with_one_player.set_estimator(example_player_one.username)

    # Then
    assert new_game.estimator == example_player_one.username


def test_error_is_thrown_when_setting_estimator_to_player_not_in_game(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.set_estimator(example_player_one.username)


def test_can_get_the_estimator(empty_game: Game, example_player_one: Player) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_estimator = game_with_one_player.set_estimator(
        example_player_one.username
    )

    # When
    estimator = game_with_estimator.get_estimator()

    # Then
    assert estimator == example_player_one.username


def test_can_get_whether_or_not_game_is_ready_to_start(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_two_players = game_with_one_player.join(example_player_two.username)
    game_with_estimator = game_with_two_players.set_estimator(
        example_player_one.username
    )

    # When / Then
    assert not empty_game.is_ready_to_start()
    assert not game_with_one_player.is_ready_to_start()
    assert not game_with_two_players.is_ready_to_start()
    assert game_with_estimator.is_ready_to_start()


def test_estimator_can_submit_answer(
    empty_game: Game, example_player_one: Player, example_prediction: Prediction
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_estimator = game_with_one_player.set_estimator(
        example_player_one.username
    )

    # When
    new_game = game_with_estimator.set_prediction(example_prediction)

    # Then
    assert empty_game.get_prediction() is None
    assert new_game.get_prediction() == example_prediction


def test_can_get_whether_estimator_has_submitted_answer(
    empty_game: Game, example_player_one: Player, example_prediction: Prediction
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_estimator = game_with_one_player.set_estimator(
        example_player_one.username
    )
    game_with_estimate = game_with_estimator.set_prediction(example_prediction)

    # When / Then
    assert not empty_game.has_prediction()
    assert not game_with_one_player.has_prediction()
    assert not game_with_estimator.has_prediction()
    assert game_with_estimate.has_prediction()


def test_can_get_and_set_the_current_player(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    new_game = game_with_two_players.set_current_player(example_player_one.username)

    # Then
    assert empty_game.get_current_player() is None
    assert new_game.get_current_player() == example_player_one.username


def test_cant_set_current_player_to_non_existing_player(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.set_current_player(example_player_one.username)


def test_can_get_opponent_of_player(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    player_one_opponent = game_with_two_players.get_opponent(
        example_player_one.username
    )
    player_two_opponent = game_with_two_players.get_opponent(
        example_player_two.username
    )

    # Then
    assert player_one_opponent == example_player_two.username
    assert player_two_opponent == example_player_one.username


def test_error_is_thrown_when_getting_opponent_of_player_not_in_game(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.get_opponent(example_player_one.username)


def test_error_is_thrown_when_getting_opponent_of_player_with_one_player(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)

    # When
    with pytest.raises(ValueError):
        game_with_one_player.get_opponent(example_player_one.username)


def test_can_set_ante_of_player(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )
    ante = 100

    # When
    new_game = game_with_two_players.set_ante(example_player_one.username, ante)

    # Then
    assert new_game.get_ante(example_player_one.username) == ante


def test_error_is_thrown_when_getting_ante_of_player_not_in_game(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.get_ante(example_player_one.username)


def test_error_is_thrown_when_setting_ante_of_player_not_in_game(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.set_ante(example_player_one.username, 100)


def test_error_is_thrown_when_setting_ante_to_non_positive_number(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    with pytest.raises(ValueError):
        game_with_two_players.set_ante(example_player_one.username, 0)

    with pytest.raises(ValueError):
        game_with_two_players.set_ante(example_player_one.username, -10)


def test_that_players_ante_is_deleted_when_player_leaves_game(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    player_one_ante = 100
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
    )

    # When
    game_with_one_player = game_with_ante.leave(example_player_one.username)

    # Then
    assert example_player_one.username in game_with_ante.get_antes()
    assert example_player_one.username not in game_with_one_player.get_antes()


def test_that_player_can_raise_the_ante(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When
    new_game = game_with_ante.raise_ante(example_player_one.username)

    # Then
    assert new_game.get_ante(example_player_one.username) == player_two_ante + 1
    assert new_game.get_ante(example_player_two.username) == player_two_ante


def test_error_is_thrown_when_raising_ante_of_player_not_in_game(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
    example_player_three: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    with pytest.raises(ValueError):
        game.raise_ante(example_player_three.username)


def test_error_is_thrown_when_raising_ante_of_player_with_one_player(
    empty_game: Game,
    example_player_one: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username)

    # When
    with pytest.raises(ValueError):
        game.raise_ante(example_player_one.username)

def test_player_can_call_ante(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When
    new_game = game_with_ante.call_ante(example_player_one.username)

    # Then
    assert new_game.get_ante(example_player_one.username) == player_two_ante
    assert new_game.get_ante(example_player_two.username) == player_two_ante

def test_error_is_thrown_when_calling_ante_but_opponents_amount_is_lower(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When
    with pytest.raises(ValueError):
        game_with_ante.call_ante(example_player_two.username)

def test_error_is_thrown_when_raising_ante_but_opponents_ante_is_lower_or_equal(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When
    with pytest.raises(ValueError):
        game_with_ante.raise_ante(example_player_two.username)

def test_player_can_fold(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game_with_ante = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When
    new_game = game_with_ante.fold(example_player_one.username)

    # Then
    assert new_game.get_ante(example_player_one.username) == 0
    assert new_game.get_ante(example_player_two.username) == player_two_ante

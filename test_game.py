import pytest

from game import Player, Game, Problem, Prediction


@pytest.fixture
def example_player_one() -> Player:
    return Player(
        username="testplayeroneid",
        balance=10,
    )


@pytest.fixture
def example_player_two() -> Player:
    return Player(
        username="testplayertwoid",
        balance=15,
    )


@pytest.fixture
def example_player_three() -> Player:
    return Player(
        username="testplayerthreeid",
        balance=20,
    )


@pytest.fixture
def example_problem() -> Problem:
    return Problem(
        question="How many miles does an average commercial airplane fly in its lifetime?",
        log_answer=9,
        source="https://my-made-up-source.com",
    )


@pytest.fixture
def example_other_problem() -> Problem:
    return Problem(
        question="How many times does a human heart beat in an average lifetime?",
        log_answer=7,
        source="https://my-other-made-up-source.com",
    )


@pytest.fixture
def example_correct_prediction(example_problem: Problem) -> Prediction:
    return Prediction(
        log_answer=example_problem.log_answer,
        log_error=2,
    )


@pytest.fixture
def example_incorrect_prediction(example_problem: Problem) -> Prediction:
    return Prediction(
        log_answer=example_problem.log_answer + 3,
        log_error=1,
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


def test_player_must_have_valid_username(empty_game: Game) -> None:
    # Given / When
    with pytest.raises(ValueError):
        empty_game.join("")

    with pytest.raises(ValueError):
        empty_game.join(" ")

    with pytest.raises(ValueError):
        empty_game.join(1)  # type: ignore


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


def test_player_cant_leave_game_if_they_have_placed_an_ante(
    empty_game: Game, example_player_one: Player
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_ante = game_with_one_player.set_ante(example_player_one.username, 1)

    # When
    with pytest.raises(ValueError):
        game_with_ante.leave(example_player_one.username)

    game_with_one_player.leave(example_player_one.username)


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
    empty_game: Game, example_player_one: Player, example_correct_prediction: Prediction
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_estimator = game_with_one_player.set_estimator(
        example_player_one.username
    )

    # When
    new_game = game_with_estimator.set_prediction(example_correct_prediction)

    # Then
    assert empty_game.get_prediction() is None
    assert new_game.get_prediction() == example_correct_prediction


def test_can_get_whether_estimator_has_submitted_answer(
    empty_game: Game, example_player_one: Player, example_correct_prediction: Prediction
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)
    game_with_estimator = game_with_one_player.set_estimator(
        example_player_one.username
    )
    game_with_estimate = game_with_estimator.set_prediction(example_correct_prediction)

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
        game_with_two_players.set_ante(example_player_one.username, -10)


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


def test_can_get_whether_player_has_called_ante(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = 4
    player_two_ante = 5
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, player_one_ante)
        .set_ante(example_player_two.username, player_two_ante)
    )

    # When / Then
    assert not game.has_called_ante(example_player_one.username)
    assert game.has_called_ante(example_player_two.username)


def test_error_is_thrown_when_checking_if_player_has_called_ante_but_player_not_in_game(
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
        game.has_called_ante(example_player_three.username)


def test_player_folding_marks_them_as_folded(
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
    assert new_game.has_folded(example_player_one.username)
    assert not new_game.has_folded(example_player_two.username)


def test_error_is_thrown_when_checking_if_player_has_folded_but_player_not_in_game(
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
        game.has_folded(example_player_three.username)


def test_error_is_thrown_when_player_not_in_game_folds(
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
        game.fold(example_player_three.username)


def test_error_is_thrown_when_player_folds_for_second_time(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    game = game.fold(example_player_one.username)

    # Then
    with pytest.raises(ValueError):
        game.fold(example_player_one.username)


def test_error_is_thrown_when_setting_ante_of_folded_player(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When
    game = game.fold(example_player_one.username)

    # Then
    with pytest.raises(ValueError):
        game.set_ante(example_player_one.username, 5)


def test_error_is_thrown_when_folded_player_calls_ante(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_ante(example_player_one.username, 5)
    )

    # When
    game = game.fold(example_player_one.username)

    # Then
    with pytest.raises(ValueError):
        game.call_ante(example_player_one.username)


def test_error_is_thrown_when_getting_ante_of_player_that_hasnt_placed_ante(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When / Then
    with pytest.raises(ValueError):
        game.get_ante(example_player_one.username)


def test_has_winner_is_true_when_estimator_has_submitted_answer(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When / Then

    # Then
    assert not empty_game.has_winner()
    assert game.has_winner()


def test_has_winner_is_false_when_estimator_has_not_submitted_answer(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
    )

    # When / Then
    assert not empty_game.has_winner()
    assert not game.has_winner()


def test_is_winner_is_estimator_when_prediction_is_correct(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When / Then
    assert not empty_game.has_winner()
    assert game.has_winner()
    assert game.is_winner(example_player_one.username)
    assert not game.is_winner(example_player_two.username)


def test_is_winner_is_estimatee_when_prediction_is_incorrect(
    empty_game: Game,
    example_incorrect_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_incorrect_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When / Then
    assert not empty_game.has_winner()
    assert game.has_winner()
    assert not game.is_winner(example_player_one.username)
    assert game.is_winner(example_player_two.username)


def test_get_payout_throws_an_error_when_the_game_has_no_winner(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
    )

    # When / Then
    assert not game.has_winner()

    with pytest.raises(ValueError):
        game.get_payout(example_player_one.username)


def test_error_is_thrown_when_getting_payout_of_non_existent_user(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
    example_player_three: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When / Then
    assert game.has_winner()

    with pytest.raises(ValueError):
        game.get_payout(example_player_three.username)


def test_starting_new_round_generates_game_with_unset_game_state(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
    example_other_problem: Problem,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
        .set_current_player(example_player_one.username)
    )

    # When
    new_game = game.start_new_round(example_other_problem)

    # Then
    assert game.get_problem() != example_other_problem
    assert new_game.get_problem() == example_other_problem

    assert game.get_estimator() == example_player_one.username
    assert new_game.get_estimator() is None

    assert game.get_prediction() == example_correct_prediction
    assert new_game.get_prediction() is None

    assert game.get_current_player() == example_player_one.username
    assert new_game.get_current_player() is None

    assert len(game.get_antes()) == 2
    assert len(new_game.get_antes()) == 0

    assert len(game.get_folded_players()) == 0
    assert len(new_game.get_folded_players()) == 0


def test_switch_turns_changes_current_player_to_opponent(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
        .set_current_player(example_player_one.username)
    )

    # When
    new_game = game.switch_turns()

    # Then
    assert game.get_current_player() == example_player_one.username
    assert new_game.get_current_player() == example_player_two.username


def test_error_is_thrown_when_switching_turns_without_current_player(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When / Then
    with pytest.raises(ValueError):
        game.switch_turns()


def test_zero_antes_sets_antes_of_all_players_to_zero(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When
    new_game = game.zero_antes()

    # Then
    assert game.get_antes() == {
        example_player_one.username: 5,
        example_player_two.username: 5,
    }

    assert new_game.get_antes() == {
        example_player_one.username: 0,
        example_player_two.username: 0,
    }


def test_zero_antes_throws_error_if_player_has_folded(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
        .fold(example_player_two.username)
    )

    # When / Then
    with pytest.raises(ValueError):
        game.zero_antes()


def test_reset_antes_sets_estimators_ante_to_one_and_other_to_zero(
    empty_game: Game,
    example_correct_prediction: Prediction,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_two.username)
        .set_prediction(example_correct_prediction)
        .set_ante(example_player_one.username, 5)
        .set_ante(example_player_two.username, 0)
        .call_ante(example_player_two.username)
    )

    # When
    new_game = game.reset_antes()

    # Then
    assert game.get_antes() == {
        example_player_one.username: 5,
        example_player_two.username: 5,
    }

    assert new_game.get_antes() == {
        example_player_one.username: 0,
        example_player_two.username: 1,
    }


def test_reset_antes_throws_error_when_estimator_is_not_set(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    new_game = game.set_estimator(example_player_one.username)

    # When / Then
    with pytest.raises(ValueError):
        game.reset_antes()

    new_game.reset_antes()

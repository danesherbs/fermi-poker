import pytest

from game import Player, Game, GameState, Problem, Estimate


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
def example_correct_prediction(example_problem: Problem) -> Estimate:
    return Estimate(
        log_answer=example_problem.log_answer,
        log_error=2,
    )


@pytest.fixture
def example_incorrect_prediction(example_problem: Problem) -> Estimate:
    return Estimate(
        log_answer=example_problem.log_answer + 3,
        log_error=1,
    )


@pytest.fixture
def empty_game(example_problem: Problem) -> Game:
    return Game(
        id="test-game-id",
        current_state=GameState.WAITING_FOR_PLAYERS,
        usernames=set(),
        problem=example_problem,
        estimator=None,
        estimate=None,
        current_player=None,
        antes=dict(),
    )


@pytest.fixture
def game_waiting_for_estimate(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> Game:
    return empty_game.join(example_player_one.username).join(
        example_player_two.username
    )


@pytest.fixture
def game_waiting_for_raise_call_or_fold(
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
) -> Game:
    return game_waiting_for_estimate.set_estimate(example_correct_prediction)


@pytest.fixture
def game_with_round_ended(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> Game:
    return game_waiting_for_raise_call_or_fold.fold(example_player_two.username)


@pytest.fixture
def game_with_correct_estimate(
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
) -> Game:
    return game_waiting_for_estimate.set_estimate(example_correct_prediction)


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


def test_player_cant_place_ante_if_theres_no_prediction_made(
    empty_game: Game, example_player_one: Player, example_player_two: Player
) -> None:
    # Given
    game_with_one_player = (
        empty_game.join(example_player_one.username)
        .join(example_player_two.username)
        .set_estimator(example_player_one.username)
    )

    # When
    with pytest.raises(ValueError):
        game_with_one_player.set_ante(example_player_one.username, 1)


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


def test_can_get_whether_estimator_has_submitted_answer(
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
) -> None:
    # Given
    game_with_estimate = game_waiting_for_estimate.set_estimate(
        example_correct_prediction
    )

    # When / Then
    assert not game_waiting_for_estimate.has_estimate()
    assert game_with_estimate.has_estimate()
    assert game_with_estimate.get_esimate() == example_correct_prediction


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
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> None:
    # Given
    new_ante = 100

    # When
    new_game = game_waiting_for_raise_call_or_fold.set_ante(
        example_player_two.username,
        new_ante,
    )

    # Then
    assert new_game.get_ante(example_player_two.username) == new_ante


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
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = game_waiting_for_raise_call_or_fold.get_ante(
        example_player_one.username
    )
    player_two_ante = game_waiting_for_raise_call_or_fold.get_ante(
        example_player_two.username
    )

    # When
    new_game = game_waiting_for_raise_call_or_fold.raise_ante(
        example_player_two.username
    )

    # Then
    assert (
        game_waiting_for_raise_call_or_fold.get_ante(example_player_one.username)
        != player_two_ante
    )
    assert new_game.get_ante(example_player_two.username) == player_one_ante + 1
    assert new_game.get_ante(example_player_one.username) == player_one_ante


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
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    player_one_ante = game_waiting_for_raise_call_or_fold.get_ante(
        example_player_one.username
    )

    # When
    new_game = game_waiting_for_raise_call_or_fold.call_ante(
        example_player_two.username
    )

    # Then
    assert new_game.get_ante(example_player_one.username) == player_one_ante
    assert new_game.get_ante(example_player_two.username) == player_one_ante


def test_error_is_thrown_when_setting_ante_lower_than_opponents_amount(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> None:
    # When / Then
    with pytest.raises(ValueError):
        game_waiting_for_raise_call_or_fold.set_ante(example_player_two.username, 0)


def test_error_is_thrown_when_raising_ante_but_opponents_ante_is_lower_or_equal(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
) -> None:
    # Given
    new_game = game_waiting_for_raise_call_or_fold.switch_turns()

    # When
    with pytest.raises(ValueError):
        new_game.raise_ante(example_player_one.username)


def test_can_get_whether_player_has_called_ante(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    new_game = game_waiting_for_raise_call_or_fold.call_ante(
        example_player_two.username
    )

    # When / Then
    assert not game_waiting_for_raise_call_or_fold.has_called_ante(
        example_player_one.username
    )
    assert not game_waiting_for_raise_call_or_fold.has_called_ante(
        example_player_two.username
    )
    assert new_game.has_called_ante(example_player_one.username)
    assert new_game.has_called_ante(example_player_two.username)


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
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_raise_call_or_fold.fold(example_player_two.username)

    # Then
    assert not new_game.has_folded(example_player_one.username)
    assert new_game.has_folded(example_player_two.username)


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
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_raise_call_or_fold.fold(example_player_two.username)

    # Then
    with pytest.raises(ValueError):
        new_game.call_ante(example_player_one.username)


def test_antes_of_both_players_is_zero_before_prediction(
    game_waiting_for_estimate: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    player_one_ante = game_waiting_for_estimate.get_ante(example_player_one.username)
    player_two_ante = game_waiting_for_estimate.get_ante(example_player_two.username)

    # Then
    assert player_one_ante == 0
    assert player_two_ante == 0


def test_has_winner_is_true_when_estimator_has_submitted_answer(
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_estimate.set_estimate(
        example_correct_prediction
    ).call_ante(example_player_two.username)

    # Then
    assert not game_waiting_for_estimate.has_winner()
    assert new_game.has_winner()


def test_has_winner_is_false_when_estimator_has_not_submitted_answer(
    empty_game: Game,
    example_correct_prediction: Estimate,
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
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_estimate.set_estimate(
        example_correct_prediction
    ).call_ante(example_player_two.username)

    # Then
    assert not game_waiting_for_estimate.has_winner()
    assert new_game.has_winner()
    assert new_game.is_winner(example_player_one.username)
    assert not new_game.is_winner(example_player_two.username)


def test_is_winner_is_estimatee_when_prediction_is_incorrect(
    game_waiting_for_estimate: Game,
    example_incorrect_prediction: Estimate,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_estimate.set_estimate(
        example_incorrect_prediction
    ).call_ante(example_player_two.username)

    # Then
    assert not game_waiting_for_estimate.has_winner()
    assert new_game.has_winner()
    assert not new_game.is_winner(example_player_one.username)
    assert new_game.is_winner(example_player_two.username)


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
    game_with_round_ended: Game,
    example_player_three: Player,
) -> None:
    # When / Then
    with pytest.raises(ValueError):
        game_with_round_ended.get_payout(example_player_three.username)


def test_switch_turns_changes_current_player_to_opponent(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # When
    new_game = game_waiting_for_raise_call_or_fold.switch_turns()

    # Then
    assert (
        game_waiting_for_raise_call_or_fold.get_current_player()
        == example_player_two.username
    )
    assert new_game.get_current_player() == example_player_one.username


def test_error_is_thrown_when_switching_turns_without_current_player(
    empty_game: Game,
) -> None:
    # When / Then
    with pytest.raises(ValueError):
        empty_game.switch_turns()


def test_game_with_one_player_still_has_state_waiting_for_player(
    empty_game: Game,
    example_player_one: Player,
) -> None:
    # Given
    game_with_one_player = empty_game.join(example_player_one.username)

    # When / Then
    assert empty_game.get_state() == GameState.WAITING_FOR_PLAYERS
    assert game_with_one_player.get_state() == GameState.WAITING_FOR_PLAYERS


def test_two_players_joining_empty_game_changes_state_to_waiting_for_estimate(
    empty_game: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    game_with_two_players = empty_game.join(example_player_one.username).join(
        example_player_two.username
    )

    # When / Then
    assert empty_game.get_state() == GameState.WAITING_FOR_PLAYERS
    assert game_with_two_players.get_state() == GameState.WAITING_FOR_ESTIMATE


def test_game_waiting_for_estimate_transitions_to_waiting_for_raise_etc_when_estimate_is_given(
    game_waiting_for_estimate: Game,
    example_correct_prediction: Estimate,
) -> None:
    # Given
    new_game = game_waiting_for_estimate.set_estimate(example_correct_prediction)

    # When / Then
    assert game_waiting_for_estimate.get_state() == GameState.WAITING_FOR_ESTIMATE
    assert new_game.get_state() == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD


def test_game_waiting_for_raise_call_or_fold_transitions_to_waiting_for_raise_when_player_raises(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> None:
    # Given
    new_game = game_waiting_for_raise_call_or_fold.raise_ante(
        example_player_two.username
    )

    # When / Then
    assert (
        game_waiting_for_raise_call_or_fold.get_state()
        == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD
    )
    assert new_game.get_state() == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD


def test_game_waiting_for_raise_call_or_fold_transitions_to_round_ended_when_player_folds(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> None:
    # Given
    new_game = game_waiting_for_raise_call_or_fold.fold(example_player_two.username)

    # When / Then
    assert (
        game_waiting_for_raise_call_or_fold.get_state()
        == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD
    )
    assert new_game.get_state() == GameState.ROUND_ENDED


def test_game_waiting_for_raise_call_or_fold_transitions_to_round_ended_when_player_calls(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_two: Player,
) -> None:
    # Given
    new_game = game_waiting_for_raise_call_or_fold.call_ante(
        example_player_two.username
    )

    # When / Then
    assert (
        game_waiting_for_raise_call_or_fold.get_state()
        == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD
    )
    assert new_game.get_state() == GameState.ROUND_ENDED


def test_game_waiting_for_raise_call_or_fold_transitions_to_round_ended_when_multiple_players_call_and_raise(
    game_waiting_for_raise_call_or_fold: Game,
    example_player_one: Player,
    example_player_two: Player,
) -> None:
    # Given
    new_game = (
        game_waiting_for_raise_call_or_fold.raise_ante(example_player_two.username)
        .raise_ante(example_player_one.username)
        .call_ante(example_player_two.username)
    )

    # When / Then
    assert (
        game_waiting_for_raise_call_or_fold.get_state()
        == GameState.WAITING_FOR_RAISE_CALL_OR_FOLD
    )
    assert new_game.get_state() == GameState.ROUND_ENDED


def test_game_with_round_ended_transitions_to_ended_when_end_is_called(
    game_with_round_ended: Game,
) -> None:
    # Given
    new_game = game_with_round_ended.end()

    # When / Then
    assert game_with_round_ended.get_state() == GameState.ROUND_ENDED
    assert new_game.get_state() == GameState.GAME_ENDED


def test_game_with_round_ended_transitions_to_waiting_for_estimate_when_reset_antes_is_called(
    game_with_round_ended: Game,
) -> None:
    # Given
    new_game = game_with_round_ended._start_new_round()

    # When / Then
    assert game_with_round_ended.get_state() == GameState.ROUND_ENDED
    assert new_game.get_state() == GameState.WAITING_FOR_ESTIMATE

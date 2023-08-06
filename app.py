from flask import Flask, render_template, request, session, jsonify, Response
from typing import Dict
from game import (
    Game,
    GameState,
    Player,
    is_valid_username,
    is_valid_game_id,
    Prediction,
    InvalidStateException,
)


app = Flask(__name__)
app.secret_key = "super secret key"
games: Dict[str, Game] = {}
players: Dict[str, Player] = {}
seen_outcome_counter: Dict[str, int] = {}


@app.route("/")
def home() -> str:
    username = session.get("username", None)

    if username is None:
        return render_template("login.html")

    return render_template("start.html", username=username)


@app.route("/game/<game_id>", methods=["GET"])
def start_game(game_id: str) -> str:
    if game_id not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    username = session.get("username", None)

    if username is None:
        return render_template("error.html", message=f"User not logged in!")

    game = games[game_id]

    if username not in players:
        players[username] = Player.create(username)

    player = players[username]
    problem = game.get_problem()

    if game.is_estimator(username):
        return render_template(
            "estimator.html",
            game_id=game_id,
            balance=player.balance,
            problem=problem.question,
        )

    return render_template(
        "estimatee.html",
        game_id=game_id,
        balance=player.balance,
        problem=problem.question,
    )


@app.route("/game/<game_id>/waiting-room", methods=["GET"])
def join_waiting_room(game_id: str) -> str:
    if not is_valid_game_id(game_id):
        return render_template("error.html", message=f"Game ID not valid!")

    if game_id.upper() not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    username = session.get("username", None)

    if username is None:
        return render_template("error.html", message=f"User not logged in!")

    return render_template("waiting-room.html", game_id=game_id)


@app.route("/game/<game_id>/raise-call-or-fold")
def raise_call_or_fold(game_id: str) -> str:
    if game_id not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    username = session.get("username", None)

    if username is None:
        return render_template("error.html", message=f"User not logged in!")

    assert is_valid_username(username)

    game = games[game_id]

    if username not in players:
        return render_template(
            "error.html", message=f"Can't get outcome for non-existent user!"
        )

    player = players[username]

    try:
        prediction = game.get_prediction()
        actual_log_answer = prediction.log_answer  # type: ignore
        actual_log_error = prediction.log_error  # type: ignore
        problem = game.get_problem()
        is_estimator = game.is_estimator(username)
        is_your_turn = game.is_current_player(username)
        opponent = game.get_opponent(username)
        opponents_ante = game.get_ante(opponent)
        your_ante = game.get_ante(username)
    except (ValueError, TypeError) as e:
        return render_template("error.html", message=str(e))

    return render_template(
        "raise-call-or-fold.html",
        is_your_turn=is_your_turn,
        balance=player.balance,
        problem=problem.question,
        is_estimator=is_estimator,
        estimate=actual_log_answer,
        error=actual_log_error,
        ante=your_ante,
        opponents_ante=opponents_ante,
        game_id=game_id,
    )


@app.route("/game/<game_id>/play-again", methods=["GET"])
def play_again(game_id: str) -> str:
    if game_id not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    return render_template("play-again.html", game_id=game_id)


@app.route("/game/<game_id>/outcome", methods=["GET"])
def show_outcome(game_id: str) -> str:
    if game_id not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    username = session.get("username", None)

    if username is None:
        return render_template("error.html", message=f"User not logged in!")

    if username not in players:
        return render_template(
            "error.html", message=f"Can't get outcome for non-existent user!"
        )

    player = players[username]
    game = games[game_id]

    try:
        balance = player.balance
        prediction = game.get_prediction()
        actual_log_answer = prediction.log_answer  # type: ignore
        actual_log_error = prediction.log_error  # type: ignore
        problem = game.get_problem()
        question = problem.question
        expected_log_answer = problem.log_answer
        is_estimator = game.is_estimator(username)
        payout = game.get_payout(username)
        is_winner = game.is_winner(username)
    except ValueError as e:
        return render_template("error.html", message=str(e))

    return render_template(
        "outcome.html",
        game_id=game_id,
        balance=balance,
        problem=question,
        estimate=actual_log_answer,
        error=actual_log_error,
        is_estimator=is_estimator,
        expected_oom=expected_log_answer,
        payout=abs(payout),
        you_won=is_winner,
        source=game.problem.source,
    )


@app.route("/api/login", methods=["POST"])
def login() -> Response:
    username = request.json["username"]  # type: ignore

    if not is_valid_username(username):
        return jsonify(
            {
                "success": False,
                "message": "Username must be a non-empty string!",
            }
        )

    session["username"] = username

    if username not in players:
        players[username] = Player.create(username)

    return jsonify(
        {
            "success": True,
            "message": f"Successfully logged in as {username}",
        }
    )


@app.route("/api/logout", methods=["GET"])
def logout() -> Response:
    username = session.get("username", None)

    if username is None:
        return jsonify(
            {
                "success": False,
                "message": "User wasn't logged in!",
            }
        )

    del session["username"]

    return jsonify(
        {
            "success": True,
            "message": f"Successfully logged out",
        }
    )


@app.route("/api/create", methods=["GET"])
def create_game() -> Response:
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    if username not in players:
        return jsonify({"success": False, "message": "User doesn't exist!"})

    game = Game.create().join(username)
    games[game.id] = game

    return jsonify(
        {
            "success": True,
            "message": f"Successfully created game",
            "game_id": game.id,
        }
    )


@app.route("/api/join", methods=["POST"])
def join_game() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    if username not in players:
        return jsonify({"success": False, "message": "User doesn't exist!"})

    player = players[username]
    game = games[game_id]

    try:
        new_game = game.join(player.username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify({"success": True, "message": f"Successfully joined game {game_id}"})


@app.route("/api/game/<game_id>/has-estimate", methods=["GET"])
def has_estimate(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    has_estimate = game.has_prediction()

    return jsonify({"success": True, "has_estimate": has_estimate})


@app.route("/api/fold", methods=["POST"])
def fold() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    game = games[game_id]

    try:
        new_game = game.fold(username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully folded"})


@app.route("/api/set-prediction", methods=["POST"])
def set_prediction() -> Response:
    game_id = request.json["game_id"]  # type: ignore
    log_answer = int(request.json["estimate"])  # type: ignore
    log_error = int(request.json["error"])  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    game = games[game_id]
    prediction = Prediction(
        log_answer=log_answer,
        log_error=log_error,
    )

    try:
        new_game = game.set_prediction(prediction)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully submitted estimate"})


@app.route("/api/raise", methods=["POST"])
def raise_ante() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    game = games[game_id]

    try:
        new_game = game.raise_ante(username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully raised ante"})


@app.route("/api/call", methods=["POST"])
def call_ante() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    game = games[game_id]

    try:
        new_game = game.call_ante(username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully called ante"})


@app.route("/api/play-again", methods=["POST"])
def to_play_or_not_to_play() -> Response:
    game_id = request.json["game_id"]  # type: ignore
    play_again = request.json["play_again"]  # type: ignore

    print(f"{play_again=} {type(play_again)}")

    if game_id not in games:
        return jsonify({"success": False, "message": "Game not found!"})

    username = session.get("username", None)

    if username is None:
        return jsonify(
            {
                "success": False,
                "message": f"User '{username}' not logged in!",
            }
        )

    game = games[game_id]

    try:
        if play_again:
            print("playing again")
            new_game = game.play_again(username)
        else:
            new_game = game.end()
    except (InvalidStateException, ValueError) as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    return jsonify(
        {
            "success": True,
            "message": "Successfully submitted play again decision",
        }
    )


@app.route("/api/game/<game_id>/is-your-turn", methods=["GET"])
def get_is_my_turn(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game not found"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    try:
        is_your_turn = game.is_current_player(username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify({"success": True, "is_your_turn": is_your_turn})


@app.route("/api/game/<game_id>/has-opponent-called", methods=["GET"])
def has_opponent_called(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    try:
        opponent = game.get_opponent(username)
        has_called = game.has_called_ante(opponent)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify({"success": True, "has_called": has_called})


@app.route("/api/game/<game_id>/has-opponent-folded", methods=["GET"])
def has_opponent_folded(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    try:
        opponent = game.get_opponent(username)
        has_folded = game.has_folded(opponent)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify({"success": True, "has_folded": has_folded})


@app.route("/api/game/<game_id>/is-waiting-for-players", methods=["GET"])
def is_ready_to_start(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    try:
        is_waiting_for_players = game.get_state() == GameState.WAITING_FOR_PLAYERS
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify({"success": True, "is_waiting_for_players": is_waiting_for_players})


@app.route("/api/game/<game_id>/is-game-over", methods=["GET"])
def is_game_over(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    try:
        is_game_over = game.is_game_over()
        opponent_has_responded = game.get_state() in [
            GameState.GAME_ENDED,
            GameState.WAITING_FOR_ESTIMATE,
        ]
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify(
        {
            "success": True,
            "is_game_over": is_game_over,
            "opponent_has_responded": opponent_has_responded,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)

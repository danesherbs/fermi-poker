from flask import Flask, render_template, request, session, jsonify, Response
from typing import Dict
from game import (
    Game,
    GameState,
    Player,
    is_valid_username,
    Estimate,
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


@app.route("/instructions")
def view_instructions() -> str:
    return render_template("instructions.html")


@app.route("/game/<game_id>", methods=["GET"])
def view_game(game_id: str) -> str:
    if game_id not in games:
        return render_template("error.html", message=f"Game ID doesn't exist!")

    username = session.get("username", None)

    if username is None:
        return render_template("error.html", message=f"User not logged in!")

    game = games[game_id]

    if username not in players:
        players[username] = Player.create(username)

    player = players[username]
    state = game.get_state()

    if state == GameState.GAME_IS_EMPTY:
        return render_template(
            "waiting-room.html",
            game_id=game_id,
            state=game.get_state(),
        )

    if state == GameState.WAITING_FOR_ANOTHER_PLAYER:
        return render_template(
            "waiting-room.html",
            game_id=game_id,
            state=game.get_state(),
        )

    opponent = game.get_opponent(username)
    problem = game.get_problem()

    if state == GameState.WAITING_FOR_ESTIMATE and game.is_estimator(username):
        return render_template(
            "estimator.html",
            game_id=game_id,
            balance=player.balance,
            problem=problem.question,
        )

    if state == GameState.WAITING_FOR_ESTIMATE and not game.is_estimator(username):
        return render_template(
            "estimatee.html",
            game_id=game_id,
            balance=player.balance,
            problem=problem.question,
            state=game.get_state(),
        )

    if state in [
        GameState.WAITING_FOR_ESTIMATEE_TO_RAISE_CALL_OR_FOLD,
        GameState.WAITING_FOR_ESTIMATOR_TO_RAISE_CALL_OR_FOLD,
    ]:
        instruction = (
            "Raise, call or fold"
            if game.is_current_player(username)
            else "Wait for opponent to raise, call or fold"
        )

        estimate_header = (
            "Estimate" if game.is_estimator(username) else "Opponent's estimate"
        )

        return render_template(
            "raise-call-or-fold.html",
            balance=player.balance,
            problem=problem.question,
            estimate=game.estimate.log_answer,  # type: ignore
            error=game.estimate.log_error,  # type: ignore
            ante=game.get_ante(username),
            opponents_ante=game.get_ante(opponent),
            game_id=game_id,
            state=game.get_state(),
            instruction=instruction,
            estimate_header=estimate_header,
            show_buttons=game.is_current_player(username),
        )

    if state in [
        GameState.ESTIMATEE_FOLDED,
        GameState.ESTIMATOR_FOLDED,
        GameState.BOTH_PLAYERS_CALLED,
    ]:
        log_estimate = game.estimate.log_answer if game.has_estimate() else None  # type: ignore
        log_error = game.estimate.log_error if game.has_estimate() else None  # type: ignore

        return render_template(
            "outcome.html",
            game_id=game_id,
            balance=player.balance,
            problem=game.problem.question,
            has_estimate=game.has_estimate(),
            estimate=log_estimate,
            error=log_error,
            is_estimator=game.is_estimator(username),
            expected_oom=game.problem.log_answer,
            payout=abs(game.get_payout(username)),
            you_won=game.is_winner(username),
            source=game.problem.source,
            state=game.get_state(),
        )

    if state == GameState.A_PLAYER_WANTS_TO_PLAY_AGAIN:
        return render_template(
            "play-again.html",
            game_id=game_id,
            state=game.get_state(),
        )

    if state == GameState.GAME_OVER:
        return render_template(
            "game-over.html",
            game_id=game_id,
            state=game.get_state(),
        )

    return render_template("error.html", message=f"Unknown game state {state}!")


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
    estimate = Estimate(
        log_answer=log_answer,
        log_error=log_error,
    )

    try:
        new_game = game.set_estimate(estimate)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    print(f"{new_game.get_esimate()=}")

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

    opponent = game.get_opponent(username)

    new_username_balance = players[username].balance + new_game.get_payout(username)
    new_opponent_balance = players[opponent].balance + new_game.get_payout(opponent)

    players[username] = players[username].set_balance(new_username_balance)
    players[opponent] = players[opponent].set_balance(new_opponent_balance)

    return jsonify({"success": True, "message": "Successfully called ante"})


@app.route("/api/fold", methods=["POST"])
def fold() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game ID doesn't exist!"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    game = games[game_id]

    try:
        new_game = game.fold(username)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    games[game_id] = new_game

    opponent = game.get_opponent(username)

    new_username_balance = players[username].balance + new_game.get_payout(username)
    new_opponent_balance = players[opponent].balance + new_game.get_payout(opponent)

    players[username] = players[username].set_balance(new_username_balance)
    players[opponent] = players[opponent].set_balance(new_opponent_balance)

    return jsonify({"success": True, "message": "Successfully folded"})


@app.route("/api/play-again", methods=["POST"])
def to_play_or_not_to_play() -> Response:
    game_id = request.json["game_id"]  # type: ignore
    play_again = request.json["play_again"]  # type: ignore

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
        new_game = game.play_again(username)

        if not play_again:
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


@app.route("/api/game/<game_id>/state", methods=["GET"])
def get_state(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    state = str(game.get_state())

    return jsonify({"success": True, "state": state})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

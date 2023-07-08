from dataclasses import asdict
from flask import Flask, render_template, request, session, jsonify, Response
from typing import Dict
from game import Game, Player, is_valid_username, is_valid_game_id


app = Flask(__name__)
app.secret_key = "super secret key"
games: Dict[str, Game] = {}
players: Dict[str, Player] = {}


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

    if game.get_number_of_players() != 2:
        return render_template(
            "error.html", message=f"Game must have two players to play!"
        )

    player = game.get_player(username)
    problem = "How many beats will your heart make in a lifetime?"

    if game.is_estimator(username):
        return render_template(
            "estimator.html",
            game_id=game_id,
            balance=player.balance,
            problem=problem,
        )

    return render_template(
        "estimatee.html",
        game_id=game_id,
        balance=player.balance,
        problem=problem,
    )


@app.route("/game/<game_id>/waiting-room", methods=["GET"])
def join_waiting_room(game_id: str) -> str:
    if game_id not in games:
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

    player = game.get_player(username)
    opponent = game.get_opponent(username)

    if opponent is None:
        return render_template(
            "error.html",
            message=f"Can't raise, call or fold until opponent joins!",
        )

    is_your_turn = game.is_players_turn(username)
    problem = "How many beats will your heart make in a lifetime?"
    is_estimator = game.is_estimator(username)
    estimate = game.get_estimate()
    error = game.get_error()
    ante = game.get_ante(username)
    opponents_ante = game.get_ante(opponent.username)

    if estimate is None or error is None:
        return render_template(
            "error.html",
            message=f"Can't raise, call or fold until the estimate and error have been set!",
        )

    return render_template(
        "raise-call-or-fold.html",
        is_your_turn=is_your_turn,
        balance=player.balance,
        problem=problem,
        is_estimator=is_estimator,
        estimate=estimate,
        error=error,
        ante=ante,
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
    
    game = games[game_id]
    player = game.get_player(username)
    balance = player.balance
    problem = game.problem
    estimate = game.get_estimate()
    error = game.get_error()
    is_estimator = game.is_estimator(username)

    assert estimate is not None
    assert error is not None

    opponent = game.get_opponent(username)
    
    assert opponent is not None

    expected_oom = game.expected_oom
    payout = game.get_payout()
    you_won = game.is_winner(username)
    
    return render_template(
        "outcome.html",
        game_id=game_id,
        balance=balance,
        problem=problem,
        estimate=estimate,
        error=error,
        is_estimator=is_estimator,
        expected_oom=expected_oom,
        payout=abs(payout),
        you_won=you_won,
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

    if not is_valid_username(username):
        return jsonify(
            {
                "success": False,
                "message": "Username must be a non-empty string!",
            }
        )

    player = Player.create(username)
    new_game = Game.create(player=player, other_player=None)
    games[new_game.id] = new_game

    return jsonify(
        {
            "success": True,
            "message": f"Successfully logged in as {username}",
            "game_id": new_game.id,
        }
    )


@app.route("/api/join", methods=["POST"])
def join_game() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"success": False, "message": "Game ID doesn't exist!"})

    if not is_valid_game_id(game_id):
        return jsonify({"success": False, "message": "Game ID should be 5 letters!"})

    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in!"})

    assert is_valid_username(username)

    if username not in players:
        players[username] = Player.create(username)

    player = players[username]

    try:
        games[game_id] = games[game_id].add_player(player)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})

    return jsonify({"success": True, "message": f"Successfully joined game {game_id}"})


@app.route("/api/game/<game_id>/number-of-players", methods=["GET"])
def get_number_of_players(game_id: str) -> Response:
    game = games.get(game_id, None)

    if game is None:
        return jsonify({"success": False, "message": "Game not found!"})

    game = games[game_id]
    n_players = game.get_number_of_players()

    return jsonify({"success": True, "number_of_players": n_players})


@app.route("/api/game/<game_id>/has-estimate", methods=["GET"])
def has_estimate(game_id: str) -> Response:
    game = games.get(game_id, None)

    if game is None:
        return jsonify({"success": False, "message": "Game not found!"})

    game = games[game_id]
    has_estimate = game.get_estimate() != None

    return jsonify({"success": True, "has_estimate": has_estimate})


@app.route("/api/fold", methods=["POST"])
def fold() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    game = games[game_id]

    try:
        new_game = game.fold().swtich_estimator().kick_players()
    except ValueError as e:
        return jsonify({"error": str(e)})

    assert new_game.player is not None
    players[new_game.player.username] = new_game.player

    assert new_game.other_player is not None
    players[new_game.other_player.username] = new_game.other_player

    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully folded"})


@app.route("/api/submit", methods=["POST"])
def submit_estimate() -> Response:
    game_id = request.json["game_id"]  # type: ignore
    estimate = int(request.json["estimate"])  # type: ignore
    error = int(request.json["error"])  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    game = games[game_id]
    new_game = game.set_estimate(estimate).set_error(error).switch_turns()
    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully submitted estimate"})


@app.route("/api/raise", methods=["POST"])
def raise_ante() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    # TODO: finish raise logic

    game = games[game_id]
    new_game = game.raise_ante().switch_turns()
    games[game_id] = new_game

    return jsonify({"success": True, "message": "Successfully raised"})


@app.route("/api/call", methods=["POST"])
def call_ante() -> Response:
    game_id = request.json["game_id"]  # type: ignore

    if game_id not in games:
        return jsonify({"error": "Game not found"})

    game = games[game_id]
    new_game = game.call_ante().switch_turns()
    games[game_id] = new_game

    assert game.player is not None
    players[game.player.username] = game.player

    assert game.other_player is not None
    players[game.other_player.username] = game.other_player

    return jsonify({"success": True, "message": "Successfully called"})


@app.route("/api/game/<game_id>/is-your-turn", methods=["GET"])
def get_is_my_turn(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game not found"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})

    try:
        player = game.get_turn()
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)})
    
    is_your_turn = username == player.username

    return jsonify({"success": True, "is_your_turn": is_your_turn})

@app.route("/api/game/<game_id>/has-called", methods=["GET"])
def has_called(game_id: str) -> Response:
    if game_id not in games:
        return jsonify({"success": False, "message": "Game not found"})

    game = games[game_id]
    username = session.get("username", None)

    if username is None:
        return jsonify({"success": False, "message": "User not logged in"})
    
    has_called = game.ante == game.other_ante

    return jsonify({"success": True, "has_called": has_called})


if __name__ == "__main__":
    app.run(debug=True)

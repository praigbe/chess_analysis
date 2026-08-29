import hashlib
import io
import math
import os
import shutil

from flask import Flask, redirect, render_template, request, session, url_for
import chess
import chess.engine
import chess.pgn
import chess.svg

app = Flask(__name__)
app.secret_key = "chess-analysis-secret-key"
ANALYSIS_CACHE = {}

ENGINE_CANDIDATES = [
    "/usr/games/stockfish",
    "/usr/local/bin/stockfish",
    "/opt/stockfish/stockfish",
]

SAMPLE_PGN = """1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6"""


def find_stockfish_path():
    for candidate in ENGINE_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    found = shutil.which("stockfish")
    if found:
        return found
    raise FileNotFoundError("Stockfish not found. Install stockfish or set the path in app.py.")


ENGINE_PATH = find_stockfish_path()


def score_to_win_probability(score_cp):
    if score_cp is None:
        return 0.5
    sigma = 600.0
    probability = 1 / (1 + math.exp(-(score_cp / sigma)))
    return max(0.01, min(0.99, probability))


def get_or_build_review_steps(pgn_text):
    if not pgn_text or not pgn_text.strip():
        raise ValueError("Please paste a PGN or a game score.")

    digest = hashlib.sha256(pgn_text.strip().encode("utf-8")).hexdigest()
    if digest not in ANALYSIS_CACHE:
        ANALYSIS_CACHE[digest] = build_review_steps(pgn_text)
        while len(ANALYSIS_CACHE) > 20:
            ANALYSIS_CACHE.pop(next(iter(ANALYSIS_CACHE)))
    return ANALYSIS_CACHE[digest]


def build_review_steps(pgn_text):
    if not pgn_text or not pgn_text.strip():
        raise ValueError("Please paste a PGN or a game score.")

    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("No valid chess game was found in the PGN text.")

    moves = list(game.mainline_moves())
    if not moves:
        return []

    board = game.board()
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    try:
        review_steps = []
        for move_number, move in enumerate(moves, start=1):
            before_eval = engine.analyse(board, chess.engine.Limit(depth=10))
            before_score = before_eval["score"]
            player = board.turn
            before_cp = before_score.pov(player).score(mate_score=100000)
            before_win = round(score_to_win_probability(before_cp) * 100, 1)
            best_move = before_eval["pv"][0]
            best_san = board.san(best_move)

            before_fen = board.fen()
            board.push(move)
            after_eval = engine.analyse(board, chess.engine.Limit(depth=10))
            after_score = after_eval["score"]
            after_cp = after_score.pov(player).score(mate_score=100000)
            after_win = round(score_to_win_probability(after_cp) * 100, 1)
            delta_cp = round(after_cp - before_cp, 1)

            if move != best_move and delta_cp < -120:
                quality = "blunder"
                coaching = f"This was a serious blunder. The engine preferred {best_san}, which changes the position much more favorably."
            elif move != best_move and delta_cp < -45:
                quality = "mistake"
                coaching = f"This was a mistake. {best_san} is the stronger move and keeps a much better win chance."
            elif delta_cp > 80:
                quality = "excellent"
                coaching = f"Excellent move. It improves the position and increases your winning chances substantially."
            elif delta_cp > 20:
                quality = "good"
                coaching = "Good move. It improves the position without giving the opponent a big counterchance."
            else:
                quality = "normal"
                coaching = "This is a reasonable move. The engine sees it as balanced, but there may still be a better option."

            review_steps.append(
                {
                    "move_number": move_number,
                    "player": "White" if player == chess.WHITE else "Black",
                    "move_uci": move.uci(),
                    "move_san": move.uci(),
                    "best_move": best_move.uci(),
                    "best_move_san": best_san,
                    "quality": quality,
                    "win_before": before_win,
                    "win_after": after_win,
                    "delta_cp": delta_cp,
                    "coaching": coaching,
                    "board_svg": chess.svg.board(board, size=440),
                    "after_fen": board.fen(),
                    "before_fen": before_fen,
                }
            )
        return review_steps
    finally:
        engine.quit()


def analyze_game(pgn_text):
    review_steps = build_review_steps(pgn_text)
    blunders = sum(1 for step in review_steps if step["quality"] == "blunder")
    good_moves = sum(1 for step in review_steps if step["quality"] in {"good", "excellent"})
    accuracy = 100.0
    if review_steps:
        accuracy = max(0.0, min(100.0, 100 - (blunders * 100 / len(review_steps))))
    return {
        "moves": review_steps,
        "summary": {
            "total_moves": len(review_steps),
            "blunders": blunders,
            "good_moves": good_moves,
            "accuracy": round(accuracy, 1),
            "message": (
                f"The engine found {blunders} likely blunder(s) across {len(review_steps)} moves. "
                f"Overall accuracy estimate: {round(accuracy, 1)}%."
            )
        }
    }


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        pgn_text = (request.form.get("pgn") or "").strip()
        if not pgn_text:
            return render_template("index.html", error="Paste a PGN first.")
        try:
            session["pgn"] = pgn_text
            return redirect(url_for("review", step=0))
        except ValueError as exc:
            return render_template("index.html", error=str(exc))
        except FileNotFoundError as exc:
            return render_template("index.html", error=str(exc))
    return render_template("index.html", error=None)


@app.route("/review")
def review():
    pgn_text = session.get("pgn")
    if not pgn_text:
        return redirect(url_for("index"))

    try:
        review_steps = get_or_build_review_steps(pgn_text)
    except ValueError as exc:
        return render_template("index.html", error=str(exc))
    except FileNotFoundError as exc:
        return render_template("index.html", error=str(exc))

    step_index = int(request.args.get("step", 0))
    if step_index < 0:
        step_index = 0
    if step_index >= len(review_steps):
        step_index = len(review_steps) - 1

    current = review_steps[step_index]
    total = len(review_steps)

    summary = {
        "total_moves": total,
        "blunders": sum(1 for step in review_steps if step["quality"] == "blunder"),
        "good_moves": sum(1 for step in review_steps if step["quality"] in {"good", "excellent"}),
        "accuracy": round(max(0.0, min(100.0, 100 - (sum(1 for step in review_steps if step["quality"] == "blunder") * 100 / total)))) if total else 0,
    }

    return render_template(
        "review.html",
        step_index=step_index,
        total=total,
        current=current,
        review_steps=review_steps,
        prev_step=step_index - 1 if step_index > 0 else None,
        next_step=step_index + 1 if step_index < total - 1 else None,
        pgn=pgn_text,
        summary=summary,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

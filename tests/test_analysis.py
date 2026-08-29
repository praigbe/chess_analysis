import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analyze_game, build_review_steps, score_to_win_probability


def test_score_to_win_probability_handles_positive_score():
    assert 0.5 <= score_to_win_probability(50) <= 0.9


def test_score_to_win_probability_handles_negative_score():
    assert 0.1 <= score_to_win_probability(-200) <= 0.5


def test_analyze_game_returns_move_entries_for_standard_pgn():
    pgn = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6"
    result = analyze_game(pgn)
    assert "moves" in result
    assert len(result["moves"]) >= 7
    assert "summary" in result


def test_build_review_steps_returns_coaching_for_each_move():
    pgn = "1. e4 e5 2. Nf3 Nc6"
    review = build_review_steps(pgn)
    assert len(review) >= 2
    assert "quality" in review[0]
    assert "win_before" in review[0]
    assert "win_after" in review[0]

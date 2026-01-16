import chess
import chess.engine

engine = chess.engine.SimpleEngine.popen_uci(r"C:\code\stockfish\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe")


board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")

result = engine.analyse(board, chess.engine.Limit(time=1))

score = result["score"]

print(score)

engine.quit()



if score is not None:
    print("Centipawns:", score)
else:
    mate_in = white_score.mate()
    print("Mate in:", mate_in)


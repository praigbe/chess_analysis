import chess
import chess.engine

# Configuration
ENGINE_PATH = r"C:\code\stockfish\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"
FEN = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"

try:
    engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
    board = chess.Board(FEN)
    
    result = engine.analyse(board, chess.engine.Limit(time=1))
    score = result["score"]
    
    # Handle centipawn vs mate scores
    if score.is_mate():
        mate_in = score.mate()
        print(f"Mate in: {mate_in}")
    else:
        centipawns = score.white().cp
        print(f"Centipawns: {centipawns}")
        
finally:
    engine.quit()

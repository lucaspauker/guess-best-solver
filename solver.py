import json
import os
from collections import defaultdict

from random import shuffle

elo = defaultdict(lambda: 1500)
K_FACTOR = 32  # standard Elo K-factor

wins = defaultdict(set)
losses = defaultdict(set)
match_counts = defaultdict(int)
win_counts = defaultdict(int)

last_predictions = []
total_predictions = 0
total_correct = 0

SAVE_FILE = "game_data.json"

def record_match(winner, loser):
    global total_predictions, total_correct

    winner = winner.upper()
    loser = loser.upper()

    predicted = predict(winner, loser)
    was_correct = (predicted == winner)

    print(f"Prediction was {'correct' if was_correct else 'wrong'}.")

    last_predictions.append(was_correct)
    if len(last_predictions) > 20:
        last_predictions.pop(0)

    correct_rolling = sum(last_predictions)
    total_predictions += 1
    total_correct += int(was_correct)

    print(f"Rolling accuracy (last {len(last_predictions)}): {correct_rolling}/{len(last_predictions)} = {correct_rolling / len(last_predictions):.1%}")
    print(f"All-time accuracy: {total_correct}/{total_predictions} = {total_correct / total_predictions:.1%}")

    wins[winner].add(loser)
    losses[loser].add(winner)
    match_counts[winner] += 1
    match_counts[loser] += 1
    win_counts[winner] += 1

    update_elo(winner, loser)

def score(item, **kwargs):
    return elo[item.upper()]

def update_elo(winner, loser):
    Ra = elo[winner]
    Rb = elo[loser]
    Ea = 1 / (1 + 10 ** ((Rb - Ra) / 400))
    Eb = 1 - Ea
    elo[winner] += K_FACTOR * (1 - Ea)
    elo[loser] += K_FACTOR * (0 - Eb)

def predict(item1, item2):
    item1 = item1.upper()
    item2 = item2.upper()

    def record_str(item):
        wins_ = win_counts[item]
        losses_ = match_counts[item] - wins_
        return f"{item} ({wins_}-{losses_})"

    if item2 in wins[item1]:
        print(f"{record_str(item1)} has directly beaten {record_str(item2)} before.")
        return item1
    if item1 in wins[item2]:
        print(f"{record_str(item2)} has directly beaten {record_str(item1)} before.")
        return item2

    s1 = score(item1)
    s2 = score(item2)
    print(f"{record_str(item1)} score: {s1:.3f}")
    print(f"{record_str(item2)} score: {s2:.3f}")
    if s1 == s2:
        return "Tie"
    return item1 if s1 > s2 else item2

def display_scores():
    items = set(wins) | set(losses)
    scored = [(item, score(item)) for item in items]
    scored.sort(key=lambda x: -x[1])  # sort descending by score

    def print_item(item, s):
        wins_ = win_counts[item]
        losses_ = match_counts[item] - wins_
        print(f"{item} ({wins_}-{losses_}): {s:.3f}")

    n = len(scored)
    if n <= 20:
        for item, s in scored:
            print_item(item, s)
    else:
        print("Top 10:")
        for item, s in scored[:10]:
            print_item(item, s)
        print("...")
        print("Bottom 10:")
        for item, s in scored[-10:]:
            print_item(item, s)

def save():
    data = {
        "wins": {k: list(v) for k, v in wins.items()},
        "losses": {k: list(v) for k, v in losses.items()},
        "match_counts": dict(match_counts),
        "win_counts": dict(win_counts),
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
    print(f"Saved to {SAVE_FILE}")

def load():
    if not os.path.exists(SAVE_FILE):
        print(f"No save file found at {SAVE_FILE}")
        return
    with open(SAVE_FILE, "r") as f:
        data = json.load(f)
    wins.clear()
    losses.clear()
    match_counts.clear()
    win_counts.clear()
    for k, v in data["wins"].items():
        wins[k] = set(v)
    for k, v in data["losses"].items():
        losses[k] = set(v)
    match_counts.update(data["match_counts"])
    win_counts.update(data["win_counts"])
    print(f"Loaded from {SAVE_FILE}")

    # Reconstruct matches
    matches = []
    for winner, losers in wins.items():
        for loser in losers:
            matches.append((winner, loser, winner))

    # Shuffle and compute Elo 5 times, then average
    elo_runs = []
    for _ in range(5):
        shuffle(matches)
        temp_elo = defaultdict(lambda: 1500)
        for a, b, w in matches:
            a = a.upper()
            b = b.upper()
            if w == a:
                Ra = temp_elo[a]
                Rb = temp_elo[b]
                Ea = 1 / (1 + 10 ** ((Rb - Ra) / 400))
                temp_elo[a] += K_FACTOR * (1 - Ea)
                temp_elo[b] += K_FACTOR * (0 - (1 - Ea))
            else:
                Ra = temp_elo[a]
                Rb = temp_elo[b]
                Eb = 1 / (1 + 10 ** ((Ra - Rb) / 400))
                temp_elo[b] += K_FACTOR * (1 - Eb)
                temp_elo[a] += K_FACTOR * (0 - (1 - Eb))
        elo_runs.append(temp_elo)

    # Average Elo scores over 5 runs
    elo.clear()
    all_players = set()
    for run in elo_runs:
        all_players.update(run.keys())

    for player in all_players:
        avg = sum(run[player] for run in elo_runs) / len(elo_runs)
        elo[player] = avg

    print("Calculated elo scores (averaged over 5 shuffled runs):")

def main():
    print("Welcome to Game Predictor!")
    print("Commands:")
    print("  win A B      → A beats B")
    print("  predict A B  → predict winner between A and B")
    print("  scores       → show scores of all items")
    print("  save         → save match data to file")
    print("  load         → load match data from file")
    print("  quit         → exit program")

    while True:
        try:
            cmd = input("> ").strip().lower()
            if not cmd:
                continue
            if cmd == "quit":
                break
            parts = cmd.split()
            if parts[0] == "win" and len(parts) == 3:
                record_match(parts[1], parts[2])
            elif parts[0] == "w" and len(parts) == 3:
                record_match(parts[1], parts[2])
            elif parts[0] == "predict" and len(parts) == 3:
                winner = predict(parts[1], parts[2])
                print("Predicted winner:", winner)
            elif parts[0] == "p" and len(parts) == 3:
                winner = predict(parts[1], parts[2])
                print("Predicted winner:", winner)
            elif parts[0] == "scores":
                display_scores()
            elif parts[0] == "save":
                save()
            elif parts[0] == "load":
                load()
            else:
                print("Invalid command.")
        except KeyboardInterrupt:
            print("\nExiting.")
            break

if __name__ == "__main__":
    main()


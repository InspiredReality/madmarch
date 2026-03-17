#!/usr/bin/env python3

import csv
import random
import argparse
from collections import defaultdict

ROUNDS = [
    "Round64",
    "Round32",
    "Sweet16",
    "Elite8",
    "Final4",
    "TitleGame"
]

PAIRINGS = [
    (1,16),(8,9),(5,12),(4,13),
    (6,11),(3,14),(7,10),(2,15)
]


def load_teams(path):
    teams = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            teams[row["Team"]] = row
    return teams


def load_bracket(path):
    bracket = defaultdict(dict)
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region = row["Region"]
            seed = int(row["Seed"])
            team = row["Team"]
            bracket[region][seed] = team
    return bracket


def validate(bracket, teams):

    all_teams = []

    for region in bracket:

        if len(bracket[region]) != 16:
            raise ValueError(f"{region} must contain 16 seeds")

        for seed, team in bracket[region].items():

            if team not in teams:
                raise ValueError(f"{team} missing from teams.csv")

            all_teams.append(team)

    if len(all_teams) != 64:
        raise ValueError("Bracket must contain 64 teams")


def variance_range(round_num):

    if round_num == 1:
        return (0.90, 1.10)

    elif round_num == 2:
        return (0.92, 1.08)

    elif round_num == 3:
        return (0.94, 1.06)

    else:
        return (0.95, 1.05)


def apply_variance(points, round_num):

    low, high = variance_range(round_num)
    multiplier = random.uniform(low, high)

    return points * multiplier


# ------------------------------
# MODELS
# ------------------------------

def model1(home, away):

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    home_ppp = (float(home["ORtg"]) + float(away["DRtg"])) / 200
    away_ppp = (float(away["ORtg"]) + float(home["DRtg"])) / 200

    return home_ppp * pace, away_ppp * pace


def model2(home, away):

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    margin = ((float(home["NetRtg"]) - float(away["NetRtg"])) / 100) * pace

    base_total = 140

    home_pts = (base_total + margin) / 2
    away_pts = (base_total - margin) / 2

    return home_pts, away_pts
def model3(home, away, round_num):

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    if round_num == 1:

        home_score = 0.7 * float(home["NetRtg"]) + 0.3 * float(home["ORtg"])
        away_score = 0.7 * float(away["NetRtg"]) + 0.3 * float(away["ORtg"])

    elif round_num == 2:

        home_score = 0.5 * float(home["ORtg"]) + 0.5 * (200 - float(away["DRtg"]))
        away_score = 0.5 * float(away["ORtg"]) + 0.5 * (200 - float(home["DRtg"]))

    else:

        home_score = 0.4 * float(home["ORtg"]) + 0.6 * (200 - float(away["DRtg"]))
        away_score = 0.4 * float(away["ORtg"]) + 0.6 * (200 - float(home["DRtg"]))

    return home_score * pace / 100, away_score * pace / 100
def model4(home, away):

    home_pts = (
        0.5 * (float(home["ORtg"]) / 100 * float(home["AdjT"])) +
        0.5 * (float(away["DRtg"]) / 100 * float(away["AdjT"]))
    )

    away_pts = (
        0.5 * (float(away["ORtg"]) / 100 * float(away["AdjT"])) +
        0.5 * (float(home["DRtg"]) / 100 * float(home["AdjT"]))
    )

    return home_pts, away_pts


def model5(home, away):
    """Model 1 with Gaussian variance instead of uniform"""

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    home_ppp = (float(home["ORtg"]) + float(away["DRtg"])) / 200
    away_ppp = (float(away["ORtg"]) + float(home["DRtg"])) / 200

    # Gaussian variance: mean=1.0, std=0.05 (most games within +/-10%)
    home_variance = random.gauss(1.0, 0.05)
    away_variance = random.gauss(1.0, 0.05)

    return home_ppp * pace * home_variance, away_ppp * pace * away_variance


def model6(home, away):
    """Model 1 with Luck bonus - lucky teams rewarded in close games"""

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    home_ppp = (float(home["ORtg"]) + float(away["DRtg"])) / 200
    away_ppp = (float(away["ORtg"]) + float(home["DRtg"])) / 200

    home_pts = home_ppp * pace
    away_pts = away_ppp * pace

    # Add luck bonus (luck ranges ~-0.1 to +0.1, multiply by ~15 pts)
    home_luck = float(home.get("Luck", 0)) * 15
    away_luck = float(away.get("Luck", 0)) * 15

    # Gaussian variance
    home_variance = random.gauss(1.0, 0.05)
    away_variance = random.gauss(1.0, 0.05)

    return (home_pts + home_luck) * home_variance, (away_pts + away_luck) * away_variance


def model7(home, away):
    """Log5 win probability model - no scores, just probability-based outcome"""

    home_rating = float(home["NetRtg"])
    away_rating = float(away["NetRtg"])

    # Log5 formula: win prob based on rating difference
    # ~15 rating points = ~10% win probability shift
    diff = home_rating - away_rating
    home_win_prob = 1 / (1 + 10 ** (-diff / 15))

    # Return dummy scores where higher = winner based on probability
    if random.random() < home_win_prob:
        return 1.0, 0.0  # home wins
    else:
        return 0.0, 1.0  # away wins


def model8(home, away):
    """Model 2 using NC_NetRtg (non-conference) for schedule-normalized ratings"""

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    # Use NC_NetRtg instead of NetRtg
    home_nc = float(home.get("NC_NetRtg", home["NetRtg"]))
    away_nc = float(away.get("NC_NetRtg", away["NetRtg"]))

    margin = ((home_nc - away_nc) / 100) * pace

    base_total = 140

    home_pts = (base_total + margin) / 2
    away_pts = (base_total - margin) / 2

    return home_pts, away_pts


def model9(home, away):
    """Hybrid: Log5 probability-derived margin with Gaussian score variance"""

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    home_rating = float(home["NetRtg"])
    away_rating = float(away["NetRtg"])
    diff = home_rating - away_rating

    # Log5 win probability
    home_win_prob = 1 / (1 + 10 ** (-diff / 15))

    # Convert probability to expected margin
    # 50% = 0 margin, 75% ≈ +7 pts, 90% ≈ +14 pts
    # Using inverse logit: margin = 15 * log10(p / (1-p)) * pace_factor
    if home_win_prob >= 0.99:
        expected_margin = 20  # cap at ~20 point margin
    elif home_win_prob <= 0.01:
        expected_margin = -20
    else:
        import math
        expected_margin = 15 * math.log10(home_win_prob / (1 - home_win_prob))

    # Scale margin by pace (faster pace = more scoring variance)
    pace_factor = pace / 68  # normalize to average pace
    expected_margin *= pace_factor

    # Base total points
    base_total = 140

    # Calculate expected scores
    home_expected = (base_total + expected_margin) / 2
    away_expected = (base_total - expected_margin) / 2

    # Apply Gaussian variance (std=5% of expected score)
    home_pts = home_expected * random.gauss(1.0, 0.05)
    away_pts = away_expected * random.gauss(1.0, 0.05)

    return home_pts, away_pts


def model10(home, away):
    """Linear NetRtg margin with luck adjustment and Gaussian score variance"""

    def safe_float(val, default=0.0):
        try:
            return float(val) if val != '' else default
        except (ValueError, TypeError):
            return default

    pace = (float(home["AdjT"]) + float(away["AdjT"])) / 2

    # Fallback to NetRtg if SOS_NetRtg is missing
    home_sos = safe_float(home.get("SOS_NetRtg"), float(home["NetRtg"]))
    away_sos = safe_float(away.get("SOS_NetRtg"), float(away["NetRtg"]))

    home_rating = .8*float(home["NetRtg"])+.1*float(home["NC_NetRtg"])+.1*home_sos
    away_rating = .8*float(away["NetRtg"])+.1*float(away["NC_NetRtg"])+.1*away_sos

    # Add luck bonus (luck ranges ~-0.1 to +0.1, reduce/add ~1.5 pts)
    home_luck = float(home.get("Luck", 0)) * 15
    away_luck = float(away.get("Luck", 0)) * 15
    home_adj = home_rating + home_luck
    away_adj = away_rating + away_luck

    # Simple linear expected margin
    expected_margin = (home_adj - away_adj) * (pace / 100)

    # Base total points from Offensive & Defensive ratings
    base_off = (float(home["ORtg"]) + float(away["ORtg"])) * (pace / 100)
    base_def = (float(home["DRtg"]) + float(away["DRtg"])) * (pace / 100)
    base_total = (base_off + base_def) / 2

    # Calculate expected scores
    home_expected = (base_total + expected_margin) / 2
    away_expected = (base_total - expected_margin) / 2

    # Apply Gaussian variance (std=5% of expected score)
    home_pts = home_expected * random.gauss(1.0, 0.05)
    away_pts = away_expected * random.gauss(1.0, 0.05)

    return home_pts, away_pts


MODELS = {
    # "model_1": model1,
    # "model_2": model2,
    # "model_3": model3,
    # "model_4": model4,
    "model_5": model5,
    "model_6": model6,
    "model_7": model7,
    # "model_8": model8,
    "model_9": model9,
    "model_10": model10
}


# ------------------------------
# GAME LOGIC
# ------------------------------

def play_game(home_name, away_name, teams, model, round_num):
    """Returns (winner, home_pts, away_pts)"""

    home = teams[home_name]
    away = teams[away_name]

    if model == "model_3":
        home_pts, away_pts = model3(home, away, round_num)
    else:
        home_pts, away_pts = MODELS[model](home, away)

    # Models 5, 6, 7, 9 handle their own variance/randomness
    if model not in ("model_5", "model_6", "model_7", "model_9"):
        home_pts = apply_variance(home_pts, round_num)
        away_pts = apply_variance(away_pts, round_num)

    if home_pts > away_pts:
        return home_name, home_pts, away_pts
    else:
        return away_name, away_pts, home_pts


def region_round(matchups, teams, model, round_num, points_tracker):
    """Returns list of winners and updates points_tracker with scores"""

    winners = []

    for team_a, team_b in matchups:
        winner, winner_pts, loser_pts = play_game(team_a, team_b, teams, model, round_num)
        winners.append(winner)

        # Track points for both teams
        loser = team_b if winner == team_a else team_a
        points_tracker[winner] += winner_pts
        points_tracker[loser] += loser_pts

    return winners


# ------------------------------
# SIMULATION
# ------------------------------

def simulate(bracket, teams, model):

    counts = defaultdict(lambda: [0] * 7)
    points = defaultdict(float)  # Track total points scored

    for region in bracket:
        for team in bracket[region].values():
            counts[team][0] += 1

    region_winners = []

    for region in bracket:

        seeds = bracket[region]

        r1 = [(seeds[a], seeds[b]) for a, b in PAIRINGS]
        r1_winners = region_round(r1, teams, model, 1, points)

        for t in r1_winners:
            counts[t][1] += 1

        r2 = [(r1_winners[i], r1_winners[i+1]) for i in range(0, 8, 2)]
        r2_winners = region_round(r2, teams, model, 2, points)

        for t in r2_winners:
            counts[t][2] += 1

        r3 = [(r2_winners[0], r2_winners[1]), (r2_winners[2], r2_winners[3])]
        r3_winners = region_round(r3, teams, model, 3, points)

        for t in r3_winners:
            counts[t][3] += 1

        r4 = [(r3_winners[0], r3_winners[1])]
        r4_winners = region_round(r4, teams, model, 4, points)

        for t in r4_winners:
            counts[t][4] += 1

        region_winners.append(r4_winners[0])

    final_four = [
        (region_winners[0], region_winners[1]),
        (region_winners[2], region_winners[3])
    ]

    ff_winners = region_round(final_four, teams, model, 5, points)

    for t in ff_winners:
        counts[t][5] += 1

    winner, winner_pts, loser_pts = play_game(ff_winners[0], ff_winners[1], teams, model, 6)
    loser = ff_winners[1] if winner == ff_winners[0] else ff_winners[0]
    points[winner] += winner_pts
    points[loser] += loser_pts

    counts[winner][6] += 1

    return counts, points


def merge_counts(base_counts, new_counts, base_points, new_points):

    for team in new_counts:
        for i in range(7):
            base_counts[team][i] += new_counts[team][i]

    for team in new_points:
        base_points[team] += new_points[team]


# ------------------------------
# MAIN
# ------------------------------

def simulate_single_game(home_name, away_name, teams, model, iterations):
    """Simulate a single matchup multiple times and return stats"""

    home_pts_total = 0
    away_pts_total = 0
    home_wins = 0

    for _ in range(iterations):
        winner, winner_pts, loser_pts = play_game(home_name, away_name, teams, model, 1)

        if winner == home_name:
            home_pts_total += winner_pts
            away_pts_total += loser_pts
            home_wins += 1
        else:
            home_pts_total += loser_pts
            away_pts_total += winner_pts

    return {
        "home_avg": home_pts_total / iterations,
        "away_avg": away_pts_total / iterations,
        "total_avg": (home_pts_total + away_pts_total) / iterations,
        "home_win_pct": home_wins / iterations * 100,
        "spread": (home_pts_total - away_pts_total) / iterations
    }


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("--teams", default="inputs/teams.csv")
    parser.add_argument("--bracket", default="inputs/bracket_2026.csv")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--home", type=str, help="Home team for single game simulation")
    parser.add_argument("--away", type=str, help="Away team for single game simulation")
    parser.add_argument("--model", type=str, default="model_9", help="Model to use for single game (default: model_9)")
    parser.add_argument("--round1", action="store_true", help="Generate round 1 totals and spreads")

    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    teams = load_teams(args.teams)

    # Single game mode
    if args.home and args.away:
        if args.home not in teams:
            print(f"Error: '{args.home}' not found in teams.csv")
            return
        if args.away not in teams:
            print(f"Error: '{args.away}' not found in teams.csv")
            return

        print(f"\nSimulating: {args.home} vs {args.away}")
        print(f"Model: {args.model}, Iterations: {args.iterations}\n")

        if args.model == "all":
            # Run all models
            for model in MODELS:
                if model == "model_7":
                    print(f"{model}: N/A (no score simulation)")
                    continue
                stats = simulate_single_game(args.home, args.away, teams, model, args.iterations)
                print(f"{model}:")
                print(f"  {args.home}: {stats['home_avg']:.1f} pts ({stats['home_win_pct']:.1f}% win)")
                print(f"  {args.away}: {stats['away_avg']:.1f} pts ({100-stats['home_win_pct']:.1f}% win)")
                print(f"  Total: {stats['total_avg']:.1f}")
                print(f"  Spread: {args.home} {stats['spread']:+.1f}")
                print()
        else:
            if args.model not in MODELS:
                print(f"Error: '{args.model}' not found. Available: {list(MODELS.keys())}")
                return
            if args.model == "model_7":
                print("model_7 uses dummy scores (0/1), no point totals available")
                return

            stats = simulate_single_game(args.home, args.away, teams, args.model, args.iterations)
            print(f"{args.home}: {stats['home_avg']:.1f} pts ({stats['home_win_pct']:.1f}% win)")
            print(f"{args.away}: {stats['away_avg']:.1f} pts ({100-stats['home_win_pct']:.1f}% win)")
            print(f"Total: {stats['total_avg']:.1f}")
            print(f"Spread: {args.home} {stats['spread']:+.1f}")

        return

    bracket = load_bracket(args.bracket)

    # Round 1 totals and spreads mode
    if args.round1:
        print(f"\nGenerating Round 1 lines using {args.model}")
        print(f"Iterations: {args.iterations}\n")

        if args.model == "model_7":
            print("Error: model_7 uses dummy scores, cannot generate totals")
            return

        model = args.model if args.model != "all" else "model_9"

        with open("outputs/round1_lines.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Region", "Matchup", "HighSeed", "LowSeed", "HighSeedPts", "LowSeedPts", "Total", "Spread", "HighSeedWin%"])

            for region in bracket:
                seeds = bracket[region]

                for high_seed, low_seed in PAIRINGS:
                    high_team = seeds[high_seed]
                    low_team = seeds[low_seed]

                    stats = simulate_single_game(high_team, low_team, teams, model, args.iterations)

                    matchup = f"{high_seed} vs {low_seed}"
                    writer.writerow([
                        region,
                        matchup,
                        high_team,
                        low_team,
                        f"{stats['home_avg']:.1f}",
                        f"{stats['away_avg']:.1f}",
                        f"{stats['total_avg']:.1f}",
                        f"{stats['spread']:+.1f}",
                        f"{stats['home_win_pct']:.1f}%"
                    ])

                    print(f"{region} {matchup}: {high_team} vs {low_team}")
                    print(f"  Total: {stats['total_avg']:.1f}")
                    print(f"  Spread: {high_team} {stats['spread']:+.1f}")
                    print(f"  Win%: {high_team} {stats['home_win_pct']:.1f}%")
                    print()

        print("Results written to outputs/round1_lines.csv")
        return

    validate(bracket, teams)

    results = {}
    all_points = {}

    for model in MODELS:

        totals = defaultdict(lambda: [0] * 7)
        total_points = defaultdict(float)

        for _ in range(args.iterations):

            sim_counts, sim_points = simulate(bracket, teams, model)

            merge_counts(totals, sim_counts, total_points, sim_points)

        results[model] = totals
        all_points[model] = total_points

    # Build team -> seed mapping
    team_seeds = {}
    for region in bracket:
        for seed, team in bracket[region].items():
            team_seeds[team] = seed

    with open("outputs/round_results_all_models.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(["Model", "Seed", "Team"] + ROUNDS + ["AvgPts", "ExpValue"])

        # Earnings per round win
        EARNINGS = [9.80, 19.80, 39.58, 79.17, 158.32, 316.67]

        # Store ExpValue for blending
        exp_values = {}

        for model, data in results.items():

            for team in sorted(data):

                seed = team_seeds.get(team, "")
                row = [model, seed, team]

                for i in range(1, 7):  # Skip index 0 (made tournament), output round wins

                    pct = data[team][i] / args.iterations * 100
                    row.append(f"{pct:.1f}%")

                # Calculate average points per game
                # Each team plays at least 1 game, winners play more
                games_played = data[team][0]  # Everyone plays round 1
                for i in range(1, 7):
                    games_played += data[team][i]  # Add games for each round won

                total_pts = all_points[model].get(team, 0)
                if games_played > 0 and model != "model_7":
                    avg_pts = total_pts / games_played
                    row.append(f"{avg_pts:.1f}")
                else:
                    row.append("N/A")  # model_7 uses dummy scores

                # Calculate expected value: sum of (win probability * earnings) per round
                exp_value = sum(
                    (data[team][i] / args.iterations) * EARNINGS[i - 1]
                    for i in range(1, 7)
                )
                row.append(f"${exp_value:.2f}")

                # Store for blending
                if model not in exp_values:
                    exp_values[model] = {}
                exp_values[model][team] = exp_value

                writer.writerow(row)

    print("Results written to outputs/round_results_all_models.csv")

    # Write blended expected values
    BLEND_WEIGHTS = {
        "model_10": 0.6,
        "model_7": 0.2,
        "model_6": 0.1,
        "model_5": 0.1,
    }

    # Get all teams from any model
    all_teams = set()
    for model in BLEND_WEIGHTS:
        if model in exp_values:
            all_teams.update(exp_values[model].keys())

    with open("outputs/blended_exp_values.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Seed", "Team", "BlendedExpValue", "M5", "M6", "M7", "M10"])

        blended_rows = []
        for team in all_teams:
            blended = 0
            model_vals = {}
            for model, weight in BLEND_WEIGHTS.items():
                val = exp_values.get(model, {}).get(team, 0)
                model_vals[model] = val
                blended += weight * val

            seed = team_seeds.get(team, "")
            blended_rows.append((
                seed,
                team,
                blended,
                model_vals.get("model_5", 0),
                model_vals.get("model_6", 0),
                model_vals.get("model_7", 0),
                model_vals.get("model_10", 0),
            ))

        # Sort by blended value descending
        blended_rows.sort(key=lambda x: x[2], reverse=True)

        for row in blended_rows:
            seed, team, blended, m5, m6, m7, m10 = row
            writer.writerow([
                seed, team, f"${blended:.2f}",
                f"${m5:.2f}", f"${m6:.2f}", f"${m7:.2f}", f"${m10:.2f}"
            ])

    print("Blended values written to outputs/blended_exp_values.csv")


if __name__ == "__main__":
    main()

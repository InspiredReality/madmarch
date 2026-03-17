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
    "TitleGame",
    "Champion"
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


MODELS = {
    "model_1": model1,
    "model_2": model2,
    "model_3": model3,
    "model_4": model4
}


# ------------------------------
# GAME LOGIC
# ------------------------------

def play_game(home_name, away_name, teams, model, round_num):

    home = teams[home_name]
    away = teams[away_name]

    if model == "model_3":
        home_pts, away_pts = model3(home, away, round_num)
    else:
        home_pts, away_pts = MODELS[model](home, away)

    home_pts = apply_variance(home_pts, round_num)
    away_pts = apply_variance(away_pts, round_num)

    if home_pts > away_pts:
        return home_name
    else:
        return away_name


def region_round(matchups, teams, model, round_num):

    winners = []

    for team_a, team_b in matchups:
        winners.append(
            play_game(team_a, team_b, teams, model, round_num)
        )

    return winners


# ------------------------------
# SIMULATION
# ------------------------------

def simulate(bracket, teams, model):

    counts = defaultdict(lambda: [0] * 7)

    for region in bracket:
        for team in bracket[region].values():
            counts[team][0] += 1

    region_winners = []

    for region in bracket:

        seeds = bracket[region]

        r1 = [(seeds[a], seeds[b]) for a, b in PAIRINGS]
        r1_winners = region_round(r1, teams, model, 1)

        for t in r1_winners:
            counts[t][1] += 1

        r2 = [(r1_winners[i], r1_winners[i+1]) for i in range(0, 8, 2)]
        r2_winners = region_round(r2, teams, model, 2)

        for t in r2_winners:
            counts[t][2] += 1

        r3 = [(r2_winners[0], r2_winners[1]), (r2_winners[2], r2_winners[3])]
        r3_winners = region_round(r3, teams, model, 3)

        for t in r3_winners:
            counts[t][3] += 1

        r4 = [(r3_winners[0], r3_winners[1])]
        r4_winners = region_round(r4, teams, model, 4)

        for t in r4_winners:
            counts[t][4] += 1

        region_winners.append(r4_winners[0])

    final_four = [
        (region_winners[0], region_winners[1]),
        (region_winners[2], region_winners[3])
    ]

    ff_winners = region_round(final_four, teams, model, 5)

    for t in ff_winners:
        counts[t][5] += 1

    champion = play_game(ff_winners[0], ff_winners[1], teams, model, 6)

    counts[champion][6] += 1

    return counts


def merge_counts(base, new):

    for team in new:
        for i in range(7):
            base[team][i] += new[team][i]


# ------------------------------
# MAIN
# ------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument("teams")
    parser.add_argument("bracket")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--seed", type=int)

    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    teams = load_teams(args.teams)
    bracket = load_bracket(args.bracket)

    validate(bracket, teams)

    results = {}

    for model in MODELS:

        totals = defaultdict(lambda: [0] * 7)

        for _ in range(args.iterations):

            sim = simulate(bracket, teams, model)

            merge_counts(totals, sim)

        results[model] = totals

    with open("round_results_all_models.csv", "w", newline="") as f:

        writer = csv.writer(f)

        writer.writerow(["Model", "Team"] + ROUNDS)

        for model, data in results.items():

            for team in sorted(data):

                row = [model, team]

                for i in range(7):

                    pct = data[team][i] / args.iterations * 100
                    row.append(f"{pct:.1f}%")

                writer.writerow(row)

    print("Results written to round_results_all_models.csv")


if __name__ == "__main__":
    main()

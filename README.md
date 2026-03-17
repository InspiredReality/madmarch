Model Breakdown
Model 1: Points Per Possession

home_ppp = (home["ORtg"] + away["DRtg"]) / 200
away_ppp = (away["ORtg"] + home["DRtg"]) / 200
score = ppp * pace
Logic: Averages each team's offensive rating with opponent's defensive rating to estimate points per possession, then multiplies by pace. Classic efficiency-based approach.

Model 2: Net Rating Margin

margin = ((home["NetRtg"] - away["NetRtg"]) / 100) * pace
home_pts = (140 + margin) / 2
away_pts = (140 - margin) / 2
Logic: Uses pure NetRtg difference to calculate margin, assumes 140 total points baseline. Simple head-to-head comparison but ignores matchup dynamics.

Model 3: Round-Adaptive Weighting

Round 1: 70% NetRtg + 30% ORtg  (favors overall quality)
Round 2: 50% ORtg + 50% (200 - opponent DRtg)
Round 3+: 40% ORtg + 60% (200 - opponent DRtg)  (favors matchups)
Logic: Early rounds favor team quality (NetRtg), later rounds weight matchup dynamics more heavily. Attempts to model how tournament games change character.

Model 4: Tempo-Weighted Efficiency

home_pts = 0.5 * (home["ORtg"]/100 * home["AdjT"]) + 
           0.5 * (away["DRtg"]/100 * away["AdjT"])
Logic: Each team's tempo affects their own contribution. High-tempo teams amplify both their offense AND how opponent's defense performs.

model_5	Model 1 + Gaussian variance (std=5%) - more realistic bell curve
model_6	Model 1 + Luck bonus (high luck teams get +3pts max) + Gaussian
model_7	Log5 win probability - no scores, just probability-based outcomes
model_8	Model 2 using NC_NetRtg instead of NetRtg

My Assessment
Model 1 is likely most accurate for these reasons:

Standard efficiency formula - This is essentially how KenPom/analytics sites calculate expected scores
Accounts for matchups - Your offense vs their defense, and vice versa
Shared pace - Uses average tempo (correct since both teams play same game)
Results look realistic - 1-seeds win ~85-100% in Round64, reasonable upset rates
Model 2 is too simplistic - NetRtg alone misses style matchups (fast vs slow, offense vs defense specialists).

Model 3 has interesting theory but the round-based weighting seems arbitrary and produces strange results (Duke only 29% to beat a 16-seed in R64?).

Model 4 has a conceptual flaw - using each team's own tempo separately doesn't reflect reality where both teams play at a compromise pace.



Model	Description
1	Points = (ORtg + opponent DRtg) / 2 × pace — basic efficiency matchup
2	Margin from NetRtg diff × pace, split around fixed 140 total
3	Round-dependent weights: early rounds favor NetRtg, later rounds favor ORtg/DRtg matchups
4	Blend of own offense × own tempo and opponent defense × opponent tempo
5	Model 1 + Gaussian variance (±5% std dev)
6	Model 1 + Luck bonus (±1.5 pts) + Gaussian variance
7	Log5 probability only — returns binary win/loss, no scores
8	Model 2 using NC_NetRtg (non-conference rating) instead of NetRtg
9	Log5 probability → margin conversion (capped ±20), fixed 140 total, Gaussian variance
10	Blended rating (80% NetRtg + 10% NC + 10% SOS) + Luck, dynamic total from ORtg+DRtg, Gaussian variance
"""Offline no-lookahead checks for nflverse pregame EPA/defense rankings."""
import sys
import unittest
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import build_nflverse_pregame_ratings as ratings

def plays(season,week,game,home,away,home_epa,away_epa):
    # 5 plays per team ensures both sides have complete offense/defense metrics.
    out=[]
    for team,opp,epa in ((home,away,home_epa),(away,home,away_epa)):
        for j in range(5):
            out.append(dict(season=season,week=week,season_type="REG",game_id=game,
                            home_team=home,away_team=away,posteam=team,defteam=opp,
                            play_type="pass" if j%2 else "run",epa=epa,
                            success=1 if epa>0 else 0))
    return out

class PregameRatingsTests(unittest.TestCase):
    def sample(self):
        data=(
            plays(2025,1,"w1_AB","A","B",.5,-.3)+
            plays(2025,1,"w1_CD","C","D",.2,-.2)+
            plays(2025,2,"w2_AC","A","C",-.8,.9)+
            plays(2025,2,"w2_BD","B","D",-.1,.1)+
            plays(2025,3,"w3_AD","A","D",.7,-.2)+
            plays(2026,1,"new_AB","A","B",-.7,.9)
        )
        return pd.DataFrame(data)

    def build(self,data=None):
        games,eligible=ratings.games_and_plays(self.sample() if data is None else data)
        return ratings.pregame_frames(games,ratings.per_game_records(eligible))

    def test_week_one_has_no_pregame_ratings(self):
        teams,matchups=self.build()
        w1=matchups[(matchups.season==2025)&(matchups.week==1)]
        self.assertEqual(len(w1),2)
        self.assertTrue((w1["home_prior_games"]==0).all())
        self.assertTrue((w1["home_off_rank"]=="").all())
        self.assertEqual(len(teams[(teams.season==2025)&(teams.week==1)]),0)

    def test_week_two_only_uses_week_one_data(self):
        teams,matchups=self.build()
        a=teams[(teams.season==2025)&(teams.week==2)&(teams.team=="A")].iloc[0]
        self.assertAlmostEqual(a["off_epa_per_play"],.5)
        self.assertAlmostEqual(a["def_epa_allowed_per_play"],-.3)
        self.assertEqual(a["off_rank"],1)
        self.assertEqual(a["prior_games"],1)
        self.assertEqual(len(matchups[(matchups.season==2025)&(matchups.week==2)]),2)

    def test_changing_same_week_stats_cannot_change_current_week_features(self):
        raw=self.sample()
        t1,m1=self.build(raw)
        altered=raw.copy()
        altered.loc[(altered.season==2025)&(altered.week==2),"epa"]=30.0
        t2,m2=self.build(altered)
        one=m1[(m1.season==2025)&(m1.week==2)].reset_index(drop=True)
        two=m2[(m2.season==2025)&(m2.week==2)].reset_index(drop=True)
        pd.testing.assert_frame_equal(one,two)
        # But future week 3 MUST change.
        a1=t1[(t1.season==2025)&(t1.week==3)&(t1.team=="A")].iloc[0]
        a2=t2[(t2.season==2025)&(t2.week==3)&(t2.team=="A")].iloc[0]
        self.assertNotEqual(a1["off_epa_per_play"],a2["off_epa_per_play"])

    def test_new_season_resets_all_ratings(self):
        _,matchups=self.build()
        new=matchups[matchups.season==2026].iloc[0]
        self.assertEqual(new["home_prior_games"],0)
        self.assertEqual(new["home_off_epa"],"")

    def test_defense_rank_is_lower_allowed_epa(self):
        teams,_=self.build()
        w2=teams[(teams.season==2025)&(teams.week==2)]
        # Team B allowed +.5 and ranks worse than Team A allowing -.3
        self.assertLess(w2[w2.team=="A"].iloc[0]["def_rank"],
                        w2[w2.team=="B"].iloc[0]["def_rank"])

    def test_non_run_pass_plays_and_null_epa_are_skipped(self):
        raw=self.sample()
        raw.loc[raw.index[0],"play_type"]="kickoff"
        raw.loc[raw.index[1],"epa"]=None
        games,eligible=ratings.games_and_plays(raw)
        self.assertEqual(len(eligible),len(raw)-2)
        self.assertEqual(len(games),6)

if __name__=="__main__":unittest.main()

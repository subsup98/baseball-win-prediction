# Feature Stability Summary

Source: `outputs\experiments\season_holdout_confirmed_2021_2025_with_park_factors_statcast`

## Stable Features In Both Feature Importance And SHAP

                         stable_feature
        away_bullpen_fip_season_to_date
       away_bullpen_whip_season_to_date
                away_lineup_bottom4_ops
  away_sp_hard_hit_rate_allowed_to_date
        away_sp_kbb_rate_season_to_date
away_team_runs_allowed_per_game_to_date
        away_team_runs_per_game_to_date
          away_team_woba_season_to_date
        home_bullpen_fip_season_to_date
       home_bullpen_whip_season_to_date
home_team_runs_allowed_per_game_to_date
        home_team_runs_per_game_to_date
                         team_woba_diff

## Feature Importance Top Stability

                                  feature  top_count  mean_rank  mean_value
  home_team_runs_allowed_per_game_to_date          4   1.750000    0.014376
  away_team_runs_allowed_per_game_to_date          4   1.750000    0.014191
                           team_woba_diff          4   4.000000    0.012533
         away_bullpen_whip_season_to_date          4   6.750000    0.012359
          home_team_runs_per_game_to_date          4  10.750000    0.010840
          home_bullpen_fip_season_to_date          4  11.750000    0.010568
                  away_lineup_bottom4_ops          4  12.500000    0.010574
         home_bullpen_whip_season_to_date          3   6.333333    0.011159
          away_bullpen_fip_season_to_date          3   6.666667    0.011117
          away_sp_kbb_rate_season_to_date          3   8.333333    0.011089
    away_sp_hard_hit_rate_allowed_to_date          3   8.666667    0.011097
          away_team_runs_per_game_to_date          3  10.000000    0.010930
            away_team_woba_season_to_date          3  10.000000    0.010871
                   home_team_ops_last_30d          3  14.333333    0.010106
away_sp_avg_exit_velocity_allowed_to_date          3  16.000000    0.010191
             away_team_ops_season_to_date          2  10.000000    0.010931
                   away_team_ops_last_30d          2  11.500000    0.010740
             home_team_ops_season_to_date          2  12.000000    0.010578
            away_lineup_avg_exit_velocity          2  13.000000    0.010312
                       sp_whiff_rate_diff          2  14.500000    0.010656
            home_team_woba_season_to_date          2  14.500000    0.010061
                home_lineup_hard_hit_rate          2  15.000000    0.010449
                   away_team_ops_last_14d          2  15.000000    0.010424
      away_sp_breaking_ball_usage_to_date          1   5.000000    0.011814
                  home_lineup_vs_rhp_woba          1  12.000000    0.010924

## SHAP Top Stability

                                feature  top_count  mean_rank  mean_value
home_team_runs_allowed_per_game_to_date          4   1.750000    0.008864
away_team_runs_allowed_per_game_to_date          4   1.750000    0.008500
                         team_woba_diff          4   3.250000    0.007783
        away_team_runs_per_game_to_date          4   6.500000    0.005763
          away_team_woba_season_to_date          4   7.500000    0.005534
        home_team_runs_per_game_to_date          4   9.250000    0.004564
  away_sp_hard_hit_rate_allowed_to_date          4  10.000000    0.004488
           away_team_ops_season_to_date          4  10.750000    0.004756
                     sp_whiff_rate_diff          4  11.500000    0.004609
       away_bullpen_whip_season_to_date          3   6.333333    0.005603
        away_sp_kbb_rate_season_to_date          3   7.333333    0.005186
       home_bullpen_whip_season_to_date          3   9.333333    0.004620
        away_bullpen_fip_season_to_date          3  14.333333    0.003949
        home_bullpen_fip_season_to_date          3  15.333333    0.003763
                            sp_fip_diff          3  16.000000    0.003695
                away_lineup_bottom4_ops          3  16.333333    0.003557
    away_sp_breaking_ball_usage_to_date          2  11.000000    0.004543
         sp_statcast_xwoba_allowed_diff          2  11.500000    0.004476
             home_sp_fip_season_to_date          2  13.000000    0.004089
          home_team_woba_season_to_date          2  13.000000    0.004010
                 away_team_ops_last_30d          2  14.000000    0.004172
           home_team_ops_season_to_date          2  15.500000    0.003623
             away_sp_whiff_rate_to_date          2  16.500000    0.003562
            away_sp_whip_season_to_date          1  11.000000    0.003972
           home_sp_ip_avg_last_3_starts          1  12.000000    0.004447

## Readout

Stable signal is concentrated in team form, run prevention, bullpen FIP/WHIP, and starter K-BB/FIP style features. Low-stability one-off features should be treated as pruning/watchlist candidates only after grouped ablation, not from importance alone.

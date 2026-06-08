-- Kommende kamper: det modellen skal forutsi.
select
    match_date,
    home_team,
    away_team,
    neutral,
    tournament
from {{ ref('stg_matches') }}
where not is_played
order by match_date

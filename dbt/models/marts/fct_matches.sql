-- Spilte landskamper: treningsgrunnlaget for modellen.
select
    match_date,
    home_team,
    away_team,
    home_score,
    away_score,
    neutral,
    tournament
from {{ ref('stg_matches') }}
where is_played

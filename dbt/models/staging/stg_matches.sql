-- Renser rådata og merker hver kamp som spilt eller kommende.
with source as (
    select * from {{ source('raw', 'raw_results') }}
)

select
    cast(date as date)                                   as match_date,
    home_team,
    away_team,
    home_score,
    away_score,
    tournament,
    neutral,
    (home_score is not null and away_score is not null)  as is_played
from source

-- Hver spillers andel av lagets mål (siden 2022, ekskl. selvmål).
with goals as (
    select team, scorer
    from {{ source('raw', 'raw_goalscorers') }}
    where date >= '2022-01-01'
      and scorer is not null
      and coalesce(own_goal, false) = false
),
per_player as (
    select team, scorer, count(*) as goals
    from goals
    group by team, scorer
)
select
    team,
    scorer,
    goals,
    sum(goals) over (partition by team)                  as team_goals,
    goals::double / sum(goals) over (partition by team)  as share
from per_player

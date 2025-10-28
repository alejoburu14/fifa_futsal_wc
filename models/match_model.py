from dataclasses import dataclass

@dataclass(frozen=True)
class Match:
    MatchId: str
    GroupName: str
    StageName: str
    HomeId: str
    HomeName: str
    AwayId: str
    AwayName: str
    KickoffDate: str

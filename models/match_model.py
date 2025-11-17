"""
Small data model for a match row.

This lightweight dataclass is a convenience wrapper that documents the
expected fields for a match record. The class is frozen (immutable) to make
it safer to pass around without accidental modification.

Fields mirror the keys returned by the API and used throughout the app:
    - `MatchId`, `GroupName`, `StageName`, `HomeId`, `HomeName`, `AwayId`,
        `AwayName`, `KickoffDate`.
"""

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

# common/ml_labels.py
"""
Labels, descriptions, and colors used by the Team Profiles page.

The clustering model produces numeric clusters, but numeric IDs are not
meaningful for users. This file centralizes the mapping from cluster IDs
to readable tactical profile names and short descriptions.
"""

from __future__ import annotations

# Fixed display order used across the app
CLUSTER_ORDER = [
    "High-Intensity Attackers",
    "Efficient Finishers",
    "Low-Intensity Teams",
]

# Human-readable descriptions shown in the UI
CLUSTER_DESCRIPTIONS = {
    "High-Intensity Attackers": (
        "Teams that generate a high volume of attacking actions per match. "
        "They tend to apply sustained offensive pressure and create many attempts."
    ),
    "Efficient Finishers": (
        "Teams that may attack less often, but convert a relatively high share of "
        "their attempts into goals. Their offensive profile is defined by efficiency."
    ),
    "Low-Intensity Teams": (
        "Teams with lower attacking volume and lower offensive output. "
        "They may rely on more conservative or reactive match approaches."
    ),
}

# Optional helper colors for charts
CLUSTER_COLORS = {
    "High-Intensity Attackers": "#1f77b4",
    "Efficient Finishers": "#2ca02c",
    "Low-Intensity Teams": "#7f7f7f",
}
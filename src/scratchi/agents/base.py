"""Base protocol for scoring agents."""

from typing import Protocol

from scratchi.models.plan import Plan
from scratchi.models.user import UserProfile


class ScoringAgent(Protocol):
    """Protocol for scoring agents that evaluate plans against user profiles.

    All scoring agents should implement this interface to ensure consistent
    scoring behavior across the recommendation engine.
    """

    def score(self, plan: Plan, user_profile: UserProfile) -> float:
        """Score a plan against a user profile.

        Args:
            plan: Plan to score
            user_profile: User profile with preferences and requirements

        Returns:
            Score between 0.0 and 1.0 (higher is better)
        """
        ...

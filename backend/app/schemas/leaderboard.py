from pydantic import BaseModel


class LeaderboardEntryOut(BaseModel):
    rank: int
    display_name: str
    # Deliberately no balance field -- only the bracket is ever exposed,
    # enforced here rather than trusted to the frontend to hide.
    credit_bracket: str

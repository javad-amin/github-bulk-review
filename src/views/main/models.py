from enum import Enum

from attr import dataclass


class PullRequestAction(Enum):
    NONE = "none"
    COMMENT = "comment"
    APPROVE = "approve"
    APPROVE_AND_MERGE = "approve_and_merge"


@dataclass
class PullRequestReview:
    selection_result: dict
    comment: str
    action: PullRequestAction

from dataclasses import dataclass
from enum import Enum
from typing import Self

from github.PullRequest import PullRequest

from config import GithubConfig


@dataclass
class PullRequestQuery:
    org_name: str
    review_requested_user: str
    author: str
    title: str
    reviewed_by: str
    check_github_actions: bool = False
    fetch_prs: bool = False

    def __post_init__(self: Self) -> None:
        for field_name, field_value in self.__dict__.items():
            if field_name != "self" and field_value is not None:
                GithubConfig().update(field_name, str(field_value))


class PullRequestAction(Enum):
    NONE = "none"
    COMMENT = "comment"
    APPROVE = "approve"
    MERGE = "merge"
    APPROVE_AND_MERGE = "approve_and_merge"


@dataclass
class PullRequestReview:
    selection_result: dict[PullRequest, bool]
    comment: str
    action: PullRequestAction

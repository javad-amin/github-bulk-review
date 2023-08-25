from dataclasses import dataclass
from enum import Enum
from typing import Self

from github.PullRequest import PullRequest

from gh_requests.config import GithubConfig


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


@dataclass
class PullRequestWithDetails:
    pr: PullRequest
    title: str
    user: str
    name: str
    number: int
    html_url: str
    needs_rebase: bool
    is_approved: bool
    github_action_checked: bool = False
    is_ready_to_merge: bool = False
    is_merged: bool = False


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

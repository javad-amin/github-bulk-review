from dataclasses import dataclass
from typing import Self

from github import Github
from github.PullRequest import PullRequest

from config import GithubConfig


@dataclass
class SearchParameters:
    org_name: str
    review_requested_user: str
    author: str
    title: str
    reviewed_by: str

    def __post_init__(self: Self) -> None:
        for field_name, field_value in self.__dict__.items():
            if field_name != "self" and field_value is not None:
                GithubConfig().update(field_name, str(field_value))


def fetch_pull_requests(fetch_pr_filter: SearchParameters, token: str) -> list[PullRequest]:
    g = Github(token)

    filter_params = "is:pr is:open archived:false"
    if fetch_pr_filter.org_name:
        filter_params += f" org:{fetch_pr_filter.org_name}"
    if fetch_pr_filter.review_requested_user:
        filter_params += f" review-requested:{fetch_pr_filter.review_requested_user}"
    if fetch_pr_filter.reviewed_by:
        filter_params += f" reviewed-by:{fetch_pr_filter.reviewed_by}"
    if fetch_pr_filter.author:
        filter_params += f" author:{fetch_pr_filter.author}"
    if fetch_pr_filter.title:
        filter_params += f" in:title {fetch_pr_filter.title}"

    issues = g.search_issues(query=filter_params)

    pull_requests = []
    for issue in issues:
        if issue.pull_request:
            pr = issue.as_pull_request()
            pull_requests.append(pr)

    return pull_requests

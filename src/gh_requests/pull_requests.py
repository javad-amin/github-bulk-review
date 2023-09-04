from functools import partial
from itertools import chain
from typing import Generator, Iterable, Iterator

import streamlit as st
from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest

from gh_requests.executor import default_executor
from gh_requests.models import PullRequestQuery, PullRequestWithDetails


@st.cache_data(ttl=300, show_spinner=False)
def fetch_pull_requests(pull_request_query: PullRequestQuery) -> Generator[PullRequestWithDetails, None, None]:
    gh = Github(st.session_state.token)

    filter_params = "is:pr is:open archived:false"
    if pull_request_query.org_name:
        filter_params += f" org:{pull_request_query.org_name}"
    if pull_request_query.review_requested_user:
        filter_params += f" review-requested:{pull_request_query.review_requested_user}"
    if pull_request_query.reviewed_by:
        filter_params += f" reviewed-by:{pull_request_query.reviewed_by}"
    if pull_request_query.author:
        filter_params += f" author:{pull_request_query.author}"
    if pull_request_query.title:
        filter_params += f" in:title {pull_request_query.title}"

    issues = list(gh.search_issues(query=filter_params))
    for pr_with_details in _fetch_prs_concurrently(issues, pull_request_query.check_github_actions):
        yield pr_with_details


def fetch_updated_pull_requests(
    current_pull_requests: list[PullRequest], modified_pull_requests: list[PullRequest]
) -> list[PullRequest]:
    gh = Github(st.session_state.token)
    updated_prs = _fetch_updated_prs_concurrently(gh, modified_pull_requests)
    return list(_combine_prs_with_precedence(current_pull_requests, updated_prs))


def _fetch_prs_concurrently(
    issues: list[Issue],
    check_github_actions: bool,
) -> Generator[PullRequestWithDetails, None, None]:
    with default_executor() as task_pool:
        for pr_with_details in task_pool.map(
            partial(_fetch_pr, check_github_actions),
            issues,
        ):
            yield pr_with_details


def _fetch_pr(check_github_actions: bool, issue: Issue) -> PullRequestWithDetails:
    return _add_pr_details(issue.as_pull_request(), check_github_actions)


def _fetch_updated_prs_concurrently(
    gh: Github,
    prs: list[PullRequest],
    check_github_actions: bool = False,
) -> Iterator[PullRequestWithDetails]:
    with default_executor() as task_pool:
        return task_pool.map(partial(_fetch_updated_pr, gh, check_github_actions), prs)


def _fetch_updated_pr(gh: Github, check_github_actions: bool, pr: PullRequest) -> PullRequest:
    return _add_pr_details(gh.get_repo(pr.base.repo.full_name).get_pull(pr.number), check_github_actions)


def _add_pr_details(pr: PullRequest, check_github_actions: bool) -> PullRequestWithDetails:
    return PullRequestWithDetails(
        pr=pr,
        title=pr.title,
        user=pr.user.login,
        name=pr.base.repo.full_name,
        number=pr.number,
        html_url=pr.html_url,
        needs_rebase=not pr.mergeable,
        is_approved=_is_approved(pr),
        github_action_checked=check_github_actions,
        is_ready_to_merge=is_ready_to_merge(pr) if check_github_actions else False,
        is_merged=pr.merged,
    )


def _combine_prs_with_precedence(a: Iterable[PullRequest], b: Iterable[PullRequest]) -> Iterable[PullRequest]:
    # PRs in B take precedence over ones in A, as they follow in the chain
    pr_map = {pr.number: pr for pr in chain(a, b)}
    return pr_map.values()


def _is_approved(pr: PullRequest) -> bool:
    approved_reviews = 0

    for review in pr.get_reviews():
        if review.state == "APPROVED":
            approved_reviews += 1
        elif review.state == "CHANGES_REQUESTED":
            return False
    return approved_reviews > 0


def is_ready_to_merge(pr: PullRequest) -> bool:
    head_commit = pr.head.sha

    check_runs = pr.base.repo.get_commit(head_commit).get_check_runs()

    github_action_status = True
    for check_run in check_runs:
        if check_run.app.name in [
            "GitHub Actions",
            "GitHub Code Scanning",
        ] and check_run.conclusion not in [
            "success",
            "skipped",
            "neutral",
        ]:
            github_action_status = False

    return bool(pr.mergeable and github_action_status)

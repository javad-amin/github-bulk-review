from concurrent.futures import Executor, ThreadPoolExecutor
from functools import partial
from itertools import chain
from typing import Iterable

import streamlit as st
from github import Github
from github.Issue import Issue
from github.PullRequest import PullRequest

from models import PullRequestQuery

DEFAULT_EXECUTOR = ThreadPoolExecutor(max_workers=4)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_pull_requests(pull_request_query: PullRequestQuery) -> list[PullRequest]:
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

    issues = gh.search_issues(query=filter_params)
    return list(_fetch_prs_concurrently(issues))


def fetch_updated_pull_requests(
    current_pull_requests: list[PullRequest], modified_pull_requests: list[PullRequest]
) -> list[PullRequest]:
    gh = Github(st.session_state.token)
    updated_prs = _fetch_updated_prs_concurrently(gh, modified_pull_requests)
    return list(_merge_pr_lists(current_pull_requests, updated_prs))


def _fetch_prs_concurrently(
    issues: Iterable[Issue],
    *,
    executor: Executor = DEFAULT_EXECUTOR,
) -> Iterable[PullRequest]:
    with executor as task_pool:
        return task_pool.map(Issue.as_pull_request, issues)


def _fetch_updated_prs_concurrently(
    gh: Github,
    prs: Iterable[PullRequest],
    *,
    executor: Executor = DEFAULT_EXECUTOR,
) -> Iterable[PullRequest]:
    with executor as task_pool:
        return task_pool.map(partial(_fetch_updated_pr, gh), prs)


def _fetch_updated_pr(gh: Github, pr: PullRequest) -> PullRequest:
    return gh.get_repo(pr.base.repo.full_name).get_pull(pr.number)


def _merge_pr_lists(a: Iterable[PullRequest], b: Iterable[PullRequest]) -> Iterable[PullRequest]:
    # PRs in B take precedence over ones in A, as they follow in the chain
    pr_map = {pr.number: pr for pr in chain(a, b)}
    return pr_map.values()

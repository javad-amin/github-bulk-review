import streamlit as st
from github import Github
from github.PullRequest import PullRequest

from models import PullRequestQuery


@st.cache_data(ttl=300, show_spinner=False)
def fetch_pull_requests(pull_request_query: PullRequestQuery) -> list[PullRequest]:
    g = Github(st.session_state.token)

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

    issues = g.search_issues(query=filter_params)

    pull_requests = []
    for issue in issues:
        if issue.pull_request:
            pr = issue.as_pull_request()
            pull_requests.append(pr)

    return pull_requests


def fetch_updated_pull_requests(
    current_pull_requests: list[PullRequest], modified_pull_requests: list[PullRequest]
) -> list[PullRequest]:
    g = Github(st.session_state.token)
    updated_pull_requests = current_pull_requests.copy()

    for i, pr in enumerate(updated_pull_requests):
        for modified_pr in modified_pull_requests:
            if pr.number == modified_pr.number:
                repo = g.get_repo(full_name_or_id=pr.base.repo.full_name)
                updated_pr = repo.get_pull(number=pr.number)
                updated_pull_requests[i] = updated_pr
                break

    return current_pull_requests

import streamlit as st
from github import Github
from github.PullRequest import PullRequest

from models import PullRequestQuery


@st.cache_data(ttl=300, show_spinner=False)
def fetch_pull_requests(pull_request_query: PullRequestQuery, token: str) -> list[PullRequest]:
    g = Github(token)

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

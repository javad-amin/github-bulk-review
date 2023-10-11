import streamlit as st

from gh_requests.config import GithubConfig
from gh_requests.models import PullRequestQuery


def pull_request_query_form() -> PullRequestQuery:
    pull_request_query = PullRequestQuery(
        org_name=st.sidebar.text_input(
            "Organization name (optional):",
            value=GithubConfig().get("org_name"),
        ),
        review_requested_user=st.sidebar.text_input(
            "Review requested from user (optional):",
            value=GithubConfig().get("review_requested_user"),
        ),
        author=st.sidebar.text_input(
            "Author name (optional):",
            value=GithubConfig().get("author"),
        ),
        title=st.sidebar.text_input(
            "Title (optional):",
            value=GithubConfig().get("title"),
        ),
        reviewed_by=st.sidebar.text_input(
            "Reviewed by (optional):",
            value=GithubConfig().get("reviewed_by"),
        ),
    )

    if not any(
        [
            pull_request_query.org_name,
            pull_request_query.review_requested_user,
            pull_request_query.author,
            pull_request_query.title,
            pull_request_query.reviewed_by,
        ]
    ):
        st.sidebar.warning("No filter is set, will fetch all open pull requests on Github! Good luck!")

    pull_request_query.check_github_actions = st.sidebar.checkbox("Github Action Status", value=False)
    if pull_request_query.check_github_actions:
        st.sidebar.warning("Note that this option is slow due to multiple API calls.")

    pull_request_query.fetch_prs = st.sidebar.button("Fetch Pull Requests")

    return pull_request_query

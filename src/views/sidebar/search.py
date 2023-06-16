import streamlit as st

from config import GithubConfig
from pull_requests import SearchParameters


def pull_request_search_inputs() -> SearchParameters:
    fetch_pr_filter = SearchParameters(
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
            fetch_pr_filter.org_name,
            fetch_pr_filter.review_requested_user,
            fetch_pr_filter.author,
            fetch_pr_filter.title,
            fetch_pr_filter.reviewed_by,
        ]
    ):
        st.sidebar.warning("No filter is set, will fetch all open pull requests on Github! Good luck!")

    return fetch_pr_filter

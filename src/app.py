import time
from configparser import ConfigParser

import streamlit as st
from github import Github
from github.PullRequest import PullRequest

from config import GithubConfig
from pull_requests import SearchParameters

github_config = GithubConfig()


def main() -> None:
    github_config.setup_config()

    if "pull_requests" not in st.session_state:
        st.session_state.pull_requests = []

    token = github_token_view()

    if token:
        pr_fetch_view(token)


def github_token_view() -> str:
    token = github_config.get("token")

    st.sidebar.title("GitHub Bulk Review")
    with st.sidebar.expander("Github Token", expanded=False if token else True):
        if token:
            new_token = prompt_remove_token()
        else:
            new_token = prompt_github_token()

    return token or new_token


def pr_fetch_view(token: str) -> None:
    fetch_pr_filter = input_fetch_pr_filter()

    if st.sidebar.button("Fetch Pull Requests"):
        st.session_state.pull_requests = fetch_pull_requests(fetch_pr_filter, token)

    selection_result = {}

    select_all = st.checkbox("Select/Deselect All", value=False)

    with st.form("pr_selection"):
        for pr in st.session_state.pull_requests:
            checked = st.checkbox(
                f"{pr.base.repo.full_name} | {pr.title} by {pr.user.login} | [{pr.number}]({pr.html_url}) ",
                value=select_all,
            )
            selection_result[pr] = checked
        comment_text = st.text_input(
            label="Approval comment:",
            value=github_config.get("comment_text"),
        )
        github_config.update("comment_text", comment_text)

        comment_only = st.form_submit_button(
            label="Add comment without approval",
        )
        approved = st.form_submit_button(
            label="Approve Selected Pull Requests",
        )
        approve_and_merge = st.form_submit_button(
            label="Approve and Merge Selected Pull Requests",
        )

    if comment_only:
        if not st.session_state.pull_requests:
            st.warning("Nothing to comment on, fetch pull requests!")
        else:
            number_of_prs_selected = 0
            for pr, selected in selection_result.items():
                if selected:
                    pr.create_comment(comment_text)
                    st.write(f"Comment added to {pr}")
                    number_of_prs_selected += 1
            if number_of_prs_selected:
                st.success(
                    f"Comment added to {number_of_prs_selected} selected pull requests."
                )
            else:
                st.warning(f"No pull requests selected.")
            st.warning(
                "Note: Fetch again to comment on more Pull Requests, the list above is cleared."
            )

    if approved or approve_and_merge:
        if not st.session_state.pull_requests:
            st.warning("Nothing to approve, fetch pull requests!")
        else:
            number_of_prs_selected = 0
            for pr, approved in selection_result.items():
                if approved:
                    approval_response = pr.create_review(
                        body=comment_text, event="APPROVE"
                    )
                    if approval_response.state != "APPROVED":
                        st.warning(
                            f"Something went wrong while approving the {pr}, response body: {approval_response.body}!"
                        )
                    st.write(pr, "was approved")
                    number_of_prs_selected += 1
                    if approve_and_merge:
                        time.sleep(1)
                        pr.merge()
                        st.write(pr, "was merged")
                    else:
                        time.sleep(1)
            if number_of_prs_selected:
                st.success(
                    f'Approved {number_of_prs_selected} selected pull requests with comment: "{comment_text}"'
                )
                st.warning(
                    "Note: Fetch again to approve more Pull Requests, the list above is cleared."
                )
            else:
                st.warning(f"No pull requests selected.")

        # Clear the pull request list after the approval.
        st.session_state.pull_requests = []


def input_fetch_pr_filter() -> SearchParameters:
    fetch_pr_filter = SearchParameters(
        org_name=st.sidebar.text_input(
            "Organization name (optional):",
            value=github_config.get("org_name"),
        ),
        review_requested_user=st.sidebar.text_input(
            "Review requested from user (optional):",
            value=github_config.get("review_requested_user"),
        ),
        author=st.sidebar.text_input(
            "Author name (optional):",
            value=github_config.get("author"),
        ),
        title=st.sidebar.text_input(
            "Title (optional):",
            value=github_config.get("title"),
        ),
        reviewed_by=st.sidebar.text_input(
            "Reviewed by (optional):",
            value=github_config.get("reviewed_by"),
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
        st.sidebar.warning(
            "No filter is set, will fetch all open pull requests on Github! Good luck!"
        )

    return fetch_pr_filter


def prompt_remove_token():
    if st.button("Remove Github token"):
        github_config.update("token", "")
        st.success("Token removed successfully!")
        return prompt_github_token()


def prompt_github_token() -> str | None:
    new_token = st.text_input("Enter your GitHub token:", type="password")

    if st.button("Save Github Token"):
        github_config.update("token", new_token)

        st.success("Token saved successfully!")
        return new_token
    return None


def fetch_pull_requests(
    fetch_pr_filter: SearchParameters, token: str
) -> list[PullRequest]:
    g = Github(token)

    filter_params = f"is:pr is:open archived:false"
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


if __name__ == "__main__":
    main()

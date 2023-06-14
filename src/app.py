import time
from configparser import ConfigParser
from dataclasses import dataclass

import streamlit as st
from github import Github

CONFIG_FILE = "config.ini"


@dataclass
class FetchPullRequestFilter:
    org_name: str
    review_requested_user: str
    author: str
    title: str


def main() -> None:
    config = setup_config()

    if "pull_requests" not in st.session_state:
        st.session_state.pull_requests = []

    token = github_token_view(config)

    if token:
        pr_fetch_view(config, token)


def github_token_view(config: ConfigParser) -> str:
    token = config.get("GitHub", "token", fallback="")

    st.sidebar.title("GitHub Bulk Review")
    with st.sidebar.expander("Github Token", expanded=False if token else True):
        if token:
            new_token = prompt_remove_token(config)
        else:
            new_token = prompt_github_token(config)

    return token or new_token


def pr_fetch_view(config: ConfigParser, token: str) -> None:
    fetch_pr_filter = input_fetch_pr_filter(config)

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
        approval_comment = st.text_input(
            label="Approval comment:",
            value=config.get("GitHub", "approval_comment", fallback=""),
        )
        update_config_file(config, "GitHub", "approval_comment", approval_comment)

        approved = st.form_submit_button(
            label="Approve Selected Pull Requests",
        )
        approve_and_merge = st.form_submit_button(
            label="Approve and Merge Selected Pull Requests",
        )

    if approved or approve_and_merge:
        if not st.session_state.pull_requests:
            st.warning("Nothing to approve, fetch pull requests!")
        else:
            number_of_prs_approved = 0
            for pr, approved in selection_result.items():
                if approved:
                    approval_response = pr.create_review(
                        body=approval_comment, event="APPROVE"
                    )
                    if approval_response.state != "APPROVED":
                        st.warning(
                            f"Something went wrong while approving the {pr}, response body: {approval_response.body}!"
                        )
                    st.write(pr, "was approved")
                    number_of_prs_approved += 1
                    if approve_and_merge:
                        time.sleep(1)
                        pr.merge()
                        st.write(pr, "was merged")
                    else:
                        time.sleep(1)
            if number_of_prs_approved:
                st.success(
                    f'Approved {number_of_prs_approved} selected pull requests with comment: "{approval_comment}"'
                )
                st.warning(
                    "Note: Fetch again to approve more Pull Requests, the list above is cleared."
                )
            else:
                st.warning(f"No pull requests selected.")

        # Clear the pull request list after the approval.
        st.session_state.pull_requests = []


def input_fetch_pr_filter(config: ConfigParser) -> FetchPullRequestFilter:
    fetch_pr_filter = FetchPullRequestFilter(
        org_name=st.sidebar.text_input(
            "Organization name:",
            value=config.get("GitHub", "org_name", fallback=""),
        ),
        review_requested_user=st.sidebar.text_input(
            "Review requested user (optional):",
            value=config.get("GitHub", "review_requested_user", fallback=""),
        ),
        author=st.sidebar.text_input(
            "Author name (optional):",
            value=config.get("GitHub", "author", fallback=""),
        ),
        title=st.sidebar.text_input(
            "Title (optional):",
            value=config.get("GitHub", "title", fallback=""),
        ),
    )

    update_config_file(config, "GitHub", "org_name", fetch_pr_filter.org_name)
    update_config_file(
        config, "GitHub", "review_requested_user", fetch_pr_filter.review_requested_user
    )
    update_config_file(config, "GitHub", "author", fetch_pr_filter.author)
    update_config_file(config, "GitHub", "title", fetch_pr_filter.title)

    return fetch_pr_filter


def update_config_file(config: ConfigParser, section: str, key: str, value: str):
    config.set(section, key, value)
    with open(CONFIG_FILE, "w") as config_file:
        config.write(config_file)


def prompt_remove_token(config: ConfigParser):
    if st.button("Remove Github token"):
        update_config_file(config, "GitHub", "token", "")
        st.success("Token removed successfully!")
        return prompt_github_token(config)


def prompt_github_token(config: ConfigParser) -> None:
    new_token = st.text_input("Enter your GitHub token:", type="password")

    if st.button("Save Github Token"):
        update_config_file(config, "GitHub", "token", new_token)

        st.success("Token saved successfully!")
        return new_token


def fetch_pull_requests(fetch_pr_filter: FetchPullRequestFilter, token: str) -> None:
    g = Github(token)

    filter_params = f"is:pr is:open archived:false"
    if fetch_pr_filter.review_requested_user:
        filter_params += f" review-requested:{fetch_pr_filter.review_requested_user}"
    if fetch_pr_filter.author:
        filter_params += f" author:{fetch_pr_filter.author}"
    if fetch_pr_filter.title:
        filter_params += f" in:title {fetch_pr_filter.title}"

    issues = g.search_issues(query=f"org:{fetch_pr_filter.org_name} {filter_params}")

    pull_requests = []
    for issue in issues:
        if issue.pull_request:
            pr = issue.as_pull_request()
            pull_requests.append(pr)

    return pull_requests


def setup_config() -> ConfigParser:
    config = ConfigParser()
    config.read(CONFIG_FILE)
    if "GitHub" not in config.sections():
        config.add_section("GitHub")
    return config


if __name__ == "__main__":
    main()

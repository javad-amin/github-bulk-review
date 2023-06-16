import time

import streamlit as st

from config import GithubConfig
from pull_requests import fetch_pull_requests
from views.sidebar.search import pull_request_search_inputs


def pr_fetch_view(token: str) -> None:
    fetch_pr_filter = pull_request_search_inputs()

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
            value=GithubConfig().get("comment_text"),
        )
        GithubConfig().update("comment_text", comment_text)

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
                st.success(f"Comment added to {number_of_prs_selected} selected pull requests.")
            else:
                st.warning("No pull requests selected.")
            st.warning("Note: Fetch again to comment on more Pull Requests, the list above is cleared.")

    if approved or approve_and_merge:
        if not st.session_state.pull_requests:
            st.warning("Nothing to approve, fetch pull requests!")
        else:
            number_of_prs_selected = 0
            for pr, approved in selection_result.items():
                if approved:
                    approval_response = pr.create_review(body=comment_text, event="APPROVE")
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
                st.success(f'Approved {number_of_prs_selected} selected pull requests with comment: "{comment_text}"')
                st.warning("Note: Fetch again to approve more Pull Requests, the list above is cleared.")
            else:
                st.warning("No pull requests selected.")

        # Clear the pull request list after the approval.
        st.session_state.pull_requests = []

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
            label="Comment:",
            value=GithubConfig().get("comment_text"),
        )
        GithubConfig().update("comment_text", comment_text)

        comment_only = st.form_submit_button(label="Comment without approval")
        approved = st.form_submit_button(label="Approve Selected Pull Requests")
        approve_and_merge = st.form_submit_button(label="Approve and Merge Selected Pull Requests")

    if comment_only:
        _submit_comment(comment_text, selection_result)
    elif approved:
        _submit_approval(comment_text, selection_result)
    elif approve_and_merge:
        _submit_approval_and_merge(comment_text, selection_result)

        # Clear the pull request list after the approval.
        st.session_state.pull_requests = []
        st.experimental_rerun()


def _submit_comment(comment_text: str, selection_result: dict) -> None:
    _process_pull_requests(comment_text=comment_text, selection_result=selection_result, action="comment", merge=False)


def _submit_approval(comment_text: str, selection_result: dict) -> None:
    _process_pull_requests(comment_text=comment_text, selection_result=selection_result, action="approve", merge=False)


def _submit_approval_and_merge(comment_text: str, selection_result: dict) -> None:
    _process_pull_requests(comment_text=comment_text, selection_result=selection_result, action="approve", merge=True)


def _process_pull_requests(comment_text: str, selection_result: dict, action: str, merge: bool) -> None:
    if not st.session_state.pull_requests:
        st.warning("No pull request selected!")
        return

    number_of_prs_selected = 0
    for pr, selected in selection_result.items():
        if selected:
            if action == "comment":
                pr.create_comment(comment_text)
                st.write(f"Comment added to {pr}")
            elif action == "approve":
                approval_response = pr.create_review(body=comment_text, event="APPROVE")
                if approval_response.state != "APPROVED":
                    st.warning(f"Something went wrong while approving {pr}: {approval_response.body}")
                st.write(f"{pr} was approved")
                number_of_prs_selected += 1

                if merge:
                    time.sleep(1)
                    pr.merge()
                    st.write("{pr} was merged")
                else:
                    time.sleep(1)

    if number_of_prs_selected:
        st.success(f'{number_of_prs_selected} selected pull requests was acted on with comment: "{comment_text}"')
        st.session_state.pull_requests = []
        time.sleep(1)
        # TODO: Maybe instead of rerunning the whole app, we can refetch the pull requests?
        st.experimental_rerun()
    else:
        st.warning("No pull requests selected.")

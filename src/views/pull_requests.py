import time

import streamlit as st
from github.PullRequest import PullRequest

from gh_requests.config import GithubConfig
from gh_requests.models import PullRequestAction, PullRequestReview
from gh_requests.pull_requests import fetch_pull_requests, fetch_updated_pull_requests
from gh_requests.review import process_pull_request_review_concurrently
from views.messages import MessageType, RetainedMessage, write_retained_messages
from views.sidebar.search import pull_request_query_form


def pr_fetch_view() -> None:
    pull_request_query = pull_request_query_form()

    if pull_request_query.fetch_prs:
        st.session_state.retained_messaged = []
        fetch_status = st.info("Fetching pull requests, please wait!")
        pull_requests = fetch_pull_requests(pull_request_query)
        st.session_state.pull_requests = pull_requests

        fetch_status.info("All pull requests fetched!")

    pull_request_review = _pull_request_form()

    write_retained_messages()

    _process_pull_requests(pull_request_review)


def _pull_request_form() -> PullRequestReview:
    selection_result: dict[PullRequest, bool] = {}
    select_all = st.checkbox("Select/Deselect All", value=False)

    with st.form("pr_selection"):
        if st.session_state.pull_requests:
            st.write(f"{len(st.session_state.pull_requests)} pull requests found!")
        else:
            st.write("Use the sidebar to fetch pull requests!")
        for pr_with_details in st.session_state.pull_requests:
            repo_name_link = f"[{pr_with_details.name}/{pr_with_details.number}]({pr_with_details.html_url})"
            if pr_with_details.github_action_checked:
                mergability = f"{' | 🟢 Mergable' if pr_with_details.is_ready_to_merge else ' | 🔴 Not Mergable'}"
            else:
                mergability = ""
            needs_rebase = f"{' | ⚠️ Rebase required' if pr_with_details.needs_rebase else ''}"
            review_status = f"{' | ✅ Approved' if pr_with_details.is_approved else ' | ❌ Not Approved'}"
            if pr_with_details.is_merged:
                review_status += f"{' | Ⓜ️ Merged'}"
                st.write(
                    f"{repo_name_link} | {pr_with_details.title} by {pr_with_details.user}{mergability}{needs_rebase}{review_status}"
                )
                continue
            checked = st.checkbox(
                f"{repo_name_link} | {pr_with_details.title} by {pr_with_details.user}{mergability}{needs_rebase}{review_status}",
                value=select_all,
            )

            selection_result[pr_with_details] = checked

        comment_text = st.text_input(
            label="Comment:",
            value=GithubConfig().get("comment_text"),
        )
        GithubConfig().update("comment_text", comment_text)

        comment_only = st.form_submit_button(label="✎ Comment without approval")
        approved = st.form_submit_button(label="✓ Approve")
        merge = st.form_submit_button(label="⛙ Merge")
        approve_and_merge = st.form_submit_button(label="✓⛙ Approve and Merge")

    return PullRequestReview(
        selection_result=selection_result,
        comment=comment_text,
        action=_get_action(comment_only, approved, merge, approve_and_merge),
    )


def _process_pull_requests(pull_request_review: PullRequestReview) -> None:
    pull_requests = st.session_state.pull_requests
    if pull_request_review.action == PullRequestAction.NONE:
        return None

    if not pull_requests:
        st.warning("No pull request selected!")
        return None

    st.session_state.prs_to_refetch = []

    st.session_state.retained_messaged = []
    for pr, message in process_pull_request_review_concurrently(pull_request_review):
        if pr:
            st.session_state.prs_to_refetch.append(pr)
        if message and pr:
            st.session_state.retained_messaged.append(RetainedMessage(MessageType.WRITE, message))
            st.write(message)
        if message and not pr:
            st.session_state.retained_messaged.append(RetainedMessage(MessageType.WARNING, message))
            st.warning(message)

    if number_of_prs_selected := len(st.session_state.prs_to_refetch):
        success_message = f'{number_of_prs_selected} selected pull requests was acted on with comment: "{pull_request_review.comment}"'
        st.success(success_message)
        st.session_state.retained_messaged.append(RetainedMessage(MessageType.SUCCESS, success_message))

        if st.session_state.prs_to_refetch:
            with st.spinner("Re-fetching pull requests, please wait..."):
                time.sleep(5)
                updated_pull_requests = fetch_updated_pull_requests(pull_requests, st.session_state.prs_to_refetch)
                st.session_state.pull_requests = updated_pull_requests
                refetch_message = "Pull requests successfully re-fetched!"
                st.info(refetch_message)
                st.session_state.retained_messaged.append(RetainedMessage(MessageType.INFO, refetch_message))

            st.experimental_rerun()
    else:
        failure_message = "No review was submitted!"
        st.warning(failure_message)
        st.session_state.retained_messaged.append(RetainedMessage(MessageType.WARNING, failure_message))
        st.experimental_rerun()


def _get_action(comment_only: bool, approved: bool, merge: bool, approve_and_merge: bool) -> PullRequestAction:
    if comment_only:
        return PullRequestAction.COMMENT
    elif approved:
        return PullRequestAction.APPROVE
    elif merge:
        return PullRequestAction.MERGE
    elif approve_and_merge:
        return PullRequestAction.APPROVE_AND_MERGE
    else:
        return PullRequestAction.NONE

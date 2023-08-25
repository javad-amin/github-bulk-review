import time

import streamlit as st
from github.PullRequest import PullRequest

from gh_requests.config import GithubConfig
from gh_requests.models import PullRequestAction, PullRequestReview, PullRequestWithDetails
from gh_requests.pull_requests import fetch_pull_requests, fetch_updated_pull_requests
from views.sidebar.search import pull_request_query_form


def pr_fetch_view() -> None:
    pull_request_query = pull_request_query_form()

    if pull_request_query.fetch_prs:
        fetch_status = st.info("Fetching pull requests, please wait!")
        pull_requests = fetch_pull_requests(pull_request_query)
        st.session_state.pull_requests: list[PullRequestWithDetails] = pull_requests

        fetch_status.info("All pull requests fetched!")

    pull_request_review = _pull_request_form()

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
            pr_with_details: PullRequestWithDetails
            repo_name_link = f"[{pr_with_details.name}/{pr_with_details.number}]({pr_with_details.html_url})"
            if pr_with_details.github_action_checked:
                mergability = f"{' | 🟢 Mergable' if pr_with_details.is_ready_to_merge else ' | 🔴 Not Mergable'}"
            else:
                mergability = ""
            needs_rebase = f"{' | ⚠️ Rebase required' if not pr_with_details.needs_rebase else ''}"
            review_status = f"{' | ✅ Approved' if pr_with_details.is_approved else ' | ❌ Not Approved'}"
            if pr_with_details.is_merged:
                review_status += f"{' | Ⓜ️ Merged'}"
                st.write(
                    f"{repo_name_link} | {pr_with_details.title} by {pr_with_details.user.login}{mergability}{needs_rebase}{review_status}"
                )
                continue
            checked = st.checkbox(
                f"{repo_name_link} | {pr_with_details.title} by {pr_with_details.user}{mergability}{needs_rebase}{review_status}",
                value=select_all,
            )

            selection_result[pr_with_details.pr] = checked

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


# TODO: Move API calls to gh_requests/pull_requests.py
def _process_pull_requests(pull_request_review: PullRequestReview) -> None:
    pull_requests = st.session_state.pull_requests
    if pull_request_review.action == PullRequestAction.NONE:
        return None

    if not pull_requests:
        st.warning("No pull request selected!")
        return None

    number_of_prs_selected = 0
    st.session_state.prs_to_refetch = []

    for pr, selected in pull_request_review.selection_result.items():
        if selected:
            number_of_prs_selected += 1

            if pull_request_review.action == PullRequestAction.COMMENT:
                pr.create_issue_comment(pull_request_review.comment)
                st.write(f"Comment added to {pr}")

            if pull_request_review.action in [PullRequestAction.APPROVE, PullRequestAction.APPROVE_AND_MERGE]:
                approval_response = pr.create_review(body=pull_request_review.comment, event="APPROVE")
                if approval_response.state != "APPROVED":
                    st.warning(f"Something went wrong while approving {pr}: {approval_response.body}")
                st.write(f"{pr} was approved")

                time.sleep(1)

            if pull_request_review.action in [PullRequestAction.MERGE, PullRequestAction.APPROVE_AND_MERGE]:
                pr.merge()
                st.write(f"{pr} was merged")

            st.session_state.prs_to_refetch.append(pr)

    if number_of_prs_selected:
        st.success(
            f'{number_of_prs_selected} selected pull requests was acted on with comment: "{pull_request_review.comment}"'
        )
        if st.session_state.prs_to_refetch:
            updated_pull_requests = fetch_updated_pull_requests(pull_requests, st.session_state.prs_to_refetch)
            st.session_state.pull_requests = updated_pull_requests
            st.info("Pull requests were refetched.")
            time.sleep(1)
            st.experimental_rerun()
    else:
        st.warning("No pull requests selected.")


@st.cache_data(ttl=300, show_spinner=False, hash_funcs={PullRequest: lambda pr: (pr.number, pr.updated_at)})
def _is_ready_to_merge(pr: PullRequest) -> bool:
    head_commit = pr.head.sha

    # Issue this increases the number of API calls, making the app even slower
    check_runs = pr.base.repo.get_commit(head_commit).get_check_runs()

    github_action_status = True
    for check_run in check_runs:
        if check_run.app.name in [
            "GitHub Actions",
            "GitHub Code Scanning",
        ] and check_run.conclusion not in [
            "success",
            "skipped",
            "neutral",
        ]:
            github_action_status = False

    return bool(pr.mergeable and github_action_status)


@st.cache_data(ttl=300, show_spinner=False, hash_funcs={PullRequest: lambda pr: (pr.number, pr.updated_at)})
def _is_approved_with_cache(pr: PullRequest) -> bool:
    return _is_approved_no_cache(pr)


def _is_approved_no_cache(pr: PullRequest) -> bool:
    approved_reviews = 0

    for review in pr.get_reviews():
        if review.state == "APPROVED":
            approved_reviews += 1
        elif review.state == "CHANGES_REQUESTED":
            return False
    return approved_reviews > 0


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

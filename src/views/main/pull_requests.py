import time

import streamlit as st
from github.PullRequest import PullRequest

from config import GithubConfig
from pull_requests import fetch_pull_requests
from views.main.models import PullRequestAction, PullRequestReview
from views.sidebar.search import pull_request_search_inputs


def pr_fetch_view(token: str) -> None:
    fetch_pr_filter = pull_request_search_inputs()

    check_github_action = st.sidebar.checkbox("Github Action Status", value=False)
    if check_github_action:
        st.sidebar.warning("Note that this option is slow due to multiple API calls.")

    if st.sidebar.button("Fetch Pull Requests"):
        fetch_status = st.info("Fetching pull requests, please wait!")
        pull_requests = fetch_pull_requests(fetch_pr_filter, token)
        st.session_state.pull_requests = pull_requests

        fetch_status.info("All pull requests fetched!")

    pull_request_review = _pull_request_form(
        check_github_action,
    )

    _process_pull_requests(pull_request_review)


def _pull_request_form(check_github_action: bool) -> PullRequestReview:
    selection_result = {}
    select_all = st.checkbox("Select/Deselect All", value=False)

    with st.form("pr_selection"):
        if st.session_state.pull_requests:
            st.write(f"{len(st.session_state.pull_requests)} pull requests found!")
        else:
            st.write("Use the sidebar to fetch pull requests!")
        for pr in st.session_state.pull_requests:
            repo_name_link = f"[{pr.base.repo.full_name}/{pr.number}]({pr.html_url})"
            if check_github_action:
                mergability = f"{' | ✅ Mergable' if _is_ready_to_merge(pr) else ' | ❌ Not Mergable'}"
            else:
                mergability = ""
            needs_rebase = f"{' | ⚠️ Rebase required' if not pr.mergeable else ''}"
            checked = st.checkbox(
                f"{repo_name_link} | {pr.title} by {pr.user.login}{mergability}{needs_rebase}",
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

    return PullRequestReview(
        selection_result=selection_result,
        comment=comment_text,
        action=_get_action(comment_only, approved, approve_and_merge),
    )


def _process_pull_requests(pull_request_review: PullRequestReview) -> None:
    pull_requests = st.session_state.pull_requests
    if pull_request_review.action == PullRequestAction.NONE:
        return None

    if not pull_requests:
        st.warning("No pull request selected!")
        return None

    number_of_prs_selected = 0
    for pr, selected in pull_request_review.selection_result.items():
        if selected:
            number_of_prs_selected += 1
            if pull_request_review.action == PullRequestAction.COMMENT:
                pr.create_issue_comment(pull_request_review.comment)
                st.write(f"Comment added to {pr}")
            elif pull_request_review.action in [PullRequestAction.APPROVE, PullRequestAction.APPROVE_AND_MERGE]:
                approval_response = pr.create_review(body=pull_request_review.comment, event="APPROVE")
                if approval_response.state != "APPROVED":
                    st.warning(f"Something went wrong while approving {pr}: {approval_response.body}")
                st.write(f"{pr} was approved")

                time.sleep(1)
                if pull_request_review.action == PullRequestAction.ApproveAndMerge:
                    pr.merge()
                    st.write("{pr} was merged")

    if number_of_prs_selected:
        st.success(
            f'{number_of_prs_selected} selected pull requests was acted on with comment: "{pull_request_review.comment}"'
        )
        st.session_state.pull_requests = []
        # TODO: Maybe instead of rerunning the whole app, we can refetch the pull requests?
        # st.experimental_rerun()
    else:
        st.warning("No pull requests selected.")


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


def _get_action(comment_only: bool, approved: bool, approve_and_merge: bool) -> PullRequestAction:
    if comment_only:
        return PullRequestAction.COMMENT
    elif approved:
        return PullRequestAction.APPROVE
    elif approve_and_merge:
        return PullRequestAction.APPROVE_AND_MERGE
    else:
        return PullRequestAction.NONE

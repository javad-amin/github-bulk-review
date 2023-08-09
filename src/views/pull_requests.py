import asyncio
import concurrent.futures

import aiocache
import streamlit as st
from github.PullRequest import PullRequest

from config import GithubConfig
from models import PullRequestAction, PullRequestQuery, PullRequestReview
from pull_requests import fetch_pull_requests
from views.sidebar.search import pull_request_query_form


async def pr_fetch_view(token: str) -> None:
    pull_request_query = pull_request_query_form()

    if pull_request_query.fetch_prs:
        fetch_status = st.info("Fetching pull requests, please wait!")
        pull_requests = await fetch_pull_requests(pull_request_query, token)
        st.session_state.pull_requests = pull_requests

        fetch_status.info("All pull requests fetched!")

    pull_request_review = await _pull_request_form(pull_request_query)

    await _process_pull_requests(pull_request_review)


async def _pull_request_form(pull_request_query: PullRequestQuery) -> PullRequestReview:
    selection_result: dict[PullRequest, bool] = {}
    select_all = st.checkbox("Select/Deselect All", value=False)

    with st.form("pr_selection"):
        if st.session_state.pull_requests:
            st.write(f"{len(st.session_state.pull_requests)} pull requests found!")
        else:
            st.write("Use the sidebar to fetch pull requests!")
        for pr in st.session_state.pull_requests:
            repo_name_link = f"[{pr.base.repo.full_name}/{pr.number}]({pr.html_url})"
            if pull_request_query.check_github_actions:
                mergability_check = await _is_ready_to_merge(pr)
                mergability = f"{' | ✅ Mergable' if mergability_check else ' | ❌ Not Mergable'}"
            else:
                mergability = ""
            needs_rebase = f"{' | ⚠️ Rebase required' if not pr.mergeable else ''}"
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


async def _process_pull_requests(pull_request_review: PullRequestReview) -> None:
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

                await asyncio.sleep(1)
                if pull_request_review.action == PullRequestAction.APPROVE_AND_MERGE:
                    await pr.merge()
                    st.write(f"{pr} was merged")

    if number_of_prs_selected:
        st.success(
            f'{number_of_prs_selected} selected pull requests was acted on with comment: "{pull_request_review.comment}"'
        )
        st.session_state.pull_requests = []
        # TODO: Maybe instead of rerunning the whole app, we can refetch the pull requests?
        # st.experimental_rerun()
    else:
        st.warning("No pull requests selected.")


@aiocache.cached(ttl=300)
async def _is_ready_to_merge(pr: PullRequest) -> bool:
    head_commit = pr.head.sha

    loop = asyncio.get_running_loop()

    def fetch_sync():
        return pr.base.repo.get_commit(head_commit).get_check_runs()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        check_runs = await loop.run_in_executor(executor, fetch_sync)

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

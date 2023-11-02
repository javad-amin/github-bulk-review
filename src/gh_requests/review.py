import datetime
import time
from functools import partial
from typing import Generator

import streamlit
from github import Github, GithubException
from github.PullRequest import PullRequest

from gh_requests.executor import default_executor
from gh_requests.models import PullRequestAction, PullRequestReview, PullRequestWithDetails
from gh_requests.pull_requests import is_ready_to_merge


# TODO: seems useless remove
def process_pull_request_review_concurrently_with_pause(
    pull_request_review: PullRequestReview,
    batch_size: int = 10,
    delay_seconds: int = 1,
) -> Generator[tuple[PullRequest, str], None, None]:
    pr_items = list(pull_request_review.selection_result.items())
    batches = [
        PullRequestReview(
            action=pull_request_review.action,
            comment=pull_request_review.comment,
            selection_result=dict(
                pr_items[i : i + batch_size],
            ),
        )
        for i in range(0, len(pr_items), batch_size)
    ]
    for batch in batches:
        yield from process_pull_request_review_concurrently(batch)
        time.sleep(delay_seconds)


def process_pull_request_review_concurrently(
    pull_request_review: PullRequestReview,
) -> Generator[tuple[PullRequest, str], None, None]:
    with default_executor() as task_pool:
        for pr, message in task_pool.map(
            partial(
                process_pull_request_review,
                action=pull_request_review.action,
                comment=pull_request_review.comment,
            ),
            pull_request_review.selection_result.items(),
        ):
            yield pr, message


def process_pull_request_review(
    pull_request_to_review: tuple[PullRequestWithDetails, bool],
    action: PullRequestAction,
    comment: str,
) -> tuple[PullRequest | None, str]:
    pr_with_details, selected = pull_request_to_review
    pr: PullRequest = pr_with_details.pr

    if selected:
        if action == PullRequestAction.COMMENT:
            response = pr.create_issue_comment(comment)

            # TODO avoid hitting secondary rate limit

            rate_limit_headers = response._headers
            reset_time = datetime.datetime.fromtimestamp(int(rate_limit_headers.get("x-ratelimit-reset")))
            reset_time_str = reset_time.strftime("%Y-%m-%d %H:%M:%S")
            print("rate_limit_headers:", rate_limit_headers)
            print("secondary Rate Limit Limit:", rate_limit_headers.get("x-ratelimit-limit"))
            print("secondary Rate Limit Remaining:", rate_limit_headers.get("x-ratelimit-remaining"))
            print("secondary Rate Limit Used:", rate_limit_headers.get("x-ratelimit-used"))
            print("secondary Rate Limit Reset Timestamp:", reset_time_str)

            return pr, f"Comment added to {pr}"

        if action in [PullRequestAction.APPROVE, PullRequestAction.APPROVE_AND_MERGE]:
            approval_response = pr.create_review(body=comment, event="APPROVE")
            if approval_response.state != "APPROVED":
                return None, f"Something went wrong while approving {pr}: {approval_response.body}"
            return pr, f"{pr} was approved"

        if action in [PullRequestAction.MERGE, PullRequestAction.APPROVE_AND_MERGE]:
            if pr_with_details.needs_rebase:
                return None, f"{pr} was not merged as it needs rebase!"
            if not pr_with_details.is_approved:
                return None, f"{pr} was not merged as it is not approved!"
            if pr_with_details.is_merged:
                return None, f"{pr} was not merged as it is already merged!"
            if not pr_with_details.is_ready_to_merge:
                # Recheck as the user might have not checked the github actions checkbox
                if not is_ready_to_merge(pr):
                    return None, f"{pr} was not merged as it is not ready to merge, could be due to github actions!"
            try:
                merge_response = pr.merge()
                if merge_response.merged:
                    return pr, f"{pr} was merged!"
                else:
                    return None, f"{pr} was not merged!"

            except GithubException as e:
                return None, f"{pr} was not merged! Error: {e}"

    return None, ""

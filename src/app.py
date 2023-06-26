import streamlit as st

from config import GithubConfig
from views.main.pull_requests import pr_fetch_view
from views.sidebar.token import github_token_view


def main() -> None:
    GithubConfig().setup_config()
    st.set_page_config(
        page_title="GitHub Bulk Review",
        page_icon="💎",
        layout="wide",
    )

    if "pull_requests" not in st.session_state:
        st.session_state.pull_requests = []

    token = github_token_view()

    if token:
        pr_fetch_view(token)


if __name__ == "__main__":
    main()

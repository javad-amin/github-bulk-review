import asyncio

import streamlit as st

from config import GithubConfig
from views.pull_requests import pr_fetch_view
from views.sidebar.token import github_token_form


def main() -> None:
    GithubConfig().setup_config()
    st.set_page_config(
        page_title="GitHub Bulk Review",
        page_icon="💎",
        layout="wide",
    )

    if "pull_requests" not in st.session_state:
        st.session_state.pull_requests = []

    if token := github_token_form():
        asyncio.run(pr_fetch_view(token))


if __name__ == "__main__":
    main()

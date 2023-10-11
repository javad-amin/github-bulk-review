import streamlit as st

from gh_requests.config import GithubConfig
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

    if "prs_to_refetch" not in st.session_state:
        st.session_state.prs_to_refetch = []

    if "retained_messaged" not in st.session_state:
        st.session_state.retained_messaged = []

    if token := github_token_form():
        if "token" not in st.session_state:
            st.session_state.token = token
        pr_fetch_view()


if __name__ == "__main__":
    main()

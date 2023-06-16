import streamlit as st

from config import GithubConfig


def github_token_view() -> str | None:
    token = GithubConfig().get("token")

    st.sidebar.title("GitHub Bulk Review")
    with st.sidebar.expander("Github Token", expanded=not token):
        if token:
            new_token = prompt_remove_token()
        else:
            new_token = prompt_github_token()

    return token or new_token


def prompt_remove_token() -> str | None:
    if st.button("Remove Github token"):
        GithubConfig().update("token", "")
        st.success("Token removed successfully!")
        return prompt_github_token()
    return None


def prompt_github_token() -> str | None:
    new_token = st.text_input("Enter your GitHub token:", type="password")

    if st.button("Save Github Token"):
        GithubConfig().update("token", new_token)

        st.success("Token saved successfully!")
        return new_token
    return None

from configparser import ConfigParser
from dataclasses import dataclass, field

from config import GithubConfig


@dataclass
class SearchParameters:
    org_name: str = field
    review_requested_user: str = field
    author: str = field
    title: str = field
    reviewed_by: str = field

    def __post_init__(self) -> None:
        for field_name, field_value in self.__dict__.items():
            if field_name != "self" and field_value is not None:
                GithubConfig().update(field_name, str(field_value))

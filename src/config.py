from typing import Self

from configparser import ConfigParser

CONFIG_FILE_NAME = "config.ini"
DEFAULT_SECTION_NAME = "GitHub"


class GithubConfig:
    config = ConfigParser()

    def setup_config(self: Self) -> None:
        self.config.read(CONFIG_FILE_NAME)
        if DEFAULT_SECTION_NAME not in self.config.sections():
            self.config.add_section(DEFAULT_SECTION_NAME)

    def get(
        self: Self,
        key: str,
        fallback: str = "",
        section: str = DEFAULT_SECTION_NAME,
    ) -> str:
        return self.config.get(section, key, fallback=fallback)

    def update(
        self: Self,
        key: str,
        value: str,
        section: str = DEFAULT_SECTION_NAME,
    ) -> None:
        self.config.set(section, key, value)
        with open(CONFIG_FILE_NAME, "w") as config_file:
            self.config.write(config_file)

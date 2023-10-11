from dataclasses import dataclass
from enum import Enum

import streamlit as st


class MessageType(Enum):
    WRITE = "write"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"


@dataclass
class RetainedMessage:
    message_type: MessageType
    message: str


def write_retained_messages():
    for retained_message in st.session_state.retained_messaged:
        message_type = retained_message.message_type
        message = retained_message.message

        match message_type:
            case MessageType.WRITE:
                st.write(message)
            case MessageType.WARNING:
                st.warning(message)
            case MessageType.INFO:
                st.info(message)
            case MessageType.SUCCESS:
                st.success(message)
            case _:
                st.write(message)

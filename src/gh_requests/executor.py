from concurrent.futures import ThreadPoolExecutor


def default_executor() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=4)

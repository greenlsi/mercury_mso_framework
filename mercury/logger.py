import logging


logger = logging.getLogger('mercury_logger')


def set_logger_level(level=logging.DEBUG):
    logger.setLevel(level)


def add_stream_handler(stream=None, formatting='%(asctime)s %(levelname)-8s %(message)s', level=None):
    if level is None:
        level = logger.level
    ch = logging.StreamHandler(stream)
    ch.setLevel(level=level)
    ch.setFormatter(logging.Formatter(formatting))
    logger.addHandler(ch)


def add_file_handler(path='mercury.log', formatting='%(asctime)s %(levelname)-8s %(message)s', level=None):
    if level is None:
        level = logger.level
    fh = logging.FileHandler(path)
    fh.setLevel(level=level)
    fh.setFormatter(logging.Formatter(formatting))
    logger.addHandler(fh)


def logging_overhead(clock: float, overhead: str) -> str:
    return f'[t={clock:.2f}] {overhead}'

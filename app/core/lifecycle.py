from loguru import logger


class ApplicationLifecycle:
    """
    Handles startup and shutdown events.
    """

    def startup(self) -> None:
        logger.info("Starting FRIDAY...")

    def shutdown(self) -> None:
        logger.info("Shutting down FRIDAY...")
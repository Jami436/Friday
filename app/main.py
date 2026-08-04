from app.core.lifecycle import ApplicationLifecycle
from app.core.logger import logger
from app.core.config import settings

def main() -> None:
    """
    Main application entry point.
    """

    lifecycle = ApplicationLifecycle()

    try:
        lifecycle.startup()

        logger.info(
            f"{settings.app_name} v{settings.app_version} is ready."
        )

    except Exception as e:
        logger.error(f"Application error: {e}")

    finally:
        lifecycle.shutdown()

if __name__ == "__main__":
    main()
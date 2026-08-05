from app.container import build_container
from app.core.logger import logger


def main() -> None:
    container = build_container()
    container.lifecycle.startup()

    try:
        while True:
            container.wake_engine.wait_for_wake(
                idle_hook=container.reminders.check_and_notify,
                idle_interval=60.0,
            )

            if not container.access_control.authorize():
                logger.info("Owner verification failed; returning to idle.")
                continue

            if not container.store.briefing_done_today():
                container.tts.speak(container.briefing.build_morning_briefing())
                container.store.mark_briefing_done()

            container.conversation.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    finally:
        container.lifecycle.shutdown()


if __name__ == "__main__":
    main()

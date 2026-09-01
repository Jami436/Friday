from app.application.access_control import AccessControlService
from app.application.briefing_service import BriefingService
from app.application.conversation_service import ConversationService
from app.application.reminder_service import ReminderService
from app.container import build_container
from app.core.logger import logger
from app.domain.ports.memory import MemoryStore
from app.domain.ports.speech import TextToSpeech, WakeEngine


def _run_once(
    wake_engine: WakeEngine,
    access_control: AccessControlService,
    store: MemoryStore,
    tts: TextToSpeech,
    briefing: BriefingService,
    conversation: ConversationService,
    reminders: ReminderService,
) -> None:
    def _idle_reminders() -> None:
        reminders.check_and_notify()

    wake_engine.wait_for_wake(
        idle_hook=_idle_reminders,
        idle_interval=60.0,
    )

    if not access_control.authorize():
        logger.info("Owner verification failed; returning to idle.")
        return

    if not store.briefing_done_today():
        tts.speak(briefing.build_morning_briefing())
        store.mark_briefing_done()

    conversation.run()


def main() -> None:
    container = build_container()
    container.lifecycle.startup()

    try:
        while True:
            try:
                _run_once(
                    wake_engine=container.wake_engine,
                    access_control=container.access_control,
                    store=container.store,
                    tts=container.tts,
                    briefing=container.briefing,
                    conversation=container.conversation,
                    reminders=container.reminders,
                )
            except KeyboardInterrupt:
                raise
            except Exception as error:  # noqa: BLE001 - keep the assistant alive
                logger.exception(f"Turn failed; returning to idle: {error}")
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

    finally:
        container.lifecycle.shutdown()


if __name__ == "__main__":
    main()

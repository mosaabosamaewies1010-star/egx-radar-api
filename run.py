"""App entry point."""
import logging
import os

from app import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "1") == "1"

    if not debug:
        # Start background scheduler only in production (not in Flask reloader)
        from app.jobs.scheduler import create_scheduler
        scheduler = create_scheduler(app)
        scheduler.start()
        logging.getLogger(__name__).info("Background scheduler started")

    app.run(debug=debug, port=5001)

"""Central logging + optional Sentry error tracking.

Configured once at app startup (api.main). Without this, application log levels
depend on uvicorn's defaults and WARNING-and-below messages can be lost; Sentry is
opt-in via SENTRY_DSN so production errors are captured centrally.
"""
import contextvars
import logging
import logging.config

logger = logging.getLogger(__name__)

# Correlation id for the current request (set by RequestIDMiddleware in api.main); "-"
# outside a request. Injected into every log record so one request can be traced across
# log lines (audit P16-01).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdLogFilter(logging.Filter):
    """Attach the current request's correlation id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    """Install a consistent console log config with *level* as the root level."""
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,  # keep uvicorn's own loggers alive
            "formatters": {
                "default": {"format": "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"},
            },
            "filters": {
                "request_id": {"()": "api.observability.RequestIdLogFilter"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"handlers": ["console"], "level": level.upper()},
            "loggers": {
                # Route uvicorn through the same handler/level (no duplicate lines).
                "uvicorn": {"level": level.upper(), "handlers": ["console"], "propagate": False},
                "uvicorn.error": {"level": level.upper(), "handlers": ["console"], "propagate": False},
                "uvicorn.access": {"level": level.upper(), "handlers": ["console"], "propagate": False},
            },
        }
    )


def init_sentry(dsn: str, environment: str = "development", traces_sample_rate: float = 0.0) -> bool:
    """Initialise Sentry if a DSN is set and the SDK is importable.

    Returns True when Sentry was initialised, else False (a no-op — Sentry is an
    opt-in feature, so a missing DSN or missing SDK must never break startup).
    """
    if not dsn:
        return False
    try:
        import sentry_sdk
    except ImportError:
        logger.warning("SENTRY_DSN is set but sentry-sdk is not installed; skipping.")
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
    )
    logger.info("Sentry initialised (environment=%s)", environment)
    return True

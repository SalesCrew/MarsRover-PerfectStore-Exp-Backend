import logging
import os

import uvicorn


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("perfectstore-export.start")


def main() -> None:
    port_value = os.environ.get("PORT", "8000")
    try:
        port = int(port_value)
    except ValueError as exc:
        raise RuntimeError(f"Invalid PORT value: {port_value!r}") from exc

    logger.info("Starting uvicorn on 0.0.0.0:%s", port)
    uvicorn.run("app:app", host="0.0.0.0", port=port, log_level="info", access_log=True)


if __name__ == "__main__":
    main()

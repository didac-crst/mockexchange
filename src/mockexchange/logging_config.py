# src/mockexchange/logging_config.py  (or just at the top of market.py)
import logging
import sys

logging.basicConfig(
    level=logging.INFO,                 # DEBUG for more verbosity
    stream=sys.stdout,                  # log to container stdout
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",          # ← no “,%f” ⇒ no milliseconds
)

logger = logging.getLogger(__name__)   # module-local logger

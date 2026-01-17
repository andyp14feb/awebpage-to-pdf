import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings

def setup_logging():
    """Configure structured JSON logging."""
    logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Create formatter
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d',
        datefmt='%Y-%m-%dT%H:%M:%S%z',
        rename_fields={
            'asctime': 'timestamp',
            'levelname': 'level'
        }
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

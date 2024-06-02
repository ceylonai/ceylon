import logging
from ceylonai import ceylonai

logging.basicConfig(level=logging.INFO)

logging.info(f"CeylonAI Python bindings loaded {ceylonai.get_version()}", )

# Define a mapping between engine names and connector classes
from ocr.connector import LocalOcrConnector
from ocr.models import OCREngine

ENGINE_CONNECTOR_MAPPING = {
    "PERO OCR - General": LocalOcrConnector,
    # Add more mappings as needed
}


# Function to get the connector based on the engine name
def get_connector_for_engine(engine: OCREngine):
    connector_class = ENGINE_CONNECTOR_MAPPING.get(engine.name)
    if connector_class:
        return connector_class()
    else:
        raise ValueError("OCREngine not known")

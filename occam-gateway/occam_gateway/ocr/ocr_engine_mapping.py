# Define a mapping between engine names and connector classes
import os
from ocr.connector import LocalOcrConnector, LoghiHTRConnector
from ocr.models import OCREngine

ENGINE_CONNECTOR_MAPPING = {
    "PERO OCR - General": LocalOcrConnector,
    "Loghi HTR - General": LoghiHTRConnector,
    # Add more mappings as needed
}


# Function to get the connector based on the engine name
def get_connector_for_engine(engine: OCREngine):
    connector_class = ENGINE_CONNECTOR_MAPPING.get(engine.name)
    if connector_class:
        if connector_class == LoghiHTRConnector:
            return connector_class(
                loghi_server=os.environ.get("LOGHI_SERVER"),
                username="root",
                key_file="/root/.ssh/id_rsa",
                remote_image_dir="/root/loghi/data/images",
                script_path="/root/loghi/scripts/inference-pipeline-v2.sh",
                # Pass other necessary parameters here
                laypa_baseline_model="/root/loghi/public-models/laypa/general/baseline2/config.yaml",
                laypa_baseline_weights="/root/loghi/public-models/laypa/general/baseline2/model_best_mIoU.pth",
                htrloghi_model="/root/loghi/public-models/loghi-htr/generic-2023-02-15",
                gpu=0,  # or -1 for CPU
                beamwidth=5,
                # Add other parameters as needed
            )
        else:
            return connector_class()
    else:
        raise ValueError(f"OCREngine '{engine.name}' not known")

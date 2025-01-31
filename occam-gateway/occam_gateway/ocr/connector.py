"""
Connector methods to PERO-OCR's and Loghi's HTR OCR APIs.
"""
import abc
import io
import logging
import os
import urllib.parse
import uuid

import paramiko
import requests

from gateway_utils.connector_utils import raise_response

# Environment variables for service URLs
LOCAL_PERO = os.environ.get("LOCAL_PERO", "")

logger = logging.getLogger(__name__)


class OcrConnector(abc.ABC):
    @abc.abstractmethod
    def ocr_image(self, file: io.BufferedReader) -> bytes:
        ...


class LocalOcrConnector(OcrConnector):
    def health_check(self) -> bool:
        """
        Check the health of the OCR service.
        """
        url = urllib.parse.urljoin(LOCAL_PERO, "docs")
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            logger.error(f"OCR service health check failed with status code {response.status_code}")
            raise Exception(f"OCR service returned status code {response.status_code}")

        logger.info("OCR service is healthy")
        return True

    def ocr_image(self, file: io.BufferedReader) -> dict:
        """
        OCRs a page and return the overlay as a page xml bytestring.

        Args:
            file: An image file to be OCR'ed

        Returns:
            A dictionary containing the OCR results.
        """
        files = {"image": file}

        url = urllib.parse.urljoin(LOCAL_PERO, "ocr")
        response_ocr_image = requests.post(url, files=files)

        if not response_ocr_image.ok:
            logger.error(f"OCR image request failed: {response_ocr_image.status_code} {response_ocr_image.text}")
            raise_response(response_ocr_image)

        logger.info("OCR image request completed successfully")
        return response_ocr_image.json()

    def ocr_image_to_PAGE(self, file) -> bytes:
        """
        OCR the text as PAGE XML from an image file.
        """
        logger.info("Converting OCR image to PAGE XML")
        return self.ocr_image(file)["xml"].encode()

    def ocr_image_to_text(self, file) -> str:
        """
        OCR the text from an image file.
        """
        logger.info("Extracting OCR text from image")
        d = self.ocr_image(file)
        return d["text"]


class LoghiHTRConnector(OcrConnector):
    def __init__(
            self,
            loghi_server: str,
            username: str,
            key_file: str,
            remote_image_dir: str,
            script_path: str,
            laypa_baseline_model: str,
            laypa_baseline_weights: str,
            htrloghi_model: str,
            gpu: int = 0,
            beamwidth: int = 1,
            use_2013_namespace: int = 1,
            # Add other parameters as needed
    ):
        self.loghi_server = loghi_server
        self.username = username
        self.key_file = key_file
        self.remote_image_dir = remote_image_dir
        self.script_path = script_path
        self.laypa_baseline_model = laypa_baseline_model
        self.laypa_baseline_weights = laypa_baseline_weights
        self.htrloghi_model = htrloghi_model
        self.gpu = gpu
        self.beamwidth = beamwidth
        self.use_2013_namespace = use_2013_namespace
        # Add other parameters as needed

    def _create_ssh_client(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=self.loghi_server,
            username=self.username,
            key_filename=self.key_file,
            timeout=10,
        )
        return ssh

    def _transfer_file_to_loghi_server(self, local_file: io.BufferedReader, remote_path: str):
        ssh = self._create_ssh_client()
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_path, 'wb') as remote_file:
                local_file.seek(0)
                remote_file.write(local_file.read())
            logger.info(f"Transferred file to {remote_path} on Loghi server")
        except Exception as e:
            logger.error(f"Failed to transfer file to Loghi server: {e}")
            raise
        finally:
            sftp.close()
            ssh.close()

    def _transfer_file_from_loghi_server(self, remote_path: str) -> bytes:
        ssh = self._create_ssh_client()
        sftp = ssh.open_sftp()
        try:
            with sftp.file(remote_path, 'rb') as remote_file:
                file_content = remote_file.read()
            logger.info(f"Retrieved file from {remote_path} on Loghi server")
            return file_content
        except Exception as e:
            logger.error(f"Failed to retrieve file from Loghi server: {e}")
            raise
        finally:
            sftp.close()
            ssh.close()

    def _execute_command_on_loghi_server(self, command: str):
        ssh = self._create_ssh_client()
        try:
            stdin, stdout, stderr = ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode()
            error = stderr.read().decode()
            if exit_status != 0:
                logger.error(f"Command failed with exit status {exit_status}: {error}")
                raise Exception(f"Command failed: {error}")
            logger.info(f"Command executed successfully: {command}")
            return output
        except Exception as e:
            logger.error(f"Failed to execute command on Loghi server: {e}")
            raise
        finally:
            ssh.close()

    def ocr_image(self, file: io.BufferedReader) -> dict:
        # Generate a unique identifier
        identifier = str(uuid.uuid4())
        image_filename = f"{identifier}.jpg"
        remote_image_path = os.path.join(self.remote_image_dir, image_filename)
        remote_output_page_path = os.path.join(self.remote_image_dir, "page")
        remote_output_path = os.path.join(remote_output_page_path, f"{identifier}.xml")

        logger.info(f"Starting OCR process for identifier: {identifier}")

        try:
            # Transfer the image to the Loghi server
            logger.info("Transferring image to Loghi server")
            self._transfer_file_to_loghi_server(file, remote_image_path)

            # Construct the command to execute the OCR script with parameters
            logger.info("Executing OCR script on Loghi server")
            command = (
                f"bash {self.script_path} "
                f"--images_path {self.remote_image_dir} "
                f"--laypa_baseline_model {self.laypa_baseline_model} "
                f"--laypa_baseline_weights {self.laypa_baseline_weights} "
                f"--htrloghi_model {self.htrloghi_model} "
                f"--gpu {self.gpu} "
                f"--beamwidth {self.beamwidth} "
                f"--use_2013_namespace {self.use_2013_namespace} "
            )

            # Add other parameters as needed

            self._execute_command_on_loghi_server(command)

            # Retrieve the final XML output
            logger.info("Retrieving final OCR output")
            final_xml_data = self._transfer_file_from_loghi_server(remote_output_path)

            logger.info(f"OCR process completed successfully for identifier: {identifier}")

            # Return JSON with XML in 'xml' field
            result = {"xml": final_xml_data.decode('utf-8')}
            return result

        except Exception as e:
            logger.error(f"OCR process failed for identifier: {identifier}: {e}")
            raise
        finally:
            # Clean up remote files
            logger.info("Cleaning up remote files")
            cleanup_command = f"rm -f {remote_image_path} {remote_output_page_path}"
            try:
                self._execute_command_on_loghi_server(cleanup_command)
            except Exception as e:
                logger.warning(f"Failed to clean up remote files: {e}")

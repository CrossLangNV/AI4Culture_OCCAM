import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "primereact/button";
import { InputTextarea } from "primereact/inputtextarea";
import { FileUpload } from "primereact/fileupload";
import { Toast } from "primereact/toast";
import { ProgressSpinner } from "primereact/progressspinner";
import fileDownload from "js-file-download";
import { useDispatch, useSelector } from "react-redux";
import { Ripple } from "primereact/ripple";
import { classNames } from "primereact/utils";
import { useInterval } from "../../Helpers";
import api from "../../interceptors/api";
import {
  GetTranslatedFileStatus,
  ResetTranslatedFileStatus,
} from "../../actions/translationActions";
import ProgressBarTranslation from "./ProgressBarTranslation";
import Analysis from "./Analysis";
import TranslateEngineSelection from "./TranslateEngineSelection";

const Translate = () => {
  const [uploadedFile, setUploadedFile] = useState(null);

  const dispatch = useDispatch();

  const [modeText, setModeText] = useState(true);

  // Selected options. Contains label and value { label: "English", value: "en" }
  const [selectedSourceLanguage, setSelectedSourceLanguage] = useState(null);
  const [selectedTargetLanguage, setSelectedTargetLanguage] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [selectedDomain, setSelectedDomain] = useState(null);

  // State of translation in progress
  const [isTranslatingText, setIsTranslatingText] = useState(false);
  const [isTranslatingFile, setIsTranslatingFile] = useState(false);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [currentFile, setCurrentFile] = useState(null);
  const [translatedFile, setTranslatedFile] = useState(null);

  // Redux status of ongoing file translation
  const translatedFileStatus = useSelector(
    (state) => state.translatedFileStatus,
  );

  // Text translation input and translated text output
  const [inputText, setInputText] = useState("");
  const [translatedText, setTranslatedText] = useState("");

  // Whether we are detecting or selecting the source language
  const [languageDetectionMode, setLanguageDetectionMode] = useState(true);

  const toast = useRef(null);
  const uploadRef = useRef(null);

  const POLL_INTERVAL_MS = 5000;
  const POLL_MAX_ATTEMPTS = 100;
  const MAX_N_CHARACTERS = 5000;
  const TOAST_LIFE = 10000;

  const MAX_FILESIZE = Number(window._env_.MAX_FILESIZE || 1000000);

  const DETECT_THRESH = 0; // Threshold for changing the detected language

  const ALLOWED_FILE_EXTENSIONS = [
    ".docx",
    ".pptx",
    ".xlsx",
    ".txt",
    ".html",
    ".pdf",
  ];

  const onTemplateRemove = (file, callback) => {
    callback();
    clearFile();
  };

  const itemTemplate = (file, props) => {
    return (
      <div className="flex flex-wrap justify-content-between m-0 p-0">
        <div
          className="flex align-items-center" // style={{ width: "40%" }}
        >
          <span className="flex flex-column text-left ml-3">
            {file.name} ({props.formatSize})
          </span>
        </div>

        <div
          className="flex align-items-center justify-content-center ml-auto mr-auto"
          style={{ width: "30%" }}
        >
          {isTranslatingFile && (
            <ProgressBarTranslation
              className="w-full"
              value={translatedFileStatus.data.progress * 100}
              /*  if the progress is 0 or the translatedFileStatus is not defined (empty object)
                                                                          then show indeterminate progress bar */
              mode={
                Object.keys(translatedFileStatus.data).length === 0 ||
                translatedFileStatus.data.progress === 0
                  ? "indeterminate"
                  : "determinate"
              }
              showValue={false}
            />
          )}
        </div>
        <Button
          type="button"
          icon="pi pi-times"
          className="p-button-rounded p-button-danger p-button-text"
          onClick={() => onTemplateRemove(file, props.onRemove)}
        />
      </div>
    );
  };

  const getFileConfig = () => {
    return {
      responseType: "blob",
    };
  };

  const getFormConfig = () => {
    return {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    };
  };

  const clearText = () => {
    setInputText("");
    setTranslatedText("");
  };

  const clearFile = useCallback(() => {
    // Order of setters in reverse order of how they are set

    setTranslatedFile(null);
    setCurrentFile(null);
    setCurrentJobId(null);
    setIsTranslatingFile(false);
    try {
      uploadRef.current.clear();
    } catch (e) {}
    dispatch(ResetTranslatedFileStatus());
    setUploadedFile(null);
  }, [dispatch]);

  /**
   * When we move away from the file translation, we clear everything.
   * This is necessary because the fileUploader has to be re-rendered and can't access the previous state.
   */
  useEffect(() => {
    if (modeText) {
      clearFile();
    }
  }, [modeText, clearFile]);

  /**
   * Language detection of the input text
   * returns sourceLanguageData e.g. {label: "English", value: "en", score: .8 }
   */
  const detectLanguage = async (inputText) => {
    // If the input text is empty, we don't need to do anything
    if (!inputText) {
      return;
    }

    try {
      let formData = new FormData();
      formData.append("text", inputText);

      const response = await api.post(
        `/catalogue/api/language-detection`,
        formData,
      );
      return response.data;
    } catch (error) {
      // Unable to detect language
    }
  };

  const translateText = async (e, source, target, provider, domain) => {
    let bodyFormData = new FormData();
    bodyFormData.append("text", inputText);

    bodyFormData.append("source", source);
    bodyFormData.append("target", target);
    bodyFormData.append("provider", provider);
    bodyFormData.append("domain", domain);

    setIsTranslatingText(true);

    await api
      .post(
        `/catalogue/api/translate-text-blocking`,
        bodyFormData,
        getFormConfig(),
      )
      .then((res) => {
        setTranslatedText(res.data);
      })
      .finally(() => {
        setIsTranslatingText(false);
      });
  };

  const translateFile = async (file, source, target, provider, domain) => {
    setCurrentFile(file);

    let bodyFormData = new FormData();

    bodyFormData.append("source", source);
    bodyFormData.append("target", target);
    bodyFormData.append("provider", provider);
    bodyFormData.append("domain", domain);

    bodyFormData.append("file", file);

    await api
      .post(`/catalogue/api/translate-document`, bodyFormData, getFormConfig())
      .then((res) => {
        setCurrentJobId(res.data.jobId);
        setIsTranslatingFile(true);
        return res.data.jobId;
      })
      .catch((e) => {
        if (e.response.status === 422) {
          console.log("PDF extraction failed.");
          toast.current.show({
            life: TOAST_LIFE,
            severity: "error",
            summary: "Could not extract text from pdf file.",
            detail:
              "Something went wrong, try again or contact the administrator.",
          });
        } else {
          console.log("File upload failed.");
          toast.current.show({
            life: TOAST_LIFE,
            severity: "error",
            summary: "File upload failed!",
            detail:
              "Something went wrong, try again or contact an administrator.",
          });
        }
        clearFile();
      });
  };

  useInterval(
    () => {
      dispatch(GetTranslatedFileStatus(currentJobId));
    },
    isTranslatingFile ? POLL_INTERVAL_MS : null,
    POLL_MAX_ATTEMPTS,
  );

  const getTranslatedFile = useCallback((jobId) => {
    let request = api.get(
      `/catalogue/api/translate-document/${jobId}/file`,
      getFileConfig(),
    );
    return request.then((result) => {
      setTranslatedFile(result);
      return result;
    });
  }, []);

  useEffect(() => {
    if (
      translatedFileStatus.data.completed ||
      translatedFileStatus.data.failed
    ) {
      if (translatedFileStatus.data.failed) {
        toast.current.show({
          life: TOAST_LIFE,
          severity: "error",
          summary: "Translation failed!",
          detail: "Document translation failed. Please try again later.",
        });
      } else {
        toast.current.show({
          life: TOAST_LIFE,
          severity: "success",
          summary: "Translation finished.",
          detail:
            "You can find the translated document in your downloads folder.",
        });

        getTranslatedFile(currentJobId);
      }
    }
  }, [
    translatedFileStatus,
    currentJobId,
    getTranslatedFile,
    dispatch,
    clearFile,
  ]);

  useEffect(() => {
    if (translatedFile) {
      let blob = new Blob([translatedFile.data], {
        type: translatedFile.headers["content-type"],
      });
      let fileName = currentFile.name;
      let extension_offset = fileName.lastIndexOf(".");
      let fName = fileName.slice(0, extension_offset);
      let extension = fileName.slice(extension_offset);

      // Check if the file is transformed from type
      if (blob.type !== currentFile.type) {
        // PDF to txt
        // Check if the returned file is a txt file.
        // Should also detect "text/plain; charset=utf-8"
        if (blob.type.includes("text/plain")) {
          extension = ".txt";
        }
      }

      let providerLabel = selectedProvider.label;
      let downloadFileName =
        fName +
        "_" +
        providerLabel +
        "_" +
        selectedSourceLanguage.value +
        "_" +
        selectedTargetLanguage.value +
        extension;
      fileDownload(blob, downloadFileName);

      // Cleanup
      clearFile();
    }
  }, [
    translatedFile,
    currentFile,
    selectedProvider,
    selectedSourceLanguage,
    selectedTargetLanguage,
    clearFile,
  ]);

  const fileUploader = async (event) => {
    const files = event.files;

    if (files) {
      const uploadedFile = files[0];
      const fileExtension = uploadedFile.name.slice(
        uploadedFile.name.lastIndexOf("."),
      );

      if (!ALLOWED_FILE_EXTENSIONS.includes(fileExtension)) {
        toast.current.show({
          life: TOAST_LIFE,
          severity: "error",
          summary: "Invalid file format",
          detail: `File format "${fileExtension}" is not supported. Please upload a file with one of the following extensions: ${ALLOWED_FILE_EXTENSIONS.join(
            ", ",
          )}.`,
        });
        uploadRef.current.clear();
        return;
      }

      // If the uploaded file has an allowed extension, set it as the uploaded file
      setUploadedFile(uploadedFile);
    }
  };

  const detectLanguageFile = async (file) => {
    try {
      let bodyFormData = new FormData();
      bodyFormData.append("file", file);

      const { data } = await api.post(
        `/catalogue/api/language-detection-document`,
        bodyFormData,
      );
      return data;
    } catch (error) {
      // Unable to detect language
    }
  };

  const setDetectedLanguage = useCallback(
    (detectedLanguageData) => {
      if (!detectedLanguageData)
        // Do nothing
        // setSelectedSourceLanguage(null);
        return;

      /** Set the langauge
       * - if the certainty is above the threshold
       * - if no language has been selected yet
       */
      if (
        !selectedSourceLanguage ||
        detectedLanguageData.score > DETECT_THRESH
      ) {
        // Only change if the language is different (You can ignore it if e.g. the score is different)
        if (detectedLanguageData.value !== selectedSourceLanguage?.value) {
          setSelectedSourceLanguage(detectedLanguageData);
        }
      }
    },
    [selectedSourceLanguage],
  );

  /** Detect language trigger
   * on file upload (and detect enabled)
   */
  useEffect(() => {
    if (!languageDetectionMode) return;

    // Text or Document mode
    if (modeText) {
      // Text
      if (!inputText) {
        selectedSourceLanguage && setSelectedSourceLanguage(null);
        return;
      }

      detectLanguage(inputText).then((detectedLanguageData) =>
        setDetectedLanguage(detectedLanguageData),
      );
    } else {
      // Document
      if (!uploadedFile) {
        selectedSourceLanguage && setSelectedSourceLanguage(null);
        return;
      }

      detectLanguageFile(uploadedFile).then((detectedLanguageData) =>
        setDetectedLanguage(detectedLanguageData),
      );
    }
  }, [
    languageDetectionMode,
    uploadedFile,
    inputText,
    modeText,
    setDetectedLanguage,
  ]);

  const fileTranslater = async (source, target, provider, domain) => {
    translateFile(uploadedFile, source, target, provider, domain);
    toast.current.show({
      severity: "info",
      summary: "Document uploaded",
      detail: "Translating...",
      life: TOAST_LIFE,
    });
  };

  return (
    <div>
      <div className="grid translate-ui-grid">
        <ul className="surface-card p-2 m-0 list-none flex overflow-x-auto select-none">
          <li className="mr-2">
            <button
              className={classNames(
                "btn-no-decoration p-ripple cursor-pointer px-4 py-3 flex align-items-center border-round transition-colors transition-duration-150 border-noround",
                {
                  "primary-bg-color": modeText,
                  "text-700 light-bg-color": !modeText,
                },
              )}
              onClick={() => setModeText(true)}
            >
              <i className="pi pi-align-left mr-2"></i>
              <span className="font-medium">Text</span>
              <Ripple />
            </button>
          </li>
          <li className="mr-2">
            <button
              className={classNames(
                "btn-no-decoration p-ripple cursor-pointer px-4 py-3 flex align-items-center border-round transition-colors transition-duration-150 border-noround",
                {
                  "primary-bg-color": !modeText,
                  "text-700 light-bg-color": modeText,
                },
              )}
              onClick={() => setModeText(false)}
            >
              <i className="pi pi-file mr-2"></i>
              <span className="font-medium">Documents</span>
              <Ripple />
            </button>
          </li>
        </ul>
      </div>
      <div className="flex w-full relative align-items-center justify-content-start my-3 px-4">
        <div className="border-top-1 border-300 top-50 left-0 absolute w-full"></div>
        <div className="px-2 z-1 surface-0 flex align-items-center">
          <i className="pi pi-cog text-900 mr-2"></i>
          <span className="text-900 font-medium">Options</span>
        </div>
      </div>
      <TranslateEngineSelection
        languageDetectionMode={languageDetectionMode}
        setLanguageDetectionMode={setLanguageDetectionMode}
        selectedSourceLanguage={selectedSourceLanguage}
        setSelectedSourceLanguage={setSelectedSourceLanguage}
        selectedTargetLanguage={selectedTargetLanguage}
        setSelectedTargetLanguage={setSelectedTargetLanguage}
        selectedDomain={selectedDomain}
        setSelectedDomain={setSelectedDomain}
        selectedProvider={selectedProvider}
        setSelectedProvider={setSelectedProvider}
      />
      <div className="flex w-full relative align-items-center justify-content-start my-3 px-4">
        <div className="border-top-1 border-300 top-50 left-0 absolute w-full"></div>
        <div className="px-2 z-1 surface-0 flex align-items-center">
          <i className="pi pi-comments text-900 mr-2"></i>
          <span className="text-900 font-medium">Translate</span>
        </div>
      </div>

      {modeText ? (
        <>
          <div className="grid translate-ui-grid">
            <div className="col-6 translate-ui-col">
              <InputTextarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                className="translate-input-text"
                placeholder="Text to translate..."
                maxLength={MAX_N_CHARACTERS}
                dir="auto"
              />
              <div className="right-side">
                {inputText.length + "/" + MAX_N_CHARACTERS}
              </div>
            </div>
            <div className="col-6 translate-ui-col">
              <InputTextarea
                value={translatedText}
                onChange={(e) => setTranslatedText(e.target.value)}
                className="translate-input-text"
                placeholder="Translation..."
                dir="auto"
              />
            </div>
          </div>
          <div className="grid translate-ui-grid">
            <div className="col-12 md:col-6 lg:col-6">
              <Button
                label={
                  isTranslatingText ? (
                    <ProgressSpinner className={"translate-loading"} />
                  ) : (
                    "Translate text"
                  )
                }
                className="translate-btn"
                onClick={(e) =>
                  translateText(
                    e,
                    selectedSourceLanguage.value,
                    selectedTargetLanguage.value,
                    selectedProvider.value,
                    selectedDomain.value,
                  )
                }
                disabled={
                  !inputText ||
                  isTranslatingText ||
                  !selectedSourceLanguage ||
                  !selectedTargetLanguage ||
                  !selectedProvider ||
                  !selectedDomain
                }
              />
            </div>
            <div className="col-12 md:col-6 lg:col-6">
              <Button
                icon="pi pi-times"
                className="p-button-outlined"
                label="Clear"
                onClick={clearText}
              />
            </div>
          </div>
        </>
      ) : (
        <div className="grid translate-ui-grid">
          <div className="col-12">
            <FileUpload
              chooseOptions={{
                className: "choose-button",
              }}
              ref={uploadRef}
              name="file_translation"
              maxFileSize={MAX_FILESIZE}
              accept={ALLOWED_FILE_EXTENSIONS.join(",")}
              customUpload
              auto={true}
              chooseLabel={"Choose document"}
              emptyTemplate={
                <p className="m-0 text-sm">
                  <i className="pi pi-info-circle"></i> Drag and drop or click
                  to upload a document.
                  <br />
                  <small>
                    Supported formats: {ALLOWED_FILE_EXTENSIONS.join(", ")}.
                    Only one file can be processed at a time. The maximum file
                    size is{" "}
                    {(MAX_FILESIZE / 1000000).toLocaleString("en", {
                      maximumSignificantDigits: 2,
                    })}{" "}
                    MB.
                  </small>
                </p>
              }
              itemTemplate={itemTemplate}
              uploadHandler={(e) => fileUploader(e)}
              disabled={uploadedFile}
              contentClassName={"translate-upload-box"} // Custom min height to avoid jumping when file is uploaded
            />
          </div>
          <div className="col-12 translate-ui-full-width">
            <Button
              label={
                isTranslatingFile ? (
                  <ProgressSpinner className={"translate-loading"} />
                ) : (
                  "Translate document"
                )
              }
              className="translate-button"
              onClick={(_) =>
                fileTranslater(
                  selectedSourceLanguage.value,
                  selectedTargetLanguage.value,
                  selectedProvider.value,
                  selectedDomain.value,
                )
              }
              disabled={
                isTranslatingFile ||
                !uploadedFile ||
                !selectedSourceLanguage ||
                !selectedTargetLanguage ||
                !selectedProvider ||
                !selectedDomain
              }
            />
          </div>
          {uploadedFile && (
            <Analysis
              file={uploadedFile}
              // TODO: add language detection
              language={
                selectedSourceLanguage ? selectedSourceLanguage.value : "en"
              }
            />
          )}
        </div>
      )}
      <Toast ref={toast} />
    </div>
  );
};

export default Translate;

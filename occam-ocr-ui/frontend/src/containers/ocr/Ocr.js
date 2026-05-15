// Ocr.js

import fileDownload from "js-file-download";
import JSZip from "jszip";
import xml2js from "xml2js";

import { Button } from "primereact/button";
import { Checkbox } from "primereact/checkbox";
import { Dialog } from "primereact/dialog";
import { Dropdown } from "primereact/dropdown";
import { FileUpload } from "primereact/fileupload";
import { ProgressSpinner } from "primereact/progressspinner";
import { Toast } from "primereact/toast";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import { ResetTranslatedFileStatus } from "../../actions/translationActions";
import api from "../../interceptors/api";

import { OCRSplitview, SelectButtonOCRView } from "./OCRSplitview";
import { PageSelection } from "./PageSelection";
import ProgressBar from "./ProgressBar";
import { ProgressBar as PrimeProgressBar } from "primereact/progressbar";

const TOAST_LIFE = 10000;

const updateArrayAtIndex = (array, index, data) => {
  const newArray = [...array];
  if (index >= newArray.length) {
    newArray.length = index + 1;
  }
  newArray[index] = data;
  return newArray;
};

const getFormConfig = () => {
  return {};
};

async function mergeUserEditsIntoPageXML(pageXML, userLines) {
  if (!pageXML || !userLines?.length) return pageXML;

  const parser = new xml2js.Parser();
  const builder = new xml2js.Builder({ headless: true });

  let parsed;
  try {
    parsed = await parser.parseStringPromise(pageXML);
  } catch (e) {
    console.warn("Failed to parse existing pageXML for merging edits.", e);
    return pageXML;
  }

  const page = parsed?.PcGts?.Page?.[0];
  if (!page) return pageXML;

  const textRegions = page.TextRegion || [];
  textRegions.forEach((region) => {
    const lines = region.TextLine || [];
    lines.forEach((lineObj) => {
      const lineId = lineObj.$.id;
      const userLine = userLines.find((ul) => ul.id === lineId);
      if (userLine) {
        if (!lineObj.TextEquiv) lineObj.TextEquiv = [{}];
        if (!lineObj.TextEquiv[0].Unicode) {
          lineObj.TextEquiv[0].Unicode = [""];
        }
        lineObj.TextEquiv[0].Unicode[0] = userLine.text;
      }
    });
  });

  return builder.buildObject(parsed);
}

const Ocr = () => {
  const dispatch = useDispatch();

  const uploadRef = useRef(null);
  const toast = useRef(null);
  const progressTimerRef = useRef(null);

  const [taskInProgress, setTaskInProgress] = useState(false);
  const [taskProgress, setTaskProgress] = useState(0);
  const [taskName, setTaskName] = useState("");

  const [uploadedFile, setUploadedFile] = useState(null);
  const [isImageFileLoading, setIsImageFileLoading] = useState(false);

  const [pages, setPages] = useState([]);
  const [indexPage, setIndexPage] = useState(null);
  const [transcription, setTranscription] = useState([]);
  const [geojson, setGeojson] = useState([]);
  const [pageXMLs, setPageXMLs] = useState([]);
  const [textLines, setTextLines] = useState([]);

  // Correction
  const [correctionLanguage, setCorrectionLanguage] = useState("");
  const [correction, setCorrection] = useState([]);
  const [correctionGeojson, setCorrectionGeojson] = useState([]);
  const [correctionPageXMLs, setCorrectionPageXMLs] = useState([]);
  const [correctionTextLines, setCorrectionTextLines] = useState([]);

  // Translation
  const [translation, setTranslation] = useState([]);
  const [translationPageXMLs, setTranslationPageXMLs] = useState([]);
  const [translationTextLines, setTranslationTextLines] = useState([]);
  const [displayTranslationOptions, setDisplayTranslationOptions] = useState(false);
  const [isTranslating, setIsTranslating] = useState(false);
  const [selectedSourceLang, setSelectedSourceLang] = useState(null);
  const [selectedTargetLang, setSelectedTargetLang] = useState(null);

  const [displayDownloadOptions, setDisplayDownloadOptions] = useState(false);

  const [availableEngines, setAvailableEngines] = useState([]);
  const [selectedOCREngine, setSelectedOCREngine] = useState(null);

  const [displayOCROptions, setDisplayOCROptions] = useState(false);
  const [oCROptionsAuto, setOCROptionsAuto] = useState(true);
  const [isOCRingFile, setIsOCRingFile] = useState(false);

  const [displayUploadTranscriptionOptions, setDisplayUploadTranscriptionOptions] =
    useState(false);

  const [displayCorrectionOptions, setDisplayCorrectionOptions] = useState(false);
  const [correctionOptionsAuto, setCorrectionOptionsAuto] = useState(true);
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [selectedCorrectionOption, setSelectedCorrectionOption] = useState(null);
  const [correctionFile, setCorrectionFile] = useState(null);

  const MAX_FILESIZE = Number(window._env_.MAX_FILESIZE || 10000000);
  const ALLOWED_FILE_EXTENSIONS = [".png", ".jpg", ".pdf"];

  const [activeStep, setActiveStep] = useState(0);
  const [pagesOpen, setPagesOpen] = useState(true);

  const [viewVisibility, setViewVisibility] = useState({
    1: true,
    2: false,
    3: false,
    4: false,
  });

  const [tooltipHighlightMode, setTooltipHighlightMode] = useState("original");
  const disableOriginalMode = false;

  function isCorrectionAvailable() {
    const lines = correctionTextLines[indexPage] || [];
    return lines.length > 0;
  }

  function isTranslationAvailable() {
    return !!(translation[indexPage] && translation[indexPage].trim());
  }

  const startTimeBasedProgress = useCallback((durationSecs, displayName) => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    setTaskProgress(0);
    setTaskName(displayName || "Processing...");
    setTaskInProgress(true);

    const startTime = Date.now();
    const intervalId = setInterval(() => {
      const elapsedSec = (Date.now() - startTime) / 1000;
      let newProgress = (elapsedSec / durationSecs) * 100;
      if (newProgress >= 99) newProgress = 99;
      setTaskProgress(newProgress);

      if (newProgress >= 99) {
        clearInterval(intervalId);
        progressTimerRef.current = null;
      }
    }, 500);

    progressTimerRef.current = intervalId;
  }, []);

  const endTimeBasedProgress = useCallback(() => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    setTaskProgress(100);
    setTimeout(() => {
      setTaskInProgress(false);
      setTaskName("");
      setTaskProgress(0);
    }, 600);
  }, []);

  const clearFile = useCallback(() => {
    try {
      uploadRef.current.clear();
    } catch (e) {}

    resetState();
  }, [dispatch]);

  const resetState = useCallback(() => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current);
      progressTimerRef.current = null;
    }

    setTaskInProgress(false);
    setTaskProgress(0);
    setTaskName("");
    setIsOCRingFile(false);
    setIsImageFileLoading(false);
    dispatch(ResetTranslatedFileStatus());

    setCorrection([]);
    setTranscription([]);
    setGeojson([]);
    setPages([]);
    setIndexPage(null);
    setUploadedFile(null);
    setOCROptionsAuto(true);
    setCorrectionOptionsAuto(true);
    setSelectedCorrectionOption(null);
    setCorrectionFile(null);
    setCorrectionGeojson([]);
    setCorrectionPageXMLs([]);
    setCorrectionTextLines([]);
    setPageXMLs([]);
    setSelectedOCREngine(null);
    setTextLines([]);
    setTranslation([]);
    setTranslationPageXMLs([]);
    setTranslationTextLines([]);
    setSelectedSourceLang(null);
    setSelectedTargetLang(null);
  }, [dispatch]);

  const onTemplateRemove = (file, callback) => {
    callback();
    clearFile();
  };

  const itemTemplate = (file, props) => {
    return (
      <div className="flex flex-wrap justify-content-between m-0 p-0">
        <div className="flex align-items-center">
          <span className="flex flex-column text-left ml-3">
            {file.name} ({props.formatSize})
          </span>
        </div>

        <div
          className="flex align-items-center justify-content-center ml-auto mr-auto"
          style={{ width: "30%" }}
        >
          {isImageFileLoading && (
            <div>
              <ProgressSpinner className={"translate-loading"} />
              <span>Extracting pages...</span>
            </div>
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

  const fileUploader = async (event) => {
    resetState();
    const files = event.files;

    if (files) {
      const uploadedFile = files[0];
      const fileExtension = uploadedFile.name.slice(
        uploadedFile.name.lastIndexOf(".")
      );

      if (!ALLOWED_FILE_EXTENSIONS.includes(fileExtension)) {
        toast.current.show({
          life: TOAST_LIFE,
          severity: "error",
          summary: "Invalid file format",
          detail: `File format "${fileExtension}" is not supported.`,
        });
        uploadRef.current.clear();
        return;
      }

      setUploadedFile(uploadedFile);
      await processUploadedFile(uploadedFile);
    }
  };

  const processUploadedFile = async (file) => {
    setIsImageFileLoading(true);

    try {
      if (file.name.slice(file.name.lastIndexOf(".")) === ".pdf") {
        const formData = new FormData();
        formData.append("file", file);

        await api
          .post(`/ocr/api/pdf2image`, formData, {
            headers: {
              "Content-Type": "multipart/form-data",
            },
            responseType: "arraybuffer",
          })
          .then(async (response) => {
            const zip = await JSZip.loadAsync(response.data);
            const imageFiles = Object.values(zip.files);

            const imagesList = imageFiles.map(async (imageZip) => {
              const imageData = await imageZip.async("arraybuffer");

              const mimeType = imageZip._data.mimeType || "image/png";

              const imageBlob = new Blob([imageData], { type: mimeType });

              const imageFile = new File([imageBlob], imageZip.name, {
                type: mimeType,
              });

              imageFile.objectURL = URL.createObjectURL(imageBlob);
              return imageFile;
            });

            const images = await Promise.all(imagesList);
            setPages(images);
            setIndexPage(0);
          })
          .catch((error) => {
            console.error(error);
          });
      } else {
        const imageFile = file;
        imageFile.objectURL = URL.createObjectURL(file);
        setPages([imageFile]);
        setIndexPage(0);
      }
    } catch (error) {
      console.error("Error processing uploaded file", error);
    } finally {
      setIsImageFileLoading(false);
    }
  };

  useEffect(() => {
    const fetchAvailableEngines = async () => {
      try {
        const response = await api.get(`/api/ocr/engines`, getFormConfig());
        const engines = response.data;
        setAvailableEngines(engines);
        if (engines.length > 0) {
          setSelectedOCREngine(engines[0].id);
        }
      } catch (error) {
        console.error("Error fetching OCR engines", error);
        toast.current.show({
          life: TOAST_LIFE,
          severity: "error",
          summary: "OCR Engines",
          detail: "Failed to fetch available OCR engines.",
        });
      }
    };

    fetchAvailableEngines();
  }, []);

  useEffect(() => {
    if (pages?.length > 0 && activeStep === 0) {
      setActiveStep(1);
    }
  }, [pages]);

  useEffect(() => {
    if (activeStep === 2 && pages?.length && oCROptionsAuto) {
      setOCROptionsAuto(false);
      setDisplayOCROptions(true);
    }
  }, [activeStep, pages, oCROptionsAuto]);

  useEffect(() => {
    if (activeStep === 3 && pages?.length && correctionOptionsAuto) {
      setCorrectionOptionsAuto(false);
      setDisplayCorrectionOptions(true);
    }
  }, [activeStep, pages, correctionOptionsAuto]);

  // When going to step 4 (translation) for the first time, show translation options dialog
  const [translationOptionsAuto, setTranslationOptionsAuto] = useState(true);
  useEffect(() => {
    if (activeStep === 4 && pages?.length && translationOptionsAuto) {
      setTranslationOptionsAuto(false);
      setDisplayTranslationOptions(true);
    }
  }, [activeStep, pages, translationOptionsAuto]);

  useEffect(() => {
    setViewVisibility({
      1: true,
      2: activeStep >= 2,
      3: activeStep >= 3,
      4: activeStep >= 4,
    });
  }, [activeStep]);

  const parsePageXML = (pagexmlString, pageIndex) => {
    const parser = new xml2js.Parser();
    parser.parseString(pagexmlString, (err, result) => {
      if (err) {
        console.error("Error parsing PageXML:", err);
        return;
      }

      const lines = [];
      const page = result?.PcGts?.Page?.[0];
      const textRegions = page?.TextRegion || [];

      textRegions.forEach((region) => {
        const textLines = region.TextLine || [];
        textLines.forEach((line, index) => {
          const textContent = line?.TextEquiv?.[0]?.Unicode?.[0] || "";
          const coordsElement = line?.Coords?.[0]?.$.points || "";
          const points = coordsElement.split(" ").map((point) => {
            const [x, y] = point.split(",").map(Number);
            return [y, x];
          });
          lines.push({
            id: line.$.id,
            text: textContent.trim(),
            coordinates: points,
            index,
          });
        });
      });

      setTextLines((prevTextLines) =>
        updateArrayAtIndex(prevTextLines, pageIndex, lines)
      );
    });
  };

  const parseCorrectionPageXML = (pagexmlString, pageIndex) => {
    const parser = new xml2js.Parser();
    parser.parseString(pagexmlString, (err, result) => {
      if (err) {
        console.error("Error parsing Correction PageXML:", err);
        return;
      }

      const lines = [];
      const page = result?.PcGts?.Page?.[0];
      const textRegions = page?.TextRegion || [];

      textRegions.forEach((region) => {
        const textLines = region.TextLine || [];
        textLines.forEach((line, index) => {
          const textContent = line?.TextEquiv?.[0]?.Unicode?.[0] || "";
          const coordsElement = line?.Coords?.[0]?.$.points || "";
          const points = coordsElement.split(" ").map((point) => {
            const [x, y] = point.split(",").map(Number);
            return [y, x];
          });
          lines.push({
            id: line.$.id,
            text: textContent.trim(),
            coordinates: points,
            index,
          });
        });
      });

      setCorrectionTextLines((prevTextLines) =>
        updateArrayAtIndex(prevTextLines, pageIndex, lines)
      );
    });
  };

  const pollCorrectionJobStatus = async (task_id) => {
    // Poll until status != PENDING/Processing
    while (true) {
      const res = await api.get(`/api/correction/status/${task_id}/`, getFormConfig());
      const status = res.data.status;
      if (status === "Completed") {
        return true;
      } else if (status === "Failed") {
        throw new Error(res.data.error || "Job failed");
      } else if (status === "Pending") {
        // Still pending, wait again
      }
      await new Promise((r) => setTimeout(r, 2000)); // wait 2s
    }
  };

  const getCorrectionJobResult = async (task_id) => {
    const res = await api.get(`/api/correction/result/${task_id}/`, getFormConfig());
    return res.data; // should be { text, geojson, pagexml }, or JSON with these keys
  };

  // Polling for async jobs
  const pollJobStatus = async (task_id) => {
    // Poll until the status is not Pending or Processing
    while (true) {
      const res = await api.get(`/api/ocr/status/${task_id}`, getFormConfig());
      const status = res.data.status;
      if (status === "Completed") {
        return true;
      } else if (status === "Failed") {
        throw new Error(res.data.error || "OCR job failed");
      } else if (status === "Pending") {
        // Still pending, wait and try again
      } else {
        // If other states, just wait
      }
      await new Promise((r) => setTimeout(r, 2000)); // wait 2s before next poll
    }
  };

  const getJobResult = async (task_id) => {
    const res = await api.get(`/api/ocr/result/${task_id}`, getFormConfig());
    // res is the HTTPResponse with application/json content
    return res.data;
  };

  const OCRFile = async (file, pageIndex) => {
    let bodyFormData = new FormData();
    bodyFormData.append("file", file);
    bodyFormData.append("engineId", selectedOCREngine);
    bodyFormData.append("async_param", "true"); // use async mode

    // Start the async job
    const startRes = await api.post(`/api/ocr/geojson`, bodyFormData, getFormConfig());
    const taskId = startRes.data.task_id;

    // Poll until completed
    await pollJobStatus(taskId);

    // Get the final result
    const resultData = await getJobResult(taskId);
    // resultData is { text, geojson, pagexml }

    setTranscription((prev) =>
      updateArrayAtIndex(prev, pageIndex, resultData.text)
    );
    setGeojson((prev) =>
      updateArrayAtIndex(prev, pageIndex, resultData.geojson)
    );
    setPageXMLs((prev) =>
      updateArrayAtIndex(prev, pageIndex, resultData.pagexml)
    );

    parsePageXML(resultData.pagexml, pageIndex);
  };

  const CorrectOCRSingle = async (pageIndex) => {
    try {
      const pageXMLContent = pageXMLs[pageIndex];
      if (!pageXMLContent) {
        toast.current.show({
          life: TOAST_LIFE,
          severity: "error",
          summary: "Correction",
          detail: "No PageXML data available for this page.",
        });
        return;
      }

      const pageXMLBlob = new Blob([pageXMLContent], { type: "application/xml" });
      const pageXMLFile = new File([pageXMLBlob], `page_${pageIndex + 1}.xml`, {
        type: "application/xml",
      });

      let bodyFormData = new FormData();
      let apiEndpoint = "";

      if (selectedCorrectionOption === "manual_transcription") {
        // manual => /api/correction/manual/geojson
        // requires (ocr_file, transcription_file, async_param)
        if (!correctionFile) {
          toast.current.show({
            life: TOAST_LIFE,
            severity: "error",
            summary: "Correction",
            detail: "Please upload a manual transcription file.",
          });
          return;
        }
        bodyFormData.append("ocr_file", pageXMLFile);
        bodyFormData.append("transcription_file", correctionFile);
        bodyFormData.append("async_param", "true");

        apiEndpoint = `/api/correction/manual/geojson`;
      } else {
        // symspell / flair / llm => /api/correction/file/geojson
        // requires (file=pageXML, language, option, async_param)
        bodyFormData.append("file", pageXMLFile);
        bodyFormData.append("async_param", "true");

        // The backend requires "language" for this route
        if (!correctionLanguage) {
          toast.current.show({
            life: TOAST_LIFE,
            severity: "error",
            summary: "Correction",
            detail: "Please select a language for SymSpell / Flair / LLM.",
          });
          return;
        }
        bodyFormData.append("language", correctionLanguage);

        if (selectedCorrectionOption === "symspell") {
          bodyFormData.append("option", "Correction (SymSpell)");
        } else if (selectedCorrectionOption === "symspell_flair") {
          bodyFormData.append("option", "Correction (SymSpell + Flair)");
        } else if (selectedCorrectionOption === "llm") {
          bodyFormData.append("option", "Correction (LLM)");
        } else {
          toast.current.show({
            life: TOAST_LIFE,
            severity: "error",
            summary: "Correction",
            detail: "Invalid correction option selected.",
          });
          return;
        }
        apiEndpoint = `/api/correction/file/geojson`;
      }

      // Start async job
      const startRes = await api.post(apiEndpoint, bodyFormData, getFormConfig());
      const taskId = startRes.data.task_id;

      // Poll
      await pollCorrectionJobStatus(taskId);

      // Retrieve result
      const resultData = await getCorrectionJobResult(taskId);

      // Store
      const { text, geojson, pagexml } = resultData;
      setCorrection((prev) => updateArrayAtIndex(prev, pageIndex, text));
      setCorrectionGeojson((prev) => updateArrayAtIndex(prev, pageIndex, geojson));
      setCorrectionPageXMLs((prev) => updateArrayAtIndex(prev, pageIndex, pagexml));

      parseCorrectionPageXML(pagexml, pageIndex);
    } catch (error) {
      console.error(`Correction failed for page ${pageIndex}`, error);
      toast.current.show({
        life: TOAST_LIFE,
        severity: "error",
        summary: "Correction",
        detail: "Something went wrong with the correction.",
      });
      setCorrection((prev) => updateArrayAtIndex(prev, pageIndex, null));
      setCorrectionGeojson((prev) => updateArrayAtIndex(prev, pageIndex, null));
      setCorrectionPageXMLs((prev) => updateArrayAtIndex(prev, pageIndex, null));
    }
  };

  // Loop for entire doc
  const correctOCRAll = async () => {
    toast.current.show({
      severity: "info",
      summary: "Correction",
      detail: "Correction started...",
      life: TOAST_LIFE,
    });

    setIsCorrecting(true);
    startTimeBasedProgress(30, "Correction in progress");
    try {
      if (selectedCorrectionOption === "manual_transcription") {
        // Typically correct single page (the current one)
        await CorrectOCRSingle(indexPage);
      } else {
        // SymSpell / Flair / LLM => correct all pages
        for (let i = 0; i < pageXMLs.length; i++) {
          if (!pageXMLs[i]) continue;
          await CorrectOCRSingle(i);
        }
      }
    } finally {
      setIsCorrecting(false);
      endTimeBasedProgress();
    }
  };
  

  const fileOCRer = async () => {
    toast.current.show({
      severity: "info",
      summary: "Scan uploaded",
      detail: "Extracting text...",
      life: TOAST_LIFE,
    });

    setIsOCRingFile(true);
    startTimeBasedProgress(Math.max(pages.length * 15, 15), "OCR in progress");
    try {
      for (const page of pages) {
        const index = pages.indexOf(page);
        await OCRFile(page, index);
      }
    } finally {
      setIsOCRingFile(false);
      endTimeBasedProgress();
    }
  };

  const uploadTranscriptionHandler = async (event) => {
    const files = event.files;

    if (files && files.length > 0) {
      const file = files[0];

      let bodyFormData = new FormData();
      bodyFormData.append("file", file);
      bodyFormData.append("engineId", "1");

      try {
        await api
          .post(
            `/api/ocr/transcription/geojson`,
            bodyFormData,
            getFormConfig()
          )
          .then((res) => {
            setTranscription((prevTranscriptions) =>
              updateArrayAtIndex(prevTranscriptions, indexPage, res.data.text)
            );

            setGeojson((prevGeojson) =>
              updateArrayAtIndex(prevGeojson, indexPage, res.data.geojson)
            );

            setPageXMLs((prevPageXMLs) =>
              updateArrayAtIndex(prevPageXMLs, indexPage, res.data.pagexml)
            );

            parsePageXML(res.data.pagexml, indexPage);
          })
          .catch((e) => {
            console.error(`Transcription upload failed for ${indexPage}`);

            toast.current.show({
              life: TOAST_LIFE,
              severity: "error",
              summary: "Transcription upload",
              detail: "Something went wrong with Transcription upload.",
            });

            setTranscription((prevTranscriptions) =>
              updateArrayAtIndex(prevTranscriptions, indexPage, null)
            );
            setGeojson((prevGeojson) =>
              updateArrayAtIndex(prevGeojson, indexPage, null)
            );
            setPageXMLs((prevPageXMLs) =>
              updateArrayAtIndex(prevPageXMLs, indexPage, null)
            );
          });

        setDisplayUploadTranscriptionOptions(false);

        toast.current.show({
          severity: "success",
          summary: "Transcription uploaded",
          detail: "Transcription uploaded successfully.",
          life: TOAST_LIFE,
        });
      } catch (error) {
        console.error("Error parsing pageXML file", error);
        toast.current.show({
          severity: "error",
          summary: "Transcription upload",
          detail: "Something went wrong while processing the file.",
          life: TOAST_LIFE,
        });
      }
    }
  };

  const correctionOptions = [
    { label: "Correct using manual transcription (Text file)", value: "manual_transcription" },
    { label: "Correction (SymSpell)", value: "symspell" },
    { label: "Correction (SymSpell + Flair)", value: "symspell_flair" },
    { label: "Correction (LLM)", value: "llm" },
  ];

  const handleCorrectionFileUpload = async (event) => {
    const files = event.files;

    if (files && files.length > 0) {
      const file = files[0];
      setCorrectionFile(file);

      toast.current.show({
        severity: "success",
        summary: "File Uploaded",
        detail: "Manual correction file uploaded successfully.",
        life: TOAST_LIFE,
      });
    }
  };

  // Translation Setup
  const [availableLanguages] = useState([
    { label: "Arabic", value: "ar" },
    { label: "Bulgarian", value: "bg" },
    { label: "Czech", value: "cs" },
    { label: "Danish", value: "da" },
    { label: "German", value: "de" },
    { label: "Greek", value: "el" },
    { label: "English", value: "en" },
    { label: "Spanish", value: "es" },
    { label: "Estonian", value: "et" },
    { label: "Finnish", value: "fi" },
    { label: "French", value: "fr" },
    { label: "Irish", value: "ga" },
    { label: "Croatian", value: "hr" },
    { label: "Hungarian", value: "hu" },
    { label: "Icelandic", value: "is" },
    { label: "Italian", value: "it" },
    { label: "Japanese", value: "ja" },
    { label: "Lithuanian", value: "lt" },
    { label: "Latvian", value: "lv" },
    { label: "Maltese", value: "mt" },
    { label: "Norwegian", value: "nb" },
    { label: "Dutch", value: "nl" },
    { label: "Polish", value: "pl" },
    { label: "Portuguese", value: "pt" },
    { label: "Romanian", value: "ro" },
    { label: "Russian", value: "ru" },
    { label: "Slovak", value: "sk" },
    { label: "Slovenian", value: "sl" },
    { label: "Swedish", value: "sv" },
    { label: "Turkish", value: "tr" },
    { label: "Ukrainian", value: "uk" },
    { label: "Chinese", value: "zh" },
  ]);

  function combineLinesForTranslation(lines) {
    const paragraphs = [];
    let buffer = "";

    lines.forEach((lineObj) => {
      const currentLine = lineObj.text.trim();
      if (!currentLine) return;

      if (!buffer) {
        buffer = currentLine;
      } else if (/[.!?]/.test(buffer.slice(-1))) {
        paragraphs.push(buffer);
        buffer = currentLine;
      } else {
        buffer += ` ${currentLine}`;
      }
    });

    if (buffer) paragraphs.push(buffer);
    return paragraphs.join("\n\n");
  }

  const translateAll = async (source, target) => {
    startTimeBasedProgress(600, "Translation in progress");
    toast.current.show({
      severity: "info",
      summary: "Translation",
      detail: "Translation started...",
      life: TOAST_LIFE,
    });

    setIsTranslating(true);
    try {
      for (let i = 0; i < pages.length; i++) {
        const lines =
          correctionTextLines[i]?.length > 0
            ? correctionTextLines[i]
            : textLines[i] || [];

        const textToTranslate = combineLinesForTranslation(lines);

        if (!textToTranslate) continue;

        let bodyFormData = new FormData();
        const textBlob = new Blob([textToTranslate], { type: "text/plain" });
        const textFile = new File([textBlob], `page_${i + 1}.txt`, {
          type: "text/plain",
        });

        bodyFormData.append("file", textFile);
        bodyFormData.append("source", source);
        bodyFormData.append("target", target);

        const response = await api.post(`/api/translation/file`, bodyFormData, {
          ...getFormConfig(),
          responseType: "blob",
          timeout: 600000,
        });

        const translatedText = await response.data.text();
        setTranslation((prevTranslation) =>
          updateArrayAtIndex(prevTranslation, i, translatedText)
        );
      }
    } catch (error) {
      console.error("Error during translation:", error);
      toast.current.show({
        severity: "error",
        summary: "Translation",
        detail: "Something went wrong with translation.",
        life: TOAST_LIFE,
      });
    } finally {
      setIsTranslating(false);
      endTimeBasedProgress();
    }
  };

  const downloadResults = async (include_transcription, include_correction) => {
    toast.current.show({
      severity: "info",
      summary: "Download",
      detail: "Download started...",
      life: TOAST_LIFE,
    });

    try {
      const zip = new JSZip();

      if (include_transcription) {
        const transcriptionFolder = zip.folder("transcription");

        for (let i = 0; i < pages.length; i++) {
          const lines = textLines[i] || [];
          const textContent = lines.map((line) => line.text).join("\n");
          transcriptionFolder.file(`page_${i + 1}.txt`, textContent);

          const pageXMLContent = pageXMLs[i];
          if (pageXMLContent) {
            transcriptionFolder.file(`page_${i + 1}.xml`, pageXMLContent);
          }
        }
      }

      if (include_correction) {
        const correctionFolder = zip.folder("correction");

        for (let i = 0; i < pages.length; i++) {
          const lines = correctionTextLines[i] || [];
          const textContent = lines.map((line) => line.text).join("\n");
          correctionFolder.file(`page_${i + 1}.txt`, textContent);

          const pageXMLContent = correctionPageXMLs[i];
          if (pageXMLContent) {
            correctionFolder.file(`page_${i + 1}.xml`, pageXMLContent);
          }
        }
      }

      // Include translation if available
      if (translation.some((t) => t && t.trim() !== "")) {
        const translationFolder = zip.folder("translation");
        for (let i = 0; i < pages.length; i++) {
          const translatedText = translation[i] || "";
          translationFolder.file(`page_${i + 1}.txt`, translatedText);
          // If you had pageXML translations, add them here
        }
      }

      const content = await zip.generateAsync({ type: "blob" });
      fileDownload(content, "results_OCR.zip");
    } catch (e) {
      console.error("Error downloading results", e);
      toast.current.show({
        life: TOAST_LIFE,
        severity: "error",
        summary: "Download",
        detail: "Something went wrong with the download.",
      });
    }
  };

  const setCorrectionTextLinesAtIndex = (pageIndex, updatedLines) => {
    setCorrectionTextLines((prevTextLines) =>
      updateArrayAtIndex(prevTextLines, pageIndex, updatedLines)
    );
    const combined = updatedLines.map((line) => line.text).join("\n");
    setCorrection((prev) => updateArrayAtIndex(prev, pageIndex, combined));

    if (correctionPageXMLs[pageIndex]) {
      mergeUserEditsIntoPageXML(correctionPageXMLs[pageIndex], updatedLines)
        .then((newXML) => {
          setCorrectionPageXMLs((prev) => updateArrayAtIndex(prev, pageIndex, newXML));
        })
        .catch((err) => console.warn("Failed to merge user edits into correction PageXML", err));
    }
  };

  const setTextLinesAtIndex = (pageIndex, updatedLines) => {
    setTextLines((prev) => updateArrayAtIndex(prev, pageIndex, updatedLines));

    if (pageXMLs[pageIndex]) {
      mergeUserEditsIntoPageXML(pageXMLs[pageIndex], updatedLines)
        .then((newXML) => {
          setPageXMLs((prev) => updateArrayAtIndex(prev, pageIndex, newXML));
        })
        .catch((err) => console.warn("Failed to merge user edits into OCR PageXML", err));
    }
  };

  return (
    <div>
      <ProgressBar activeStep={activeStep} setActiveStep={setActiveStep} />

      {taskInProgress && (
        <div className="mt-3">
          <PrimeProgressBar
            value={taskProgress}
            showValue
            displayValueTemplate={(val) => `${Math.round(val)}%`}
          />
          <p style={{ textAlign: "center" }}>
            {taskName} ({Math.round(taskProgress)}%)
          </p>
        </div>
      )}

      {activeStep > 0 && (
        <div className="flex flex-row justify-content-between mb-3">
          <div className="flex flex-row">
            <Button
              className={`${!pagesOpen ? "p-button-outlined" : ""}`}
              icon={`pi pi-th-large`}
              label="Pages"
              onClick={() => setPagesOpen(!pagesOpen)}
            />

            <div className={"flex flex-row ml-3 align-items-center"}>
              <Button
                className={"p-button-text"}
                icon={`pi pi-angle-left`}
                onClick={() => setIndexPage(indexPage - 1)}
                disabled={indexPage <= 0}
                text
              />
              <div className={"ml-1 mr-1"}>{`${indexPage + 1} / ${pages?.length}`}</div>
              <Button
                className={"p-button-text"}
                icon={`pi pi-angle-right`}
                onClick={() => setIndexPage(indexPage + 1)}
                disabled={indexPage >= pages.length - 1}
              />
            </div>
          </div>

          <div className="ocr-select-buttons align-items-end">
            {activeStep >= 2 && (
              <SelectButtonOCRView
                viewVisibility={viewVisibility}
                setViewVisibility={setViewVisibility}
                allow_text={activeStep >= 2}
                allow_correction={activeStep >= 3}
                allow_translation={activeStep >= 4}
              />
            )}

            {activeStep >= 2 && (
              <Dropdown
                value={tooltipHighlightMode}
                options={[
                  { label: "Original OCR", value: "original", disabled: disableOriginalMode },
                  {
                    label: "Correction",
                    value: "correction",
                    disabled: !isCorrectionAvailable(),
                  },
                  {
                    label: "Translation",
                    value: "translation",
                    disabled: !isTranslationAvailable(),
                  },
                ]}
                onChange={(e) => {
                  if (e.value === "original" && disableOriginalMode) {
                    return;
                  }
                  setTooltipHighlightMode(e.value);
                }}
                itemTemplate={(option) => {
                  if (option.disabled) {
                    return <span style={{ color: "gray" }}>{option.label}</span>;
                  }
                  return <span>{option.label}</span>;
                }}
                className="ml-3"
              />
            )}
          </div>
        </div>
      )}

      {activeStep === 0 && (
        <FileUpload
          chooseOptions={{
            className: "cl-primary-background cl-primary-border",
          }}
          ref={uploadRef}
          name="file_translation"
          maxFileSize={MAX_FILESIZE}
          accept={ALLOWED_FILE_EXTENSIONS.join(",")}
          customUpload
          auto={true}
          chooseLabel={"Choose scanned document"}
          emptyTemplate={
            <p className="m-0 text-sm">
              <i className="pi pi-info-circle"></i> Drag and drop or click to
              upload a document.
              <br />
              <small>
                Supported formats: {ALLOWED_FILE_EXTENSIONS.join(", ")}. Only one
                file can be processed at a time.
              </small>
            </p>
          }
          itemTemplate={itemTemplate}
          uploadHandler={(e) => fileUploader(e)}
          contentClassName={"translate-upload-box"}
        />
      )}

      {activeStep > 0 && (
        <div
          className="flex md:flex-row flex-column mt-3"
          style={{
            height: "75vh",
          }}
        >
          {pagesOpen && (
            <PageSelection
              pages={pages}
              selectedPage={indexPage}
              setSelectedPage={setIndexPage}
            />
          )}

          <OCRSplitview
            file_url={pages[indexPage]?.objectURL}
            text={transcription[indexPage]}
            setText={(text) => {
              setTranscription((prev) =>
                updateArrayAtIndex(prev, indexPage, text)
              );

              const lines = textLines[indexPage] || [];
              setTimeout(async () => {
                if (pageXMLs[indexPage]) {
                  const newXML = await mergeUserEditsIntoPageXML(pageXMLs[indexPage], lines);
                  setPageXMLs((prev) => updateArrayAtIndex(prev, indexPage, newXML));
                }
              }, 0);
            }}
            geojson={geojson[indexPage]}
            textLines={textLines[indexPage]}
            setTextLinesAtIndex={setTextLinesAtIndex}
            correction={correction[indexPage]}
            setCorrection={(text) => {
              setCorrection((prev) =>
                updateArrayAtIndex(prev, indexPage, text)
              );
            }}
            correctionGeojson={correctionGeojson[indexPage]}
            correctionTextLines={correctionTextLines[indexPage]}
            allow_text={activeStep >= 2}
            allow_correction={activeStep >= 3}
            translation={translation[indexPage]}
            allow_translation={activeStep >= 4}
            viewVisibility={viewVisibility}
            setCorrectionTextLinesAtIndex={setCorrectionTextLinesAtIndex}
            currentPageIndex={indexPage}
            tooltipDisplayMode={tooltipHighlightMode}
          />
        </div>
      )}

      {/* Action Menu */}
      <div className="flex flex-row justify-content-between mt-3">
        <Button
          label="Prev"
          icon="pi pi-arrow-left"
          onClick={(e) => {
            let nextStep = activeStep - 1;
            nextStep = Math.min(nextStep, 4);
            nextStep = Math.max(nextStep, 0);
            setActiveStep(nextStep);
          }}
          disabled={activeStep <= 0}
        />

        <div className="flex">
          {activeStep === 2 && (
            <>
              <Button
                label={
                  isOCRingFile ? (
                    <ProgressSpinner className={"translate-loading"} />
                  ) : (
                    "Extract text"
                  )
                }
                className="translate-button cl-primary-background"
                onClick={(e) => setDisplayOCROptions(true)}
                disabled={isOCRingFile || indexPage === null}
              />
              <Button
                label="Upload transcription"
                className="translate-button cl-primary-background ml-2"
                onClick={(e) => setDisplayUploadTranscriptionOptions(true)}
                disabled={isOCRingFile || indexPage === null}
              />
            </>
          )}

          {activeStep === 3 && (
            <Button
              label={
                isCorrecting ? (
                  <ProgressSpinner className={"translate-loading"} />
                ) : (
                  "Correct text"
                )
              }
              className="translate-button cl-primary-background"
              onClick={(e) => setDisplayCorrectionOptions(true)}
              disabled={
                isCorrecting || indexPage === null || !transcription[indexPage]
              }
            />
          )}

          {activeStep === 4 && (
            <Button
              label={
                isTranslating ? (
                  <ProgressSpinner className={"translate-loading"} />
                ) : (
                  "Translate text"
                )
              }
              className="translate-button cl-primary-background"
              onClick={(e) => setDisplayTranslationOptions(true)}
              disabled={isTranslating || indexPage === null}
            />
          )}

          {activeStep >= 2 && (
            <Button
              icon={"pi pi-download"}
              className="ml-3"
              onClick={(e) => setDisplayDownloadOptions(true)}
            />
          )}
        </div>

        <Button
          label="Next"
          icon="pi pi-arrow-right"
          onClick={(e) => {
            let nextStep = activeStep + 1;
            // now we have steps 0-4 for translation step
            nextStep = Math.min(nextStep, 4);
            nextStep = Math.max(nextStep, 0);
            setActiveStep(nextStep);
          }}
          disabled={activeStep >= 4}
        />
      </div>

      {/* OCR Options Dialog */}
      <Dialog
        header="Select OCR options"
        visible={displayOCROptions}
        onHide={() => setDisplayOCROptions(false)}
        style={{
          minWidth: "40vw",
          minHeight: "30vh",
        }}
        contentClassName={"flex flex-column justify-content-evenly"}
      >
        <div className="grid translate-ui-grid flex justify-content-center">
          <div className="flex flex-column mb-2">
            <label className="text-900 font-medium text-sm mb-2">
              OCR Engine
            </label>
            <Dropdown
              options={availableEngines.map((engine) => ({
                label: engine.name,
                value: engine.id,
              }))}
              value={selectedOCREngine}
              placeholder="Select an OCR engine"
              onChange={(e) => setSelectedOCREngine(e.value)}
            />
          </div>
        </div>

        <div className="flex justify-content-center">
          <Button
            label="Extract text"
            onClick={() => {
              fileOCRer();
              setDisplayOCROptions(false);
            }}
            disabled={isOCRingFile || indexPage === null || !selectedOCREngine}
          />
        </div>
      </Dialog>

      {/* Upload Transcription Dialog */}
      <Dialog
        header="Upload transcription"
        visible={displayUploadTranscriptionOptions}
        onHide={() => setDisplayUploadTranscriptionOptions(false)}
        style={{
          minWidth: "40vw",
          minHeight: "30vh",
        }}
        contentClassName={"flex flex-column justify-content-evenly"}
      >
        <p>
          Please upload a manual transcription file (e.g., a PageXML file) for this
          page.
        </p>
        <FileUpload
          name="transcription_file"
          accept=".xml"
          maxFileSize={MAX_FILESIZE}
          customUpload
          auto
          chooseLabel={"Choose transcription file"}
          uploadHandler={uploadTranscriptionHandler}
          contentClassName={"translate-upload-box"}
        />
      </Dialog>

      {/* Correction Options Dialog */}
      <Dialog
        header="Select correction options"
        visible={displayCorrectionOptions}
        onHide={() => setDisplayCorrectionOptions(false)}
        style={{
          minWidth: "40vw",
          minHeight: "45vh",
        }}
        contentClassName={"flex flex-column justify-content-between"}
      >
        <div className={"w-full"}>
          <div className="flex flex-column mb-2">
            <label className="text-900 font-medium text-sm mb-2">
              Correction Method
            </label>
            <Dropdown
              options={correctionOptions}
              value={selectedCorrectionOption}
              placeholder="Select a correction method"
              onChange={(e) => {
                setSelectedCorrectionOption(e.value);
              }}
            />
          </div>

          {/* 
            Show language input only if selectedCorrectionOption 
            is NOT manual_transcription 
          */}
          {selectedCorrectionOption &&
            selectedCorrectionOption !== "manual_transcription" && (
              <div className="flex flex-column mb-2 mt-3">
                <label className="text-900 font-medium text-sm mb-2">
                  Language (required)
                </label>
                <input
                  type="text"
                  className="p-inputtext p-component"
                  placeholder="e.g. en, fr, es"
                  value={correctionLanguage}
                  onChange={(e) => setCorrectionLanguage(e.target.value)}
                />
              </div>
            )}

          {selectedCorrectionOption === "manual_transcription" && (
            <div className="mt-4">
              <p>
                Please upload a manual correction file (e.g., a text file) for this
                page.
              </p>
              <FileUpload
                name="correction_file"
                accept=".txt"
                maxFileSize={MAX_FILESIZE}
                customUpload
                auto
                chooseLabel={"Choose correction file"}
                uploadHandler={handleCorrectionFileUpload}
                contentClassName={"translate-upload-box"}
              />
            </div>
          )}
        </div>

        <div className="flex justify-content-center mt-2">
          <Button
            label="Run Correction"
            onClick={() => {
              correctOCRAll().then(() => {});
              setDisplayCorrectionOptions(false);
            }}
            disabled={
              selectedCorrectionOption === null ||
              (selectedCorrectionOption === "manual_transcription" &&
                correctionFile === null)
            }
          />
        </div>
      </Dialog>

      {/* Translation Options Dialog */}
      <Dialog
        header="Select translation options"
        visible={displayTranslationOptions}
        onHide={() => setDisplayTranslationOptions(false)}
        style={{
          minWidth: "40vw",
          minHeight: "40vh",
        }}
        contentClassName={"flex flex-column justify-content-between"}
      >
        <div className="w-full">
          <div className="flex flex-column mb-2">
            <label className="text-900 font-medium text-sm mb-2">
              Source Language
            </label>
            <Dropdown
              options={availableLanguages}
              value={selectedSourceLang}
              placeholder="Select source language"
              onChange={(e) => setSelectedSourceLang(e.value)}
            />
          </div>

          <div className="flex flex-column mb-2">
            <label className="text-900 font-medium text-sm mb-2">
              Target Language
            </label>
            <Dropdown
              options={availableLanguages}
              value={selectedTargetLang}
              placeholder="Select target language"
              onChange={(e) => setSelectedTargetLang(e.value)}
            />
          </div>
        </div>

        <div className="flex justify-content-center mt-2">
          <Button
            label="Run Translation"
            onClick={() => {
              translateAll(selectedSourceLang, selectedTargetLang).then(() => {});
              setDisplayTranslationOptions(false);
            }}
            disabled={!selectedSourceLang || !selectedTargetLang || isTranslating}
          />
        </div>
      </Dialog>

      <Dialog
        header="Download results"
        visible={displayDownloadOptions}
        onHide={() => setDisplayDownloadOptions(false)}
      >
        <p>Select which results to download</p>
        <div className="mb-2">
          <Checkbox
            inputId="cb-transcription"
            checked={transcription.length > 0}
            onChange={(e) => {}}
            disabled
          />
          <label className="ml-2" htmlFor="cb-transcription">
            Transcription
          </label>
        </div>
        <div className="mb-2">
          <Checkbox
            inputId="cb-correction"
            checked={correction.length > 0}
            onChange={(e) => {}}
            disabled
          />
          <label className="ml-2" htmlFor="cb-correction">
            Correction
          </label>
        </div>
        <div className="mb-4">
          <Checkbox
            inputId="cb-translation"
            checked={translation.some((t) => t && t.trim() !== "")}
            onChange={(e) => {}}
            disabled
          />
          <label className="ml-2" htmlFor="cb-translation">
            Translation
          </label>
        </div>
        <div className="flex justify-content-center">
          <Button
            label="Download"
            onClick={() => {
              downloadResults(
                transcription.length > 0,
                correction.length > 0
              );
              setDisplayDownloadOptions(false);
            }}
            disabled={
              transcription.length === 0 &&
              correction.length === 0 &&
              !translation.some((t) => t && t.trim() !== "")
            }
          />
        </div>
      </Dialog>

      <Toast ref={toast} />
    </div>
  );
};

export default Ocr;

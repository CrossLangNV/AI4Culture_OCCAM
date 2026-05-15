// OCRSplitview.js

import React, {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
} from "react";
import { Splitter, SplitterPanel } from "primereact/splitter";
import { CRS } from "leaflet";
import {
  MapContainer,
  ImageOverlay,
  Polygon,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { ProgressSpinner } from "primereact/progressspinner";
import { SelectButton } from "primereact/selectbutton";
import HideImageOutlinedIcon from "@mui/icons-material/HideImageOutlined";
import { hw } from "./leafletUtils";

const ContentEditableLine = React.forwardRef(function ContentEditableLine(
  { initialText, editable, className, onBlur, onMouseOver, onMouseOut },
  forwardedRef
) {
  const divRef = useRef(null);
  const [didInit, setDidInit] = useState(false);

  useEffect(() => {
    if (!didInit && divRef.current) {
      divRef.current.innerText = initialText || "";
      setDidInit(true);
    }
  }, [didInit, initialText]);

  const handleBlur = useCallback(
    (e) => {
      const finalText = e.target.innerText;
      if (onBlur) onBlur(finalText);
    },
    [onBlur]
  );

  return (
    <div
      ref={(el) => {
        divRef.current = el;
        if (typeof forwardedRef === "function") {
          forwardedRef(el);
        } else if (forwardedRef) {
          forwardedRef.current = el;
        }
      }}
      contentEditable={editable}
      suppressContentEditableWarning
      className={className}
      onBlur={handleBlur}
      onMouseOver={onMouseOver}
      onMouseOut={onMouseOut}
    />
  );
});

const ImageComponent = memo(function ImageComponent({ image }) {
  const map = useMap();

  const imageBounds = useMemo(() => {
    const origin = hw([0, 0], null);
    const corner = hw([image.height, image.width], null);
    return [origin, corner];
  }, [image.height, image.width]);

  useEffect(() => {
    if (image.width > 0 && image.height > 0) {
      map.fitBounds(imageBounds, { animate: true });
    }
  }, [map, imageBounds, image.width, image.height]);

  return (
    <ImageOverlay url={image.src} bounds={imageBounds} opacity={1} zIndex={10} />
  );
});

function ResetMapHook() {
  const map = useMap();

  useEffect(() => {
    map.invalidateSize({ animate: true });
  }, [map]);

  return null;
}

function buildPolygons(geojson) {
  if (!geojson || !geojson.features) return [];

  return geojson.features.map((feat) => {
    const coords = feat.geometry.coordinates.map((pt) => hw(pt, null));
    const textVal = feat.properties.text || feat.properties.name || "";
    return { coords, text: textVal };
  });
}

function segmentTranslationByOriginalLines(translation, originalLines) {
  if (!translation) return [];
  const translationWords = translation.trim().split(/\s+/);
  if (!translationWords.length) return [];

  const originalWordCounts = originalLines.map((lineObj) =>
    (lineObj?.text?.trim() || "").split(/\s+/).filter(Boolean).length
  );
  const sumWordCounts = originalWordCounts.reduce((a, c) => a + c, 0);
  if (!sumWordCounts) return [translation];

  const totalTranslationWords = translationWords.length;
  let lineLengths = originalWordCounts.map((count) =>
    Math.round((count / sumWordCounts) * totalTranslationWords)
  );
  const allocated = lineLengths.reduce((a, c) => a + c, 0);
  const diff = totalTranslationWords - allocated;

  if (diff !== 0 && lineLengths.length) {
    lineLengths[lineLengths.length - 1] += diff;
    if (lineLengths[lineLengths.length - 1] < 0) {
      lineLengths[lineLengths.length - 1] = 0;
    }
  }

  const result = [];
  let currentIdx = 0;
  for (let i = 0; i < lineLengths.length; i++) {
    const howMany = lineLengths[i];
    if (howMany > 0) {
      result.push(translationWords.slice(currentIdx, currentIdx + howMany).join(" "));
      currentIdx += howMany;
    } else {
      result.push("");
    }
  }

  if (currentIdx < translationWords.length && result.length) {
    result[result.length - 1] +=
      (result[result.length - 1] ? " " : "") +
      translationWords.slice(currentIdx).join(" ");
  }

  return result;
}

export const SelectButtonOCRView = ({
  viewVisibility,
  setViewVisibility,
  allow_text = true,
  allow_correction = true,
  allow_translation = true,
}) => {
  const valueFromViewVisibility = useCallback(() => {
    const defaultValues = Object.keys(viewVisibility)
      .filter((key) => viewVisibility[key])
      .map((key) => parseInt(key, 10));

    return defaultValues.length > 0 ? defaultValues : [1];
  }, [viewVisibility]);

  const [value, setValue] = useState(valueFromViewVisibility());

  useEffect(() => {
    setValue(valueFromViewVisibility());
  }, [valueFromViewVisibility]);

  const viewOptions = [{ value: 1, icon: "pi pi-image" }];

  if (allow_text) {
    viewOptions.splice(1, 0, { value: 2, icon: "pi pi-align-left" });
  }

  if (allow_correction) {
    viewOptions.splice(2, 0, { value: 3, icon: "pi pi-check" });
  }

  if (allow_translation) {
    viewOptions.splice(3, 0, { value: 4, icon: "pi pi-globe" });
  }

  const handleSelectedValues = (selectedValues) => {
    if (selectedValues.length === 0) {
      return;
    }

    const updatedVisibility = {};
    viewOptions.forEach((option) => {
      updatedVisibility[option.value] = selectedValues.includes(option.value);
    });

    setViewVisibility(updatedVisibility);
    setValue(
      Object.keys(updatedVisibility)
        .filter((key) => updatedVisibility[key])
        .map((key) => parseInt(key, 10))
    );
  };

  const itemTemplate = (option) => {
    return <i className={option.icon + " p-button-icon"}></i>;
  };

  return (
    <SelectButton
      value={value}
      options={viewOptions}
      onChange={(e) => handleSelectedValues(e.value)}
      optionLabel="label"
      itemTemplate={itemTemplate}
      multiple
    />
  );
};

export function OCRSplitview({
  file_url,
  text,
  setText,
  geojson,
  textLines = [],
  setTextLinesAtIndex,
  allow_text = false,
  correction,
  setCorrection,
  correctionGeojson,
  correctionTextLines = [],
  setCorrectionTextLinesAtIndex,
  allow_correction = false,
  translation,
  allow_translation = false,
  viewVisibility,
  currentPageIndex,
  tooltipDisplayMode = "original",
}) {
  const [map, setMap] = useState(null);
  const [image, setImage] = useState(new Image());
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(false);

  useEffect(() => {
    if (!file_url) {
      setImage(new Image());
      setImageLoading(false);
      setImageError(false);
      return;
    }

    const img = new Image();
    setImageLoading(true);
    img.onload = () => {
      setImageLoading(false);
      setImageError(false);
      setImage(img);
    };
    img.onerror = () => {
      setImageLoading(false);
      setImageError(true);
    };
    img.src = file_url;
  }, [file_url]);

  const [originalPolygons, setOriginalPolygons] = useState([]);
  const [correctionPolygons, setCorrectionPolygons] = useState([]);

  useEffect(() => {
    setOriginalPolygons(buildPolygons(geojson));
  }, [geojson]);

  useEffect(() => {
    setCorrectionPolygons(buildPolygons(correctionGeojson));
  }, [correctionGeojson]);

  useEffect(() => {
    if (viewVisibility[1] && map) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          map.invalidateSize();
        });
      });
    }
  }, [viewVisibility, map]);

  const originalPolygonRefs = useRef([]);
  const correctionPolygonRefs = useRef([]);
  const originalLineRefs = useRef([]);
  const correctionLineRefs = useRef([]);
  const translationLineRefs = useRef([]);

  const [translationLines, setTranslationLines] = useState([]);
  useEffect(() => {
    if (!translation) {
      setTranslationLines([]);
    } else {
      setTranslationLines(segmentTranslationByOriginalLines(translation, textLines));
    }
  }, [translation, textLines]);

  const highlightPolygon = (refArray, idx) => {
    const poly = refArray.current[idx];
    if (!poly || !poly.setStyle) return;
    if (!poly._origStyle) {
      poly._origStyle = { ...poly.options };
    }
    poly.setStyle({ color: "yellow", fillColor: "yellow", fillOpacity: 0.3 });
  };

  const removeHighlightPolygon = (refArray, idx) => {
    const poly = refArray.current[idx];
    if (poly && poly._origStyle) {
      poly.setStyle(poly._origStyle);
    }
  };

  const highlightLine = (refArray, idx) => {
    const el = refArray.current[idx];
    if (el) el.classList.add("highlight");
  };

  const removeHighlightLine = (refArray, idx) => {
    const el = refArray.current[idx];
    if (el) el.classList.remove("highlight");
  };

  const handleOcrLineMouseOver = (idx) => {
    if (tooltipDisplayMode === "original" || tooltipDisplayMode === "translation") {
      highlightPolygon(originalPolygonRefs, idx);
    }
    highlightLine(correctionLineRefs, idx);
    highlightLine(translationLineRefs, idx);
  };

  const handleOcrLineMouseOut = (idx) => {
    if (tooltipDisplayMode === "original" || tooltipDisplayMode === "translation") {
      removeHighlightPolygon(originalPolygonRefs, idx);
    }
    removeHighlightLine(correctionLineRefs, idx);
    removeHighlightLine(translationLineRefs, idx);
  };

  const handleCorrectionLineMouseOver = (idx) => {
    if (tooltipDisplayMode === "correction" || tooltipDisplayMode === "translation") {
      highlightPolygon(correctionPolygonRefs, idx);
    }
    highlightLine(originalLineRefs, idx);
    highlightLine(translationLineRefs, idx);
  };

  const handleCorrectionLineMouseOut = (idx) => {
    if (tooltipDisplayMode === "correction" || tooltipDisplayMode === "translation") {
      removeHighlightPolygon(correctionPolygonRefs, idx);
    }
    removeHighlightLine(originalLineRefs, idx);
    removeHighlightLine(translationLineRefs, idx);
  };

  const handleTranslationLineMouseOver = (idx) => {
    if (tooltipDisplayMode === "translation") {
      highlightPolygon(originalPolygonRefs, idx);
      highlightPolygon(correctionPolygonRefs, idx);
    }
    highlightLine(originalLineRefs, idx);
    highlightLine(correctionLineRefs, idx);
  };

  const handleTranslationLineMouseOut = (idx) => {
    if (tooltipDisplayMode === "translation") {
      removeHighlightPolygon(originalPolygonRefs, idx);
      removeHighlightPolygon(correctionPolygonRefs, idx);
    }
    removeHighlightLine(originalLineRefs, idx);
    removeHighlightLine(correctionLineRefs, idx);
  };

  const getOriginalPolygonTooltip = useCallback(
    (idx) => {
      if (idx < 0 || idx >= originalPolygons.length) return "";
      const polygonText = originalPolygons[idx].text;
      if (tooltipDisplayMode === "original") {
        return textLines[idx]?.text || polygonText;
      }
      if (tooltipDisplayMode === "translation") {
        return translationLines[idx] || "";
      }
      return "";
    },
    [tooltipDisplayMode, originalPolygons, textLines, translationLines]
  );

  const getCorrectionPolygonTooltip = useCallback(
    (idx) => {
      if (idx < 0 || idx >= correctionPolygons.length) return "";
      if (tooltipDisplayMode === "correction") {
        return correctionTextLines[idx]?.text || correctionPolygons[idx].text;
      }
      if (tooltipDisplayMode === "translation") {
        return translationLines[idx] || "";
      }
      return "";
    },
    [tooltipDisplayMode, correctionPolygons, correctionTextLines, translationLines]
  );

  useEffect(() => {
    if (!map) return;

    const closeAndUnbindTooltips = () => {
      originalPolygonRefs.current.forEach((poly) => {
        if (poly) {
          poly.closeTooltip();
          poly.unbindTooltip();
        }
      });
      correctionPolygonRefs.current.forEach((poly) => {
        if (poly) {
          poly.closeTooltip();
          poly.unbindTooltip();
        }
      });
    };

    const rebindTooltips = () => {
      originalPolygonRefs.current.forEach((poly, idx) => {
        if (poly) {
          poly.bindTooltip(getOriginalPolygonTooltip(idx));
        }
      });
      correctionPolygonRefs.current.forEach((poly, idx) => {
        if (poly) {
          poly.bindTooltip(getCorrectionPolygonTooltip(idx));
        }
      });
    };

    map.on("dragstart", closeAndUnbindTooltips);
    map.on("dragend", rebindTooltips);

    return () => {
      map.off("dragstart", closeAndUnbindTooltips);
      map.off("dragend", rebindTooltips);
    };
  }, [map, getOriginalPolygonTooltip, getCorrectionPolygonTooltip]);

  const handleCorrectionLineBlur = useCallback(
    (idx, finalText) => {
      if (!allow_correction || !setCorrectionTextLinesAtIndex) return;
      const newArr = [...correctionTextLines];
      if (newArr[idx]) {
        newArr[idx] = { ...newArr[idx], text: finalText };
      }
      setCorrectionTextLinesAtIndex(currentPageIndex, newArr);
    },
    [allow_correction, currentPageIndex, correctionTextLines, setCorrectionTextLinesAtIndex]
  );

  const [isSyncingScroll, setIsSyncingScroll] = useState(false);
  const ocrPanelRef = useRef(null);
  const correctionPanelRef = useRef(null);
  const translationPanelRef = useRef(null);

  const handleSyncScroll = (e, source) => {
    if (isSyncingScroll) return;
    setIsSyncingScroll(true);
    const newScrollTop = e.target.scrollTop;

    if (source === "ocr") {
      if (correctionPanelRef.current) correctionPanelRef.current.scrollTop = newScrollTop;
      if (translationPanelRef.current) translationPanelRef.current.scrollTop = newScrollTop;
    } else if (source === "correction") {
      if (ocrPanelRef.current) ocrPanelRef.current.scrollTop = newScrollTop;
      if (translationPanelRef.current) translationPanelRef.current.scrollTop = newScrollTop;
    } else if (source === "translation") {
      if (ocrPanelRef.current) ocrPanelRef.current.scrollTop = newScrollTop;
      if (correctionPanelRef.current) correctionPanelRef.current.scrollTop = newScrollTop;
    }

    setTimeout(() => setIsSyncingScroll(false), 50);
  };

  const handleOriginalPolygonMouseOver = (idx) => {
    if (tooltipDisplayMode === "original" || tooltipDisplayMode === "translation") {
      highlightLine(originalLineRefs, idx);
    }
    highlightLine(correctionLineRefs, idx);
    highlightLine(translationLineRefs, idx);
  };

  const handleOriginalPolygonMouseOut = (idx) => {
    if (tooltipDisplayMode === "original" || tooltipDisplayMode === "translation") {
      removeHighlightLine(originalLineRefs, idx);
    }
    removeHighlightLine(correctionLineRefs, idx);
    removeHighlightLine(translationLineRefs, idx);
  };

  const handleCorrectionPolygonMouseOver = (idx) => {
    if (tooltipDisplayMode === "correction" || tooltipDisplayMode === "translation") {
      highlightLine(correctionLineRefs, idx);
    }
    highlightLine(originalLineRefs, idx);
    highlightLine(translationLineRefs, idx);
  };

  const handleCorrectionPolygonMouseOut = (idx) => {
    if (tooltipDisplayMode === "correction" || tooltipDisplayMode === "translation") {
      removeHighlightLine(correctionLineRefs, idx);
    }
    removeHighlightLine(originalLineRefs, idx);
    removeHighlightLine(translationLineRefs, idx);
  };

  return (
    <div className="occ-full-width flex flex-column flex-grow-1">
      <Splitter
        className="flex-grow-1"
        layout="horizontal"
        stateKey="ocr-splitter"
        stateStorage="local"
        onResizeEnd={() => {
          if (map) map.invalidateSize({ animate: true });
        }}
      >
        <SplitterPanel key="panelImage" minSize={10} className={!viewVisibility[1] ? "hidden" : ""}>
          <MapContainer center={[0, 0]} scrollWheelZoom crs={CRS.Simple} ref={setMap}>
            <ResetMapHook />
            {imageLoading && (
              <div className="flex align-items-center justify-content-center" style={{ height: "100%" }}>
                <ProgressSpinner />
              </div>
            )}
            {imageError && (
              <div className="flex align-items-center justify-content-center" style={{ height: "100%" }}>
                <HideImageOutlinedIcon style={{ fontSize: 100 }} />
                <p>Failed to load image</p>
              </div>
            )}
            {!!image.width && <ImageComponent image={image} />}

            {originalPolygons.map((poly, idx) => {
              const style = { color: "#3388ff", fillColor: "#3388ff", fillOpacity: 0.15 };
              return (
                <Polygon
                  key={`orig-poly-${idx}`}
                  positions={poly.coords}
                  pathOptions={style}
                  ref={(r) => (originalPolygonRefs.current[idx] = r)}
                  eventHandlers={{
                    mouseover: () => handleOriginalPolygonMouseOver(idx),
                    mouseout: () => handleOriginalPolygonMouseOut(idx),
                  }}
                >
                  <Tooltip key={`orig-tooltip-${idx}-${tooltipDisplayMode}`}>
                    {getOriginalPolygonTooltip(idx)}
                  </Tooltip>
                </Polygon>
              );
            })}

            {correctionPolygons.map((poly, idx) => {
              const style = { color: "#3388ff", fillColor: "#3388ff", fillOpacity: 0.15 };
              return (
                <Polygon
                  key={`corr-poly-${idx}`}
                  positions={poly.coords}
                  pathOptions={style}
                  ref={(r) => (correctionPolygonRefs.current[idx] = r)}
                  eventHandlers={{
                    mouseover: () => handleCorrectionPolygonMouseOver(idx),
                    mouseout: () => handleCorrectionPolygonMouseOut(idx),
                  }}
                >
                  <Tooltip
                    key={`corr-tooltip-${idx}-${tooltipDisplayMode}`}
                    direction="bottom"
                    offset={[0, 20]}
                    opacity={1}
                  >
                    {getCorrectionPolygonTooltip(idx)}
                  </Tooltip>
                </Polygon>
              );
            })}
          </MapContainer>
        </SplitterPanel>

        <SplitterPanel key="panelOCR" minSize={10} className={!viewVisibility[2] ? "hidden" : ""}>
          <div
            ref={ocrPanelRef}
            className="transcription-panel"
            style={{ overflowY: "auto", height: "100%" }}
            onScroll={(e) => handleSyncScroll(e, "ocr")}
          >
            {textLines.map((lineObj, idx) => (
              <ContentEditableLine
                key={`ocr-line-${idx}`}
                initialText={lineObj.text}
                editable={allow_text}
                className="transcription-line"
                onMouseOver={() => handleOcrLineMouseOver(idx)}
                onMouseOut={() => handleOcrLineMouseOut(idx)}
                onBlur={(finalText) => {
                  if (!allow_text || typeof setTextLinesAtIndex !== "function") return;
                  const updatedLines = [...textLines];
                  updatedLines[idx] = { ...updatedLines[idx], text: finalText };
                  setTextLinesAtIndex(currentPageIndex, updatedLines);
                  setText(updatedLines.map((line) => line.text).join("\n"));
                }}
                ref={(el) => (originalLineRefs.current[idx] = el)}
              />
            ))}
          </div>
        </SplitterPanel>

        <SplitterPanel key="panelCorrection" minSize={10} className={!viewVisibility[3] ? "hidden" : ""}>
          <div
            ref={correctionPanelRef}
            className="transcription-panel"
            style={{ overflowY: "auto", height: "100%" }}
            onScroll={(e) => handleSyncScroll(e, "correction")}
          >
            {correctionTextLines.map((lineObj, idx) => (
              <ContentEditableLine
                key={`corr-line-${idx}`}
                initialText={lineObj.text}
                editable={allow_correction}
                className="correction-line"
                onMouseOver={() => handleCorrectionLineMouseOver(idx)}
                onMouseOut={() => handleCorrectionLineMouseOut(idx)}
                onBlur={(finalText) => {
                  handleCorrectionLineBlur(idx, finalText);
                  const updatedLines = correctionTextLines.map((line, lineIndex) =>
                    lineIndex === idx ? { ...line, text: finalText } : line
                  );
                  setCorrection(updatedLines.map((line) => line.text).join("\n"));
                }}
                ref={(el) => (correctionLineRefs.current[idx] = el)}
              />
            ))}
          </div>
        </SplitterPanel>

        <SplitterPanel key="panelTranslation" minSize={10} className={!viewVisibility[4] ? "hidden" : ""}>
          <div
            ref={translationPanelRef}
            className="translation-panel"
            style={{ overflowY: "auto", height: "100%" }}
            onScroll={(e) => handleSyncScroll(e, "translation")}
          >
            {translationLines.map((lineText, idx) => (
              <ContentEditableLine
                key={`translation-line-${idx}`}
                initialText={lineText}
                editable={allow_translation}
                className="translation-line"
                onMouseOver={() => handleTranslationLineMouseOver(idx)}
                onMouseOut={() => handleTranslationLineMouseOut(idx)}
                ref={(el) => (translationLineRefs.current[idx] = el)}
              />
            ))}
          </div>
        </SplitterPanel>
      </Splitter>
    </div>
  );
}

export default OCRSplitview;

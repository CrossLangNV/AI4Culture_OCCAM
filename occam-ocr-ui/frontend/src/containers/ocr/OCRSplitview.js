// OCRSplitview.js

import HideImageOutlinedIcon from "@mui/icons-material/HideImageOutlined";
import { CRS } from "leaflet";
import { ProgressSpinner } from "primereact/progressspinner";
import { SelectButton } from "primereact/selectbutton";
import { Splitter, SplitterPanel } from "primereact/splitter";
import React, {
  memo,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
} from "react";
import {
  ImageOverlay,
  MapContainer,
  Polygon,
  Tooltip,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { hw } from "./leafletUtils";

export const SelectButtonOCRView = ({
  viewVisibility,
  setViewVisibility,
  allow_text = true,
  allow_correction = true,
}) => {
  const valueFromViewVisibility = () => {
    const defaultValues = Object.keys(viewVisibility)
      .filter((key) => viewVisibility[key])
      .map((key) => parseInt(key, 10));

    return defaultValues.length > 0 ? defaultValues : [1];
  };

  const [value, setValue] = useState(valueFromViewVisibility());

  useEffect(() => {
    setValue(valueFromViewVisibility());
  }, [viewVisibility]);

  const viewOptions = [
    {
      value: 1,
      icon: "pi pi-image",
    },
  ];
  if (allow_text) {
    viewOptions.splice(1, 0, {
      value: 2,
      icon: "pi pi-align-left",
    });
  }

  if (allow_correction) {
    viewOptions.splice(2, 0, {
      value: 3,
      icon: "pi pi-check",
    });
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

const ImageComponent = memo(({ image }) => {
  const map = useMap();

  const imageBounds = useMemo(() => {
    const origin = hw([0, 0], null);
    const corner = hw([image.height, image.width], null);
    return [origin, corner];
  }, [image.height, image.width]);

  useEffect(() => {
    map.fitBounds(imageBounds, { animate: true });
  }, [map, imageBounds]);

  return (
    <ImageOverlay
      url={image.src}
      bounds={imageBounds}
      opacity={1}
      zIndex={10}
    />
  );
});

const LeafletMarkers = memo(
  ({
    leafletMarkers,
    highlightText,
    removeHighlightText,
    polygonRefs,
    panel,
  }) => {
    const map = useMap();

    return leafletMarkers.map((marker, idx) => {
      const initialStyle = {
        color: "#3388ff",
        fillColor: "#3388ff",
        fillOpacity: 0.1,
      };

      return (
        <Polygon
          key={`${panel}-polygon-${idx}`}
          positions={marker.bounds}
          pathOptions={initialStyle}
          eventHandlers={{
            mouseover: () => {
              highlightText(idx);
            },
            mouseout: () => {
              removeHighlightText(idx);
            },
          }}
          ref={(ref) => {
            if (ref) {
              polygonRefs.current[idx] = ref;
            }
          }}
        >
          <Tooltip
            className="occ-leaflet-tooltip"
            direction="bottom"
            offset={[0, 20]}
            opacity={1}
          >
            {marker.popupMessage}
          </Tooltip>
        </Polygon>
      );
    });
  }
);

export const OCRSplitview = ({
  file_url,
  text,
  setText,
  geojson, // Transcription geojson
  textLines, // Transcription textLines
  correction,
  setCorrection,
  correctionGeojson, // Correction geojson
  correctionTextLines, // Correction textLines
  allow_text = false,
  allow_correction = false,
  viewVisibility,
  setCorrectionTextLinesAtIndex,
  currentPageIndex,
}) => {
  const [map, setMap] = useState(null);

  // Refs for transcription panel
  const polygonRefs = useRef([]);
  const textLineRefs = useRef([]);

  // Refs for correction panel
  const correctionPolygonRefs = useRef([]);
  const correctionTextLineRefs = useRef([]);

  const [leafletMarkers, setLeafletMarkers] = useState([]);
  const [correctionLeafletMarkers, setCorrectionLeafletMarkers] = useState([]);

  const [image, setImage] = useState(new Image());
  const [imageLoading, setImageLoading] = useState(false);
  const [imageError, setImageError] = useState(false);

  // Load image
  useEffect(() => {
    const img = new Image();

    if (!file_url) {
      setImage(img);
      setImageError(false);
      setImageLoading(false);
      return;
    }

    setImageLoading(true);

    img.onload = function () {
      setImageLoading(false);
      setImageError(false);
      setImage(img);
    };

    img.onerror = function () {
      setImageLoading(false);
      setImageError(true);
    };

    img.src = file_url;
  }, [file_url]);

  // Generate markers for transcription geojson
  useEffect(() => {
    if (geojson) {
      getLeafletMarkers(geojson, setLeafletMarkers);
    } else {
      setLeafletMarkers([]);
    }
  }, [geojson]);

  // Generate markers for correction geojson
  useEffect(() => {
    if (correctionGeojson) {
      getLeafletMarkers(correctionGeojson, setCorrectionLeafletMarkers);
    } else {
      setCorrectionLeafletMarkers([]);
    }
  }, [correctionGeojson]);

  const getLeafletMarkers = (geojson, setMarkers) => {
    geojson = geojson || { features: [] };

    const leafletMarkersArr = geojson.features.map((c) => {
      const bounds = c.geometry.coordinates.map(hw);
      const popupMessage = c.properties.name;
      const text = c.properties.text || c.properties.name;

      return { popupMessage, bounds, text };
    });

    setMarkers(leafletMarkersArr);
  };

  // Highlighting functions for transcription
  const highlightRegion = (idx) => {
    const polygonRef = polygonRefs.current[idx];
    if (polygonRef) {
      // Store the original style if not already stored
      if (!polygonRef._originalStyle) {
        polygonRef._originalStyle = { ...polygonRef.options };
      }

      polygonRef.setStyle({
        color: "yellow",
        fillColor: "yellow",
        fillOpacity: 0.3,
      });
    }
  };

  const removeHighlight = (idx) => {
    const polygonRef = polygonRefs.current[idx];
    if (polygonRef && polygonRef._originalStyle) {
      polygonRef.setStyle(polygonRef._originalStyle);
    }
  };

  const highlightText = (idx) => {
    const element = textLineRefs.current[idx];
    if (element) {
      element.classList.add("highlight");
    }
  };

  const removeHighlightText = (idx) => {
    const element = textLineRefs.current[idx];
    if (element) {
      element.classList.remove("highlight");
    }
  };

  // Highlighting functions for correction
  const highlightCorrectionRegion = (idx) => {
    const polygonRef = correctionPolygonRefs.current[idx];
    if (polygonRef) {
      // Store original style if not stored
      if (!polygonRef._originalStyle) {
        polygonRef._originalStyle = { ...polygonRef.options };
      }

      polygonRef.setStyle({
        color: "yellow",
        fillColor: "yellow",
        fillOpacity: 0.3,
      });
    }
  };

  const removeCorrectionHighlight = (idx) => {
    const polygonRef = correctionPolygonRefs.current[idx];
    if (polygonRef && polygonRef._originalStyle) {
      polygonRef.setStyle(polygonRef._originalStyle);
    }
  };

  const highlightCorrectionText = (idx) => {
    const element = correctionTextLineRefs.current[idx];
    if (element) {
      element.classList.add("highlight");
    }
  };

  const removeCorrectionHighlightText = (idx) => {
    const element = correctionTextLineRefs.current[idx];
    if (element) {
      element.classList.remove("highlight");
    }
  };

   // Highlight transcription line when interacting with correction line
   const highlightTranscriptionLine = (idx) => {
    const element = textLineRefs.current[idx];
    if (element) {
      element.classList.add("highlight");
    }
  };

  const removeHighlightTranscriptionLine = (idx) => {
    const element = textLineRefs.current[idx];
    if (element) {
      element.classList.remove("highlight");
    }
  };

  // Handle text changes in the correction panel
  const handleCorrectionTextChange = useCallback(
    (idx, event) => {
      const updatedText = event.target.innerText;
      if (correctionTextLines && correctionTextLines[idx]) {
        const updatedLines = [...correctionTextLines];
        updatedLines[idx] = {
          ...updatedLines[idx],
          text: updatedText,
        };
        // Update the parent component's state
        setCorrectionTextLinesAtIndex(currentPageIndex, updatedLines);
      }
    },
    [correctionTextLines, setCorrectionTextLinesAtIndex, currentPageIndex]
  );

  // Reset the map size when necessary
  const ResetMapHook = () => {
    const map = useMap();

    useEffect(() => {
      map.invalidateSize({ animate: true });
    }, [map]);
    return null;
  };

  return (
    <div className="occ-full-width flex flex-column flex-grow-1">
      <Splitter
        className="flex-grow-1"
        layout={"horizontal"}
        stateKey={"ocr-splitter"}
        stateStorage={"local"}
        onResizeEnd={(e) => {
          if (map) {
            map.invalidateSize({ animate: true });
          }
        }}
      >
        <SplitterPanel
          key="panelDocument"
          minSize={10}
          className={!viewVisibility[1] && "hidden"}
        >
          <MapContainer
            center={[0, 0]}
            scrollWheelZoom={true}
            crs={CRS.Simple}
            ref={setMap}
          >
            <ResetMapHook />
            {imageLoading && (
              <div
                className="flex flex-column align-items-center justify-content-center"
                style={{ height: "100%" }}
              >
                <ProgressSpinner />
              </div>
            )}
            {imageError && (
              <div
                className="flex flex-column align-items-center justify-content-center"
                style={{ height: "100%" }}
              >
                <HideImageOutlinedIcon style={{ fontSize: 100 }} />
                <p>Failed to load image</p>
              </div>
            )}
            {!!image.width && <ImageComponent image={image} />}
            {/* Render transcription markers */}
            {leafletMarkers && (
              <LeafletMarkers
                leafletMarkers={leafletMarkers}
                highlightText={highlightText}
                removeHighlightText={removeHighlightText}
                polygonRefs={polygonRefs}
                panel="transcription"
              />
            )}
            {/* Render correction markers */}
            {correctionLeafletMarkers && (
              <LeafletMarkers
                leafletMarkers={correctionLeafletMarkers}
                highlightText={highlightCorrectionText}
                removeHighlightText={removeCorrectionHighlightText}
                polygonRefs={correctionPolygonRefs}
                panel="correction"
              />
            )}
          </MapContainer>
        </SplitterPanel>

         {/* Transcription Panel */}
         <SplitterPanel
          key="panelText"
          minSize={10}
          className={!viewVisibility[2] && "hidden"}
        >
          <div className="transcription-panel" style={{ overflowY: "auto" }}>
            {leafletMarkers &&
              leafletMarkers.map((marker, idx) => (
                <div
                  key={`textline-${idx}`}
                  data-index={idx}
                  ref={(el) => (textLineRefs.current[idx] = el)}
                  onMouseOver={() => highlightRegion(idx)}
                  onMouseOut={() => removeHighlight(idx)}
                  className="transcription-line"
                >
                  {marker.text}
                </div>
              ))}
          </div>
        </SplitterPanel>

        {/* Correction Panel */}
        <SplitterPanel
          key="panelCorrection"
          minSize={10}
          className={!viewVisibility[3] && "hidden"}
        >
          <div className="transcription-panel" style={{ overflowY: "auto" }}>
            {correctionLeafletMarkers &&
              correctionLeafletMarkers.map((marker, idx) => (
                <div
                  key={`correctionline-${idx}`}
                  data-index={idx}
                  ref={(el) => (correctionTextLineRefs.current[idx] = el)}
                  onMouseOver={() => {
                    highlightCorrectionRegion(idx);
                    highlightTranscriptionLine(idx);
                  }}
                  onMouseOut={() => {
                    removeCorrectionHighlight(idx);
                    removeHighlightTranscriptionLine(idx);
                  }}
                  onFocus={() => {
                    highlightCorrectionRegion(idx);
                    highlightTranscriptionLine(idx);
                  }}
                  onBlur={() => {
                    removeCorrectionHighlight(idx);
                    removeHighlightTranscriptionLine(idx);
                  }}
                  className="transcription-line"
                  contentEditable={true}
                  suppressContentEditableWarning={true}
                  onInput={(event) => handleCorrectionTextChange(idx, event)}
                >
                  {marker.text}
                </div>
              ))}
          </div>
        </SplitterPanel>
      </Splitter>
    </div>
  );
};

export default OCRSplitview;

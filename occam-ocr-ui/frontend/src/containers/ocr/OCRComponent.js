import React, { useEffect, useState } from "react";
import L from "leaflet";

const OCRComponent = ({ pagexmlString, imageUrl }) => {
  const [textLines, setTextLines] = useState([]);

  useEffect(() => {
    // Parse the XML and extract text lines
    const parser = new DOMParser();
    const xmlDoc = parser.parseFromString(pagexmlString, "text/xml");
    const lines = [];
    const textLineElements = xmlDoc.getElementsByTagName("TextLine");

    for (let i = 0; i < textLineElements.length; i++) {
      const textLineElement = textLineElements[i];
      const unicodeElements = textLineElement.getElementsByTagName("Unicode");
      const textContent = unicodeElements[0]?.textContent || "";
      const coordsElement = textLineElement.getElementsByTagName("Coords")[0];
      const points = coordsElement.getAttribute("points");
      const coordinates = points.split(" ").map((point) => {
        const [x, y] = point.split(",").map(Number);
        return [y, x]; // Leaflet uses [lat, lng]
      });

      lines.push({
        id: textLineElement.getAttribute("id"),
        text: textContent.trim(),
        coordinates,
        index: i,
      });
    }

    setTextLines(lines);

    // Initialize Leaflet map and add image overlay
    const map = L.map("map", {
      crs: L.CRS.Simple,
      zoomControl: false,
      attributionControl: false,
    });

    const img = new Image();
    img.src = imageUrl;
    img.onload = function () {
      const bounds = [[0, 0], [img.height, img.width]];
      const image = L.imageOverlay(imageUrl, bounds).addTo(map);
      map.fitBounds(bounds);

      // Add polygons to the map
      lines.forEach((line) => {
        const polygon = L.polygon(line.coordinates, {
          color: "transparent",
          fillColor: "transparent",
        }).addTo(map);

        polygon.on("mouseover", () => highlightText(line.index));
        polygon.on("mouseout", () => removeHighlight(line.index));

        // Store reference
        line.polygon = polygon;
      });
    };
  }, [pagexmlString, imageUrl]);

  const highlightRegion = (index) => {
    const line = textLines[index];
    line.polygon.setStyle({
      color: "blue",
      fillColor: "blue",
      fillOpacity: 0.3,
    });
  };

  const removeHighlight = (index) => {
    const line = textLines[index];
    line.polygon.setStyle({
      color: "transparent",
      fillColor: "transparent",
      fillOpacity: 0,
    });
  };

  const highlightText = (index) => {
    document.querySelector(`[data-index='${index}']`).classList.add("highlight");
  };

  const removeHighlight = (index) => {
    document.querySelector(`[data-index='${index}']`).classList.remove("highlight");
  };

  return (
    <div className="ocr-container">
      <div id="map" className="ocr-map"></div>
      <div className="transcription-panel">
        {textLines.map((line) => (
          <div
            key={line.id}
            data-index={line.index}
            onMouseOver={() => highlightRegion(line.index)}
            onMouseOut={() => removeHighlight(line.index)}
            className="transcription-line"
          >
            {line.text}
          </div>
        ))}
      </div>
    </div>
  );
};

export default OCRComponent;

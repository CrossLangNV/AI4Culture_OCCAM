import Leaflet from "leaflet";

export const leafletScale = 0.1; // TODO Change scale later

export const hw = (h, w) => {
  if (Leaflet.Util.isArray(h)) {
    // When doing xy([x, y]);
    return hw(h[0], h[1]);
  }
  // let height go from top to bottom
  return Leaflet.latLng(-h * leafletScale, w * leafletScale); // When doing xy(x, y);
};

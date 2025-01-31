import axios from "axios";
import { setupInterceptorsTo } from "./interceptors";
import { baseUrl } from "../constants/axiosConf";

const api = setupInterceptorsTo(
  axios.create({
    baseURL: baseUrl,
  })
);
// Attach access token if it exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

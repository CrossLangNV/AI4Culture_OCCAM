import axios from "axios";
import { Logout } from "../actions/authActions";
import { useDispatch } from "react-redux";
import { baseUrl } from "../constants/axiosConf";

export const setupInterceptorsTo = (axiosInstance) => {
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;

      // If 401, try refresh
      if (error.response?.status === 401 && !originalRequest._retry) {
        originalRequest._retry = true; // prevent infinite loop

        const refreshToken = localStorage.getItem("refreshToken");
        if (!refreshToken) {
          // No refresh token => must log out
          useDispatch(Logout());
          return Promise.reject(error);
        }

        try {
          // Attempt refresh
          // FIX ME: baseUrl is defined somehow as undefined
          //const response = await axios.post(baseUrl + "/api/user/token/refresh/", {
          //  refresh: refreshToken,
          //});

          //hardcoded url for now
          const response = await axios.post("https://ai4culture.crosslang.dev/api/user/token/refresh/", {
            refresh: refreshToken,
          });

          // Store new access token
          localStorage.setItem("accessToken", response.data.access);
          // Optionally update Redux:
          // store.dispatch({
          //   type: LOGIN_SUCCESS,
          //   payload: { access: response.data.access, refresh: refreshToken },
          // });

          // Update the original request’s Authorization header
          originalRequest.headers["Authorization"] = `Bearer ${response.data.access}`;

          // Re-try the original request
          return axiosInstance(originalRequest);
        } catch (refreshError) {
          // Refresh failed => must log out
          useDispatch(Logout());
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );

  return axiosInstance;
};

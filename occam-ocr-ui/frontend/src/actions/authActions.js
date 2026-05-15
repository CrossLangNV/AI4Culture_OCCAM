import { AuthActionTypes } from "../constants/auth-action-types";
import api from "../interceptors/api";

export const LoadUser = () => async (dispatch) => {
  if (localStorage.getItem("access")) {
    dispatch({
      type: AuthActionTypes.GET_USER_LOADING,
    });

    try {
      const res = await api.get("/auth/me");

      dispatch({
        type: AuthActionTypes.GET_USER_SUCCESS,
        payload: res.data,
      });
    } catch (err) {
      dispatch({
        type: AuthActionTypes.GET_USER_FAIL,
      });
    }
  } else {
    dispatch({
      type: AuthActionTypes.GET_USER_FAIL,
    });
  }
};

export const rehydrateAuth = () => (dispatch) => {
  // 1. Check localStorage for tokens
  const accessToken = localStorage.getItem("accessToken");
  const refreshToken = localStorage.getItem("refreshToken");

  // 2. If both tokens exist, dispatch LOGIN_SUCCESS so Redux knows
  if (accessToken && refreshToken) {
    dispatch({
      type: AuthActionTypes.AUTH_LOGIN_SUCCESS,
      payload: { access: accessToken, refresh: refreshToken },
    });
  }

  // 3. Dispatch AUTH_REHYDRATE_COMPLETE so the UI knows we're done
  dispatch({
    type: AuthActionTypes.AUTH_REHYDRATE_COMPLETE,
  });
};

export const HasUserAcceptedToS = () => async (dispatch) => {
  if (localStorage.getItem("access")) {
    dispatch({
      type: AuthActionTypes.HAS_USER_ACCEPTED_TOS_LOADING,
    });

    try {
      const res = await api.get("/terms/api/accepted");

      dispatch({
        type: AuthActionTypes.HAS_USER_ACCEPTED_TOS_SUCCESS,
        payload: res.data,
      });
    } catch (err) {
      dispatch({
        type: AuthActionTypes.HAS_USER_ACCEPTED_TOS_FAIL,
      });
    }
  } else {
    dispatch({
      type: AuthActionTypes.HAS_USER_ACCEPTED_TOS_FAIL,
    });
  }
};

export const AcceptToS = () => async (dispatch) => {
  if (localStorage.getItem("access")) {
    dispatch({
      type: AuthActionTypes.ACCEPT_TOS_LOADING,
    });

    try {
      const res = await api.post("/terms/api/accept", {});

      dispatch({
        type: AuthActionTypes.ACCEPT_TOS_SUCCESS,
        payload: res.data,
      });
    } catch (err) {
      dispatch({
        type: AuthActionTypes.ACCEPT_TOS_FAIL,
      });
    }
  } else {
    dispatch({
      type: AuthActionTypes.ACCEPT_TOS_FAIL,
    });
  }
};

export const Login = (email, password, onSuccess) => async (dispatch) => {
  try {
    dispatch({
      type: AuthActionTypes.AUTH_LOGIN_LOADING,
    });

    const response = await api.post("/api/user/login/", {
      email,
      password,
    });

    // Response expected to have { access, refresh }
    const { access, refresh } = response.data;

    // Optionally store tokens in localStorage or wherever
    localStorage.setItem("accessToken", access);
    localStorage.setItem("refreshToken", refresh);

    dispatch({
      type: AuthActionTypes.AUTH_LOGIN_SUCCESS,
      payload: { access, refresh },
    });

    // Fire the callback to navigate user
    if (typeof onSuccess === "function") {
      onSuccess();
    }
    
  } catch (error) {
    dispatch({ type: AuthActionTypes.AUTH_LOGIN_FAILED });
  }
};

export const Register = (email, password, name) => {
  // Return the thunk function:
  return async (dispatch) => {
    dispatch({ type: AuthActionTypes.AUTH_REGISTER_LOADING});

    try {
      const res = await api.post("/api/user/register/", {
        email,
        password,
        name,
      });

      // For a successful creation, Django REST typically returns 201
      if (res.status === 201) {
        dispatch({ type: AuthActionTypes.AUTH_REGISTER_SUCCESS });
        // **IMPORTANT**: return something so the promise resolves
        return res.data;  
      } else {
        // For any unexpected status code
        dispatch({ type: AuthActionTypes.AUTH_REGISTER_FAILED });
        // cause the promise to reject, so .catch() runs
        throw new Error(`Registration failed with status ${res.status}`);
      }
    } catch (err) {
      // If your server returns 400 with a body like { "email": ["already exists"] }
      if (err.response?.status === 400 && err.response.data) {
        const registrationError = new Error("Registration validation failed");
        registrationError.fieldErrors = err.response.data;
        throw registrationError;
      } else {
        // Some other error (network error, 500, etc.)
        dispatch({ type: AuthActionTypes.AUTH_REGISTER_FAILED });
        throw err;
      }
    }
  };
};

export const ModifyRegistrationSuccessMessage = (value) => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.MESSAGE_REGISTRATION_SUCCESS,
    payload: value,
  });
};

export const ModifyUserNotInvitedMessage = (value) => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.MESSAGE_REGISTRATION_NOT_INVITED,
    payload: value,
  });
};

export const ModifyResetSuccessMessage = (value) => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.MESSAGE_PASSWORD_RESET_SUCCESS,
    payload: value,
  });
};

export const ModifyForgotPasswordMessage = (value) => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.MESSAGE_FORGOT_PASSWORD,
    payload: value,
  });
};

export const Logout = () => async (dispatch) => {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  dispatch({
    type: AuthActionTypes.LOGOUT,
  });
};

export const ChangeTutorialState = (userId, value) => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.CHANGE_TUTORIAL_STATE_LOADING,
  });

  try {
    await api.post("/tutorial/api/usertutorials", {
      user: userId,
      value: value,
    });

    dispatch({
      type: AuthActionTypes.CHANGE_TUTORIAL_STATE_SUCCESS,
      payload: value,
    });
  } catch (err) {
    dispatch({
      type: AuthActionTypes.CHANGE_TUTORIAL_STATE_FAILED,
    });
  }
};

export const CloseTutorial = () => async (dispatch) => {
  dispatch({
    type: AuthActionTypes.CHANGE_TUTORIAL_STATE_SUCCESS,
    payload: true,
  });
};

export const ResetPassword = (reset_code, new_password) => async (dispatch) => {
  try {
    dispatch({
      type: AuthActionTypes.AUTH_RESET_PASSWORD_LOADING,
    });

    await api
      .post("/auth/reset-password", {
        reset_code,
        new_password,
      })
      .then((res) => {
        if (res.status === 200) {
          dispatch({
            type: AuthActionTypes.AUTH_RESET_PASSWORD_SUCCESS,
          });
          dispatch(ModifyResetSuccessMessage(true));
        }
      });
  } catch (err) {
    dispatch({
      type: AuthActionTypes.AUTH_RESET_PASSWORD_FAILED,
    });
  }
};

export const ForgotPasswordRequest = (email) => async (dispatch) => {
  try {
    dispatch({
      type: AuthActionTypes.AUTH_FORGOT_PASSWORD_LOADING,
    });

    await api
      .post("/auth/forgot-password", {
        email,
      })
      .then((res) => {
        dispatch({
          type: AuthActionTypes.AUTH_FORGOT_PASSWORD_SUCCESS,
        });
        dispatch(ModifyForgotPasswordMessage(true));
      });
  } catch (err) {
    dispatch({
      type: AuthActionTypes.AUTH_FORGOT_PASSWORD_FAILED,
    });
  }
};

export const GetInvitedUsers = () => async (dispatch) => {
  try {
    dispatch({
      type: AuthActionTypes.GET_INVITED_USERS_LOADING,
    });

    await api.get("/auth/invited").then((res) => {
      dispatch({
        type: AuthActionTypes.GET_INVITED_USERS_SUCCESS,
        payload: res.data,
      });
    });
  } catch (err) {
    dispatch({
      type: AuthActionTypes.GET_INVITED_USERS_FAILED,
    });
  }
};

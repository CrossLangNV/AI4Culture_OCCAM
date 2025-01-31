import { UiActionTypes } from "../constants/ui-action-types";
import api from "../interceptors/api";

export const ModifyLanguage = (language) => async (dispatch) => {
  dispatch({
    type: UiActionTypes.UI_LANGUAGE_MODIFY,
    payload: language,
  });
};

export const GetThemeConfig = () => async (dispatch) => {
  dispatch({
    type: UiActionTypes.UI_GET_THEME_CONFIG_LOADING,
  });

  try {
    let res;
    if (localStorage.getItem("access")) {
      res = await api.get("/theme/");
    } else {
      res = await api.get("/theme/");
    }

    dispatch({
      type: UiActionTypes.UI_GET_THEME_CONFIG_SUCCESS,
      payload: res.data,
    });
  } catch (err) {
    dispatch({
      type: UiActionTypes.UI_GET_THEME_CONFIG_FAILED,
      payload: err,
    });
  }
};

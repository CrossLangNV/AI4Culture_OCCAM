import { TranslationActionTypes } from "../constants/translation-action-types";
import api from "../interceptors/api";

export const GetDocumentAnalysis = (file, language) => async (dispatch) => {
  try {
    dispatch({
      type: TranslationActionTypes.ANALYSIS_LOADING,
    });
    let formData = new FormData();
    formData.append("file", file);
    formData.append("language", language);
    const res = await api.post(`/catalogue/api/readability-document`, formData);
    dispatch({
      type: TranslationActionTypes.ANALYSIS_SUCCESS,
      payload: res.data,
    });
  } catch (e) {
    dispatch({
      type: TranslationActionTypes.ANALYSIS_FAIL,
    });
  }
};

import { TranslationActionTypes } from "../constants/translation-action-types";
import api from "../interceptors/api";

export const GetTranslatedFileStatus = (jobId) => async (dispatch) => {
  try {
    dispatch({
      type: TranslationActionTypes.TRANSLATION_LOADING,
    });

    const res = await api.get(`/catalogue/api/translate-document/${jobId}`);

    dispatch({
      type: TranslationActionTypes.TRANSLATION_SUCCESS,
      payload: res.data,
    });
  } catch (e) {
    dispatch({
      type: TranslationActionTypes.TRANSLATION_FAIL,
    });
  }
};

export const ResetTranslatedFileStatus = () => async (dispatch) => {
  dispatch({
    type: TranslationActionTypes.RESET_TRANSLATED_FILE_STATUS,
  });
};

import { TranslationActionTypes } from "../constants/translation-action-types";

const DefaultState = {
  loading: false,
  data: {},
  errorMsg: "",
};

const AnalysisReducer = (state = DefaultState, action) => {
  switch (action.type) {
    case TranslationActionTypes.ANALYSIS_LOADING:
      return {
        ...state,
        loading: true,
        errorMsg: "",
      };
    case TranslationActionTypes.ANALYSIS_FAIL:
      return {
        ...state,
        loading: false,
        errorMsg: "Unable to load document analysis.",
      };
    case TranslationActionTypes.ANALYSIS_SUCCESS:
      return {
        ...state,
        loading: false,
        errorMsg: "",
        data: action.payload,
      };
    default:
      return state;
  }
};

export default AnalysisReducer;

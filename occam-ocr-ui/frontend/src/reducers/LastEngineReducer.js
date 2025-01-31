import { EngineActionTypes } from "../constants/engine-action-types";

const initialState = {
  sourceLanguage: null,
  targetLanguage: null,
  provider: null,
  domain: null,
  detectLanguage: null,
  ...localStorage.getItem("lastEngine") ? JSON.parse(localStorage.getItem("lastEngine")) : {},
};

const lastEngineReducer = (state = initialState, action) => {
  switch (action.type) {
    case EngineActionTypes.SET_LAST_ENGINE:

      const LastEngine = {
        sourceLanguage: action.payload.sourceLanguage,
        targetLanguage: action.payload.targetLanguage,
        provider: action.payload.provider,
        domain: action.payload.domain,
        detectLanguage: action.payload.detectLanguage,
      }

      localStorage.setItem("lastEngine", JSON.stringify(LastEngine));

      return {
        ...state,
        ...LastEngine,
      };
    default:
      return state;
  }
};

export default lastEngineReducer;

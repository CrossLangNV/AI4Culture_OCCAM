import { UiActionTypes } from "../constants/ui-action-types";

const DefaultState = {
  language: "en",
  themeConfig: [],
};

const UiReducer = (state = DefaultState, action) => {
  switch (action.type) {
    case UiActionTypes.UI_LANGUAGE_MODIFY:
      return {
        ...state,
        language: action.payload,
      };
    case UiActionTypes.UI_GET_THEME_CONFIG_SUCCESS:
      return {
        ...state,
        themeConfig: action.payload,
      };
    default:
      return state;
  }
};

export default UiReducer;

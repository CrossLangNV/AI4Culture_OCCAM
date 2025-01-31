import { combineReducers } from "redux";
import UiReducer from "./uiReducer";
import AuthReducer from "./AuthReducer";
import AnalysisReducer from "./AnalysisReducer";
import LastEngineReducer from "./LastEngineReducer";

const RootReducer = combineReducers({
  uiStates: UiReducer,
  auth: AuthReducer,
  analysis: AnalysisReducer,

  // Store the last engine used/selected for translation
  lastEngine: LastEngineReducer,
});

export default RootReducer;

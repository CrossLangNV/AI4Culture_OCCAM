import { AuthActionTypes } from "../constants/auth-action-types";

const initialState = {
  loading: false,
  access: null,
  refresh: null,
  isAuthenticated: false,
  rehydrated: false,
  showSuccessMessage: false,
  errorMessage: "",
  fieldErrors: {},
};

export default function AuthReducer(state = initialState, action) {
  switch (action.type) {
    case AuthActionTypes.AUTH_LOGIN_LOADING:
      return {
        ...state,
        loading: true,
        showSuccessMessage: false,
        errorMessage: "",
        fieldErrors: {},
      }
    
    case AuthActionTypes.AUTH_REGISTER_LOADING:
      return {
        ...state,
        loading: true,
        showSuccessMessage: false,
        errorMessage: "",
        fieldErrors: {},
      }

    case AuthActionTypes.AUTH_LOGIN_SUCCESS:
      return {
        ...state,
        loading: false,
        access: action.payload.access,
        refresh: action.payload.refresh,
        isAuthenticated: true,
      };

    case AuthActionTypes.AUTH_REGISTER_SUCCESS:
      return {
        ...state,
        loading: false,
        showSuccessMessage: true,
        errorMessage: "",
        fieldErrors: {},
      };

    case AuthActionTypes.AUTH_LOGIN_FAILED:
      return { ...state, loading: false };
    
    case AuthActionTypes.AUTH_REGISTER_FAILED:
      return { 
        ...state, 
        loading: false, 
        errorMessage: action.payload,
        fieldErrors: {},
      }

    case AuthActionTypes.AUTH_REGISTER_FIELD_ERRORS:
      return {
        ...state,
        loading: false,
        fieldErrors: action.payload,
      };
    
    case AuthActionTypes.LOGOUT:
      return {
        ...state,
        access: null,
        refresh: null,
        isAuthenticated: false,
      };
    case AuthActionTypes.AUTH_REHYDRATE_COMPLETE:
      return { ...state, rehydrated: true };

    default:
      return state;
  }
}
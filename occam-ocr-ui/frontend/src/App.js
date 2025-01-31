import { Route, Routes } from "react-router-dom";
import Header from "./containers/core/Header";

import React, { useEffect } from "react";

import { ScrollTop } from "primereact/scrolltop";
import Footer from "./containers/core/Footer";


import "./App.scss";
import "./assets/css/demo/flags.css";
import "./assets/css/demo/lang-flags.css";
import CookieConsent from "./containers/core/CookieConsent";
import Ocr from "./containers/ocr/Ocr";
import PrivateRoute from "./containers/core/PrivateRoute";
import LoginPage from "./containers/core/LoginPage";
import SignupPage from "./containers/core/SignupPage";
import { useDispatch, useSelector } from "react-redux";
import { rehydrateAuth } from "./actions/authActions";

function App() {
  const dispatch = useDispatch();
  const rehydrated = useSelector((state) => state.auth.rehydrated);

  useEffect(() => {
    // on mount, set redux state from localStorage (if tokens exist)
    dispatch(rehydrateAuth());
    // cookie consent dark theme
    document.body.classList.toggle("c_darkmode");

  }, [dispatch]);

   // If we haven't finished checking tokens, show a loading spinner
   if (!rehydrated) {
    return <div>Loading...</div>;
  }

  return (
    <div className="App min-h-screen flex flex-column">
      <Header />

      <div className="p-5 flex flex-column flex-auto">
        <div className="border-2 border-dashed surface-border border-round surface-section flex-auto p-3">
          <Routes>
            <Route
              path="/ui"
              element={
                <PrivateRoute>
                  <Ocr />
                </PrivateRoute>
              }
            />
            <Route path={"/login"} element={<LoginPage />} />
            <Route path={"/signup"} element={<SignupPage />} />
          </Routes>
        </div>
      </div>

      <CookieConsent />
      <Footer />
      <ScrollTop />
    </div>
  );
}

export default App;

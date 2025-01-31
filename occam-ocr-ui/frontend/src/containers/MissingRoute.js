import React from "react";
import { Button } from "primereact/button";
import { useNavigate } from "react-router-dom";

const MissingRoute = () => {
  const navigate = useNavigate();
  return (
    <div className="surface-section px-4 py-8 md:px-6 lg:px-8">
      <div
        style={{
          background:
            "radial-gradient(50% 109137.91% at 50% 50%, rgba(233, 30, 99, 0.1) 0%, rgba(254, 244, 247, 0) 100%)",
        }}
        className="text-center"
      >
        <span className="bg-white text-pink-500 font-bold text-2xl inline-block px-3">
          404
        </span>
      </div>
      <div className="mt-6 mb-5 font-bold text-6xl text-900 text-center">
        Page Not Found
      </div>
      <p className="text-700 text-3xl mt-0 mb-6 text-center">
        Sorry, we couldn't find the page.
      </p>
      <div className="text-center">
        <Button
          className="p-button-text mr-2"
          label="Go Back"
          icon="pi pi-arrow-left"
          onClick={() => {
            navigate(-1);
          }}
        />
        <Button
          label="Go to Home"
          icon="pi pi-home"
          onClick={() => navigate("/")}
        />
      </div>
    </div>
  );
};

export default MissingRoute;

import React from "react";

/**
 *
 * @param activeStep: Index of the active step (0-4)
 */
const ProgressBar = ({ activeStep, setActiveStep }) => {
  const steps = [
    {
      name: "Document selection",
      details: "Upload scanned document",
      icon: "file",
    },
    {
      name: "Page view",
      details: "View pages",
      icon: "images",
    },
    {
      name: "Text recognition",
      details: "Extract text with OCR",
      icon: "align-left",
    },
    {
      name: "Correction",
      details: "Correct pages",
      icon: "check",
    },
    {
      name: "Translation",
      details: "Translate text",
      icon: "globe",
    },
  ];

  const renderStep = (step_index, icon, active_index, nSteps = steps.length) => {
    const borderCN =
      step_index === active_index
        ? "border-2 primary-border-color"
        : "border-2 border-300";
    const iconCN = step_index <= active_index ? "primary-color" : "text-600";
    const nameCN = step_index === active_index ? "primary-color" : "text-900";
    const bgCN = step_index <= active_index ? "surface-card" : "surface-50";

    return (
      <>
        <div
          className={`${borderCN} ${bgCN} border-round p-3
           flex flex-column md:flex-row align-items-center z-1 cursor-pointer`}
          onClick={() => setActiveStep(step_index)}
        >
          <i
            className={`pi pi-${icon} ${iconCN} text-2xl md:text-4xl mb-2 md:mb-0 mr-0
             md:mr-3`}
          ></i>
          <div>
            <div className={`${nameCN} font-medium mb-1`}>
              {steps[step_index].name}
            </div>
            <span className="text-600 text-sm hidden md:block">
              {steps[step_index].details}
            </span>
          </div>
        </div>
        {step_index !== nSteps - 1 && renderStepLine()}
      </>
    );
  };

  const renderStepLine = () => {
    return (
      <div
        className="absolute top-50 left-100 surface-300 hidden md:block w-5rem"
        style={{ transform: "translateY(-50%)", height: "2px" }}
      ></div>
    );
  };

  return (
    <div className="pb-3">
      <ul className="list-none p-0 m-0 flex flex-column md:flex-row">
        {steps.map((step, index) => {
          return (
            <li
              key={index}
              className={`relative mr-0 flex-auto ${
                index !== steps.length - 1 ? "md:mr-8" : ""
              }`}
            >
              {renderStep(index, step.icon, activeStep)}
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default ProgressBar;

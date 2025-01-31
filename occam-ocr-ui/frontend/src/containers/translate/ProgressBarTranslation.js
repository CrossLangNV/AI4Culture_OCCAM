import React from "react";
import { ProgressBar } from "primereact/progressbar";

const ProgressBarTranslation = (props) => {
  const [value, setValue] = React.useState(props.value);
  const [mode, setMode] = React.useState(props.mode);

  React.useEffect(() => {
    setValue(props.value);
    setMode(props.mode);
  }, [props.value, props.mode]);

  return (
    <div className="w-full card">
      <div className="mb-2 w-full">
        <span className="tiny">
          {mode === "indeterminate" ? "Loading..." : "Translating..."}
        </span>
      </div>
      <ProgressBar mode={mode} value={value} />
    </div>
  );
};

export default React.memo(ProgressBarTranslation);

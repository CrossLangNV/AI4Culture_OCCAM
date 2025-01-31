import { InputTextarea } from "primereact/inputtextarea";
import { Button } from "primereact/button";
import React from "react";

export const CopyInputTextArea = ({ text, setText, placeholder = "..." }) => {
  return (
    <div className="relative h-full w-full">
      <InputTextarea
        // Make sure to enter empty string if no text is available
        value={text == null ? "" : text}
        onChange={(e) => setText(e.target.value)}
        className={"w-full h-full"}
        placeholder={placeholder}
      />
      <Button
        className="p-button-outlined absolute right-0 bottom-0 m-3"
        icon="pi pi-copy"
        onClick={() => {
          if (text) {
            navigator.clipboard
              .writeText(text)
              .then(function () {})
              .catch(function () {});
          }
        }}
      ></Button>
    </div>
  );
};

export default CopyInputTextArea;

import React from "react";
import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import { useSelector, useDispatch } from "react-redux";
import { GetDocumentAnalysis } from "../../actions/analysisActions";
import { Tooltip } from "primereact/tooltip";

const Analysis = ({ file, language, className = "" }) => {
  const analysis = useSelector((state) => state.analysis);
  const dispatch = useDispatch();

  React.useEffect(() => {
    dispatch(GetDocumentAnalysis(file, language));
  }, [file, language]);

  return (
    <div className={`w-full ${className}`}>
      <div className="flex w-full relative align-items-center justify-content-start my-3 px-4">
        <div className="border-top-1 border-300 top-50 left-0 absolute w-full"></div>
        <div className="px-2 z-1 surface-0 flex align-items-center">
          <i className="pi pi-search text-900 mr-2"></i>
          <span className="text-900 font-medium">Analysis</span>
        </div>
      </div>
      {analysis.errorMsg ? (
        <div className="col-12">{analysis.errorMsg}</div>
      ) : analysis.loading ? (
        <div className="col-12">Loading analysis data...</div>
      ) : (
        <div className="col-12">
          <DataTable
            value={[analysis.data]}
            className="translate-ui-full-width"
          >
            <Column field="sentence_count" header="Sentence count"></Column>
            <Column field="word_count" header="Word count"></Column>
            <Column field="char_count" header="Character count"></Column>
            <Column
              field="avg_sentence_length"
              header="Average sentence length"
            ></Column>
            <Column
              field="avg_word_length"
              header="Average word length"
            ></Column>
            <Column
              field="readability_score"
              header={
                <>
                  Readability{" "}
                  <i className="pi pi-info-circle p-dt-tooltip-readability">
                    <Tooltip
                      target=".p-dt-tooltip-readability"
                      position="top"
                      content="Readability is a measure of how easy it is to read and understand a text. The score ranges from 1 to 18. The lower the score, the easier it is to read."
                    />
                  </i>
                </>
              }
            ></Column>
          </DataTable>
        </div>
      )}
    </div>
  );
};

export default React.memo(Analysis);

import { ScrollPanel } from "primereact/scrollpanel";
import { Card } from "primereact/card";
import { Image } from "primereact/image";
import React from "react";

/**
 * Page selection component
 * Shows a list of pages and allows the user to select one
 * The pages are shown as thumbnails
 * @param pages
 * @param selectedPage - index of the selected page
 * @param setSelectedPage - callback to set the selected page index
 */
export const PageSelection = ({ pages, selectedPage, setSelectedPage }) => {
  const onPageClick = (index) => {
    setSelectedPage(index);
  };

  const pageScrollerHeight = "360px";
  const pageThumbnailHeight = "200px";
  const pageThumbnailWidth = "150px";

  return (
    <div className={"mr-0 md:mr-3 mb-3 md:mb-0"}>
      <ScrollPanel
        // className={"h-100"}
        style={{
          width: "100%",
          //   // height: pageScrollerHeight,
          //
          height: "100%",
          padding: "0",
        }}
      >
        <div
          className="flex
        flex-row
        md:flex-column
"
        >
          {pages.length === 0 && <p>No pages found. Please upload a document</p>}
          {pages.map((page, index) => (
            <Card
              className="cursor-pointer"
              key={`page-${index}`}
              style={{
                cursor: "pointer",
                margin: "0.5rem",
                padding: "0rem",
              }}
              onClick={() => onPageClick(index)}
              footer={`Page ${index + 1}`}
            >
              <div className={selectedPage === index ? "selected" : ""}>
                <Image
                  src={page.objectURL}
                  alt={page.name}
                  width={pageThumbnailWidth}
                  height={pageThumbnailHeight}
                />
              </div>
            </Card>
          ))}
        </div>
      </ScrollPanel>
    </div>
  );
};

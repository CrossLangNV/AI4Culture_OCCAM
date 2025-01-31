import React, { lazy, Suspense } from "react";
import { useSelector } from "react-redux";

const WcsTheme = lazy(() => import("./WcsTheme"));

export const ThemeSelector = ({ children }) => {
  const auth = useSelector((state) => state.auth);

  const companyThemeMap = {
    wcs: <WcsTheme />,
  };

  const selectedTheme = companyThemeMap[auth?.company?.toLowerCase()] || (
    <WcsTheme />
  );

  return (
    <>
      <Suspense fallback={<div>Loading...</div>}>{selectedTheme}</Suspense>
      {children}
    </>
  );
};

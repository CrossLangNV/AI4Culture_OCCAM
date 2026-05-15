import React from "react";
import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <div>
      <div className="occ-footer">
        <a href="http://www.crosslang.com" target="_blank" rel="noreferrer">
          <img
            src="/ai4c_colored.png"
            className="occ-footer-logo"
            alt="Crosslang logo"
          />
        </a>
        <br />
        <span className="font-light text-xs w-10 text-600">
          Version: {window._env_.REACT_APP_VERSION}
        </span>
        <br />
        <Link
          to="/privacy-statement"
          className="footer-links font-light text-xs w-10 text-600"
        >
          Privacy Statement
        </Link>
        <span className="font-light text-xs w-10 text-600"> — </span>
        <Link
          to="/terms-and-conditions"
          className="footer-links font-light text-xs w-10 text-600"
        >
          Terms and Conditions
        </Link>
        <span className="font-light text-xs w-10 text-600"> — </span>
        <a
          href="https://crosslang.com/about-us/"
          className="footer-links font-light text-xs w-10 text-600"
        >
          Copyright © 2026
        </a>
        <p></p>
      </div>
    </div>
  );
};

export default Footer;

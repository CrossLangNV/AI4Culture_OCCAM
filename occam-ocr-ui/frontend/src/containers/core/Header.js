import React, { useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  Logout,
  ModifyRegistrationSuccessMessage,
} from "../../actions/authActions";
import { StyleClass } from "primereact/styleclass";
import { Ripple } from "primereact/ripple";
import { Menu } from "primereact/menu";
import { Menubar } from "primereact/menubar";
import { Button } from "primereact/button";
import { Tooltip } from "primereact/tooltip";

const Header = () => {
  const location = useLocation();
  const dispatch = useDispatch();
  const navigate = useNavigate();

  // Redux
  const auth = useSelector((state) => state.auth);

  // For the navigation mapping (e.g. Home > Configure > Manage configurations)
  const routeMapping = [
    {
      route: "/config",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Manage configurations",
      nameLink: null,
      detail: null,
    },
    {
      route: "/config/create",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Manage configurations",
      nameLink: "/config",
      detail: "Create configuration",
    },
    {
      route: "/config/:id/edit",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Manage configurations",
      nameLink: "/config",
      detail: "Edit Configuration",
    },
    {
      route: "/config/:id",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Manage configurations",
      nameLink: "/config",
      detail: "Configuration Details",
    },
    {
      route: "/engines",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Engines",
      nameLink: "/engines",
      detail: null,
    },
    {
      route: "/providers",
      category: "Configure",
      categoryLink: "/config",
      categoryClickable: false,
      name: "Providers",
      nameLink: "/providers",
      detail: null,
    },
    {
      route: "/providers/:id",
      category: "Configure",
      categoryLink: "/providers",
      categoryClickable: false,
      name: "Providers",
      nameLink: "/providers",
      detail: "Provider Details",
    },
    {
      route: "/help/faq",
      category: "Help",
      categoryLink: "/help",
      categoryClickable: false,
      name: "FAQ",
      nameLink: "/help/faq",
      detail: null,
    },
    {
      route: "/privacy-statement",
      category: "Privacy Statement",
      categoryLink: "/privacy-statement",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/terms-and-conditions",
      category: "Terms and Conditions",
      categoryLink: "/terms-and-conditions",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/help/tms",
      category: "Help",
      categoryLink: "/help/tms",
      categoryClickable: false,
      name: "TMS",
      nameLink: "/help/tms",
      detail: null,
    },
    {
      route: "/help/tms/:id",
      category: "Help",
      categoryLink: "/help",
      categoryClickable: false,
      name: "TMS",
      nameLink: "/help/tms",
      detail: "TMS Details",
    },
    {
      route: "/dashboard",
      category: "Dashboard",
      categoryLink: "/dashboard",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/engine-advisory",
      category: "Engine Advisory",
      categoryLink: "/engine-advisory",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/engine-advisory/contact",
      category: "Engine Advisory",
      categoryLink: "/engine-advisory",
      categoryClickable: true,
      name: "Professional Advisory",
      nameLink: "/engine-advisory/contact",
      detail: null,
    },
    {
      route: "/engine-advisory/automated",
      category: "Engine Advisory",
      categoryLink: "/engine-advisory",
      categoryClickable: true,
      name: "Automated",
      // nameLink: "/engine-advisory/automated",
      // detail: "New",
    },
    {
      route: "/engine-advisory/automated/new",
      category: "Engine Advisory",
      categoryLink: "/engine-advisory",
      categoryClickable: true,
      name: "Automated",
      nameLink: "/engine-advisory/automated",
      detail: "New",
    },
    {
      route: "/engine-advisory/automated/:id",
      category: "Engine Advisory",
      categoryLink: "/engine-advisory",
      categoryClickable: true,
      name: "Automated",
      nameLink: "/engine-advisory/automated",
      detail: "Results",
    },
    {
      route: "/ocr",
      category: "Optical Character Recognition",
      categoryLink: "/ocr",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/user-management",
      category: "User management",
      categoryLink: "/user-management",
      categoryClickable: false,
      name: null,
      nameLink: null,
      detail: null,
    },
    {
      route: "/profile",
      category: "Account",
      categoryLink: "/profile",
      categoryClickable: false,
      name: "Profile",
      nameLink: "/profile",
      detail: null,
    },
    {
      route: "/not-implemented-yet",
      category: "Error",
      categoryLink: "/",
      categoryClickable: false,
      name: "Not implemented yet",
      nameLink: "/not-implemented-yet",
      detail: null,
    },
  ];

  const findRouteItem = (route) => {
    return routeMapping.find((item) => {
      // split the route into an array of strings, filter out empty strings
      // e.g. "/config/123/edit" => ["config", "123", "edit"]
      let splitRoute = route.split("/").filter(Boolean);
      splitRoute = splitRoute.map((item) => {
        // item is a parameter if it is a number or if
        // the route matches regex of type /config/:id where id is a hash string
        // reserved keywords: config, create and edit are not parameters
        if (
          parseInt(item) ||
          ((/\/config\/[0-9a-zA-Z]+/.test(route) ||
            /\/automated\/[0-9a-zA-Z]+/.test(route)) &&
            item.match(
              /^config$|^create$|^edit$|^engine-advisory$|^automated$/
            ) === null)
        ) {
          // replace the parameter with a placeholder
          return ":id";
        } else {
          // return the item as is
          return item;
        }
      });
      // join the array of strings back into a string, e.g. "config/123/edit"
      // prepend a slash to the route
      let newRoute = "/" + splitRoute.join("/");
      // compare the new route with the route in the routeMapping
      return item.route === newRoute;
    });
  };

  const getName = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.name;
    }
  };

  const getCategory = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.category;
    }
  };

  const getCategoryLink = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.categoryLink;
    }
  };

  const getNameLink = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.nameLink;
    }
  };

  const getDetail = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.detail;
    }
  };

  const isCategoryClickable = (route) => {
    const routeItem = findRouteItem(route);
    if (routeItem) {
      return routeItem.categoryClickable;
    }
  };

  const configureItems = [
    {
      label: "Manage configurations",
      icon: "pi pi-sliders-h mr-2",
      command: (_) => {
        navigate("/config");
      },
    },
    {
      label: "Engines",
      icon: "pi pi-server mr-2",
      command: (_) => {
        navigate("/engines");
      },
    },
    {
      label: "Providers",
      icon: "pi pi-th-large mr-2",
      command: (_) => {
        navigate("/providers");
      },
    },
  ];

  let advisoryItems = [
    {
      label: "New",
      icon: "pi pi-check-circle mr-2",
      command: (_) => {
        navigate("/engine-advisory");
      },
    },
    {
      label: "History",
      icon: "pi pi-server mr-2",
      command: (_) => {
        navigate("/engine-advisory/automated");
      },
    },
  ];

  let settingsItems = [
    {
      label: "Profile",
      icon: "pi pi-user mr-2",
      command: (_) => {
        navigate("/profile");
      },
    },
    {
      label: "User management",
      icon: "pi pi-cog mr-2",
      command: (_) => {
        navigate("/user-management");
      },
    },
    {
      label: "Sign out",
      icon: "pi pi-sign-out mr-2",
      command: (_) => {
        dispatch(Logout());
        navigate("/login");
      },
    },
  ];

  let helpItems = [
    {
      label: "TMS",
      icon: "pi pi-th-large mr-2",
      command: (_) => {
        navigate("/help/tms");
      },
    },
    {
      label: "FAQ",
      icon: "pi pi-question-circle mr-2",
      command: (_) => {
        navigate("/help/faq");
      },
    },
  ];

  let extraItems = [
    {
      label: "OCR",
      icon: "pi pi-image", // OR pi-search
      command: (_) => {
        navigate("/ocr");
      },
    },
  ];

  const menuItems = [
    {
      label: "Translate",
      icon: "pi pi-comments",
      command: (_) => {
        navigate("/");
      },
    },
    {
      label: "Configure",
      icon: "pi pi-sliders-h",
      items: configureItems,
    },
    {
      label: "Advisory",
      icon: "pi pi-check-circle",
      items: advisoryItems,
    },
    // Dashboard no longer available for now
    {
      label: "Extra",
      icon: "pi pi-list",
      items: extraItems,
    },
    {
      label: "Help",
      icon: "pi pi-question-circle",
      items: helpItems,
    },
    {
      label: auth.user,
      items: settingsItems,
    },
  ];

  const start = (
    <button
      className={"btn-no-decoration text-white white-space-nowrap"}
      onClick={() => {
        navigate("/");
      }}
    >
      <img
        alt="logo"
        src="/icon-crosslang.svg"
        height="48"
        className="mr-2 top-logo"
        aria-hidden={true}
      ></img>
    </button>
  );

  return (
    <div className="bg-white">
      <Tooltip
        target="#info-tooltip-icon"
        content="This interface provides an extension of the OCCAM services as part of the AI4Culture project."
        position="right"
      />
      {/* END Menu */}

      {/* BEGIN Breadcrumbs */}
      <ul
        id="breadcrumbs"
        className="list-none py-3 px-5 m-0 flex align-items-center font-medium overflow-x-auto"
      >
        {/* HOME breadcrumb */}
        {location.pathname.startsWith("/ui") && (
          <>
            <li className="pr-3">
              <button
                className="btn-no-decoration text-white white-space-nowrap underline"
                onClick={() => navigate("/ui")}
              >
                Home
              </button>
            </li>
            <li className="px-2">
              <i className="pi pi-angle-right text-white" />
            </li>
            <i
              id="info-tooltip-icon"
              className="pi pi-info-circle"
              style={{
                position: "absolute",
                left: "9rem",
                top: "1.2rem",
                cursor: "pointer",
                color: "#fff"
              }}
            />
          </>
        )}
        {/* OTHER breadcrumbs */}
        {location.pathname !== "/" &&
          !location.pathname.startsWith("/ui") &&
          location.pathname !== "/login" &&
          !location.pathname.startsWith("signup") &&
          location.pathname !== "/forgot-password" &&
          location.pathname.substr(0, "/reset-password".length) !==
            "/reset-password" && (
            <>
              <li className="pr-3">
                <button
                  className="btn-no-decoration text-white white-space-nowrap underline"
                  onClick={() => navigate("/ui")}
                >
                  Home
                </button>
              </li>
              <li className="px-2">
                <i className="pi pi-angle-right text-white" />
              </li>
            </>
          )}
        {/* breadcrumb levels: home > category > name > detail
            check the level of the current page and display the breadcrumb accordingly */}
        {getName(location.pathname) ? (
          <>
            {getDetail(location.pathname) ? (
              <>
                {/* breadcrumb of type: home > category > name > detail */}
                <li className="px-2">
                  {/* check if category link is clickable */}
                  {isCategoryClickable(location.pathname) ? (
                    <button
                      onClick={() =>
                        navigate(getCategoryLink(location.pathname))
                      }
                      className="btn-no-decoration text-white white-space-nowrap underline"
                    >
                      {getCategory(location.pathname)}
                    </button>
                  ) : (
                    <button className="btn-no-decoration text-white white-space-nowrap disabled-button">
                      {getCategory(location.pathname)}
                    </button>
                  )}
                </li>
                <li className="px-2">
                  <i className="pi pi-angle-right text-white"></i>
                </li>
                <li className="px-2">
                  <button
                    className="btn-no-decoration text-white white-space-nowrap underline"
                    onClick={() => navigate(getNameLink(location.pathname))}
                  >
                    {" "}
                    {getName(location.pathname)}
                  </button>
                </li>
                <li className="px-2">
                  <i className="pi pi-angle-right text-white"></i>
                </li>
                <li className="px-2">
                  <button className="btn-no-decoration text-white white-space-nowrap disabled-button">
                    {" "}
                    {getDetail(location.pathname)}
                  </button>
                </li>
              </>
            ) : (
              <>
                {/* breadcrumb of type: home > category > name */}
                <li className="px-2">
                  {/* check if category link is clickable */}
                  {isCategoryClickable(location.pathname) ? (
                    <button
                      onClick={() =>
                        navigate(getCategoryLink(location.pathname))
                      }
                      className="btn-no-decoration text-white white-space-nowrap underline"
                    >
                      {getCategory(location.pathname)}
                    </button>
                  ) : (
                    <button className="btn-no-decoration text-white white-space-nowrap disabled-button">
                      {getCategory(location.pathname)}
                    </button>
                  )}
                </li>
                <li className="px-2">
                  <i className="pi pi-angle-right text-white"></i>
                </li>
                <li className="px-2">
                  <button className="btn-no-decoration text-white white-space-nowrap disabled-button">
                    {" "}
                    {getName(location.pathname)}
                  </button>
                </li>
              </>
            )}
          </>
        ) : (
          <>
            {/* breadcrumb of type: home > category */}
            <li className="px-2">
              <button
                onClick={() => navigate(getCategoryLink(location.pathname))}
                className="btn-no-decoration text-white white-space-nowrap disabled-button"
              >
                {getCategory(location.pathname)}
              </button>
            </li>
          </>
        )}
      </ul>
      {/* END Breadcrumbs */}
    </div>
  );
};

export default Header;

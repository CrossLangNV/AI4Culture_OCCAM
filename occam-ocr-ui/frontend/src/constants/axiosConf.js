let baseUrl;

const logging = false;

baseUrl = window._env_.REACT_APP_API_URL;

if (process.env.NODE_ENV === "production") {
  if (logging) {
    console.log("Production build");
  }
} else {
  if (logging) {
    console.log("Development build");
  }
}

if (logging) {
  console.log("Build: ", process.env.NODE_ENV);
  console.log("baseUrl: ", baseUrl);
}

export { baseUrl };

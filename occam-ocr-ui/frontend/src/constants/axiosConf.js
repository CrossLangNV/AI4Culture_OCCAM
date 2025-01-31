let baseUrl;
let clientId;
let clientSecret;

const logging = false;

baseUrl = window._env_.REACT_APP_API_URL;
clientId = window._env_.REACT_APP_DJANGO_CLIENT_ID;
clientSecret = window._env_.REACT_APP_DJANGO_CLIENT_SECRET;

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
  console.log("clientId: ", clientId);
  console.log("clientSecret: ", clientSecret);
}

export { baseUrl, clientId, clientSecret };

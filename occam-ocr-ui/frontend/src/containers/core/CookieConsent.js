import { useEffect } from "react";

import "../../../node_modules/vanilla-cookieconsent/dist/cookieconsent.css";
import "../../../node_modules/vanilla-cookieconsent/dist/cookieconsent.js";

export default function CookieConsent() {
  useEffect(() => {
    const cc = window.initCookieConsent();

    cc.run({
      current_lang: "en",
      autoclear_cookies: true, // default: false
      page_scripts: true, // default: false

      // mode: 'opt-in'                          // default: 'opt-in'; value: 'opt-in' or 'opt-out'
      // delay: 0,                               // default: 0
      // auto_language: null                     // default: null; could also be 'browser' or 'document'
      // autorun: true,                          // default: true
      // force_consent: false,                   // default: false
      // hide_from_bots: false,                  // default: false
      remove_cookie_tables: true, // default: false
      // cookie_name: 'cc_cookie',               // default: 'cc_cookie'
      // cookie_expiration: 182,                 // default: 182 (days)
      // cookie_necessary_only_expiration: 182   // default: disabled
      // cookie_domain: location.hostname,       // default: current domain
      // cookie_path: '/',                       // default: root
      // cookie_same_site: 'Lax',                // default: 'Lax'
      // use_rfc_cookie: false,                  // default: false
      // revision: 0,                            // default: 0

      onFirstAction: function (user_preferences, cookie) {
        // callback triggered only once
      },

      onAccept: function (cookie) {
        // ...
      },

      onChange: function (cookie, changed_preferences) {
        // ...
      },

      gui_options: {
        consent_modal: {
          layout: "box", // box/cloud/bar
          position: "bottom left", // bottom/middle/top + left/right/center
          transition: "slide", // zoom/slide
          swap_buttons: false, // enable to invert buttons
        },
        settings_modal: {
          layout: "box", // box/bar
          // position: 'left',         // left/right
          transition: "slide", // zoom/slide
        },
      },

      languages: {
        en: {
          consent_modal: {
            title: "We use cookies!",
            description:
              "This website uses cookies to ensure its proper operation. " +
              "You can block the use of all but necessary cookies by clicking <strong>Reject all</strong>, " +
              "or agree to the usage of all cookies by clicking <strong>Accept all</strong>. " +
              "To configure the cookie settings, please click " +
              '<button type="button" data-cc="c-settings" class="cc-link">here</button>.',
            primary_btn: {
              text: "Accept all",
              role: "accept_all", // 'accept_selected' or 'accept_all'
            },
            secondary_btn: {
              text: "Reject all",
              role: "accept_necessary", // 'settings' or 'accept_necessary'
            },
          },
          settings_modal: {
            title: "Cookie preferences",
            save_settings_btn: "Save settings",
            accept_all_btn: "Accept all",
            reject_all_btn: "Reject all",
            close_btn_label: "Close",
            cookie_table_headers: [
              { col1: "Name" },
              { col2: "Domain" },
              { col3: "Expiration" },
              { col4: "Description" },
            ],
            blocks: [
              {
                title: "Cookie usage 🍪",
                description:
                  'CrossLang uses cookies to ensure the basic functionalities of the website and to enhance your online experience. You can choose for each category to opt-in/out whenever you want. For more details relative to cookies and other sensitive data, please read the full <a href="/privacy-statement" class="cc-link">privacy statement</a>.',
              },
              {
                title: "Strictly necessary cookies",
                description:
                  "These cookies are essential for the proper functioning of the website. Without these cookies, the website would not work properly.",
                toggle: {
                  value: "necessary",
                  enabled: true,
                  readonly: true, // cookie categories with readonly=true are all treated as "necessary cookies"
                },
              },
              {
                title: "Performance and Analytics cookies",
                description:
                  "These cookies allow the website to remember the choices you have made in the past.",
                toggle: {
                  value: "analytics", // your cookie category
                  enabled: false,
                  readonly: false,
                },
                cookie_table: [
                  // list of all expected cookies, there are none at the moment
                  // e.g. [{col1: '_ga', col2: 'crosslangmt.com', col3: 'session', col4: 'Google Analytics'}]
                ],
              },
              {
                title: "Advertisement and Targeting cookies",
                description:
                  "These cookies collect information about how you use the website, which pages you visited and which links you clicked on. All of the data is anonymized and cannot be used to identify you.",
                toggle: {
                  value: "targeting",
                  enabled: false,
                  readonly: false,
                },
              },
              {
                title: "More information",
                description:
                  'For any queries in relation to our policy on cookies and your choices, please <a class="cc-link" href="https://www.crosslang.com">contact us</a>.',
              },
            ],
          },
        },
      },
    });
  }, []);

  return null;
}

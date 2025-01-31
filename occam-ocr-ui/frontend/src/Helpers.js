import React from "react";

export const sourceLanguageFlagTemplate = (rowData, type) => {
  return <React.Fragment>{rowData[type + "_display_name"]}</React.Fragment>;
};

/*
Poll a function until a certain condition is met through a given validate function
*/
export const poll = async ({
  fn,
  fnParams,
  validate,
  interval,
  maxAttempts,
}) => {
  let attempts = 0;

  const executePoll = async (resolve, reject) => {
    const result = await fn(...fnParams);
    attempts++;

    if (validate(result)) {
      return resolve(result);
    } else if (maxAttempts && attempts === maxAttempts) {
      return reject(new Error("Exceeded max attempts"));
    } else {
      setTimeout(executePoll, interval, resolve, reject);
    }
  };

  return new Promise(executePoll);
};

export const delay = (time) => {
  return new Promise((resolve) => setTimeout(resolve, time));
};

/**
 * https://www.30secondsofcode.org/articles/s/react-use-interval-explained
 * useInterval hook
 */
export const useInterval = (callback, delay, maxAttempts) => {
  const savedCallback = React.useRef();
  let attempts = 0;

  React.useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  React.useEffect(() => {
    const tick = () => {
      if (maxAttempts && attempts >= maxAttempts) {
        return new Error("Exceeded max attempts");
      }

      savedCallback.current();
      attempts++;
    };
    if (delay !== null) {
      let id = setInterval(tick, delay);
      return () => clearInterval(id);
    }
  }, [delay, attempts, maxAttempts]);
};

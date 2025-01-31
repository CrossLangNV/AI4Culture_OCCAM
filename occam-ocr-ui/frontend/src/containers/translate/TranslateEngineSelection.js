import React, { Component, useCallback, useEffect } from "react";
import Select from "react-select";
import { useDispatch, useSelector } from "react-redux";
import {
  GetAvailableDomains,
  GetAvailableProviders,
  GetAvailableSourceLanguages,
  GetAvailableTargetLanguages,
  ResetAvailableDomains,
  ResetAvailableProviders,
  ResetAvailableTargetLanguages,
  setLastEngine,
} from "../../actions/engineActions";

const customSelectColors = {
  primary: "var(--primary-color)",
  primary25: "var(--accent-color)",
  primary50: "var(--primary-color-lightest)",
  primary75: "var(--primary-color-lightest)",
};

/**
 * Set a selector only when the value is changed
 * To avoid unnecessary re-renders
 */
const setSelectorChanged = (selector, value, setter) => {
  function areObjectsEqual(objA, objB) {
    if (objA === null && objB === null) {
      return true;
    }

    if (objA === null || objB === null) {
      return false;
    }

    const keysA = Object.keys(objA);
    const keysB = Object.keys(objB);

    if (keysA.length !== keysB.length) {
      return false;
    }

    for (const key of keysA) {
      if (objA[key] !== objB[key]) {
        return false;
      }
    }

    return true;
  }

  if (!areObjectsEqual(selector, value)) {
    setter(value);
  }
};

export class LanguageSelector extends Component {
  constructor(props) {
    super(props);

    this.VALUE_DETECT_LANGUAGE = "Detect language";

    this.onSourceLanguageChange = this.onSourceLanguageChange.bind(this);
    this.determineLabel = this.determineLabel.bind(this);
  }

  onSourceLanguageChange(e) {
    const { setDetectionMode, setSelectedSourceLanguage } = this.props;

    if (!e.detect) {
      setSelectedSourceLanguage(e);
    } else {
      setSelectedSourceLanguage(null);
    }

    setDetectionMode(!!e.detect);
  }

  determineLabel() {
    const { detectionMode, selectedSourceLanguage } = this.props;

    if (!detectionMode) {
      return selectedSourceLanguage;
    }

    if (selectedSourceLanguage) {
      return { label: `${selectedSourceLanguage.label} (Detected)` };
    }

    return {
      label: this.props.enabled
        ? this.VALUE_DETECT_LANGUAGE
        : `Language detection not available`,
    };
  }

  render() {
    const { availableSourceLanguages, ...selectProperties } = this.props;

    const options = (
      this.props.enabled
        ? [{ label: this.VALUE_DETECT_LANGUAGE, detect: true }]
        : []
    ).concat(availableSourceLanguages.data);

    const value = this.determineLabel();

    return (
      <div>
        <Select
          options={options}
          value={value}
          onChange={this.onSourceLanguageChange}
          theme={(theme) => ({
            ...theme,
            colors: {
              ...theme.colors,
              ...customSelectColors,
            },
          })}
          {...selectProperties}
        />
      </div>
    );
  }
}

/**
 * @param enable_language_detection
 * @param languageDetectionMode
 * @param setLanguageDetectionMode
 * Selected options. Contains label and value { label: "English", value: "en" }
 * @param selectedSourceLanguage
 * @param setSelectedSourceLanguage
 * @param selectedTargetLanguage
 * @param setSelectedTargetLanguage
 * @param selectedDomain
 * @param setSelectedDomain
 * @param selectedProvider
 * @param setSelectedProvider
 */
const TranslateEngineSelection = ({
  enable_language_detection,
  languageDetectionMode,
  setLanguageDetectionMode,
  selectedSourceLanguage,
  setSelectedSourceLanguage,
  selectedTargetLanguage,
  setSelectedTargetLanguage,
  selectedDomain,
  setSelectedDomain,
  selectedProvider,
  setSelectedProvider,
}) => {
  const dispatch = useDispatch();

  // Dropdown menu options
  const availableSourceLanguages = useSelector(
    (state) => state.availableSourceLanguages,
  );
  const availableTargetLanguages = useSelector(
    (state) => state.availableTargetLanguages,
  );
  const availableProviders = useSelector((state) => state.availableProviders);
  const availableDomains = useSelector((state) => state.availableDomains);

  const lastEngine = useSelector((state) => state.lastEngine);

  // On page load: load source languages and reset state for language selection
  React.useEffect(() => {
    dispatch(GetAvailableSourceLanguages());
  }, [dispatch]);

  /**
   * When the source language options are loaded, try to preselect the last engine's source language
   */
  React.useEffect(() => {
    if (availableSourceLanguages.loading) {
      // Don't change the selected target language when loading
      return;
    }

    // Check if the last engine had language detection saved
    if (lastEngine?.detectLanguage !== null) {
      // Preselect the detect language option
      languageDetectionMode !== lastEngine?.detectLanguage &&
        setLanguageDetectionMode(lastEngine?.detectLanguage);
    }

    if (!availableSourceLanguages?.data?.length) {
      // No available source languages, reset the selected source language.
      // Should not happen, but just in case.
      console.log(
        "No source languages available. Try to reload the page or try again later.",
      );

      setSelectorChanged(
        selectedSourceLanguage,
        null,
        setSelectedSourceLanguage,
      );
      // setLanguageDetectionMode(false);
      return;
    }

    if (lastEngine?.detectLanguage) {
      // When the last engine had language detection enabled, no need to preselect a source language

      setSelectorChanged(
        selectedSourceLanguage,
        null,
        setSelectedSourceLanguage,
      );
      return;
    }

    // No language detection, so try to preselect the last engine's source language
    const lastEngineSourceLanguage = lastEngine?.sourceLanguage?.value;
    const matchingSourceLanguage = availableSourceLanguages.data.find(
      (sourceLanguage) => sourceLanguage.value === lastEngineSourceLanguage,
    );

    setSelectorChanged(
      selectedSourceLanguage,
      matchingSourceLanguage,
      setSelectedSourceLanguage,
    );
  }, [availableSourceLanguages]);

  const loadTargetLanguages = useCallback(
    (source) => {
      dispatch(GetAvailableTargetLanguages(null, source));
    },
    [dispatch],
  );

  const onSourceLanguageChange = useCallback(
    (e) => {
      if (e?.value) {
        loadTargetLanguages(e.value);
      } else {
        dispatch(ResetAvailableTargetLanguages());
      }
    },
    [loadTargetLanguages],
  );

  // Make onSourceLanguageChange with useEffect
  useEffect(() => {
    onSourceLanguageChange(selectedSourceLanguage);
  }, [selectedSourceLanguage, onSourceLanguageChange]);

  /**
   * When to load the available domains
   */
  useEffect(() => {
    if (!selectedTargetLanguage || !selectedSourceLanguage) {
      // Only load domains if target language is selected
      dispatch(ResetAvailableDomains());
      return;
    }

    dispatch(
      GetAvailableDomains(
        selectedSourceLanguage.value,
        selectedTargetLanguage.value,
      ),
    );
  }, [selectedSourceLanguage, selectedTargetLanguage, dispatch]);

  /**
   * When to load the available providers
   */
  useEffect(() => {
    if (!selectedSourceLanguage || !selectedTargetLanguage || !selectedDomain) {
      // Only load providers if domain is selected

      dispatch(ResetAvailableProviders());
      return;
    }

    dispatch(
      GetAvailableProviders(
        selectedSourceLanguage.value,
        selectedTargetLanguage.value,
        selectedDomain.value,
      ),
    );
  }, [
    selectedDomain,
    selectedSourceLanguage,
    selectedTargetLanguage,
    dispatch,
  ]);

  /**
   * Triggers when to set target language
   */
  React.useEffect(() => {
    if (availableTargetLanguages.loading) {
      // Don't change the selected target language when loading
      return;
    }

    if (!availableTargetLanguages?.data?.length) {
      setSelectorChanged(
        selectedTargetLanguage,
        null,
        setSelectedTargetLanguage,
      );
      return;
    }

    /**
     * Convert a language code to without locale information
     */
    const lang_no_locale = (lang) => {
      return lang ? lang.split("-")[0] : "";
    };

    const findAndSetTargetLanguage = (suggestedTargetLanguage) => {
      // Check for exact match first
      const exactMatch = availableTargetLanguages.data.find(
        (targetLanguage) => targetLanguage.value === suggestedTargetLanguage,
      );

      if (exactMatch) {
        setSelectorChanged(
          selectedTargetLanguage,
          exactMatch,
          setSelectedTargetLanguage,
        );
        return;
      }

      // If no exact match is found, check for close match without locale
      const suggestedLanguageWithoutLocale = lang_no_locale(
        suggestedTargetLanguage,
      );
      const matchingTargetLanguage = availableTargetLanguages.data.find(
        (targetLanguage) => {
          // Split on "-" a close match without locale
          const targetLanguageValueWithoutLocale = lang_no_locale(
            targetLanguage.value,
          );
          return (
            targetLanguageValueWithoutLocale === suggestedLanguageWithoutLocale
          );
        },
      );

      setSelectorChanged(
        selectedTargetLanguage,
        matchingTargetLanguage || null,
        setSelectedTargetLanguage,
      );
    };

    // Try to preselect the last engine's target language
    const lastEngineTargetLanguage = lastEngine?.targetLanguage?.value;
    if (!lastEngineTargetLanguage) {
      // No last engine's target language
      setSelectorChanged(
        selectedTargetLanguage,
        null,
        setSelectedTargetLanguage,
      );
      return;
    }

    // Get the selected source language
    const selectedSourceLanguageValue = selectedSourceLanguage?.value;

    // If the current source language is the same as the last engine's target language,
    // then preselect the last engine's source language as the target language
    if (
      lastEngineTargetLanguage === selectedSourceLanguageValue ||
      lang_no_locale(lastEngineTargetLanguage) ===
        lang_no_locale(selectedSourceLanguageValue)
    ) {
      const lastEngineSourceLanguage = lastEngine?.sourceLanguage?.value;
      findAndSetTargetLanguage(lastEngineSourceLanguage);
    } else {
      // Otherwise, if the current source language is not the same as the last engine's target language,
      // preselect the last engine's target language as the target language
      findAndSetTargetLanguage(lastEngineTargetLanguage);
    }
  }, [availableTargetLanguages]);

  /**
   * Triggers when to set domain
   */
  React.useEffect(() => {
    if (availableDomains.loading) {
      // Don't change the selected domain when loading
      return;
    }

    // When no domains are available, reset the selected domain
    if (!availableDomains?.data?.length) {
      setSelectorChanged(selectedDomain, null, setSelectedDomain);
      return;
    }

    // Try to preselect the last engine's domain
    const lastEngineDomain = lastEngine?.domain?.value;
    const matchingDomain = availableDomains.data.find(
      (domain) => domain.value === lastEngineDomain,
    );
    if (matchingDomain) {
      setSelectorChanged(selectedDomain, matchingDomain, setSelectedDomain);
      return;
    }

    // Preselect the first available domain
    setSelectorChanged(
      selectedDomain,
      availableDomains.data[0],
      setSelectedDomain,
    );
  }, [availableDomains]);

  /**
   * Triggers when to set provider
   */
  React.useEffect(() => {
    if (availableProviders.loading) {
      // Don't change the selected provider when loading
      return;
    }

    // When no providers are available, reset the selected provider
    if (!availableProviders.data.length) {
      setSelectorChanged(selectedProvider, null, setSelectedProvider);
      return;
    }

    // Try to preselect the last engine's provider
    const lastEngineProvider = lastEngine?.provider?.value;
    const matchingProvider = availableProviders.data.find(
      (provider) => provider.value === lastEngineProvider,
    );
    if (matchingProvider) {
      setSelectorChanged(
        selectedProvider,
        matchingProvider,
        setSelectedProvider,
      );
      return;
    }

    // Preselect the first available provider
    setSelectorChanged(
      selectedProvider,
      availableProviders.data[0],
      setSelectedProvider,
    );
  }, [availableProviders]);

  /**
   * When all selections are made, we can save the last engine used/selected
   * @returns {{responseType: string}}
   * TODO
   *  - When selecting another source language, it still fires the useEffect while it should first reset the selectedTargetLanguage etc. Aka it should not fire the useEffect
   */
  React.useEffect(() => {
    if (
      !selectedSourceLanguage ||
      !selectedTargetLanguage ||
      !selectedProvider ||
      !selectedDomain
    ) {
      return;
    }

    dispatch(
      setLastEngine(
        selectedSourceLanguage,
        selectedTargetLanguage,
        selectedProvider,
        selectedDomain,
        languageDetectionMode,
      ),
    );
  }, [
    // Only trigger when all selections are made..
    // i.e. when provider is selected, we also have a source language, target language and domain
    selectedProvider,
    dispatch,
  ]);

  return (
    <div className="grid translate-ui-grid">
      <div className="grid col-12 md:col-12 lg:col-6">
        <div className="col-12 md:col-6 lg:col-6">
          <label className="text-900 font-medium text-sm">Source</label>
          <LanguageSelector
            availableSourceLanguages={availableSourceLanguages}
            selectedSourceLanguage={selectedSourceLanguage}
            setSelectedSourceLanguage={setSelectedSourceLanguage}
            detectionMode={languageDetectionMode}
            setDetectionMode={setLanguageDetectionMode}
            enabled={
              enable_language_detection == null
                ? true // Default to true if not set
                : enable_language_detection
            }
            placeholder="Select source language..."
            className="z-5"
          />
        </div>
        <div className="col-12 md:col-6 lg:col-6">
          <label className="text-900 font-medium text-sm">Target</label>
          <Select
            options={availableTargetLanguages.data}
            value={selectedTargetLanguage}
            placeholder="Select target language..."
            onChange={setSelectedTargetLanguage}
            isDisabled={!selectedSourceLanguage}
            theme={(theme) => ({
              ...theme,
              colors: {
                ...theme.colors,
                ...customSelectColors,
              },
            })}
            className="z-4"
            isLoading={availableTargetLanguages.loading}
          />
        </div>
      </div>
      <div className="grid col-12 md:col-12 lg:col-6">
        <div className="col-12 md:col-6 lg:col-6">
          <label className="text-900 font-medium text-sm">Domain</label>
          <Select
            value={selectedDomain}
            options={availableDomains.data}
            onChange={setSelectedDomain}
            placeholder="Select domain..."
            isDisabled={!selectedTargetLanguage}
            theme={(theme) => ({
              ...theme,
              colors: {
                ...theme.colors,
                ...customSelectColors,
              },
            })}
            className="z-3"
            isLoading={availableDomains.loading}
          />
        </div>
        <div className="col-12 md:col-6 lg:col-6">
          <label className="text-900 font-medium text-sm">Provider</label>
          <Select
            value={selectedProvider}
            options={availableProviders.data}
            onChange={setSelectedProvider}
            placeholder="Select provider..."
            isDisabled={!selectedDomain}
            theme={(theme) => ({
              ...theme,
              colors: {
                ...theme.colors,
                ...customSelectColors,
              },
            })}
            className="z-2"
          />
        </div>
      </div>
    </div>
  );
};

export default React.memo(TranslateEngineSelection);

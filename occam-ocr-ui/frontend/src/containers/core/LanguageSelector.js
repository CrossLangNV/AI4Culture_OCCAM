import React from "react";
import { useTranslation } from "react-i18next";
import { Dropdown } from "primereact/dropdown";
import { useDispatch, useSelector } from "react-redux";
import { ModifyLanguage } from "../../actions/uiActions";
import { TabMenu } from "primereact/tabmenu";

const LanguageSelector = ({ inline }) => {
  const { i18n } = useTranslation();
  const dispatch = useDispatch();
  const { t } = useTranslation();

  const uiStates = useSelector((state) => state.uiStates);

  const languagesForTabmenu = [
    { label: t("language.en"), value: "en" },
    { label: t("language.nl"), value: "nl" },
    { label: t("language.fr"), value: "fr" },
  ];

  const languagesForDropdown = [
    { name: t("language.en"), value: "en" },
    { name: t("language.nl"), value: "nl" },
    { name: t("language.fr"), value: "fr" },
  ];

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng).then((r) => {
      dispatch(ModifyLanguage(lng));
    });
  };

  return (
    <div>
      {inline ? (
        <TabMenu
          activeIndex={languagesForTabmenu.findIndex(
            (p) => p.value === uiStates.language
          )}
          model={languagesForTabmenu}
          onTabChange={(e) => {
            changeLanguage(e.value.value);
          }}
          optionLabel="name"
          placeholder={t("settings.select-language")}
        />
      ) : (
        <Dropdown
          value={uiStates.language}
          options={languagesForDropdown}
          onChange={(e) => {
            changeLanguage(e.value);
          }}
          optionLabel="name"
          placeholder={t("settings.select-language")}
        />
      )}
    </div>
  );
};

export default LanguageSelector;

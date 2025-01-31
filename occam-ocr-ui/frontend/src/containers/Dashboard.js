import React, { useRef, useState } from "react";
import { Chart } from "primereact/chart";
import "chartjs-adapter-date-fns";
import { Calendar } from "primereact/calendar";
import api from "../interceptors/api";
import { ProgressSpinner } from "primereact/progressspinner";

const Dashboard = () => {
  const calendarRef = useRef(null);

  const defaultStartDate = () => {
    let currentDate = new Date();
    // set last months based on date now
    let diffMonth = currentDate.getMonth() - 3;
    let startYear =
      diffMonth < 0 ? currentDate.getFullYear() - 1 : currentDate.getFullYear();
    let startMonth = ((diffMonth % 12) + 12) % 12;
    return new Date(startYear, startMonth, 1);
  };

  const [range, setRange] = useState([defaultStartDate(), new Date()]);

  const [languagePairData, setLanguagePairData] = useState(null);
  const [languagePairOptions, setLanguagePairOptions] = useState(null);
  const [languagePairDataLoading, setLanguagePairDataLoading] = useState(false);

  const [providerData, setProviderData] = useState(null);
  const [providerOptions, setProviderOptions] = useState(null);
  const [providerDataLoading, setProviderDataLoading] = useState(false);

  const [translationVolumeData, setTranslationVolumeData] = useState(null);
  const [translationVolumeOptions, setTranslationVolumeOptions] =
    useState(null);
  const [translationVolumeDataLoading, setTranslationVolumeDataLoading] =
    useState(false);

  React.useEffect(() => {
    if (range[0] && range[1]) {
      fetchLanguagePairData(range[0], range[1]);
      fetchProviderData(range[0], range[1]);
      fetchTranslationVolumeData(range[0], range[1]);
      loadVolumeChartOptions(range[0], range[1]);
      loadPieOptions();
    }
  }, [range]);

  const fetchTranslationVolumeData = async (beginDate, endDate) => {
    setTranslationVolumeDataLoading(true);
    if (!beginDate || !endDate) {
      return null;
    }
    beginDate = beginDate.toISOString();
    endDate = endDate.toISOString();
    let apiResponse = await api.get(
      `/catalogue/api/usage/volume?beginDate=${beginDate}&endDate=${endDate}`
    );
    let responseData = apiResponse.data;
    const data = {
      datasets: [
        {
          type: "line",
          label: "Words translated",
          backgroundColor: "#f99ba4",
          data: responseData,
          pointStyle: "circle",
          pointRadius: 10,
          pointHoverRadius: 15,
        },
      ],
    };
    setTranslationVolumeData(data);
    setTranslationVolumeDataLoading(false);
    return data;
  };

  const loadVolumeChartOptions = (beginDate, endDate) => {
    let options = {
      maintainAspectRatio: false,
      aspectRatio: 0.6,
      plugins: {
        legend: {
          labels: {
            color: "#495057",
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: {
            unit: "month",
          },
          min: beginDate,
          max: endDate,
          offset: true,
          ticks: {
            color: "#495057",
          },
          grid: {
            color: "#ebedef",
          },
        },
        y: {
          ticks: {
            color: "#495057",
            precision: 0,
          },
          grid: {
            color: "#ebedef",
          },
        },
      },
    };
    setTranslationVolumeOptions(options);
  };

  const loadPieOptions = () => {
    let options = {
      maintainAspectRatio: false,
      aspectRatio: 0.6,
      plugins: {
        legend: {
          labels: {
            color: "#495057",
          },
        },
      },
    };
    setLanguagePairOptions(options);
    setProviderOptions(options);
  };

  const fetchLanguagePairData = async (beginDate, endDate) => {
    setLanguagePairDataLoading(true);
    if (!beginDate || !endDate) {
      return null;
    }
    beginDate = beginDate.toISOString();
    endDate = endDate.toISOString();
    let apiResponse = await api.get(
      `/catalogue/api/usage/lp?beginDate=${beginDate}&endDate=${endDate}`
    );
    let labels = Object.keys(apiResponse.data);
    let responseData = Object.values(apiResponse.data);
    const data = {
      labels: labels,
      datasets: [
        {
          data: responseData,
          backgroundColor: [
            "#FFF1C9",
            "#F7B7A3",
            "#EA5F89",
            "#9B3192",
            "#57167E",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
          ],
          hoverBackgroundColor: [
            "#FFF1C9",
            "#F7B7A3",
            "#EA5F89",
            "#9B3192",
            "#57167E",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
          ],
        },
      ],
    };
    setLanguagePairData(data);
    setLanguagePairDataLoading(false);
    return data;
  };

  const fetchProviderData = async (beginDate, endDate) => {
    setProviderDataLoading(true);
    beginDate = beginDate.toISOString();
    endDate = endDate.toISOString();
    let apiResponse = await api.get(
      `/catalogue/api/usage/providers?beginDate=${beginDate}&endDate=${endDate}`
    );
    let labels = Object.keys(apiResponse.data);
    let responseData = Object.values(apiResponse.data);
    const data = {
      labels: labels,
      datasets: [
        {
          data: responseData,
          backgroundColor: [
            "#FFF1C9",
            "#F7B7A3",
            "#EA5F89",
            "#9B3192",
            "#57167E",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
          ],
          hoverBackgroundColor: [
            "#FFF1C9",
            "#F7B7A3",
            "#EA5F89",
            "#9B3192",
            "#57167E",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
            "#2B0B3F",
          ],
        },
      ],
    };
    setProviderData(data);
    setProviderDataLoading(false);
    return data;
  };

  return (
    <div>
      <div className="grid">
        <div className="col-5">
          View data from{" "}
          <Calendar
            ref={calendarRef}
            id="range"
            value={range}
            onChange={(e) => {
              setRange(e.value);
              if (e.value[1]) {
                // set end date to the end of the day
                e.value[1].setHours(23, 59, 59, 999);
                setRange(e.value);
                fetchLanguagePairData(e.value[0], e.value[1]);
                fetchProviderData(e.value[0], e.value[1]);
                fetchTranslationVolumeData(e.value[0], e.value[1]);
                loadVolumeChartOptions(e.value[0], e.value[1]);
                calendarRef.current.hide();
              }
            }}
            selectionMode="range"
            dateFormat={"d/m/y"}
            readOnlyInput
          />
        </div>
      </div>

      <div className="grid">
        <div className="col-12">
          <div className="surface-card p-4 shadow-2 border-round dashboard-stat-item">
            <div className="mb-3 flex flex-column md:flex-row md:align-items-center md:justify-content-between">
              <div className="flex align-items-start">
                <i className="pi pi-comments mr-3 text-5xl" />

                <div>
                  <div className="text-xl font-medium text-900 mb-2">
                    Translation volume
                  </div>
                  <div className="font-medium text-500 mb-3 text-sm">
                    Words translated (
                    {range[0] ? range[0].toLocaleDateString("en-GB") : "N/A"}{" "}
                    to&nbsp;
                    {range[1] ? range[1].toLocaleDateString("en-GB") : "N/A"}),
                    grouped per month
                  </div>
                </div>
              </div>
            </div>

            {translationVolumeDataLoading ? (
              <div className="flex align-items-center justify-content-center dashboard-spinner-box">
                <ProgressSpinner />
              </div>
            ) : (
              <Chart
                id="translationVolumeChart"
                type="line"
                data={translationVolumeData}
                options={translationVolumeOptions}
              />
            )}
          </div>
        </div>
      </div>

      <div className="grid">
        <div className="col-6">
          <div className="surface-card p-4 shadow-2 border-round dashboard-stat-item">
            <div className="mb-3 flex flex-column md:flex-row md:align-items-center md:justify-content-between">
              <div className="flex align-items-start">
                <i className="pi pi-sliders-h mr-3 text-5xl" />

                <div>
                  <div className="text-xl font-medium text-900 mb-2">
                    Languages
                  </div>
                  <div className="font-medium text-500 mb-3 text-sm">
                    Most popular language pairs (
                    {range[0] ? range[0].toLocaleDateString("en-GB") : "N/A"}{" "}
                    to&nbsp;
                    {range[1] ? range[1].toLocaleDateString("en-GB") : "N/A"})
                  </div>
                </div>
              </div>
            </div>

            {languagePairDataLoading ? (
              <div className="flex align-items-center justify-content-center dashboard-spinner-box">
                <ProgressSpinner />
              </div>
            ) : (
              <Chart
                id="languagePairChart"
                type="pie"
                data={languagePairData}
                options={languagePairOptions}
                style={{ position: "relative", width: "70%" }}
              />
            )}
          </div>
        </div>
        <div className="col-6">
          <div className="surface-card p-4 shadow-2 border-round dashboard-stat-item">
            <div className="mb-3 flex flex-column md:flex-row md:align-items-center md:justify-content-between">
              <div className="flex align-items-start">
                <i className="pi pi-check-circle mr-3 text-5xl" />

                <div>
                  <div className="text-xl font-medium text-900 mb-2">
                    Providers
                  </div>
                  <div className="font-medium text-500 mb-3 text-sm">
                    Provider distribution (
                    {range[0] ? range[0].toLocaleDateString("en-GB") : "N/A"}{" "}
                    to&nbsp;
                    {range[1] ? range[1].toLocaleDateString("en-GB") : "N/A"})
                  </div>
                </div>
              </div>
            </div>

            {providerDataLoading ? (
              <div className="flex align-items-center justify-content-center dashboard-spinner-box">
                <ProgressSpinner />
              </div>
            ) : (
              <Chart
                id="providerChart"
                type="pie"
                data={providerData}
                options={providerOptions}
                style={{ position: "relative", width: "70%" }}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
export default Dashboard;

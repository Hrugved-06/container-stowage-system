import { useEffect, useMemo, useState } from "react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";

import "./App.css";


const API = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");


const ALGORITHMS = [
  ["priority_greedy", "Priority Greedy"],
  ["genetic", "Genetic Algorithm"],
  ["cp_sat", "CP-SAT"],
];


const CONTAINER_FIELDS = [
  "container_id",
  "size",
  "weight",
  "destination",
  "destination_order",
  "priority",
  "hazardous",
  "refrigerated",
];


const SLOT_FIELDS = [
  "slot_id",
  "bay",
  "row",
  "tier",
  "size",
  "max_weight",
  "reefer_capable",
  "hazardous_allowed",
];


function getErrorMessage(detail) {

  if (!detail) {
    return "An unexpected error occurred.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (detail.message) {
    return detail.message;
  }

  if (detail.errors) {
    return detail.errors.join("\n");
  }

  if (detail.missing_container_columns) {
    return (
      "Missing container columns:\n" +
      detail.missing_container_columns.join(", ")
    );
  }

  if (detail.missing_slot_columns) {
    return (
      "Missing slot columns:\n" +
      detail.missing_slot_columns.join(", ")
    );
  }

  return JSON.stringify(detail, null, 2);
}


function formatAlgorithmName(name) {

  const found = ALGORITHMS.find(
    item => item[0] === name
  );

  return found ? found[1] : name;
}

function formatDatasetName(name) {
  const labels = {
    demo: "Demo",
    small: "Small",
    medium: "Medium",
    large: "Large",
    custom: "Custom",
    rcspp_small: "RCSPPSuite Small",
    rcspp_medium: "RCSPPSuite Medium",
    rcspp_large: "RCSPPSuite Large",
  };
  return labels[name] || name;
}


function App() {

  const [datasets, setDatasets] = useState([]);

  const [dataset, setDataset] = useState("demo");

  const [selectedAlgorithms, setSelectedAlgorithms] =
    useState(
      ALGORITHMS.map(item => item[0])
    );

  const [customFiles, setCustomFiles] = useState([]);

  const [uploadSummary, setUploadSummary] = useState(null);

  const [uploaded, setUploaded] =
    useState(false);

  const [loading, setLoading] =
    useState(false);

  const [results, setResults] =
    useState(null);

  const [error, setError] =
    useState("");

  const [errorTitle, setErrorTitle] =
    useState("Notice");

  const [activeAlgorithm, setActiveAlgorithm] =
    useState(null);

  const [backendOnline, setBackendOnline] =
    useState(false);


  // -------------------------------------------------------
  // LOAD DATASETS
  // -------------------------------------------------------

  const loadDatasets = async () => {

    try {

      const response = await fetch(
        `${API}/api/datasets`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          getErrorMessage(data.detail)
        );
      }

      setDatasets(data);

      setBackendOnline(true);

      const custom = data.find(
        item => item.id === "custom"
      );

      if (custom?.available) {
        setUploaded(true);
      }

    } catch (err) {

      setBackendOnline(false);

      setErrorTitle("Connection Error");
      setError(
        "Could not connect to the backend. Start FastAPI on port 8000."
      );

    }
  };


  useEffect(() => {
    loadDatasets();
  }, []);


  // -------------------------------------------------------
  // SELECTED DATASET
  // -------------------------------------------------------

  const selectedDataset =
    datasets.find(
      item => item.id === dataset
    );


  // -------------------------------------------------------
  // ALGORITHM CONTROLS
  // -------------------------------------------------------

  const toggleAlgorithm = (name) => {

    setSelectedAlgorithms(current => {

      if (current.includes(name)) {

        return current.filter(
          item => item !== name
        );

      }

      return [
        ...current,
        name
      ];

    });

  };


  const selectAll = () => {

    setSelectedAlgorithms(
      ALGORITHMS.map(item => item[0])
    );

  };


  const clearAlgorithms = () => {

    setSelectedAlgorithms([]);

  };


  // -------------------------------------------------------
  // DATASET SELECTION
  // -------------------------------------------------------

  const handleDatasetChange = (event) => {

    const value = event.target.value;

    setDataset(value);

    setResults(null);
    setActiveAlgorithm(null);
    setError("");
    setErrorTitle("Notice");

  };


  // -------------------------------------------------------
  // SMART MULTI-FILE SELECTION
  // -------------------------------------------------------

  const handleCustomFiles = (event) => {
    const files = Array.from(event.target.files || []);
    setCustomFiles(files);
    setUploaded(false);
    setUploadSummary(null);
    setError("");
    setErrorTitle("Notice");
    setResults(null);
  };


  // -------------------------------------------------------
  // CUSTOM DATASET UPLOAD
  // -------------------------------------------------------

  const uploadCustomDataset = async () => {
    setUploaded(false);
    setUploadSummary(null);
    setError("");
    setErrorTitle("Upload Error");

    if (customFiles.length < 2) {
      setError("Select at least two CSV files containing cargo/container data and vessel-slot data.");
      return;
    }

    const formData = new FormData();
    customFiles.forEach(file => formData.append("files", file));
    setLoading(true);

    try {
      const response = await fetch(`${API}/api/upload`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(getErrorMessage(data.detail));
      setUploaded(true);
      setUploadSummary(data);
      setDataset("custom");
      await loadDatasets();
    } catch (err) {
      setUploaded(false);
      setErrorTitle("Upload Error");
      setError(err.message || "The selected files could not be uploaded.");
    } finally {
      setLoading(false);
    }
  };


  // -------------------------------------------------------
  // RUN OPTIMIZATION
  // -------------------------------------------------------

  const runOptimization = async () => {

    setErrorTitle("Optimization Error");

    if (selectedAlgorithms.length === 0) {

      setError(
        "Select at least one algorithm."
      );

      return;

    }


    if (
      dataset === "custom" &&
      !uploaded
    ) {

      setError(
        "Upload the custom dataset before running optimization."
      );

      return;

    }


    setLoading(true);
    setError("");
    setResults(null);
    setActiveAlgorithm(null);


    try {

      const response = await fetch(
        `${API}/api/optimize`,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            dataset,
            algorithms: ALGORITHMS.map((item) => item[0]),
          }),

        }
      );


      const data =
        await response.json();


      if (!response.ok) {

        throw new Error(
          getErrorMessage(data.detail)
        );

      }


      setResults(data);


      const firstSuccessful =
        data.comparison?.find(
          item =>
            item.status === "SUCCESS"
        );


      if (firstSuccessful) {

        setActiveAlgorithm(
          firstSuccessful.algorithm
        );

      }


    } catch (err) {

      const message = err?.message === "Failed to fetch"
        ? "The optimization request could not reach the backend. Confirm the backend terminal is still running, then try again."
        : (err?.message || "Optimization could not be completed.");

      setErrorTitle("Optimization Error");
      setError(message);

    } finally {

      setLoading(false);

    }

  };


  const downloadExport = (path) => {
    if (!path) return;
    const encoded = path.split("/").map(encodeURIComponent).join("/");
    window.open(`${API}/api/download/${encoded}`, "_blank", "noopener,noreferrer");
  };


  // -------------------------------------------------------
  // ACTIVE SOLUTION
  // -------------------------------------------------------

  const activeSolution = useMemo(() => {

    if (
      !results ||
      !activeAlgorithm
    ) {

      return [];

    }


    return (
      results.solutions?.[
        activeAlgorithm
      ] || []
    );

  }, [
    results,
    activeAlgorithm,
  ]);


  // -------------------------------------------------------
  // SUCCESSFUL RESULTS
  // -------------------------------------------------------

  const successfulResults =
    results?.comparison?.filter(
      item =>
        item.status === "SUCCESS"
    ) || [];


  // -------------------------------------------------------
  // DYNAMIC RESEARCH SUMMARY
  // -------------------------------------------------------

  const researchSummary = useMemo(() => {

    if (!results) {
      return null;
    }


    const totalAlgorithms =
      results.comparison?.length || 0;


    const successful =
      successfulResults.length;


    const failed =
      totalAlgorithms - successful;


    const allFullAssignment =
      successful > 0 &&
      successfulResults.every(
        item =>
          Number(item.assignment_rate) === 100
      );


    const allConstraintFree =
      successful > 0 &&
      successfulResults.every(
        item =>
          Number(item.constraint_violations) === 0
      );


    const assignmentRates =
      successfulResults.map(
        item =>
          Number(item.assignment_rate)
      );


    const utilizationValues =
      successfulResults.map(
        item =>
          Number(item.slot_utilization)
      );


    const objectiveValues =
      successfulResults.map(
        item =>
          Number(item.objective_score)
      );


    const runtimeValues =
      successfulResults.map(
        item =>
          Number(item.runtime_seconds)
      );


    const averageAssignment =
      assignmentRates.length
        ? (
            assignmentRates.reduce(
              (a, b) => a + b,
              0
            ) / assignmentRates.length
          ).toFixed(1)
        : "0";


    const averageUtilization =
      utilizationValues.length
        ? (
            utilizationValues.reduce(
              (a, b) => a + b,
              0
            ) / utilizationValues.length
          ).toFixed(1)
        : "0";


    const minObjective =
      objectiveValues.length
        ? Math.min(...objectiveValues)
        : null;


    const maxObjective =
      objectiveValues.length
        ? Math.max(...objectiveValues)
        : null;


    const minRuntime =
      runtimeValues.length
        ? Math.min(...runtimeValues)
        : null;


    const maxRuntime =
      runtimeValues.length
        ? Math.max(...runtimeValues)
        : null;


    let summary =
      `The ${formatAlgorithmName(results.dataset)} dataset contained ` +
      `${results.container_count} containers and ` +
      `${results.slot_count} available slots. `;


    summary +=
      `${successful} of ${totalAlgorithms} selected algorithms ` +
      `completed successfully`;


    if (failed > 0) {

      summary +=
        `, while ${failed} algorithm` +
        `${failed === 1 ? "" : "s"} failed during execution`;

    }


    summary += ". ";


    if (allFullAssignment) {

      summary +=
        "All completed algorithms achieved a 100% assignment rate. ";

    } else {

      summary +=
        `The average assignment rate across completed algorithms was ` +
        `${averageAssignment}%. `;

    }


    if (allConstraintFree) {

      summary +=
        "No constraint violations were recorded in the completed solutions. ";

    } else {

      summary +=
        "Constraint-violation counts differed across the completed solutions. ";

    }


    summary +=
      `Average slot utilization was ${averageUtilization}%. `;


    if (
      minObjective !== null &&
      maxObjective !== null
    ) {

      summary +=
        `Objective scores ranged from ` +
        `${minObjective.toFixed(2)} to ` +
        `${maxObjective.toFixed(2)}. `;

    }


    if (
      minRuntime !== null &&
      maxRuntime !== null
    ) {

      summary +=
        `Observed algorithm runtimes ranged from ` +
        `${minRuntime.toFixed(3)} to ` +
        `${maxRuntime.toFixed(3)} seconds. `;

    }


    summary +=
      "These results demonstrate trade-offs between computational runtime, " +
      "stowage quality and resource utilization under the same constraint " +
      "and evaluation framework. The comparison is intended to support " +
      "multi-objective analysis rather than identify a universally superior algorithm.";


    return {
      text: summary,
      successful,
      failed,
      averageAssignment,
      averageUtilization,
    };


  }, [
    results,
    successfulResults,
  ]);


  return (

    <div className="app">


      {/* ================================================= */}
      {/* HEADER */}
      {/* ================================================= */}

      <header className="topbar">

        <div className="hero-content">

          <div className="eyebrow">
            AI-ASSISTED
          </div>

          <h1>
            CONTAINER STOWAGE PLANNER
          </h1>

          <p>
            Multi-Objective Optimization Framework
            for Constraint-Aware Container Stowage Planning
          </p>

        </div>


        <div
          className={
            backendOnline
              ? "status-pill online"
              : "status-pill offline"
          }
        >

          <span className="status-dot"></span>

          {backendOnline
            ? "System Ready"
            : "Backend Offline"}

        </div>

      </header>


      <main className="container">


        {/* ================================================= */}
        {/* ERROR */}
        {/* ================================================= */}

        {error && (
          <div className="error-box">
            <div className="error-title">{errorTitle}</div>
            <div className="error-message">{error}</div>
          </div>
        )}


        {/* ================================================= */}
        {/* CONFIGURATION */}
        {/* ================================================= */}

        <section className="grid two">


          {/* ------------------------------------------------ */}
          {/* DATASET CARD */}
          {/* ------------------------------------------------ */}

          <div className="card">

            <div className="section-title">

              <span>01</span>

              Select Dataset

            </div>


            <p className="section-description">
              Choose a prepared benchmark dataset or
              upload your own container and slot data.
            </p>


            <label>
              Benchmark Dataset
            </label>


            <select
              value={dataset}
              onChange={handleDatasetChange}
            >

              {datasets
                .filter(
                  item =>
                    item.id !== "custom"
                )
                .map(item => (

                  <option
                    key={item.id}
                    value={item.id}
                    disabled={!item.available}
                  >

                    {item.name}
                    {" — "}
                    {item.available
                      ? `${item.containers} containers / ${item.slots} slots`
                      : "Not available"}

                  </option>

                ))}


              <option value="custom">
                Custom — Upload your own data
              </option>

            </select>


            {selectedDataset &&
              dataset !== "custom" && (

              <div className="dataset-info">

                <div>

                  <strong>
                    {selectedDataset.containers}
                  </strong>

                  <span>
                    Containers
                  </span>

                </div>


                <div>

                  <strong>
                    {selectedDataset.slots}
                  </strong>

                  <span>
                    Slots
                  </span>

                </div>

                <div className="dataset-scenario">
                  <strong>{selectedDataset.description}</strong>
                  <span>{selectedDataset.route}</span>
                  {selectedDataset.benchmark && (
                    <span className="benchmark-source">
                      Public benchmark source: {selectedDataset.source}. Reduced/adapted to the constraints implemented in this prototype.
                    </span>
                  )}
                </div>

              </div>

            )}


            {/* ------------------------------------------------ */}
            {/* CUSTOM UPLOAD */}
            {/* ------------------------------------------------ */}

            <div className="custom-upload">

              <div className="upload-heading">
                <div>
                  <h3>Custom Dataset</h3>
                  <p>Select the CSV files for this stowage run.</p>
                </div>
              </div>

              <div className="smart-upload-panel compact-upload">
                <label className="file-button">
                  Select CSV Files
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    multiple
                    onChange={handleCustomFiles}
                  />
                </label>

                <div className="selected-file">
                  {customFiles.length
                    ? `${customFiles.length} file(s) selected: ${customFiles.map(f => f.name).join(", ")}`
                    : "No files selected"}
                </div>
              </div>

              <button
                className="secondary"
                onClick={uploadCustomDataset}
                disabled={loading}
              >
                {loading ? "Uploading..." : "Upload Dataset"}
              </button>

              {uploaded && dataset === "custom" && (
                <div className="success compact-success">
                  <strong>✓ Dataset ready</strong>
                  {uploadSummary && (
                    <span>
                      {uploadSummary.container_count} containers • {uploadSummary.slot_count} slots • {uploadSummary.files_processed} files
                    </span>
                  )}
                </div>
              )}

            </div>

          </div>


          {/* ------------------------------------------------ */}
          {/* ALGORITHM CARD */}
          {/* ------------------------------------------------ */}

          <div className="card">

            <div className="section-title">

              <span>02</span>

              Select Algorithms

            </div>


            <p className="section-description">
              Select one or more optimization methods to
              compare them under the same dataset and
              constraint framework.
            </p>


            <div className="algorithm-actions">

              <button
                className="text-button"
                onClick={selectAll}
              >
                Select All
              </button>


              <button
                className="text-button clear-button"
                onClick={clearAlgorithms}
              >
                Clear
              </button>

            </div>


            <div className="algorithm-list">

              <div className="auto-optimization-info">
  <strong>Automatic Optimization Engine</strong>

  <p>
    The system automatically evaluates multiple optimization
    strategies and selects the best feasible stowage plan.
  </p>

  <div className="optimization-methods">
    <span>Priority-Based Optimization</span>
    <span>Genetic Search</span>
    <span>Constraint Optimization</span>
  </div>
</div>

            </div>


            <div className="algorithm-note">
  <strong>
    Automatic Plan Selection
  </strong>

  <p>
    The optimization engine automatically evaluates the internal
    strategies under the same constraints and selects one best
    feasible stowage plan for the user.
  </p>
</div>

            </div>


            <button
  className="run-button"
  onClick={runOptimization}
  disabled={loading}
>
  {loading
    ? "Running Optimization..."
    : "Generate Best Optimized Stowage Plan"}
</button>


        </section>


        {/* ================================================= */}
        {/* LOADING */}
        {/* ================================================= */}

        {loading && (

          <section className="card loading-card">

            <div className="loader"></div>

            <h2>
              Optimization in Progress
            </h2>

            <p>
              Heuristic methods normally complete quickly,
              while metaheuristic methods may require
              significantly more computation.
            </p>

          </section>

        )}


        {/* ================================================= */}
        {/* RESULTS */}
        {/* ================================================= */}

        {results && (

          <>

            {/* ------------------------------------------------ */}
            {/* SUMMARY METRICS */}
            {/* ------------------------------------------------ */}

            <section className="summary-grid">

              <div className="metric-card">

                <span>
                  Dataset
                </span>

                <strong>
                  {formatDatasetName(
                    results.dataset
                  )}
                </strong>

              </div>


              <div className="metric-card">

                <span>
                  Containers
                </span>

                <strong>
                  {results.container_count}
                </strong>

              </div>


              <div className="metric-card">

                <span>
                  Slots
                </span>

                <strong>
                  {results.slot_count}
                </strong>

              </div>


              <div className="metric-card">

                <span>
                  Total Runtime
                </span>

                <strong>
                  {Number(
                    results.total_runtime_seconds
                  ).toFixed(2)}s
                </strong>

              </div>

            </section>


            <section className="card result-action-card">
              <div className="recommended-summary">
                <div>
                  <span className="mini-label">Recommended Plan</span>
                  <strong>
                    {results.recommended_algorithm
                      ? formatAlgorithmName(results.recommended_algorithm)
                      : "No successful plan"}
                  </strong>
                  <small>
                    {results.container_count} containers competing for {results.slot_count} slots
                  </small>
                  {results.scenario?.benchmark && (
                    <small>
                      Source: {results.scenario.source} • adapted benchmark mode
                    </small>
                  )}
                </div>

                <div className="export-actions">
                  {[
                    ["csv", "CSV"],
                    ["xlsx", "Excel"],
                    ["docx", "Word"],
                    ["pdf", "PDF"],
                    ["json", "JSON"],
                    ["zip", "All Files"],
                  ].map(([key, label]) => (
                    results.export_files?.[key] && (
                      <button
                        key={key}
                        className="export-button"
                        onClick={() => downloadExport(results.export_files[key])}
                      >
                        {label}
                      </button>
                    )
                  ))}
                </div>
              </div>
            </section>


            {/* ------------------------------------------------ */}
            {/* ALGORITHM COMPARISON */}
            {/* ------------------------------------------------ */}

            <section className="card">

              <div className="section-title">

                <span>03</span>

                Best Optimized Stowage Plan

              </div>


              <div className="table-wrapper">

                <table>

                  <thead>

                    <tr>

                      <th>Algorithm</th>
                      <th>Runtime</th>
                      <th>Assignment</th>
                      <th>Utilization</th>
                      <th>Violations</th>
                      <th>Imbalance</th>
                      <th>Objective</th>

                    </tr>

                  </thead>


                  <tbody>

                    {results.comparison
  .filter(
    row =>
      row.algorithm ===
      results.recommended_algorithm
  )
  .map(
    row => (

                        <tr
                          key={row.algorithm}
                          onClick={() =>
                            row.status === "SUCCESS" &&
                            setActiveAlgorithm(
                              row.algorithm
                            )
                          }
                          className={
                            activeAlgorithm ===
                            row.algorithm
                              ? "active-row"
                              : ""
                          }
                        >

                          <td>
                            <strong>
                              {formatAlgorithmName(
                                row.algorithm
                              )}
                            </strong>
                          </td>

                          <td>
                            {Number(
                              row.runtime_seconds
                            ).toFixed(3)}s
                          </td>

                          <td>
                            {row.status === "SUCCESS"
                              ? `${row.assignment_rate}%`
                              : "—"}
                          </td>

                          <td>
                            {row.status === "SUCCESS"
                              ? `${row.slot_utilization}%`
                              : "—"}
                          </td>

                          <td>
                            {row.status === "SUCCESS"
                              ? row.constraint_violations
                              : "—"}
                          </td>

                          <td>
                            {row.status === "SUCCESS"
                              ? Number(
                                  row.weight_imbalance_std
                                ).toFixed(2)
                              : "—"}
                          </td>

                          <td>
                            {row.status === "SUCCESS"
                              ? Number(
                                  row.objective_score
                                ).toFixed(2)
                              : "Failed"}
                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            </section>


            {/* ------------------------------------------------ */}
            {/* CHARTS */}
            {/* ------------------------------------------------ */}

            {successfulResults.length > 0 && (

              <section className="grid two">


                <div className="card chart-card">

                  <div className="section-title">

                    <span>04</span>

                    Runtime Comparison

                  </div>


                  <ResponsiveContainer
                    width="100%"
                    height={320}
                  >

                    <BarChart
                      data={
                        successfulResults
                      }
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                      />

                      <XAxis
                        dataKey="algorithm"
                        angle={-20}
                        textAnchor="end"
                        height={80}
                      />

                      <YAxis />

                      <Tooltip />

                      <Bar
                        dataKey="runtime_seconds"
                        name="Runtime (seconds)"
                      />

                    </BarChart>

                  </ResponsiveContainer>

                </div>


                <div className="card chart-card">

                  <div className="section-title">

                    <span>05</span>

                    Objective Comparison

                  </div>


                  <ResponsiveContainer
                    width="100%"
                    height={320}
                  >

                    <LineChart
                      data={
                        successfulResults
                      }
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                      />

                      <XAxis
                        dataKey="algorithm"
                        angle={-20}
                        textAnchor="end"
                        height={80}
                      />

                      <YAxis />

                      <Tooltip />

                      <Line
                        type="monotone"
                        dataKey="objective_score"
                        name="Objective Score"
                      />

                    </LineChart>

                  </ResponsiveContainer>

                </div>

              </section>

            )}


            {/* ------------------------------------------------ */}
            {/* STOWAGE PLAN */}
            {/* ------------------------------------------------ */}

            <section className="card">

              <div className="section-title">

                <span>06</span>

                Stowage Assignment

              </div>


              <div className="solution-selector">

                {successfulResults.map(
                  row => (

                    <button
                      key={
                        row.algorithm
                      }
                      className={
                        activeAlgorithm ===
                        row.algorithm
                          ? "selected"
                          : ""
                      }
                      onClick={() =>
                        setActiveAlgorithm(
                          row.algorithm
                        )
                      }
                    >

                      {formatAlgorithmName(
                        row.algorithm
                      )}

                    </button>

                  )
                )}

              </div>


              <div className="table-wrapper">

                <table>

                  <thead>

                    <tr>

                      <th>Container</th>
                      <th>Slot</th>
                      <th>Bay</th>
                      <th>Row</th>
                      <th>Tier</th>
                      <th>Weight</th>
                      <th>Destination</th>
                      <th>Priority</th>

                    </tr>

                  </thead>


                  <tbody>

                    {activeSolution.map(
                      (item, index) => (

                        <tr
                          key={
                            `${item.container_id}-${index}`
                          }
                        >

                          <td>
                            {item.container_id}
                          </td>

                          <td>
                            {item.slot_id}
                          </td>

                          <td>
                            {item.bay}
                          </td>

                          <td>
                            {item.row}
                          </td>

                          <td>
                            {item.tier}
                          </td>

                          <td>
                            {item.container_weight}
                          </td>

                          <td>
                            {item.destination}
                          </td>

                          <td>
                            {item.priority}
                          </td>

                        </tr>

                      )
                    )}

                  </tbody>

                </table>

              </div>

            </section>


            {/* ------------------------------------------------ */}
            {/* RESEARCH SUMMARY */}
            {/* ------------------------------------------------ */}

            {researchSummary && (

              <section className="card research-card">

                <div className="section-title">

                  <span>07</span>

                  Research Summary

                </div>


                <p className="research-summary-text">
                  {researchSummary.text}
                </p>


                <div className="research-points">

                  <div>

                    <strong>
                      {researchSummary.successful}
                    </strong>

                    <span>
                      Algorithms completed
                    </span>

                  </div>


                  <div>

                    <strong>
                      {researchSummary.averageAssignment}%
                    </strong>

                    <span>
                      Average assignment
                    </span>

                  </div>


                  <div>

                    <strong>
                      {researchSummary.averageUtilization}%
                    </strong>

                    <span>
                      Average slot utilization
                    </span>

                  </div>


                  <div>

                    <strong>
                      {researchSummary.failed}
                    </strong>

                    <span>
                      Algorithms failed
                    </span>

                  </div>

                </div>

              </section>

            )}

          </>

        )}

      </main>


      {/* ================================================= */}
      {/* FOOTER */}
      {/* ================================================= */}

      <footer>

        AI-Assisted Multi-Objective Optimization
        Framework for Container Stowage Planning

      </footer>

    </div>

  );

}


export default App;
import { useEffect, useMemo, useState } from "react";

const API = (
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000"
).replace(/\/$/, "");

const CORE_ALGORITHMS = [
  "priority_greedy",
  "genetic",
  "cp_sat",
];

const ALGORITHM_NAMES = {
  priority_greedy: "Priority Greedy",
  genetic: "Genetic Algorithm",
  cp_sat: "CP-SAT",
};

/* =========================================================
   HELPERS
========================================================= */

function algorithmName(value) {
  return ALGORITHM_NAMES[value] || value || "N/A";
}

function numberValue(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatNumber(value, digits = 2) {
  const n = Number(value);

  return Number.isFinite(n)
    ? n.toFixed(digits)
    : "N/A";
}

function formatPercent(value) {
  const n = Number(value);

  return Number.isFinite(n)
    ? `${n.toFixed(2)}%`
    : "N/A";
}

function isTrue(value) {
  if (typeof value === "boolean") {
    return value;
  }

  return ["true", "1", "yes", "y"].includes(
    String(value ?? "")
      .trim()
      .toLowerCase()
  );
}

function isAssigned(container) {
  if (!container) {
    return false;
  }

  if (typeof container.assigned === "boolean") {
    return container.assigned;
  }

  const slot =
    container.slot_id ??
    container.slotId;

  return Boolean(
    slot &&
      String(slot).toLowerCase() !== "none" &&
      String(slot).toLowerCase() !== "n/a"
  );
}

function normalizeContainer(raw = {}) {
  return {
    ...raw,

    container_id:
      raw.container_id ??
      raw.containerId ??
      raw.id ??
      "N/A",

    slot_id:
      raw.slot_id ??
      raw.slotId ??
      null,

    container_size:
      raw.container_size ??
      raw.size ??
      raw.containerSize ??
      "N/A",

    container_weight:
      raw.container_weight ??
      raw.weight ??
      raw.containerWeight ??
      "N/A",

    destination:
      raw.destination ??
      "N/A",

    destination_order:
      raw.destination_order ??
      raw.destinationOrder ??
      "N/A",

    priority:
      raw.priority ??
      "N/A",

    priority_score:
      raw.priority_score ??
      raw.priorityScore ??
      null,

    priority_level:
      raw.priority_level ??
      raw.priorityLevel ??
      null,

    priority_reason:
      raw.priority_reason ??
      raw.priorityReason ??
      "",

    hazardous:
      raw.hazardous ?? false,

    refrigerated:
      raw.refrigerated ?? false,

    bay:
      raw.bay ?? null,

    row:
      raw.row ?? null,

    tier:
      raw.tier ?? null,

    assigned:
      typeof raw.assigned === "boolean"
        ? raw.assigned
        : undefined,
  };
}

/* =========================================================
   PRIORITY EXPLANATION
========================================================= */

function getPriorityReasons(container) {
  if (!container) {
    return [];
  }

  if (
    container.priority_reason &&
    String(container.priority_reason).trim() !== "" &&
    String(
      container.priority_reason
    ).toLowerCase() !== "n/a"
  ) {
    return String(container.priority_reason)
      .split(";")
      .map((reason) => reason.trim())
      .filter(Boolean);
  }

  const reasons = [];

  if (
    container.priority !== undefined &&
    container.priority !== null &&
    container.priority !== "N/A"
  ) {
    reasons.push(
      `Input business priority: ${container.priority}`
    );
  }

  if (
    container.destination_order !== undefined &&
    container.destination_order !== null &&
    container.destination_order !== "N/A"
  ) {
    reasons.push(
      `Destination sequence order: ${container.destination_order}`
    );
  }

  if (isTrue(container.hazardous)) {
    reasons.push(
      "Hazardous cargo requires safety-compatible placement"
    );
  }

  if (isTrue(container.refrigerated)) {
    reasons.push(
      "Refrigerated cargo requires a reefer-compatible slot"
    );
  }

  if (reasons.length === 0) {
    reasons.push(
      "Normal operational priority based on available container attributes"
    );
  }

  return reasons;
}

/* =========================================================
   PLACEMENT EXPLANATION
========================================================= */

function getPlacementReasons(container) {
  if (!container) {
    return [];
  }

  if (!isAssigned(container)) {
    return [
      "No feasible vessel slot was assigned to this container.",
      "This can occur because of vessel capacity or implemented compatibility constraints.",
      "The optimizer leaves the container unassigned instead of creating an invalid placement.",
    ];
  }

  const reasons = [
    `Assigned to slot ${container.slot_id} at Bay ${container.bay}, Row ${container.row}, Tier ${container.tier}.`,
    "Container-to-slot feasibility checks were satisfied.",
    "This placement is part of the automatically selected optimized plan.",
  ];

  if (
    container.container_size !== "N/A"
  ) {
    reasons.push(
      `Container size ${container.container_size} is compatible with the selected slot.`
    );
  }

  if (
    container.container_weight !== "N/A"
  ) {
    reasons.push(
      `Container weight ${container.container_weight} satisfies the implemented slot weight rule.`
    );
  }

  if (isTrue(container.hazardous)) {
    reasons.push(
      "Hazardous-cargo slot eligibility was considered."
    );
  }

  if (isTrue(container.refrigerated)) {
    reasons.push(
      "Reefer compatibility was considered for this refrigerated container."
    );
  }

  return reasons;
}

/* =========================================================
   PRIORITY COLOR
========================================================= */

function getPriorityStyle(level) {
  const value = String(
    level || ""
  ).toLowerCase();

  if (value === "critical") {
    return {
      backgroundColor: "#fee2e2",
      color: "#991b1b",
      border: "1px solid #fecaca",
    };
  }

  if (value === "high") {
    return {
      backgroundColor: "#ffedd5",
      color: "#9a3412",
      border: "1px solid #fed7aa",
    };
  }

  if (value === "medium") {
    return {
      backgroundColor: "#fef9c3",
      color: "#854d0e",
      border: "1px solid #fde68a",
    };
  }

  return {
    backgroundColor: "#dcfce7",
    color: "#166534",
    border: "1px solid #bbf7d0",
  };
}

/* =========================================================
   FALLBACK BEST PLAN SELECTION
========================================================= */

function getFallbackAlgorithm(
  comparison = []
) {
  const successful =
    comparison.filter(
      (row) =>
        row.status === "SUCCESS"
    );

  if (!successful.length) {
    return null;
  }

  const sorted = [
    ...successful,
  ].sort((a, b) => {
    const tests = [
      [
        numberValue(
          a.constraint_violations,
          999999
        ),
        numberValue(
          b.constraint_violations,
          999999
        ),
      ],

      [
        numberValue(
          a.unassigned,
          999999
        ),
        numberValue(
          b.unassigned,
          999999
        ),
      ],

      [
        -numberValue(
          a.assignment_rate,
          0
        ),
        -numberValue(
          b.assignment_rate,
          0
        ),
      ],

      [
        numberValue(
          a.objective_score,
          Infinity
        ),
        numberValue(
          b.objective_score,
          Infinity
        ),
      ],

      [
        numberValue(
          a.weight_imbalance_std,
          Infinity
        ),
        numberValue(
          b.weight_imbalance_std,
          Infinity
        ),
      ],

      [
        numberValue(
          a.runtime_seconds,
          Infinity
        ),
        numberValue(
          b.runtime_seconds,
          Infinity
        ),
      ],
    ];

    for (const [left, right] of tests) {
      if (left < right) {
        return -1;
      }

      if (left > right) {
        return 1;
      }
    }

    return 0;
  });

  return (
    sorted[0]?.algorithm ||
    null
  );
}

function errorMessage(detail) {
  if (!detail) {
    return "Unexpected error.";
  }

  if (
    typeof detail === "string"
  ) {
    return detail;
  }

  if (detail.message) {
    return detail.message;
  }

  if (
    Array.isArray(detail.errors)
  ) {
    return detail.errors.join(
      "\n"
    );
  }

  try {
    return JSON.stringify(detail);
  } catch {
    return "Unexpected error.";
  }
}

/* =========================================================
   SMALL COMPONENTS
========================================================= */

function Metric({
  label,
  value,
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Stat({
  label,
  value,
}) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DetailBox({
  label,
  value,
}) {
  return (
    <div className="detail-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

/* =========================================================
   APP
========================================================= */
function createRunId(datasetId, date = new Date()) {
  const stamp = date
    .toISOString()
    .replace(/\D/g, "")
    .slice(0, 14);

  return `RUN-${String(
    datasetId || "DATA"
  ).toUpperCase()}-${stamp}`;
}

function sortPositionValues(a, b) {
  const numberA = Number(a);
  const numberB = Number(b);

  if (
    Number.isFinite(numberA) &&
    Number.isFinite(numberB)
  ) {
    return numberA - numberB;
  }

  return String(a).localeCompare(
    String(b),
    undefined,
    { numeric: true }
  );
}

function App() {
  const [
    datasets,
    setDatasets,
  ] = useState([]);

  const [
    dataset,
    setDataset,
  ] = useState("small");

  const [
    backendOnline,
    setBackendOnline,
  ] = useState(false);

  const [
    results,
    setResults,
  ] = useState(null);

  const [
    loading,
    setLoading,
  ] = useState(false);

  const [
    error,
    setError,
  ] = useState("");

  const [
    search,
    setSearch,
  ] = useState("");

  const [
    selectedContainer,
    setSelectedContainer,
  ] = useState(null);

  const [
  voyageResult,
  setVoyageResult,
] = useState(null);

const [
  voyageLoading,
  setVoyageLoading,
] = useState(false);

const [
  voyageError,
  setVoyageError,
] = useState("");

const [
  runInfo,
  setRunInfo,
] = useState(null);

const [
  selectedBay,
  setSelectedBay,
] = useState("");
  /* =====================================================
     LOAD DATASETS
  ===================================================== */

  useEffect(() => {
    async function load() {
      try {
        const response =
          await fetch(
            `${API}/api/datasets`
          );

        const data =
          await response.json();

        if (!response.ok) {
          throw new Error(
            errorMessage(
              data.detail
            )
          );
        }

        const list =
          Array.isArray(data)
            ? data
            : [];

        setDatasets(list);

        setBackendOnline(true);

        const small =
          list.find(
            (item) =>
              item.id ===
                "small" &&
              item.available
          );

        const first =
          list.find(
            (item) =>
              item.available
          );

        if (small) {
          setDataset(
            small.id
          );
        } else if (first) {
          setDataset(
            first.id
          );
        }
      } catch (err) {
        setBackendOnline(
          false
        );

        setError(
          "Backend connection failed. Start FastAPI on http://127.0.0.1:8000"
        );
      }
    }

    load();
  }, []);

  /* =====================================================
     RECOMMENDED ALGORITHM
  ===================================================== */

  const recommendedAlgorithm =
    useMemo(() => {
      if (!results) {
        return null;
      }

      return (
        results.recommended_algorithm ||
        getFallbackAlgorithm(
          results.comparison ||
            []
        )
      );
    }, [results]);

  /* =====================================================
     RECOMMENDED METRICS
  ===================================================== */

  const recommendedMetrics =
    useMemo(() => {
      if (
        !results ||
        !recommendedAlgorithm
      ) {
        return null;
      }

      return (
        results.comparison?.find(
          (row) =>
            row.algorithm ===
              recommendedAlgorithm &&
            row.status ===
              "SUCCESS"
        ) || null
      );
    }, [
      results,
      recommendedAlgorithm,
    ]);

  /* =====================================================
     RECOMMENDED SOLUTION
  ===================================================== */

  const plan =
    useMemo(() => {
      if (
        !results ||
        !recommendedAlgorithm
      ) {
        return [];
      }

      const raw =
        results.solutions?.[
          recommendedAlgorithm
        ] || [];

      return Array.isArray(
        raw
      )
        ? raw.map(
            normalizeContainer
          )
        : [];
    }, [
      results,
      recommendedAlgorithm,
    ]);

  /* =====================================================
     FILTER
  ===================================================== */

  const filteredPlan =
    useMemo(() => {
      const query =
        search
          .trim()
          .toLowerCase();

      if (!query) {
        return plan;
      }

      return plan.filter(
        (container) => {
          const text = [
            container.container_id,
            container.destination,
            container.priority,
            container.priority_level,
            container.priority_score,
            container.slot_id,
            container.bay,
            container.row,
            container.tier,
          ]
            .map((value) =>
              String(
                value ?? ""
              ).toLowerCase()
            )
            .join(" ");

          return text.includes(
            query
          );
        }
      );
    }, [plan, search]);

  const scheduledCount =
    plan.filter(
      isAssigned
    ).length;

  const unscheduledCount =
    plan.length -
    scheduledCount;

    /* =====================================================
   CONSTRAINT VALIDATION
===================================================== */

const constraintValidation =
  useMemo(() => {
    const assignedContainers =
      plan.filter(isAssigned);

    const slotIds =
      assignedContainers
        .map(
          (container) =>
            container.slot_id
        )
        .filter(Boolean);

    const containerIds =
      assignedContainers
        .map(
          (container) =>
            container.container_id
        )
        .filter(Boolean);

    const uniqueSlots =
      new Set(slotIds).size ===
      slotIds.length;

    const uniqueContainers =
      new Set(containerIds).size ===
      containerIds.length;

    const backendConstraintsPassed =
      Number(
        recommendedMetrics
          ?.constraint_violations
      ) === 0;

    const checks = [
      {
        label:
          "One container per slot",
        passed: uniqueSlots,
      },
      {
        label:
          "One slot per container",
        passed: uniqueContainers,
      },
      {
        label:
          "Weight limit satisfied",
        passed:
          backendConstraintsPassed,
      },
      {
        label:
          "Container-size compatibility",
        passed:
          backendConstraintsPassed,
      },
      {
        label:
          "Reefer compatibility",
        passed:
          backendConstraintsPassed,
      },
      {
        label:
          "Hazardous cargo eligibility",
        passed:
          backendConstraintsPassed,
      },
      {
        label:
          "No duplicate assignments",
        passed:
          uniqueSlots &&
          uniqueContainers,
      },
    ];

    return {
      checks,
      feasible:
        checks.every(
          (check) =>
            check.passed
        ),
    };
  }, [
    plan,
    recommendedMetrics,
  ]);


/* =====================================================
   BAY / ROW / TIER LAYOUT
===================================================== */

const bayLayouts =
  useMemo(() => {
    const assigned =
      plan.filter(
        (container) =>
          isAssigned(container) &&
          container.bay != null &&
          container.row != null &&
          container.tier != null
      );

    const grouped =
      new Map();

    assigned.forEach(
      (container) => {
        const bay =
          container.bay;

        if (!grouped.has(bay)) {
          grouped.set(
            bay,
            []
          );
        }

        grouped
          .get(bay)
          .push(container);
      }
    );

    return Array.from(
      grouped.entries()
    )
      .sort(
        ([bayA], [bayB]) =>
          sortPositionValues(
            bayA,
            bayB
          )
      )
      .map(
        ([bay, containers]) => {
          const rows = [
            ...new Set(
              containers.map(
                (container) =>
                  container.row
              )
            ),
          ].sort(
            sortPositionValues
          );

          const tiers = [
            ...new Set(
              containers.map(
                (container) =>
                  container.tier
              )
            ),
          ].sort(
            (a, b) =>
              sortPositionValues(
                b,
                a
              )
          );

          const positions =
            new Map();

          containers.forEach(
            (container) => {
              positions.set(
                `${container.row}-${container.tier}`,
                container
              );
            }
          );

          return {
            bay,
            rows,
            tiers,
            positions,
          };
        }
      );
  }, [plan]);


useEffect(() => {
  if (!bayLayouts.length) {
    setSelectedBay("");
    return;
  }

  const exists =
    bayLayouts.some(
      (layout) =>
        String(layout.bay) ===
        String(selectedBay)
    );

  if (!exists) {
    setSelectedBay(
      String(
        bayLayouts[0].bay
      )
    );
  }
}, [
  bayLayouts,
  selectedBay,
]);


const selectedBayLayout =
  useMemo(() => {
    return (
      bayLayouts.find(
        (layout) =>
          String(layout.bay) ===
          String(selectedBay)
      ) ||
      bayLayouts[0] ||
      null
    );
  }, [
    bayLayouts,
    selectedBay,
  ]);

  /* =====================================================
     RUN OPTIMIZATION
  ===================================================== */

  async function runOptimization() {
    if (!backendOnline) {
      setError(
        "Backend is offline."
      );
      return;
    }

    setLoading(true);
    setError("");
    setResults(null);
    setSearch("");

    setSelectedContainer(
  null
);

setRunInfo(null);

    
    try {
      const response =
        await fetch(
          `${API}/api/optimize`,
          {
            method: "POST",

            headers: {
              "Content-Type":
                "application/json",
            },

            body: JSON.stringify(
              {
                dataset,

                algorithms:
                  CORE_ALGORITHMS,
              }
            ),
          }
        );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          errorMessage(
            data.detail
          )
        );
      }

      setResults(data);

const completedAt =
  new Date();

setRunInfo({
  id: createRunId(
    dataset,
    completedAt
  ),

  generatedAt:
    completedAt.toISOString(),

  dataset:
    data.dataset ||
    dataset,
});
      /* =====================================================
   AUTOMATIC VOYAGE PLANNING
===================================================== */

try {
  setVoyageLoading(true);
  setVoyageError("");
  setVoyageResult(null);

  const chosenAlgorithm =
    data.recommended_algorithm ||
    getFallbackAlgorithm(
      data.comparison || []
    );

  const selectedPlan =
    data.solutions?.[
      chosenAlgorithm
    ] || [];

  const selectedDataset =
    datasets.find(
      (item) =>
        item.id === dataset
    );

  const route =
    selectedDataset?.route ||
    "JNPT (Mumbai) → Colombo → Port Klang → Singapore";

  const voyageResponse =
    await fetch(
      `${API}/api/voyage-plan`,
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json",
        },

        body: JSON.stringify({
          route: route,

          plan: selectedPlan,

          vessel_speed_knots: 18,

          fuel_consumption_tpd: 45,

          port_stay_hours: 8,

          emission_factor: 3.114,
        }),
      }
    );

  const voyageData =
    await voyageResponse.json();

  if (!voyageResponse.ok) {
    throw new Error(
      errorMessage(
        voyageData.detail
      )
    );
  }

  setVoyageResult(
    voyageData
  );
} catch (voyageErr) {
  console.error(
    "Voyage planning error:",
    voyageErr
  );

  setVoyageError(
    voyageErr.message ||
      "Voyage planning failed."
  );
} finally {
  setVoyageLoading(false);
}
    } catch (err) {
      setError(
        err.message ===
          "Failed to fetch"
          ? "Could not reach backend. Make sure FastAPI is running."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  /* =====================================================
     UI
  ===================================================== */

  return (
    <div className="app">
      <style>
        {`
        * {
          box-sizing: border-box;
        }

        body {
          margin: 0;
          background: #eef2f7;
          color: #0f172a;
          font-family: Arial, Helvetica, sans-serif;
        }

        button,
        input,
        select {
          font: inherit;
        }

        .app {
          min-height: 100vh;
          padding: 28px 18px 60px;
          background:
            radial-gradient(
              circle at top left,
              rgba(37,99,235,.08),
              transparent 420px
            ),
            #eef2f7;
        }

        .container {
          width: min(1180px, 100%);
          margin: auto;
        }

        .hero {
          background: #111827;
          color: white;
          padding: 45px 34px;
          border-radius: 26px;
        }

        .hero-small {
          color: #cbd5e1;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: .18em;
        }

        .hero h1 {
          font-size: clamp(
            34px,
            5vw,
            58px
          );
          line-height: 1.05;
          max-width: 1000px;
          margin: 14px 0;
        }

        .hero p {
          color: #dbe4f0;
          font-size: 17px;
        }

        .hero-tags {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
          margin-top: 24px;
        }

        .green-pill {
          background: #22c55e;
          color: #052e16;
          padding: 10px 15px;
          border-radius: 999px;
          font-size: 12px;
          font-weight: 900;
        }

        .connection {
          background:
            rgba(
              255,
              255,
              255,
              .08
            );
          border:
            1px solid
            rgba(
              255,
              255,
              255,
              .15
            );
          padding: 10px 15px;
          border-radius: 999px;
          font-size: 12px;
        }

        .card {
          background: white;
          border:
            1px solid
            #e2e8f0;
          border-radius: 24px;
          padding: 30px;
          margin-top: 24px;
        }

        .step {
          color: #2563eb;
          font-size: 12px;
          font-weight: 900;
          letter-spacing: .16em;
        }

        .card h2 {
          margin:
            8px 0
            5px;
          font-size: 26px;
        }

        .muted {
          color: #64748b;
          line-height: 1.6;
        }

        .form-grid {
          display: grid;
          grid-template-columns:
            1fr 1fr;
          gap: 16px;
          margin-top: 22px;
        }

        label {
          display: block;
          font-size: 12px;
          font-weight: 800;
          margin-bottom: 8px;
        }

        select {
          width: 100%;
          min-height: 58px;
          border:
            1px solid
            #cbd5e1;
          border-radius: 14px;
          padding: 0 15px;
          background: white;
        }

        .mode {
          min-height: 58px;
          display: flex;
          align-items: center;
          justify-content:
            center;
          background: #f1f5f9;
          border:
            1px solid
            #cbd5e1;
          border-radius: 14px;
          font-weight: 800;
        }

        .strategies {
          margin-top: 18px;
          padding: 20px;
          background: #eff6ff;
          border:
            1px solid
            #bfdbfe;
          border-radius: 16px;
          text-align: center;
        }

        .chips {
          display: flex;
          justify-content:
            center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .chip {
          padding: 8px 12px;
          border:
            1px solid
            #bfdbfe;
          border-radius: 999px;
          background: white;
          font-size: 12px;
          font-weight: 800;
        }

        .run {
          width: 100%;
          min-height: 56px;
          margin-top: 18px;
          border: 0;
          border-radius: 14px;
          background: #2563eb;
          color: white;
          font-weight: 900;
          cursor: pointer;
        }

        .run:disabled {
          opacity: .55;
        }

        .error {
          margin-top: 16px;
          background: #fff1f2;
          border:
            1px solid
            #fecaca;
          color: #991b1b;
          padding: 15px;
          border-radius: 12px;
          text-align: center;
        }

        .plan-head {
          display: flex;
          justify-content:
            space-between;
          gap: 20px;
          align-items: center;
          background: #f8fafc;
          padding: 20px;
          border-radius: 15px;
        }

        .plan-head span {
          display: block;
          color: #64748b;
        }

        .plan-head strong {
          display: block;
          font-size: 24px;
          margin-top: 4px;
        }

        .metrics {
          display: grid;
          grid-template-columns:
            repeat(
              6,
              1fr
            );
          gap: 10px;
          margin-top: 16px;
        }

        .metric,
        .stat,
        .detail-box {
          background: #f8fafc;
          border:
            1px solid
            #e2e8f0;
          border-radius: 14px;
          padding: 15px;
          text-align: center;
        }

        .metric span,
        .stat span,
        .detail-box span {
          display: block;
          color: #64748b;
          font-size: 11px;
          margin-bottom: 6px;
        }

        .metric strong {
          font-size: 20px;
        }

        .why {
          margin-top: 18px;
          padding: 22px;
          background: #f0fdf4;
          border:
            1px solid
            #bbf7d0;
          border-radius: 16px;
        }

        .why h3 {
          text-align: center;
        }

        .why-list {
          max-width: 760px;
          margin: auto;
          line-height: 2;
        }

        .stats {
          display: grid;
          grid-template-columns:
            repeat(
              4,
              1fr
            );
          gap: 12px;
          margin-top: 20px;
        }

        .stat strong {
          font-size: 21px;
        }

        .toolbar {
          display: flex;
          align-items: center;
          gap: 12px;
          margin:
            20px 0
            14px;
        }

        .toolbar input {
          flex: 1;
          min-height: 45px;
          background: #263141;
          color: white;
          border:
            1px solid
            #334155;
          border-radius: 10px;
          padding: 0 14px;
        }

        .table-wrap {
          overflow-x: auto;
          border:
            1px solid
            #e2e8f0;
          border-radius: 15px;
        }

        table {
          width: 100%;
          min-width: 1050px;
          border-collapse:
            collapse;
        }

        th {
          background: #f8fafc;
          padding: 14px 12px;
          text-align: left;
          font-size: 11px;
          border-bottom:
            1px solid
            #e2e8f0;
        }

        td {
          padding: 13px 12px;
          font-size: 13px;
          border-bottom:
            1px solid
            #eef2f7;
        }

        .scheduled {
          display:
            inline-flex;
          background: #dcfce7;
          color: #166534;
          padding: 5px 9px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 800;
        }

        .unscheduled {
          display:
            inline-flex;
          background: #fee2e2;
          color: #991b1b;
          padding: 5px 9px;
          border-radius: 999px;
          font-size: 11px;
          font-weight: 800;
        }

        .priority-cell {
          display: flex;
          flex-direction:
            column;
          align-items:
            flex-start;
          gap: 4px;
        }

        .priority-badge {
          padding: 5px 9px;
          border-radius: 999px;
          font-size: 10px;
          font-weight: 900;
          text-transform:
            uppercase;
        }

        .priority-score {
          font-size: 10px;
          color: #64748b;
        }

        .view {
          border:
            1px solid
            #bfdbfe;
          background: #eff6ff;
          color: #1d4ed8;
          border-radius: 8px;
          padding: 7px 10px;
          font-weight: 800;
          cursor: pointer;
        }

        .selected-row {
          background: #f0fdf4;
        }

        .modal-overlay {
          position: fixed;
          inset: 0;
          z-index: 9999;
          background:
            rgba(
              15,
              23,
              42,
              .70
            );
          display: grid;
          place-items: center;
          padding: 20px;
        }

        .modal {
          width:
            min(
              1050px,
              100%
            );
          max-height: 90vh;
          overflow-y: auto;
          background: white;
          border-radius: 22px;
          padding: 26px;
        }

        .modal-header {
          display: flex;
          justify-content:
            space-between;
          align-items:
            flex-start;
        }

        .close {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          border:
            1px solid
            #e2e8f0;
          background: white;
          font-size: 23px;
          cursor: pointer;
        }

        .details {
          display: grid;
          grid-template-columns:
            repeat(
              4,
              1fr
            );
          gap: 10px;
          margin-top: 18px;
        }

        .modal-section {
          margin-top: 18px;
          padding: 22px;
          border:
            1px solid
            #e2e8f0;
          border-radius: 15px;
          background: #f8fafc;
        }

        .modal-section h3 {
          text-align: center;
          margin-top: 0;
        }

        .priority-summary {
          display: flex;
          justify-content:
            center;
          flex-wrap: wrap;
          gap: 10px;
          margin-bottom: 18px;
        }

        .info-pill {
          padding: 8px 15px;
          border-radius: 999px;
          background: #eff6ff;
          border:
            1px solid
            #bfdbfe;
          color: #1d4ed8;
          font-weight: 800;
        }

        .reason-list {
          line-height: 1.9;
          color: #334155;
        }

        @media (
          max-width: 900px
        ) {
          .metrics {
            grid-template-columns:
              repeat(
                3,
                1fr
              );
          }

          .stats,
          .details {
            grid-template-columns:
              repeat(
                2,
                1fr
              );
          }
        }

        @media (
          max-width: 650px
        ) {
          .form-grid,
          .metrics,
          .stats,
          .details {
            grid-template-columns:
              1fr;
          }

          .toolbar {
            flex-direction:
              column;
            align-items:
              stretch;
          }
        }

        /* =====================================================
   RUN INFORMATION
===================================================== */

.run-info-panel {
  margin-top: 18px;
  padding: 22px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 16px;
}

.run-info-panel h3 {
  margin: 0 0 16px;
  text-align: center;
}

.run-info-grid {
  display: grid;
  grid-template-columns:
    repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.run-info-grid > div {
  background: white;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}

.run-info-grid span {
  display: block;
  color: #64748b;
  font-size: 11px;
  margin-bottom: 6px;
}

.run-info-grid strong {
  display: block;
  font-size: 13px;
  overflow-wrap: anywhere;
}


/* =====================================================
   CONSTRAINT VALIDATION
===================================================== */

.constraint-validation {
  margin-top: 18px;
  padding: 24px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 16px;
}

.constraint-validation h3 {
  margin: 0;
  text-align: center;
  font-size: 20px;
}

.constraint-subtitle {
  text-align: center;
  color: #64748b;
  font-size: 13px;
  margin: 7px 0 18px;
}

.constraint-check-grid {
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.constraint-check {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px;
  background: white;
  border-radius: 11px;
  font-size: 13px;
  font-weight: 700;
}

.constraint-check.passed {
  border: 1px solid #bbf7d0;
}

.constraint-check.failed {
  border: 1px solid #fecaca;
}

.check-circle {
  width: 27px;
  height: 27px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.passed .check-circle {
  background: #dcfce7;
  color: #15803d;
}

.failed .check-circle {
  background: #fee2e2;
  color: #b91c1c;
}

.overall-feasible,
.overall-infeasible {
  margin: 18px auto 0;
  max-width: 430px;
  text-align: center;
  padding: 13px 18px;
  border-radius: 11px;
}

.overall-feasible {
  background: #dcfce7;
  color: #166534;
}

.overall-infeasible {
  background: #fee2e2;
  color: #991b1b;
}


/* =====================================================
   VESSEL LAYOUT
===================================================== */

.vessel-layout-panel {
  margin-top: 24px;
  padding: 24px;
  background: #f8fafc;
  border: 1px solid #dbe3ee;
  border-radius: 18px;
}

.vessel-layout-header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 20px;
  margin-bottom: 18px;
}

.vessel-layout-header h3 {
  margin: 0 0 5px;
}

.vessel-layout-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.bay-control {
  width: 170px;
  flex-shrink: 0;
}

.bay-control select {
  min-height: 42px;
}

.vessel-bay-title {
  padding: 12px;
  text-align: center;
  background: #0f172a;
  color: white;
  border-radius: 11px 11px 0 0;
  font-weight: 900;
  letter-spacing: .08em;
}

.vessel-grid-wrapper {
  padding: 18px;
  background: white;
  border: 1px solid #e2e8f0;
  border-top: 0;
  overflow-x: auto;
}

.vessel-grid-row {
  display: grid;
  gap: 8px;
  min-width: max-content;
  margin-bottom: 8px;
  align-items: center;
}

.vessel-grid-heading {
  color: #475569;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
}

.tier-name {
  color: #475569;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
}

.vessel-slot {
  min-height: 55px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 7px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 900;
  text-align: center;
}

.vessel-slot.normal {
  background: #dbeafe;
  color: #1d4ed8;
  border: 1px solid #93c5fd;
}

.vessel-slot.priority {
  background: #ffedd5;
  color: #9a3412;
  border: 1px solid #fdba74;
}

.vessel-slot.reefer {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #86efac;
}

.vessel-slot.hazardous {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.vessel-slot.empty {
  background: #f8fafc;
  color: #94a3b8;
  border: 1px dashed #cbd5e1;
}

.vessel-legend {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 16px;
  font-size: 11px;
  color: #475569;
}

.vessel-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.vessel-legend i {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-normal {
  background: #93c5fd;
}

.legend-priority {
  background: #fdba74;
}

.legend-reefer {
  background: #86efac;
}

.legend-hazardous {
  background: #fca5a5;
}

.legend-empty {
  background: #e2e8f0;
}


/* =====================================================
   VOYAGE ROUTE TIMELINE
===================================================== */

.voyage-visual-panel {
  margin-top: 24px;
  padding: 24px;
  background: #f8fafc;
  border: 1px solid #dbe3ee;
  border-radius: 18px;
}

.voyage-visual-panel h3 {
  margin: 0;
  text-align: center;
}

.timeline-subtitle {
  text-align: center;
  color: #64748b;
  font-size: 13px;
  margin: 7px 0 20px;
}

.route-timeline {
  display: flex;
  align-items: center;
  overflow-x: auto;
  padding: 6px 2px 14px;
}

.route-leg-group {
  display: flex;
  align-items: center;
}

.route-node {
  width: 190px;
  min-width: 190px;
  min-height: 150px;
  padding: 18px 14px;
  background: white;
  border: 2px solid #bfdbfe;
  border-radius: 15px;
  text-align: center;

  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 7px;
}

.route-start {
  background: #f0fdf4;
  border-color: #86efac;
}

.route-final {
  background: #eff6ff;
  border-color: #60a5fa;
}

.route-node-label {
  color: #2563eb;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: .12em;
}

.route-node strong {
  font-size: 17px;
  color: #0f172a;
}

.route-node small {
  color: #64748b;
  line-height: 1.4;
}

.route-connector {
  width: 150px;
  min-width: 150px;
  text-align: center;
  color: #2563eb;
  font-size: 11px;
  font-weight: 800;
}

.route-arrow {
  font-size: 32px;
  line-height: 1;
  margin: 4px 0;
}

.route-connector small {
  display: block;
  color: #64748b;
}


/* =====================================================
   RESPONSIVE ADDITIONS
===================================================== */

@media (max-width: 800px) {
  .run-info-grid,
  .constraint-check-grid {
    grid-template-columns:
      repeat(2, minmax(0, 1fr));
  }

  .vessel-layout-header {
    flex-direction: column;
    align-items: stretch;
  }

  .bay-control {
    width: 100%;
  }
}

@media (max-width: 550px) {
  .run-info-grid,
  .constraint-check-grid {
    grid-template-columns: 1fr;
  }
}

/* ================================
   VISIBILITY FIXES
================================ */

.card h2 {
  color: #0f172a !important;
  opacity: 1 !important;
}

.card h3,
.card h4 {
  color: #0f172a !important;
}

.modal h2,
.modal h3,
.modal h4 {
  color: #0f172a !important;
  opacity: 1 !important;
}

select {
  color: #0f172a !important;
  background-color: #ffffff !important;
  -webkit-text-fill-color: #0f172a !important;
  opacity: 1 !important;
}

select option {
  color: #0f172a !important;
  background-color: #ffffff !important;
}

label {
  color: #334155 !important;
}

.step {
  color: #2563eb !important;
}

.modal {
  color: #0f172a !important;
}

.modal-header h2 {
  color: #0f172a !important;
}
        `}
      </style>

      <main className="container">
        {/* HERO */}

        <section className="hero">
          <div className="hero-small">
          
          </div>

          <h1>
            AI-Driven Container Vessel
            Cargo Scheduling &amp;
            Voyage Planning System
          </h1>

          <p>
            Automatic constraint-aware
            container assignment and optimized
            Bay–Row–Tier stowage planning.
          </p>

          <div className="hero-tags">
            <span className="green-pill">
             AI / Optimization & Voyage Planning Engine
            </span>

            <span className="connection">
              {backendOnline
                ? "● Backend Connected"
                : "● Backend Offline"}
            </span>
          </div>
        </section>

        {/* STEP 1 */}

        <section className="card container-section">
          <div className="step">
            STEP 01
          </div>

          <h2>
            Generate Optimized Plan
          </h2>

          <p className="muted">
            Select a dataset. The system
            automatically evaluates the core
            optimization strategies.
          </p>

          <div className="form-grid">
            <div>
              <label>
                Dataset
              </label>

              <select
                value={dataset}
                onChange={(event) => {
                  setDataset(
                    event.target.value
                  );

                  setResults(
                    null
                  );

                  setError("");
                }}
              >
                {datasets
                  .filter(
                    (item) =>
                      item.id !==
                      "custom"
                  )
                  .map((item) => (
                    <option
                      key={
                        item.id
                      }
                      value={
                        item.id
                      }
                      disabled={
                        !item.available
                      }
                    >
                      {item.name} —{" "}
                      {
                        item.containers
                      }{" "}
                      containers /{" "}
                      {item.slots}{" "}
                      slots
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label>
                Optimization Mode
              </label>

              <div className="mode">
                Automatic Best-Plan
                Selection
              </div>
            </div>
          </div>

          <div className="strategies">
            <h3>
              Internal Optimization
              Strategies
            </h3>

            <p className="muted">
              The system evaluates all core
              optimization methods internally
              and returns one final plan.
            </p>

            <div className="chips">
              <span className="chip">
                Priority-Based
                Optimization
              </span>

              <span className="chip">
                Genetic Search
              </span>

              <span className="chip">
                Constraint
                Optimization
              </span>
            </div>
          </div>

          <button
            type="button"
            className="run"
            disabled={
              loading ||
              !backendOnline
            }
            onClick={
              runOptimization
            }
          >
            {loading
              ? "Running Optimization..."
              : "Generate Best Optimized Stowage Plan"}
          </button>

          {error && (
            <div className="error">
              <strong>
                Optimization Error
              </strong>

              <div>{error}</div>
            </div>
          )}
        </section>

        {/* RESULTS */}

        {results &&
          recommendedMetrics && (
            <>
              {/* STEP 2 */}

              <section className="card">
                <div className="step">
                  STEP 02
                </div>

                <h2>
                  Best Optimized Stowage
                  Plan
                </h2>

                <div className="plan-head">
                  <div>
                    <span>
                      Selected Strategy
                    </span>

                    <strong>
                      {algorithmName(
                        recommendedAlgorithm
                      )}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Dataset
                    </span>

                    <strong>
                      {results.dataset ||
                        dataset}
                    </strong>
                  </div>
                </div>

                <div className="metrics">
                  <Metric
                    label="Assignment"
                    value={formatPercent(
                      recommendedMetrics.assignment_rate
                    )}
                  />

                  <Metric
                    label="Slot Utilization"
                    value={formatPercent(
                      recommendedMetrics.slot_utilization
                    )}
                  />

                  <Metric
                    label="Violations"
                    value={
                      recommendedMetrics.constraint_violations ??
                      "N/A"
                    }
                  />

                  <Metric
                    label="Weight Imbalance"
                    value={formatNumber(
                      recommendedMetrics.weight_imbalance_std
                    )}
                  />

                  <Metric
                    label="Objective Score"
                    value={formatNumber(
                      recommendedMetrics.objective_score
                    )}
                  />

                  <Metric
                    label="Runtime"
                    value={`${formatNumber(
                      recommendedMetrics.runtime_seconds,
                      3
                    )} s`}
                  />
                </div>

{runInfo && (
  <div className="run-info-panel">
    <h3>
      Run Information
    </h3>

    <div className="run-info-grid">
      <div>
        <span>
          Run ID
        </span>

        <strong>
          {runInfo.id}
        </strong>
      </div>

      <div>
        <span>
          Generated
        </span>

        <strong>
          {new Date(
            runInfo.generatedAt
          ).toLocaleString()}
        </strong>
      </div>

      <div>
        <span>
          Dataset
        </span>

        <strong>
          {runInfo.dataset}
        </strong>
      </div>

      <div>
        <span>
          Selected Algorithm
        </span>

        <strong>
          {algorithmName(
            recommendedAlgorithm
          )}
        </strong>
      </div>
    </div>
  </div>
)}

<div className="constraint-validation">
  <h3>
    Constraint Validation
  </h3>

  <p className="constraint-subtitle">
    Verification of the selected
    stowage plan against implemented
    hard constraints.
  </p>

  <div className="constraint-check-grid">
    {constraintValidation.checks.map(
      (check) => (
        <div
          key={check.label}
          className={
            check.passed
              ? "constraint-check passed"
              : "constraint-check failed"
          }
        >
          <span className="check-circle">
            {check.passed
              ? "✓"
              : "✕"}
          </span>

          <span>
            {check.label}
          </span>
        </div>
      )
    )}
  </div>

  <div
    className={
      constraintValidation.feasible
        ? "overall-feasible"
        : "overall-infeasible"
    }
  >
    Overall Status:{" "}
    <strong>
      {constraintValidation.feasible
        ? "FEASIBLE"
        : "REVIEW REQUIRED"}
    </strong>
  </div>
</div>

                <div className="why">
                  <h3>
                    Why this plan was
                    selected
                  </h3>

                  <ol className="why-list">
                    <li>
                      Minimum constraint
                      violations
                    </li>

                    <li>
                      Minimum unassigned
                      containers
                    </li>

                    <li>
                      Maximum container
                      assignment rate
                    </li>

                    <li>
                      Lower overall objective
                      penalty
                    </li>

                    <li>
                      Lower weight imbalance
                    </li>

                    <li>
                      Runtime used only as
                      final tie-breaker
                    </li>
                  </ol>
                </div>
              </section>

              {/* STEP 3 */}

              <section className="card">
                <div className="step">
                  STEP 03
                </div>

                <h2>
                  Container Scheduling
                  &amp; Stowage Assignment
                </h2>

                <div className="stats">
                  <Stat
                    label="Containers in Plan"
                    value={
                      plan.length
                    }
                  />

                  <Stat
                    label="Scheduled"
                    value={
                      scheduledCount
                    }
                  />

                  <Stat
                    label="Unscheduled"
                    value={
                      unscheduledCount
                    }
                  />

                  <Stat
                    label="Selected Strategy"
                    value={algorithmName(
                      recommendedAlgorithm
                    )}
                  />
                </div>

{selectedBayLayout && (
  <div className="vessel-layout-panel">
    <div className="vessel-layout-header">
      <div>
        <h3>
          Vessel Layout Visualization
        </h3>

        <p>
          Bay–Row–Tier representation of
          the selected optimized stowage plan.
        </p>
      </div>

      <div className="bay-control">
        <label>
          Select Bay
        </label>

        <select
          value={selectedBay}
          onChange={(event) =>
            setSelectedBay(
              event.target.value
            )
          }
        >
          {bayLayouts.map(
            (layout) => (
              <option
                key={
                  layout.bay
                }
                value={
                  String(
                    layout.bay
                  )
                }
              >
                Bay{" "}
                {String(
                  layout.bay
                ).padStart(
                  2,
                  "0"
                )}
              </option>
            )
          )}
        </select>
      </div>
    </div>

    <div className="vessel-bay-title">
      BAY{" "}
      {String(
        selectedBayLayout.bay
      ).padStart(
        2,
        "0"
      )}
    </div>

    <div className="vessel-grid-wrapper">
      <div
        className="vessel-grid-row vessel-grid-heading"
        style={{
          gridTemplateColumns:
            `90px repeat(${selectedBayLayout.rows.length}, minmax(90px, 1fr))`,
        }}
      >
        <div>
          Tier / Row
        </div>

        {selectedBayLayout.rows.map(
          (row) => (
            <div key={row}>
              R{row}
            </div>
          )
        )}
      </div>

      {selectedBayLayout.tiers.map(
        (tier) => (
          <div
            key={tier}
            className="vessel-grid-row"
            style={{
              gridTemplateColumns:
                `90px repeat(${selectedBayLayout.rows.length}, minmax(90px, 1fr))`,
            }}
          >
            <div className="tier-name">
              Tier {tier}
            </div>

            {selectedBayLayout.rows.map(
              (row) => {
                const container =
                  selectedBayLayout
                    .positions
                    .get(
                      `${row}-${tier}`
                    );

                let type =
                  "empty";

                if (container) {
                  if (
                    isTrue(
                      container.hazardous
                    )
                  ) {
                    type =
                      "hazardous";
                  } else if (
                    isTrue(
                      container.refrigerated
                    )
                  ) {
                    type =
                      "reefer";
                  } else if (
                    ["critical", "high"].includes(
                      String(
                        container.priority_level ||
                        ""
                      ).toLowerCase()
                    )
                  ) {
                    type =
                      "priority";
                  } else {
                    type =
                      "normal";
                  }
                }

                return (
                  <div
                    key={`${row}-${tier}`}
                    className={`vessel-slot ${type}`}
                    title={
                      container
                        ? `${container.container_id} | ${container.destination} | ${container.slot_id}`
                        : "Empty position"
                    }
                  >
                    {container
                      ? container.container_id
                      : "Empty"}
                  </div>
                );
              }
            )}
          </div>
        )
      )}
    </div>

    <div className="vessel-legend">
      <span>
        <i className="legend-normal" />
        Normal
      </span>

      <span>
        <i className="legend-priority" />
        High / Critical Priority
      </span>

      <span>
        <i className="legend-reefer" />
        Reefer
      </span>

      <span>
        <i className="legend-hazardous" />
        Hazardous
      </span>

      <span>
        <i className="legend-empty" />
        Empty
      </span>
    </div>
  </div>
)}

                <div className="toolbar">
                  <input
                    type="search"
                    value={
                      search
                    }
                    placeholder="Search container, destination, priority, slot..."
                    onChange={(
                      event
                    ) =>
                      setSearch(
                        event.target
                          .value
                      )
                    }
                  />

                  <span className="muted">
                    {
                      filteredPlan.length
                    }{" "}
                    container(s)
                  </span>
                </div>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>
                          Container
                        </th>

                        <th>
                          Status
                        </th>

                        <th>
                          Operational
                          Priority
                        </th>

                        <th>
                          Destination
                        </th>

                        <th>
                          Weight
                        </th>

                        <th>
                          Bay
                        </th>

                        <th>
                          Row
                        </th>

                        <th>
                          Tier
                        </th>

                        <th>
                          Details
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {filteredPlan.map(
                        (
                          container
                        ) => {
                          const assigned =
                            isAssigned(
                              container
                            );

                          return (
                            <tr
                              key={`${container.container_id}-${container.slot_id ?? "none"}`}
                            >
                              <td>
                                <strong>
                                  {
                                    container.container_id
                                  }
                                </strong>
                              </td>

                              <td>
                                <span
                                  className={
                                    assigned
                                      ? "scheduled"
                                      : "unscheduled"
                                  }
                                >
                                  {assigned
                                    ? "Scheduled"
                                    : "Unscheduled"}
                                </span>
                              </td>

                              <td>
                                <div className="priority-cell">
                                  <span
                                    className="priority-badge"
                                    style={getPriorityStyle(
                                      container.priority_level
                                    )}
                                  >
                                    {container.priority_level ||
                                      "Normal"}
                                  </span>

                                  <span className="priority-score">
                                    Score:{" "}
                                    {container.priority_score ??
                                      "N/A"}
                                  </span>

                                  <span className="priority-score">
                                    Input
                                    Priority:{" "}
                                    {container.priority ??
                                      "N/A"}
                                  </span>
                                </div>
                              </td>

                              <td>
                                {
                                  container.destination
                                }
                              </td>

                              <td>
                                {
                                  container.container_weight
                                }
                              </td>

                              <td>
                                {assigned
                                  ? container.bay
                                  : "—"}
                              </td>

                              <td>
                                {assigned
                                  ? container.row
                                  : "—"}
                              </td>

                              <td>
                                {assigned
                                  ? container.tier
                                  : "—"}
                              </td>

                              <td>
                                <button
                                  type="button"
                                  className="view"
                                  onClick={() =>
                                    setSelectedContainer(
                                      container
                                    )
                                  }
                                >
                                  View Why
                                </button>
                              </td>
                            </tr>
                          );
                        }
                      )}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* STEP 4 */}

              <section className="card">
                <div className="step">
                  STEP 04
                </div>

                <h2>
                  Algorithm Comparison
                </h2>

                <p className="muted">
                  All algorithms are tested
                  using the same dataset and
                  scoring framework.
                </p>

                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>
                          Algorithm
                        </th>

                        <th>
                          Status
                        </th>

                        <th>
                          Assignment
                        </th>

                        <th>
                          Utilization
                        </th>

                        <th>
                          Violations
                        </th>

                        <th>
                          Unassigned
                        </th>

                        <th>
                          Imbalance
                        </th>

                        <th>
                          Objective
                        </th>

                        <th>
                          Runtime
                        </th>
                      </tr>
                    </thead>

                    <tbody>
                      {(results.comparison ||
                        []).map(
                        (row) => (
                          <tr
                            key={
                              row.algorithm
                            }
                            className={
                              row.algorithm ===
                              recommendedAlgorithm
                                ? "selected-row"
                                : ""
                            }
                          >
                            <td>
                              <strong>
                                {algorithmName(
                                  row.algorithm
                                )}
                              </strong>
                            </td>

                            <td>
                              {
                                row.status
                              }
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? formatPercent(
                                    row.assignment_rate
                                  )
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? formatPercent(
                                    row.slot_utilization
                                  )
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? row.constraint_violations
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? row.unassigned
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? formatNumber(
                                    row.weight_imbalance_std
                                  )
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? formatNumber(
                                    row.objective_score
                                  )
                                : "—"}
                            </td>

                            <td>
                              {row.status ===
                              "SUCCESS"
                                ? `${formatNumber(
                                    row.runtime_seconds,
                                    3
                                  )} s`
                                : "Failed"}
                            </td>
                          </tr>
                        )
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {/* =====================================================
    STEP 04 - VOYAGE PLANNING
===================================================== */}

{results && (
  <section className="card voyage-section">
    <div className="step">
      STEP 04
    </div>

    <h2>
      Voyage Planning
    </h2>

    <p className="muted">
      Port-wise voyage schedule generated
      from the selected optimized stowage
      plan and container destinations.
    </p>

    {voyageLoading && (
      <div
        style={{
          marginTop: "20px",
          padding: "22px",
          textAlign: "center",
          background: "#eff6ff",
          border: "1px solid #bfdbfe",
          borderRadius: "14px",
          color: "#1d4ed8",
          fontWeight: "800",
        }}
      >
        Generating voyage plan...
      </div>
    )}

    {voyageError && (
      <div className="error">
        <strong>
          Voyage Planning Error
        </strong>

        <div>
          {voyageError}
        </div>
      </div>
    )}

    {voyageResult && (
      <>
        {/* ROUTE */}

        <div
          style={{
            marginTop: "22px",
            padding: "22px",
            borderRadius: "16px",
            background: "#0f172a",
            color: "#ffffff",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              letterSpacing: "0.12em",
              color: "#93c5fd",
              fontWeight: "900",
              marginBottom: "10px",
            }}
          >
            VOYAGE ROUTE
          </div>

          <div
            style={{
              fontSize: "22px",
              fontWeight: "800",
            }}
          >
            {voyageResult.route_text}
          </div>
        </div>

{/* VISUAL ROUTE TIMELINE */}

<div className="voyage-visual-panel">
  <h3>
    Visual Route Timeline
  </h3>

  <p className="timeline-subtitle">
    Port sequence and discharge activity
    derived from the selected cargo plan.
  </p>

  <div className="route-timeline">
    <div className="route-node route-start">
      <span className="route-node-label">
        DEPARTURE
      </span>

      <strong>
        {voyageResult.legs?.[0]
          ?.from_port ||
          voyageResult.route?.[0] ||
          "JNPT (Mumbai)"}
      </strong>

      <small>
        {
          voyageResult.summary
            ?.scheduled_containers
        }{" "}
        containers loaded
      </small>

      {voyageResult.departure_time && (
        <small>
          {new Date(
            voyageResult.departure_time
          ).toLocaleString()}
        </small>
      )}
    </div>

    {(voyageResult.legs || []).map(
      (leg, index) => (
        <div
          className="route-leg-group"
          key={leg.sequence}
        >
          <div className="route-connector">
            <span>
              {formatNumber(
                leg.distance_nm
              )}{" "}
              NM
            </span>

            <div className="route-arrow">
              →
            </div>

            <small>
              {formatNumber(
                leg.sailing_hours
              )}{" "}
              hrs
            </small>
          </div>

          <div
            className={`route-node ${
              index ===
              voyageResult.legs.length -
                1
                ? "route-final"
                : ""
            }`}
          >
            <span className="route-node-label">
              {index ===
              voyageResult.legs.length -
                1
                ? "FINAL PORT"
                : `PORT ${leg.sequence}`}
            </span>

            <strong>
              {leg.to_port}
            </strong>

            <small>
              Discharge:{" "}
              {
                leg.containers_to_discharge
              }{" "}
              containers
            </small>

            <small>
              ETA:{" "}
              {leg.estimated_arrival
                ? new Date(
                    leg.estimated_arrival
                  ).toLocaleString()
                : "N/A"}
            </small>
          </div>
        </div>
      )
    )}
  </div>
</div>

        {/* VOYAGE METRICS */}

        <div className="stats">
          <Stat
            label="Total Distance"
            value={`${formatNumber(
              voyageResult.summary
                ?.total_distance_nm
            )} NM`}
          />

          <Stat
            label="Sailing Time"
            value={`${formatNumber(
              voyageResult.summary
                ?.total_sailing_hours
            )} hrs`}
          />

          <Stat
            label="Estimated Fuel"
            value={`${formatNumber(
              voyageResult.summary
                ?.estimated_sailing_fuel_tonnes
            )} t`}
          />

          <Stat
            label="Estimated CO₂"
            value={`${formatNumber(
              voyageResult.summary
                ?.estimated_co2_tonnes
            )} t`}
          />
        </div>

        <div className="stats">
          <Stat
            label="Voyage Duration"
            value={`${formatNumber(
              voyageResult.summary
                ?.estimated_total_voyage_days
            )} days`}
          />

          <Stat
            label="Port Stay"
            value={`${formatNumber(
              voyageResult.summary
                ?.total_port_stay_hours
            )} hrs`}
          />

          <Stat
            label="Scheduled Cargo"
            value={
              voyageResult.summary
                ?.scheduled_containers ??
              "N/A"
            }
          />

          <Stat
            label="Unscheduled Cargo"
            value={
              voyageResult.summary
                ?.unscheduled_containers ??
              "N/A"
            }
          />
        </div>

        {/* PORT SCHEDULE */}

        <div
          style={{
            marginTop: "28px",
          }}
        >
          <h3
            style={{
              textAlign: "center",
              color: "#0f172a",
            }}
          >
            Port-wise Voyage Schedule
          </h3>

          <div className="voyage-table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>
                    Leg
                  </th>

                  <th>
                    From
                  </th>

                  <th>
                    To
                  </th>

                  <th>
                    Distance
                  </th>

                  <th>
                    Sailing Time
                  </th>

                  <th>
                    ETA
                  </th>

                  <th>
                    Containers
                    to Discharge
                  </th>

                  <th>
                    Port Stay
                  </th>
                </tr>
              </thead>

              <tbody>
                {(
                  voyageResult.legs ||
                  []
                ).map((leg) => (
                  <tr
                    key={
                      leg.sequence
                    }
                  >
                    <td>
                      <strong>
                        {
                          leg.sequence
                        }
                      </strong>
                    </td>

                    <td>
                      {
                        leg.from_port
                      }
                    </td>

                    <td>
                      {
                        leg.to_port
                      }
                    </td>

                    <td>
                      {formatNumber(
                        leg.distance_nm
                      )}{" "}
                      NM
                    </td>

                    <td>
                      {formatNumber(
                        leg.sailing_hours
                      )}{" "}
                      hrs
                    </td>

                    <td>
                      {leg.estimated_arrival
                        ? new Date(
                            leg.estimated_arrival
                          ).toLocaleString()
                        : "N/A"}
                    </td>

                    <td>
                      <strong>
                        {
                          leg.containers_to_discharge
                        }
                      </strong>
                    </td>

                    <td>
                      {formatNumber(
                        leg.port_stay_hours
                      )}{" "}
                      hrs
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* PORT CARGO SUMMARY */}

        <div
          style={{
            marginTop: "28px",
          }}
        >
          <h3
            style={{
              textAlign: "center",
              color: "#0f172a",
            }}
          >
            Port Cargo Summary
          </h3>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>
                    Sequence
                  </th>

                  <th>
                    Port
                  </th>

                  <th>
                    Operation
                  </th>

                  <th>
                    Containers
                  </th>

                  <th>
                    Cargo Weight
                  </th>
                </tr>
              </thead>

              <tbody>
                {(
                  voyageResult.port_cargo ||
                  []
                ).map(
                  (
                    port,
                    index
                  ) => (
                    <tr
                      key={`${port.port}-${index}`}
                    >
                      <td>
                        {
                          port.sequence
                        }
                      </td>

                      <td>
                        <strong>
                          {
                            port.port
                          }
                        </strong>
                      </td>

                      <td>
                        {
                          port.operation
                        }
                      </td>

                      <td>
                        {
                          port.containers
                        }
                      </td>

                      <td>
                        {formatNumber(
                          port.cargo_weight
                        )}{" "}
                        kg
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* DISCLAIMER */}

        <div
          style={{
            marginTop: "20px",
            padding: "15px",
            borderRadius: "12px",
            background: "#fff7ed",
            border:
              "1px solid #fed7aa",
            color: "#9a3412",
            fontSize: "13px",
            lineHeight: 1.6,
          }}
        >
          <strong>
            Academic Voyage Planning:
          </strong>{" "}
          Sailing distance, ETA, fuel and
          emission values are planning
          estimates based on configured
          vessel parameters and predefined
          port sequence. This module is not
          intended for certified maritime
          navigation.
        </div>
      </>
    )}
  </section>
)}

        {/* CONTAINER MODAL */}

        {selectedContainer && (
          <div
            className="modal-overlay"
            onMouseDown={(
              event
            ) => {
              if (
                event.target ===
                event.currentTarget
              ) {
                setSelectedContainer(
                  null
                );
              }
            }}
          >
            <div className="modal">
              <div className="modal-header">
                <div>
                  <div className="step">
                      COMPARATIVE ANALYSIS
                  </div>

                  <h2>
                    {
                      selectedContainer.container_id
                    }
                  </h2>
                </div>

                <button
  onClick={() => setSelectedContainer(null)}
  style={{
    position: "absolute",
    top: "18px",
    right: "18px",
    width: "42px",
    height: "42px",
    borderRadius: "50%",
    border: "2px solid #cbd5e1",
    background: "#ffffff",
    color: "#0f172a",
    fontSize: "24px",
    fontWeight: "700",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 9999,
    boxShadow: "0 2px 8px rgba(0,0,0,0.08)"
  }}
  aria-label="Close"
  title="Close"
>
  ×
</button>
              </div>

              <div className="details">
                <DetailBox
                  label="Status"
                  value={
                    isAssigned(
                      selectedContainer
                    )
                      ? "Scheduled"
                      : "Unscheduled"
                  }
                />

                <DetailBox
                  label="Input Priority"
                  value={
                    selectedContainer.priority
                  }
                />

                <DetailBox
                  label="Destination"
                  value={
                    selectedContainer.destination
                  }
                />

                <DetailBox
                  label="Destination Order"
                  value={
                    selectedContainer.destination_order
                  }
                />

                <DetailBox
                  label="Size"
                  value={
                    selectedContainer.container_size
                  }
                />

                <DetailBox
                  label="Weight"
                  value={
                    selectedContainer.container_weight
                  }
                />

                <DetailBox
                  label="Hazardous"
                  value={
                    isTrue(
                      selectedContainer.hazardous
                    )
                      ? "Yes"
                      : "No"
                  }
                />

                <DetailBox
                  label="Refrigerated"
                  value={
                    isTrue(
                      selectedContainer.refrigerated
                    )
                      ? "Yes"
                      : "No"
                  }
                />

                <DetailBox
                  label="Slot"
                  value={
                    selectedContainer.slot_id ||
                    "—"
                  }
                />

                <DetailBox
                  label="Bay"
                  value={
                    selectedContainer.bay ??
                    "—"
                  }
                />

                <DetailBox
                  label="Row"
                  value={
                    selectedContainer.row ??
                    "—"
                  }
                />

                <DetailBox
                  label="Tier"
                  value={
                    selectedContainer.tier ??
                    "—"
                  }
                />
              </div>

              {/* PRIORITY */}

              <div className="modal-section">
                <h3>
                  Operational Priority
                </h3>

                <div className="priority-summary">
                  <span
                    className="priority-badge"
                    style={{
                      ...getPriorityStyle(
                        selectedContainer.priority_level
                      ),

                      padding:
                        "9px 16px",
                    }}
                  >
                    {selectedContainer.priority_level ||
                      "Normal"}
                  </span>

                  <span className="info-pill">
                    Priority Score:{" "}
                    {selectedContainer.priority_score ??
                      "N/A"}
                  </span>

                  <span className="info-pill">
                    Input Priority:{" "}
                    {selectedContainer.priority ??
                      "N/A"}
                  </span>
                </div>

                <h4>
                  Why this priority was
                  assigned
                </h4>

                <ul className="reason-list">
                  {getPriorityReasons(
                    selectedContainer
                  ).map(
                    (
                      reason,
                      index
                    ) => (
                      <li
                        key={
                          index
                        }
                      >
                        {reason}
                      </li>
                    )
                  )}
                </ul>
              </div>

              {/* POSITION */}

              <div className="modal-section">
                <h3>
                  Why was this position
                  selected?
                </h3>

                <ul className="reason-list">
                  {getPlacementReasons(
                    selectedContainer
                  ).map(
                    (
                      reason,
                      index
                    ) => (
                      <li
                        key={
                          index
                        }
                      >
                        {reason}
                      </li>
                    )
                  )}
                </ul>
              </div>

              <div
                style={{
                  marginTop:
                    "18px",

                  padding:
                    "14px",

                  borderRadius:
                    "12px",

                  background:
                    "#fff7ed",

                  border:
                    "1px solid #fed7aa",

                  color:
                    "#9a3412",

                  fontSize:
                    "13px",

                  lineHeight:
                    1.6,
                }}
              >
                <strong>
                  Important:{" "}
                </strong>

                Operational priority is
                generated by the implemented
                backend priority-enrichment
                logic. Placement explanations
                describe implemented
                feasibility rules and do not
                represent certified naval
                stability calculations.
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
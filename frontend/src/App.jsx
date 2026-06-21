import { useEffect, useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

const overviewFields = [
  ["total_theses", "Theses"],
  ["first_year", "First year"],
  ["last_year", "Last year"],
  ["universities", "Universities"],
  ["categories", "Categories"],
];

const statsConfig = [
  ["byUniversity", "By university"],
  ["byProfession", "By profession"],
  ["byCategory", "By category"],
  ["byYear", "By year"],
];

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function useRoute() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const updatePath = () => setPath(window.location.pathname);
    window.addEventListener("popstate", updatePath);
    return () => window.removeEventListener("popstate", updatePath);
  }, []);

  return path;
}

async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function useApi(path) {
  const [state, setState] = useState({ data: null, loading: true, error: "" });

  useEffect(() => {
    let ignore = false;
    setState({ data: null, loading: true, error: "" });

    fetchJson(path)
      .then((data) => {
        if (!ignore) setState({ data, loading: false, error: "" });
      })
      .catch((error) => {
        if (!ignore) setState({ data: null, loading: false, error: error.message });
      });

    return () => {
      ignore = true;
    };
  }, [path]);

  return state;
}

function App() {
  const path = useRoute();
  const detailMatch = path.match(/^\/theses\/(\d+)$/);
  const filteredMatch = path.match(/^\/(year|university|profession|category)\/(.+)$/);

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => navigate("/")}>
          Prehospitala Avhandlingar
        </button>
        <nav aria-label="Primary navigation">
          <button className={path === "/" ? "active" : ""} onClick={() => navigate("/")}>
            Overview
          </button>
          <button
            className={path.startsWith("/theses") || filteredMatch ? "active" : ""}
            onClick={() => navigate("/theses")}
          >
            Theses
          </button>
        </nav>
      </header>

      <main>
        {path === "/" && <HomePage />}
        {path === "/theses" && <ThesesPage />}
        {detailMatch && <ThesisDetail runningNumber={detailMatch[1]} />}
        {filteredMatch && (
          <FilteredThesesPage
            filterType={filteredMatch[1]}
            filterValue={decodeURIComponent(filteredMatch[2])}
          />
        )}
      </main>
    </div>
  );
}

function HomePage() {
  const overview = useApi("/stats/overview");
  const byUniversity = useApi("/stats/by-university");
  const byProfession = useApi("/stats/by-profession");
  const byCategory = useApi("/stats/by-category");
  const byYear = useApi("/stats/by-year");
  const { data: categories } = useApi("/categories");
  const categoryIdsByName = useMemo(
    () => Object.fromEntries((categories ?? []).map((category) => [category.name, category.id])),
    [categories]
  );
  const stats = {
    byUniversity: {
      title: "By university",
      getPath: (row) => `/university/${encodePathValue(row.label)}`,
      ...byUniversity,
    },
    byProfession: {
      title: "By profession",
      getPath: (row) => `/profession/${encodePathValue(row.label)}`,
      ...byProfession,
    },
    byCategory: {
      title: "By category",
      getPath: (row) => `/category/${encodePathValue(categoryIdsByName[row.label] ?? row.label)}`,
      ...byCategory,
    },
    byYear: {
      title: "By year",
      getPath: (row) => `/year/${encodePathValue(row.label)}`,
      sortRows: (rows) => [...rows].sort((a, b) => Number(b.label) - Number(a.label)),
      scrollable: true,
      ...byYear,
    },
  };

  return (
    <>
      <section className="intro">
        <p className="eyebrow">Research catalogue</p>
        <h1>Swedish prehospital doctoral theses</h1>
        <p>
          A concise overview of dissertations, institutions, professions, and research
          categories represented in the catalogue.
        </p>
      </section>

      <section className="overview-grid" aria-label="Overview statistics">
        {overview.loading && <Status message="Loading overview..." />}
        {overview.error && <Status message="Could not load overview." />}
        {overview.data &&
          overviewFields.map(([key, label]) => (
            <article className="stat-card" key={key}>
              <span>{label}</span>
              <strong>{overview.data[key] ?? "-"}</strong>
            </article>
          ))}
      </section>

      <section className="stats-grid" aria-label="Descriptive statistics">
        {statsConfig.map(([key]) => (
          <StatsPanel key={key} state={stats[key]} />
        ))}
      </section>
    </>
  );
}

function StatsPanel({ state }) {
  const rows = state.sortRows ? state.sortRows(state.data ?? []) : state.data ?? [];
  const max = Math.max(...rows.map((row) => row.count), 1);
  const visibleRows = state.scrollable ? rows : rows.slice(0, 10);

  return (
    <article className={`panel ${state.scrollable ? "panel-scroll" : ""}`}>
      <h2>{state.title}</h2>
      {state.loading && <Status message="Loading..." />}
      {state.error && <Status message="Could not load data." />}
      {!state.loading && !state.error && (
        <ol className="rank-list">
          {visibleRows.map((row) => (
            <li key={`${row.label}-${row.count}`}>
              <button className="rank-item" onClick={() => navigate(state.getPath(row))}>
                <div className="rank-line">
                  <span>{row.label}</span>
                  <strong>{row.count}</strong>
                </div>
                <div className="bar-track" aria-hidden="true">
                  <div className="bar-fill" style={{ width: `${(row.count / max) * 100}%` }} />
                </div>
              </button>
            </li>
          ))}
        </ol>
      )}
    </article>
  );
}

function ThesesPage() {
  const { data: theses, loading, error } = useApi("/theses");
  const { data: categories } = useApi("/categories");
  const [filters, setFilters] = useState({
    category: "",
    university: "",
    profession: "",
    year: "",
  });

  const categoryNames = useMemo(() => makeNameMap(categories), [categories]);

  const options = useMemo(() => {
    const source = theses ?? [];
    return {
      category: uniqueValues(source.map((thesis) => thesis.category_id)).map((id) => ({
        value: id,
        label: categoryNames[id] ?? id,
      })),
      university: uniqueValues(source.map((thesis) => thesis.university)),
      profession: uniqueValues(source.map((thesis) => thesis.profession)),
      year: uniqueValues(source.map((thesis) => thesis.year)).sort((a, b) => b - a),
    };
  }, [categoryNames, theses]);

  const filtered = useMemo(() => {
    return (theses ?? []).filter((thesis) => {
      return (
        matchesFilter(thesis.category_id, filters.category) &&
        matchesFilter(thesis.university, filters.university) &&
        matchesFilter(thesis.profession, filters.profession) &&
        matchesFilter(thesis.year, filters.year)
      );
    });
  }, [theses, filters]);

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Catalogue</p>
          <h1>All theses</h1>
        </div>
        <span className="result-count">{filtered.length} results</span>
      </div>

      {loading && <Status message="Loading theses..." />}
      {error && <Status message="Could not load theses." />}
      {theses && (
        <>
          <div className="filters" aria-label="Thesis filters">
            <SelectFilter
              label="Category"
              value={filters.category}
              options={options.category}
              onChange={(value) => setFilters((current) => ({ ...current, category: value }))}
            />
            <SelectFilter
              label="University"
              value={filters.university}
              options={options.university}
              onChange={(value) => setFilters((current) => ({ ...current, university: value }))}
            />
            <SelectFilter
              label="Profession"
              value={filters.profession}
              options={options.profession}
              onChange={(value) => setFilters((current) => ({ ...current, profession: value }))}
            />
            <SelectFilter
              label="Year"
              value={filters.year}
              options={options.year}
              onChange={(value) => setFilters((current) => ({ ...current, year: value }))}
            />
          </div>

          <ThesisList theses={filtered} />
        </>
      )}
    </section>
  );
}

function FilteredThesesPage({ filterType, filterValue }) {
  const { data: theses, loading, error } = useApi("/theses");
  const { data: categories } = useApi("/categories");
  const categoryNames = useMemo(() => makeNameMap(categories), [categories]);
  const categoryId = useMemo(() => {
    if (filterType !== "category") return filterValue;
    return (
      (categories ?? []).find(
        (category) => category.id === filterValue || category.name === filterValue
      )?.id ?? filterValue
    );
  }, [categories, filterType, filterValue]);
  const heading = filterType === "category" ? categoryNames[categoryId] ?? filterValue : filterValue;
  const label = {
    year: "Year",
    university: "University",
    profession: "Profession",
    category: "Category",
  }[filterType];

  const filtered = useMemo(() => {
    return (theses ?? []).filter((thesis) => {
      if (filterType === "year") return matchesFilter(thesis.year, filterValue);
      if (filterType === "university") return matchesFilter(thesis.university, filterValue);
      if (filterType === "profession") return matchesFilter(thesis.profession, filterValue);
      if (filterType === "category") return matchesFilter(thesis.category_id, categoryId);
      return false;
    });
  }, [categoryId, filterType, filterValue, theses]);

  return (
    <section className="page-section">
      <button className="back-button" onClick={() => navigate("/theses")}>
        Back to all theses
      </button>

      <div className="section-heading filtered-heading">
        <div>
          <p className="eyebrow">{label}</p>
          <h1>{heading}</h1>
        </div>
        <span className="result-count">{filtered.length} results</span>
      </div>

      {loading && <Status message="Loading theses..." />}
      {error && <Status message="Could not load theses." />}
      {theses && <ThesisList theses={filtered} />}
    </section>
  );
}

function ThesisList({ theses }) {
  return (
    <div className="thesis-list">
      {theses.map((thesis) => (
        <button
          className="thesis-row"
          key={thesis.running_number}
          onClick={() => navigate(`/theses/${thesis.running_number}`)}
        >
          <span className="thesis-number">#{thesis.running_number}</span>
          <span className="thesis-main">
            <strong>{thesis.title}</strong>
            <span>
              {thesis.author} · {thesis.university} · {thesis.year}
            </span>
          </span>
          <span className="thesis-meta">{thesis.profession}</span>
        </button>
      ))}
    </div>
  );
}

function ThesisDetail({ runningNumber }) {
  const { data: thesis, loading, error } = useApi(`/theses/${runningNumber}`);
  const { data: categories } = useApi("/categories");
  const { data: subcategories } = useApi("/subcategories");
  const categoryNames = useMemo(() => makeNameMap(categories), [categories]);
  const subcategoryNames = useMemo(() => makeNameMap(subcategories), [subcategories]);

  return (
    <section className="page-section detail-section">
      <button className="back-button" onClick={() => navigate("/theses")}>
        Back to theses
      </button>

      {loading && <Status message="Loading thesis..." />}
      {error && <Status message="Could not load thesis." />}
      {thesis && (
        <article className="detail">
          <p className="eyebrow">Thesis #{thesis.running_number}</p>
          <h1>{thesis.title}</h1>
          <dl>
            <div>
              <dt>Author</dt>
              <dd>{thesis.author}</dd>
            </div>
            <div>
              <dt>Profession</dt>
              <dd>{thesis.profession || "-"}</dd>
            </div>
            <div>
              <dt>University</dt>
              <dd>{thesis.university || "-"}</dd>
            </div>
            <div>
              <dt>Year</dt>
              <dd>{thesis.year || "-"}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{categoryNames[thesis.category_id] || thesis.category_id || "-"}</dd>
            </div>
            <div>
              <dt>Subcategory</dt>
              <dd>{subcategoryNames[thesis.subcategory_id] || thesis.subcategory_id || "-"}</dd>
            </div>
          </dl>
        </article>
      )}
    </section>
  );
}

function SelectFilter({ label, value, options, onChange }) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">All</option>
        {options.map((option) => (
          <option key={option.value ?? option} value={option.value ?? option}>
            {option.label ?? option}
          </option>
        ))}
      </select>
    </label>
  );
}

function Status({ message }) {
  return <p className="status">{message}</p>;
}

function uniqueValues(values) {
  return [...new Set(values.filter((value) => value !== null && value !== undefined && value !== ""))];
}

function matchesFilter(value, filter) {
  return !filter || String(value) === String(filter);
}

function makeNameMap(rows) {
  return Object.fromEntries((rows ?? []).map((row) => [row.id, row.name]));
}

function encodePathValue(value) {
  return encodeURIComponent(String(value));
}

export default App;

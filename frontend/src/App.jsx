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

async function sendJson(path, method, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  const researchAreaMatch = path.match(/^\/research-areas\/([A-I])$/);

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
          <button
            className={path.startsWith("/research-areas") ? "active" : ""}
            onClick={() => navigate("/research-areas")}
          >
            Forskningsområden
          </button>
          <button
            className={path === "/references" ? "active" : ""}
            onClick={() => navigate("/references")}
          >
            Referenser
          </button>
        </nav>
      </header>

      <main>
        {path === "/" && <HomePage />}
        {path === "/theses" && <ThesesPage />}
        {path === "/research-areas" && <ResearchAreasPage />}
        {researchAreaMatch && <ResearchAreasPage categoryId={researchAreaMatch[1]} />}
        {path === "/references" && <ReferencesPage />}
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

function ResearchAreasPage({ categoryId }) {
  const endpoint = categoryId ? `/research-areas/${categoryId}` : "/research-areas";
  const { data, loading, error } = useApi(endpoint);
  const { data: theses } = useApi("/theses");
  const areas = categoryId && data ? [data] : data ?? [];
  const authorLinks = useMemo(() => makeAuthorLinks(theses), [theses]);

  useEffect(() => {
    if (!data || !window.location.hash) return;
    const element = document.querySelector(window.location.hash);
    if (element) element.scrollIntoView({ block: "start" });
  }, [data]);

  return (
    <section className="page-section research-page">
      {categoryId && (
        <button className="back-button" onClick={() => navigate("/research-areas")}>
          Alla forskningsområden
        </button>
      )}

      <div className="section-heading">
        <div>
          <p className="eyebrow">Rapportens tematisering</p>
          <h1>Forskningsområden</h1>
        </div>
        {areas.length > 0 && <span className="result-count">{areas.length} områden</span>}
      </div>

      {loading && <Status message="Loading research areas..." />}
      {error && <Status message="Could not load research areas." />}
      {!loading && !error && (
        <div className="research-area-list">
          {areas.map((area) => (
            <ResearchAreaSection
              key={area.id}
              area={area}
              authorLinks={authorLinks}
              singleCategory={Boolean(categoryId)}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ResearchAreaSection({ area, authorLinks, singleCategory }) {
  return (
    <article className="research-area" id={`category-${area.id}`}>
      <div className="research-area-heading">
        <div>
          <p className="eyebrow">Huvudkategori {area.id}</p>
          <h2>{area.name}</h2>
        </div>
        {!singleCategory && (
          <button className="text-link-button" onClick={() => navigate(`/research-areas/${area.id}`)}>
            Visa området
          </button>
        )}
      </div>

      {area.narrative_text && (
        <NarrativeText authorLinks={authorLinks} collapsible linkCitations text={area.narrative_text} />
      )}

      {area.subcategories.length > 0 && (
        <div className="subcategory-list">
          {area.subcategories.map((subcategory) => (
            <SubcategoryCard
              key={subcategory.id}
              authorLinks={authorLinks}
              subcategory={subcategory}
            />
          ))}
        </div>
      )}
    </article>
  );
}

function SubcategoryCard({ authorLinks, subcategory }) {
  const [tab, setTab] = useState("overview");

  return (
    <article className="subcategory-card" id={`subcategory-${subcategory.id}`}>
      <div className="subcategory-heading">
        <div>
          <p className="eyebrow">Subkategori {subcategory.id}</p>
          <h3>{subcategory.name}</h3>
        </div>
      </div>

      <div className="tab-list" role="tablist" aria-label={`${subcategory.id} sections`}>
        <button
          className={tab === "overview" ? "active" : ""}
          onClick={() => setTab("overview")}
          type="button"
        >
          Översikt
        </button>
        <button
          className={tab === "theses" ? "active" : ""}
          onClick={() => setTab("theses")}
          type="button"
        >
          Avhandlingar
        </button>
        <button
          className={tab === "publications" ? "active" : ""}
          onClick={() => setTab("publications")}
          type="button"
        >
          Publikationer
        </button>
      </div>

      {tab === "overview" && (
        <div className="tab-panel">
          {subcategory.narrative_text ? (
            <NarrativeText
              authorLinks={authorLinks}
              collapsible
              linkCitations
              text={subcategory.narrative_text}
            />
          ) : (
            <Status message="Ingen narrativ text importerad för denna subkategori." />
          )}
        </div>
      )}
      {tab === "theses" && (
        <div className="tab-panel">
          {subcategory.theses.length > 0 ? (
            <ThesisList theses={subcategory.theses} />
          ) : (
            <Status message="Inga avhandlingar är kopplade till denna subkategori." />
          )}
        </div>
      )}
      {tab === "publications" && (
        <div className="tab-panel">
          <p className="placeholder-text">Publikationer läggs till i en senare version.</p>
        </div>
      )}
    </article>
  );
}

function ReferencesPage() {
  const { data: references, loading, error } = useApi("/references");

  useEffect(() => {
    if (!references || !window.location.hash) return;
    const element = document.querySelector(window.location.hash);
    if (element) element.scrollIntoView({ block: "start" });
  }, [references]);

  return (
    <section className="page-section references-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Rapportens källor</p>
          <h1>Referenser</h1>
        </div>
        {references && <span className="result-count">{references.length} referenser</span>}
      </div>

      {loading && <Status message="Loading references..." />}
      {error && <Status message="Could not load references." />}
      {references && (
        <ol className="reference-list">
          {references.map((reference) => (
            <li id={`ref-${reference.number}`} key={reference.id}>
              <span className="reference-number">{reference.number}</span>
              <p>{reference.text}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function NarrativeText({
  authorLinks = [],
  collapsible = false,
  linkCitations = false,
  text,
}) {
  const [expanded, setExpanded] = useState(false);
  const paragraphs = text.split("\n\n");
  const visibleParagraphs = collapsible && !expanded ? paragraphs.slice(0, 1) : paragraphs;

  return (
    <div className="narrative-text">
      {visibleParagraphs.map((paragraph, index) => (
        <p key={`${paragraph.slice(0, 24)}-${index}`}>
          {renderNarrativeParts(paragraph, { authorLinks, linkCitations })}
        </p>
      ))}
      {collapsible && paragraphs.length > 1 && (
        <button className="text-link-button narrative-toggle" onClick={() => setExpanded(!expanded)}>
          {expanded ? "Visa mindre" : "Visa mer"}
        </button>
      )}
    </div>
  );
}

function ThesisDetail({ runningNumber }) {
  const thesisRequest = useApi(`/theses/${runningNumber}`);
  const [savedThesis, setSavedThesis] = useState(null);
  const [paperReload, setPaperReload] = useState(0);
  const papers = useApi(`/theses/${runningNumber}/papers?reload=${paperReload}`);
  const { data: categories } = useApi("/categories");
  const { data: subcategories } = useApi("/subcategories");
  const categoryNames = useMemo(() => makeNameMap(categories), [categories]);
  const subcategoryNames = useMemo(() => makeNameMap(subcategories), [subcategories]);
  const thesis = savedThesis ?? thesisRequest.data;
  const hasDigitalMetadata = Boolean(
    thesis?.abstract ||
      thesis?.dissertation_url ||
      thesis?.pdf_url ||
      thesis?.doi ||
      thesis?.urn ||
      (papers.data && papers.data.length > 0)
  );

  return (
    <section className="page-section detail-section">
      <button className="back-button" onClick={() => navigate("/theses")}>
        Back to theses
      </button>

      {thesisRequest.loading && <Status message="Loading thesis..." />}
      {thesisRequest.error && <Status message="Could not load thesis." />}
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
              <dd>
                {thesis.category_id ? (
                  <button
                    className="detail-link"
                    onClick={() => navigate(`/research-areas/${thesis.category_id}`)}
                  >
                    {categoryNames[thesis.category_id] || thesis.category_id}
                  </button>
                ) : (
                  "-"
                )}
              </dd>
            </div>
            <div>
              <dt>Subcategory</dt>
              <dd>
                {thesis.subcategory_id ? (
                  <button
                    className="detail-link"
                    onClick={() =>
                      navigate(
                        `/research-areas/${thesis.subcategory_id[0]}#subcategory-${thesis.subcategory_id}`
                      )
                    }
                  >
                    {subcategoryNames[thesis.subcategory_id] || thesis.subcategory_id}
                  </button>
                ) : (
                  "-"
                )}
              </dd>
            </div>
          </dl>

          <section className="digital-metadata">
            <h2>Digital avhandling</h2>
            {!hasDigitalMetadata && (
              <p className="placeholder-text">Digital metadata has not been added yet.</p>
            )}

            <div className="metadata-block">
              <h3>Abstrakt</h3>
              {thesis.abstract ? (
                <NarrativeText text={thesis.abstract} />
              ) : (
                <p className="placeholder-text">Digital metadata has not been added yet.</p>
              )}
            </div>

            {(thesis.dissertation_url || thesis.pdf_url || thesis.doi || thesis.urn) && (
              <dl className="metadata-list">
                {thesis.dissertation_url && (
                  <div>
                    <dt>Dissertation URL</dt>
                    <dd>
                      <a href={thesis.dissertation_url} target="_blank" rel="noreferrer">
                        Open dissertation record
                      </a>
                    </dd>
                  </div>
                )}
                {thesis.pdf_url && (
                  <div>
                    <dt>PDF</dt>
                    <dd>
                      <a href={thesis.pdf_url} target="_blank" rel="noreferrer">
                        Open PDF
                      </a>
                    </dd>
                  </div>
                )}
                {thesis.doi && (
                  <div>
                    <dt>DOI</dt>
                    <dd>
                      <a href={doiUrl(thesis.doi)} target="_blank" rel="noreferrer">
                        {thesis.doi}
                      </a>
                    </dd>
                  </div>
                )}
                {thesis.urn && (
                  <div>
                    <dt>URN</dt>
                    <dd>{thesis.urn}</dd>
                  </div>
                )}
              </dl>
            )}

            <div className="metadata-block">
              <h3>Ingående artiklar</h3>
              {papers.loading && <Status message="Loading included papers..." />}
              {papers.error && <Status message="Could not load included papers." />}
              {papers.data && papers.data.length === 0 && (
                <p className="placeholder-text">Digital metadata has not been added yet.</p>
              )}
              {papers.data && papers.data.length > 0 && (
                <div className="paper-list">
                  {papers.data.map((paper) => (
                    <article className="paper-item" key={paper.id}>
                      <h4>
                        {paper.url ? (
                          <a href={paper.url} target="_blank" rel="noreferrer">
                            {paper.title}
                          </a>
                        ) : (
                          paper.title
                        )}
                      </h4>
                      <p className="paper-meta">
                        {[paper.journal, paper.year, paper.doi && `DOI: ${paper.doi}`, paper.pubmed_id && `PubMed: ${paper.pubmed_id}`]
                          .filter(Boolean)
                          .join(" · ")}
                      </p>
                      {paper.abstract && <NarrativeText text={paper.abstract} />}
                    </article>
                  ))}
                </div>
              )}
            </div>

            <MetadataEditForm
              onSaved={setSavedThesis}
              thesis={thesis}
            />
            <MetadataLookup
              onSaved={setSavedThesis}
              runningNumber={runningNumber}
            />
            <IncludedPaperForm
              onSaved={() => setPaperReload((current) => current + 1)}
              runningNumber={runningNumber}
            />
          </section>
        </article>
      )}
    </section>
  );
}

function MetadataEditForm({ onSaved, thesis }) {
  const [form, setForm] = useState(metadataFormFromThesis(thesis));
  const [status, setStatus] = useState("");

  useEffect(() => {
    setForm(metadataFormFromThesis(thesis));
  }, [thesis]);

  async function handleSubmit(event) {
    event.preventDefault();
    setStatus("Sparar...");
    try {
      const saved = await sendJson(`/theses/${thesis.running_number}`, "PATCH", form);
      onSaved(saved);
      setStatus("Sparat.");
    } catch {
      setStatus("Kunde inte spara metadata.");
    }
  }

  return (
    <form className="metadata-form" onSubmit={handleSubmit}>
      <h3>Edit metadata</h3>
      <label>
        <span>Abstrakt</span>
        <textarea
          rows="6"
          value={form.abstract}
          onChange={(event) => setForm((current) => ({ ...current, abstract: event.target.value }))}
        />
      </label>
      <div className="metadata-form-grid">
        <label>
          <span>Dissertation URL</span>
          <input
            value={form.dissertation_url}
            onChange={(event) =>
              setForm((current) => ({ ...current, dissertation_url: event.target.value }))
            }
          />
        </label>
        <label>
          <span>PDF URL</span>
          <input
            value={form.pdf_url}
            onChange={(event) => setForm((current) => ({ ...current, pdf_url: event.target.value }))}
          />
        </label>
        <label>
          <span>DOI</span>
          <input
            value={form.doi}
            onChange={(event) => setForm((current) => ({ ...current, doi: event.target.value }))}
          />
        </label>
        <label>
          <span>URN</span>
          <input
            value={form.urn}
            onChange={(event) => setForm((current) => ({ ...current, urn: event.target.value }))}
          />
        </label>
      </div>
      <div className="form-actions">
        <button className="primary-button" type="submit">Spara metadata</button>
        {status && <span className="form-status">{status}</span>}
      </div>
    </form>
  );
}

function MetadataLookup({ onSaved, runningNumber }) {
  const [lookup, setLookup] = useState({ candidates: [], search: null });
  const [status, setStatus] = useState("");

  async function handleLookup() {
    setStatus("Söker...");
    try {
      const result = await sendJson(`/theses/${runningNumber}/lookup-metadata`, "POST", {});
      setLookup(result);
      setStatus(result.candidates.length ? "" : "Inga kandidater hittades.");
    } catch {
      setStatus("Kunde inte söka metadata.");
    }
  }

  async function useCandidate(candidate) {
    setStatus("Sparar kandidat...");
    try {
      const saved = await sendJson(`/theses/${runningNumber}`, "PATCH", candidateToMetadata(candidate));
      onSaved(saved);
      setStatus("Kandidat sparad.");
    } catch {
      setStatus("Kunde inte spara kandidat.");
    }
  }

  return (
    <section className="metadata-lookup">
      <div className="lookup-heading">
        <div>
          <h3>Find digital metadata</h3>
          <p className="placeholder-text">Candidates are never applied without approval.</p>
        </div>
        <button className="primary-button" onClick={handleLookup} type="button">
          Find digital metadata
        </button>
      </div>

      {status && <p className="status">{status}</p>}
      {lookup.candidates.length > 0 && (
        <div className="candidate-list">
          {lookup.candidates.map((candidate, index) => (
            <article className="candidate-card" key={`${candidate.source}-${index}`}>
              <h4>{candidate.title || "Untitled candidate"}</h4>
              <p className="paper-meta">
                {[candidate.source, `Confidence: ${candidate.confidence}`].filter(Boolean).join(" · ")}
              </p>
              <dl className="metadata-list">
                {candidate.dissertation_url && (
                  <div>
                    <dt>Dissertation URL</dt>
                    <dd>{candidate.dissertation_url}</dd>
                  </div>
                )}
                {candidate.pdf_url && (
                  <div>
                    <dt>PDF URL</dt>
                    <dd>{candidate.pdf_url}</dd>
                  </div>
                )}
                {candidate.doi && (
                  <div>
                    <dt>DOI</dt>
                    <dd>{candidate.doi}</dd>
                  </div>
                )}
                {candidate.urn && (
                  <div>
                    <dt>URN</dt>
                    <dd>{candidate.urn}</dd>
                  </div>
                )}
              </dl>
              {candidate.abstract && <NarrativeText text={candidate.abstract} />}
              <button className="primary-button" onClick={() => useCandidate(candidate)} type="button">
                Use this metadata
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function IncludedPaperForm({ onSaved, runningNumber }) {
  const [form, setForm] = useState(emptyPaperForm());
  const [status, setStatus] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.title.trim()) {
      setStatus("Titel krävs.");
      return;
    }

    setStatus("Sparar...");
    try {
      await sendJson(`/theses/${runningNumber}/papers`, "POST", {
        ...form,
        year: form.year ? Number(form.year) : null,
      });
      setForm(emptyPaperForm());
      setStatus("Artikel sparad.");
      onSaved();
    } catch {
      setStatus("Kunde inte spara artikel.");
    }
  }

  return (
    <form className="metadata-form" onSubmit={handleSubmit}>
      <h3>Lägg till ingående artikel</h3>
      <label>
        <span>Titel</span>
        <input
          value={form.title}
          onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
        />
      </label>
      <div className="metadata-form-grid">
        <label>
          <span>Tidskrift</span>
          <input
            value={form.journal}
            onChange={(event) => setForm((current) => ({ ...current, journal: event.target.value }))}
          />
        </label>
        <label>
          <span>År</span>
          <input
            inputMode="numeric"
            value={form.year}
            onChange={(event) => setForm((current) => ({ ...current, year: event.target.value }))}
          />
        </label>
        <label>
          <span>DOI</span>
          <input
            value={form.doi}
            onChange={(event) => setForm((current) => ({ ...current, doi: event.target.value }))}
          />
        </label>
        <label>
          <span>PubMed ID</span>
          <input
            value={form.pubmed_id}
            onChange={(event) =>
              setForm((current) => ({ ...current, pubmed_id: event.target.value }))
            }
          />
        </label>
      </div>
      <label>
        <span>URL</span>
        <input
          value={form.url}
          onChange={(event) => setForm((current) => ({ ...current, url: event.target.value }))}
        />
      </label>
      <label>
        <span>Abstrakt</span>
        <textarea
          rows="4"
          value={form.abstract}
          onChange={(event) => setForm((current) => ({ ...current, abstract: event.target.value }))}
        />
      </label>
      <div className="form-actions">
        <button className="primary-button" type="submit">Spara artikel</button>
        {status && <span className="form-status">{status}</span>}
      </div>
    </form>
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

function doiUrl(doi) {
  return doi.startsWith("http") ? doi : `https://doi.org/${doi}`;
}

function metadataFormFromThesis(thesis) {
  return {
    abstract: thesis?.abstract ?? "",
    dissertation_url: thesis?.dissertation_url ?? "",
    pdf_url: thesis?.pdf_url ?? "",
    doi: thesis?.doi ?? "",
    urn: thesis?.urn ?? "",
  };
}

function emptyPaperForm() {
  return {
    title: "",
    journal: "",
    year: "",
    doi: "",
    pubmed_id: "",
    url: "",
    abstract: "",
  };
}

function candidateToMetadata(candidate) {
  return Object.fromEntries(
    ["abstract", "dissertation_url", "pdf_url", "doi", "urn"]
      .map((field) => [field, candidate[field]])
      .filter(([, value]) => value !== null && value !== undefined && value !== "")
  );
}

function makeAuthorLinks(theses) {
  const byAuthor = new Map();
  for (const thesis of theses ?? []) {
    if (thesis.author && !byAuthor.has(thesis.author)) {
      byAuthor.set(thesis.author, thesis.running_number);
    }
  }

  return [...byAuthor.entries()]
    .map(([author, runningNumber]) => ({ author, runningNumber }))
    .sort((a, b) => b.author.length - a.author.length);
}

function renderNarrativeParts(paragraph, { authorLinks, linkCitations }) {
  const patterns = [];
  if (linkCitations) patterns.push("\\(\\d+\\)");
  if (authorLinks.length > 0) {
    patterns.push(...authorLinks.map((link) => escapeRegExp(link.author)));
  }

  if (patterns.length === 0) return paragraph;

  const regex = new RegExp(`(${patterns.join("|")})`, "g");
  return paragraph.split(regex).filter(Boolean).map((part, index) => {
    if (linkCitations && /^\(\d+\)$/.test(part)) {
      const referenceNumber = part.slice(1, -1);
      return (
        <button
          className="citation-link"
          key={`${part}-${index}`}
          onClick={() => navigate(`/references#ref-${referenceNumber}`)}
        >
          {part}
        </button>
      );
    }

    const authorMatch = authorLinks.find((link) => link.author === part);
    if (authorMatch) {
      return (
        <button
          className="author-link"
          key={`${part}-${index}`}
          onClick={() => navigate(`/theses/${authorMatch.runningNumber}`)}
        >
          {part}
        </button>
      );
    }

    return part;
  });
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export default App;

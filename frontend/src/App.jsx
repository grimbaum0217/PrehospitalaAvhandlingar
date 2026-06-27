import { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

const translations = {
  sv: {
    overview: "Statistik",
    theses: "Avhandlingar",
    researchAreas: "Forskningsområden",
    references: "Referenser",
    admin: "Admin",
    publicMode: "Publikt läge",
    adminMode: "Adminläge",
    catalogueEyebrow: "Forskningskatalog",
    homeTitle: "Svenska prehospitala doktorsavhandlingar",
    homeIntro:
      "En översikt över avhandlingar, lärosäten, professioner och forskningskategorier i katalogen.",
    totalTheses: "Avhandlingar",
    firstYear: "Första år",
    lastYear: "Senaste år",
    universities: "Lärosäten",
    categories: "Kategorier",
    byUniversity: "Per lärosäte",
    byProfession: "Per profession",
    byCategory: "Per kategori",
    byYear: "Per år",
    allTheses: "Alla avhandlingar",
    results: "resultat",
    category: "Kategori",
    university: "Lärosäte",
    profession: "Profession",
    selectProfession: "Välj profession",
    addNewProfession: "Lägg till ny profession",
    newProfession: "Ny profession",
    professionRequired: "Profession krävs.",
    confirmCreateProfession: "Skapa ny profession?",
    year: "År",
    all: "Alla",
    backToAllTheses: "Till alla avhandlingar",
    backToTheses: "Till avhandlingar",
    author: "Författare",
    subcategory: "Subkategori",
    digitalThesis: "Digital avhandling",
    abstract: "Abstrakt",
    dissertationUrl: "Avhandlingspost",
    openDissertationRecord: "Öppna avhandlingspost",
    openPdf: "Öppna PDF",
    includedPapers: "Ingående artiklar",
    editMetadata: "Redigera metadata",
    saveMetadata: "Spara metadata",
    findDigitalMetadata: "Sök digital metadata",
    candidatesManual: "Kandidater används aldrig utan godkännande.",
    lookupFromUrl: "Sök från URL",
    pasteDissertationUrl: "Klistra in URL till avhandlingspost",
    extractMetadata: "Extrahera metadata",
    extractedMetadata: "Extraherad metadata",
    currentValue: "Nuvarande",
    extractedValue: "Extraherat",
    copyField: "Kopiera",
    acceptAllFields: "Använd alla fält",
    parserUsed: "Parser",
    missingFields: "Saknade fält",
    noMissingFields: "Inga saknade fält",
    useMetadata: "Använd denna metadata",
    addIncludedPaper: "Lägg till ingående artikel",
    title: "Titel",
    journal: "Tidskrift",
    savePaper: "Spara artikel",
    showMore: "Visa mer",
    showLess: "Visa mindre",
    showArea: "Visa området",
    reportThemes: "Rapportens tematisering",
    allResearchAreas: "Alla forskningsområden",
    mainCategory: "Huvudkategori",
    subcategoryLabel: "Subkategori",
    overviewTab: "Översikt",
    publications: "Publikationer",
    reportSources: "Rapportens källor",
    referencesCount: "referenser",
    researchAreasCount: "områden",
    noDigitalMetadata: "Digital metadata har inte lagts till ännu.",
    loadingOverview: "Laddar statistik...",
    loadingTheses: "Laddar avhandlingar...",
    loadingResearchAreas: "Laddar forskningsområden...",
    loadingReferences: "Laddar referenser...",
    loadingPapers: "Laddar ingående artiklar...",
    loading: "Laddar...",
    couldNotLoadOverview: "Kunde inte ladda statistik.",
    couldNotLoadData: "Kunde inte ladda data.",
    couldNotLoadTheses: "Kunde inte ladda avhandlingar.",
    couldNotLoadResearchAreas: "Kunde inte ladda forskningsområden.",
    couldNotLoadReferences: "Kunde inte ladda referenser.",
    couldNotLoadPapers: "Kunde inte ladda ingående artiklar.",
    noNarrative: "Ingen narrativ text importerad för denna subkategori.",
    noLinkedTheses: "Inga avhandlingar är kopplade till denna subkategori.",
    publicationsLater: "Publikationer läggs till i en senare version.",
    searching: "Söker...",
    fetchingUrl: "Hämtar metadata från URL...",
    noCandidates: "Inga kandidater hittades.",
    lookupFailed: "Kunde inte söka metadata.",
    urlLookupFailed: "Kunde inte hämta metadata från URL.",
    saving: "Sparar...",
    saved: "Sparat.",
    saveFailed: "Kunde inte spara metadata.",
    savingCandidate: "Sparar kandidat...",
    candidateSaved: "Kandidat sparad.",
    candidateSaveFailed: "Kunde inte spara kandidat.",
    titleRequired: "Titel krävs.",
    paperSaved: "Artikel sparad.",
    paperSaveFailed: "Kunde inte spara artikel.",
    confidence: "Konfidens",
    untitledCandidate: "Namnlös kandidat",
    metadataStatus: "Metadatastatus",
    not_started: "Ej påbörjad",
    candidate_found: "Kandidat hittad",
    accepted: "Accepterad",
    not_found: "Ej hittad",
    needs_review: "Behöver granskas",
    markNotFound: "Markera ej hittad",
    markNeedsReview: "Markera behöver granskas",
    statusUpdated: "Status uppdaterad.",
    statusUpdateFailed: "Kunde inte uppdatera status.",
    lastChecked: "Senast kontrollerad",
    discovery: "Discovery",
    dissertationDiscovery: "Avhandlingsdiscovery",
    missingDissertationDiscovery: "Saknade avhandlingar",
    runDiscovery: "Kör discovery",
    discoveryDashboard: "Discoveryöversikt",
    existingTheses: "Befintliga avhandlingar",
    awaitingReview: "Väntar granskning",
    approvedNewTheses: "Godkända nya avhandlingar",
    rejectedCandidates: "Avvisade kandidater",
    activeCandidates: "Aktiva",
    classificationQueue: "Klassificering",
    needsClassification: "Behöver klassificeras",
    noClassificationQueue: "Inga avhandlingar behöver klassificeras.",
    saveClassification: "Spara klassificering",
    classificationSaved: "Klassificering sparad.",
    classificationSaveFailed: "Kunde inte spara klassificering.",
    selectCategory: "Välj huvudtema",
    selectSubcategory: "Välj subtema",
    categoryRequired: "Huvudtema krävs.",
    subcategoryRequired: "Subtema krävs.",
    candidateDetails: "Kandidatdetaljer",
    reviewCandidate: "Granska",
    candidateReview: "Kandidatgranskning",
    sourceUrl: "Käll-URL",
    pdfUrl: "PDF-URL",
    emsMatchReason: "Varför EMS/prehospital",
    yearFrom: "Från år",
    yearTo: "Till år",
    source: "Källa",
    keywordGroup: "Nyckelordsgrupp",
    knownPerson: "Känd person",
    knownPersonPlaceholder: "Namn, DiVA-URL eller diva2-ID",
    allSources: "Alla källor",
    allKeywords: "Alla nyckelord",
    swedishKeywords: "Svenska",
    englishKeywords: "Engelska",
    allMatches: "Nya och möjliga dubbletter",
    newCandidate: "Ny kandidat",
    possibleDuplicate: "Möjlig dubblett",
    alreadyInDatabase: "Finns redan i databasen",
    matchStatus: "Matchstatus",
    relevanceStatus: "Beslut",
    createdThesis: "Skapad avhandling",
    includeAlreadyKnown: "Visa redan kända träffar",
    matchedKeywords: "Matchade nyckelord",
    possibleDuplicateWarning: "Möjlig dubblett",
    matchedExistingThesis: "Matchar befintlig avhandling",
    similarity: "Likhet",
    approve: "Godkänn",
    reject: "Avvisa",
    needsReviewAction: "Behöver granskas",
    approved: "Godkänd",
    rejected: "Avvisad",
    active: "Aktiva",
    approveDuplicateConfirm: "Den här kandidaten är markerad som möjlig dubblett. Vill du ändå skapa en ny avhandling?",
    discoveryStored: "Sparade kandidater",
    skippedKnown: "Hoppade över kända",
    parsedTitle: "Tolkad titel",
    documentType: "Dokumenttyp",
    classification: "Klassificering",
    abstractAvailable: "Abstrakt finns",
    pdfAvailable: "PDF finns",
    includedPapersFound: "Ingående artiklar hittade",
    yes: "Ja",
    no: "Nej",
    someRepositorySearchesFailed: "Vissa repository-sökningar misslyckades",
    showDetails: "Visa detaljer",
    hideDetails: "Dölj detaljer",
    libraryRecordOnly: "Endast bibliotekspost – inget abstrakt/fulltext hittades",
  },
  en: {
    overview: "Statistics",
    theses: "Dissertations",
    researchAreas: "Research areas",
    references: "References",
    admin: "Admin",
    publicMode: "Public mode",
    adminMode: "Admin mode",
    catalogueEyebrow: "Research catalogue",
    homeTitle: "Swedish prehospital doctoral theses",
    homeIntro:
      "A concise overview of dissertations, institutions, professions, and research categories represented in the catalogue.",
    totalTheses: "Dissertations",
    firstYear: "First year",
    lastYear: "Latest year",
    universities: "Universities",
    categories: "Categories",
    byUniversity: "By university",
    byProfession: "By profession",
    byCategory: "By category",
    byYear: "By year",
    allTheses: "All dissertations",
    results: "results",
    category: "Category",
    university: "University",
    profession: "Profession",
    selectProfession: "Select profession",
    addNewProfession: "Add new profession",
    newProfession: "New profession",
    professionRequired: "Profession is required.",
    confirmCreateProfession: "Create new profession?",
    year: "Year",
    all: "All",
    backToAllTheses: "Back to all dissertations",
    backToTheses: "Back to dissertations",
    author: "Author",
    subcategory: "Subcategory",
    digitalThesis: "Digital dissertation",
    abstract: "Abstract",
    dissertationUrl: "Dissertation record",
    openDissertationRecord: "Open dissertation record",
    openPdf: "Open PDF",
    includedPapers: "Included papers",
    editMetadata: "Edit metadata",
    saveMetadata: "Save metadata",
    findDigitalMetadata: "Find digital metadata",
    candidatesManual: "Candidates are never applied without approval.",
    lookupFromUrl: "Lookup from URL",
    pasteDissertationUrl: "Paste a dissertation record URL",
    extractMetadata: "Extract metadata",
    extractedMetadata: "Extracted metadata",
    currentValue: "Current",
    extractedValue: "Extracted",
    copyField: "Copy",
    acceptAllFields: "Use all fields",
    parserUsed: "Parser",
    missingFields: "Missing fields",
    noMissingFields: "No missing fields",
    useMetadata: "Use this metadata",
    addIncludedPaper: "Add included paper",
    title: "Title",
    journal: "Journal",
    savePaper: "Save paper",
    showMore: "Show more",
    showLess: "Show less",
    showArea: "Show area",
    reportThemes: "Report themes",
    allResearchAreas: "All research areas",
    mainCategory: "Main category",
    subcategoryLabel: "Subcategory",
    overviewTab: "Overview",
    publications: "Publications",
    reportSources: "Report sources",
    referencesCount: "references",
    researchAreasCount: "areas",
    noDigitalMetadata: "Digital metadata has not been added yet.",
    loadingOverview: "Loading statistics...",
    loadingTheses: "Loading dissertations...",
    loadingResearchAreas: "Loading research areas...",
    loadingReferences: "Loading references...",
    loadingPapers: "Loading included papers...",
    loading: "Loading...",
    couldNotLoadOverview: "Could not load statistics.",
    couldNotLoadData: "Could not load data.",
    couldNotLoadTheses: "Could not load dissertations.",
    couldNotLoadResearchAreas: "Could not load research areas.",
    couldNotLoadReferences: "Could not load references.",
    couldNotLoadPapers: "Could not load included papers.",
    noNarrative: "No narrative text has been imported for this subcategory.",
    noLinkedTheses: "No dissertations are linked to this subcategory.",
    publicationsLater: "Publications will be added in a later version.",
    searching: "Searching...",
    fetchingUrl: "Fetching metadata from URL...",
    noCandidates: "No candidates found.",
    lookupFailed: "Could not search metadata.",
    urlLookupFailed: "Could not fetch metadata from URL.",
    saving: "Saving...",
    saved: "Saved.",
    saveFailed: "Could not save metadata.",
    savingCandidate: "Saving candidate...",
    candidateSaved: "Candidate saved.",
    candidateSaveFailed: "Could not save candidate.",
    titleRequired: "Title is required.",
    paperSaved: "Paper saved.",
    paperSaveFailed: "Could not save paper.",
    confidence: "Confidence",
    untitledCandidate: "Untitled candidate",
    metadataStatus: "Metadata status",
    not_started: "Not started",
    candidate_found: "Candidate found",
    accepted: "Accepted",
    not_found: "Not found",
    needs_review: "Needs review",
    markNotFound: "Mark not found",
    markNeedsReview: "Mark needs review",
    statusUpdated: "Status updated.",
    statusUpdateFailed: "Could not update status.",
    lastChecked: "Last checked",
    discovery: "Discovery",
    dissertationDiscovery: "Dissertation discovery",
    missingDissertationDiscovery: "Missing dissertations",
    runDiscovery: "Run discovery",
    discoveryDashboard: "Discovery dashboard",
    existingTheses: "Existing theses",
    awaitingReview: "Awaiting review",
    approvedNewTheses: "Approved new theses",
    rejectedCandidates: "Rejected candidates",
    activeCandidates: "Active",
    classificationQueue: "Classification",
    needsClassification: "Needs classification",
    noClassificationQueue: "No theses need classification.",
    saveClassification: "Save classification",
    classificationSaved: "Classification saved.",
    classificationSaveFailed: "Could not save classification.",
    selectCategory: "Select category",
    selectSubcategory: "Select subcategory",
    categoryRequired: "Category is required.",
    subcategoryRequired: "Subcategory is required.",
    candidateDetails: "Candidate details",
    reviewCandidate: "Review",
    candidateReview: "Candidate review",
    sourceUrl: "Source URL",
    pdfUrl: "PDF URL",
    emsMatchReason: "Why EMS/prehospital",
    yearFrom: "From year",
    yearTo: "To year",
    source: "Source",
    keywordGroup: "Keyword group",
    knownPerson: "Known person",
    knownPersonPlaceholder: "Name, DiVA URL or diva2 ID",
    allSources: "All sources",
    allKeywords: "All keywords",
    swedishKeywords: "Swedish",
    englishKeywords: "English",
    allMatches: "New and possible duplicates",
    newCandidate: "New candidate",
    possibleDuplicate: "Possible duplicate",
    alreadyInDatabase: "Already in database",
    matchStatus: "Match status",
    relevanceStatus: "Decision",
    createdThesis: "Created thesis",
    includeAlreadyKnown: "Show already known matches",
    matchedKeywords: "Matched keywords",
    possibleDuplicateWarning: "Possible duplicate",
    matchedExistingThesis: "Matches existing thesis",
    similarity: "Similarity",
    approve: "Approve",
    reject: "Reject",
    needsReviewAction: "Needs review",
    approved: "Approved",
    rejected: "Rejected",
    active: "Active",
    approveDuplicateConfirm: "This candidate is marked as a possible duplicate. Create a new thesis anyway?",
    discoveryStored: "Stored candidates",
    skippedKnown: "Skipped known",
    parsedTitle: "Parsed title",
    documentType: "Document type",
    classification: "Classification",
    abstractAvailable: "Abstract available",
    pdfAvailable: "PDF available",
    includedPapersFound: "Included papers found",
    yes: "Yes",
    no: "No",
    someRepositorySearchesFailed: "Some repository searches failed",
    showDetails: "Show details",
    hideDetails: "Hide details",
    libraryRecordOnly: "Library record only – no abstract/fulltext found",
  },
};

const metadataStatusOptions = [
  "not_started",
  "candidate_found",
  "accepted",
  "not_found",
  "needs_review",
];

const overviewFields = [
  ["total_theses", "totalTheses"],
  ["first_year", "firstYear"],
  ["last_year", "lastYear"],
  ["universities", "universities"],
  ["categories", "categories"],
];

const statsConfig = [
  ["byUniversity", "byUniversity"],
  ["byProfession", "byProfession"],
  ["byCategory", "byCategory"],
  ["byYear", "byYear"],
];

function navigate(path, isAdmin = false) {
  const nextPath = isAdmin ? adminPath(path) : path;
  window.history.pushState({}, "", nextPath);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function adminPath(path) {
  if (path === "/") return "/admin";
  return `/admin${path}`;
}

function statisticsPath(isAdmin) {
  return isAdmin ? "/admin/statistics" : "/";
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
  const [language, setLanguageState] = useState(() => localStorage.getItem("language") || "sv");
  const isAdmin = path === "/admin" || path.startsWith("/admin/");
  const adminContentPath = path.replace(/^\/admin/, "");
  const contentPath = isAdmin
    ? adminContentPath === "/statistics"
      ? "/"
      : adminContentPath || "/theses"
    : path;
  const detailMatch = contentPath.match(/^\/theses\/(\d+)$/);
  const filteredMatch = contentPath.match(/^\/(year|university|profession|category)\/(.+)$/);
  const researchAreaMatch = contentPath.match(/^\/research-areas\/([A-I])$/);
  const t = (key) => translations[language]?.[key] ?? translations.sv[key] ?? key;

  function setLanguage(nextLanguage) {
    localStorage.setItem("language", nextLanguage);
    setLanguageState(nextLanguage);
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <button className="brand" onClick={() => navigate("/", isAdmin)}>
          Prehospitala Avhandlingar
        </button>
        <nav aria-label="Primary navigation">
          <button
            className={contentPath === "/" ? "active" : ""}
            onClick={() => navigate(statisticsPath(isAdmin))}
          >
            {t("overview")}
          </button>
          <button
            className={contentPath.startsWith("/theses") || filteredMatch ? "active" : ""}
            onClick={() => navigate("/theses", isAdmin)}
          >
            {t("theses")}
          </button>
          <button
            className={contentPath.startsWith("/research-areas") ? "active" : ""}
            onClick={() => navigate("/research-areas", isAdmin)}
          >
            {t("researchAreas")}
          </button>
          <button
            className={contentPath === "/references" ? "active" : ""}
            onClick={() => navigate("/references", isAdmin)}
          >
            {t("references")}
          </button>
          {isAdmin && (
            <button
              className={contentPath === "/discovery" ? "active" : ""}
              onClick={() => navigate("/discovery", true)}
            >
              {t("discovery")}
            </button>
          )}
          {isAdmin && (
            <button
              className={contentPath === "/classification" ? "active" : ""}
              onClick={() => navigate("/classification", true)}
            >
              {t("classificationQueue")}
            </button>
          )}
        </nav>
        <div className="header-actions">
          <button className={isAdmin ? "active" : ""} onClick={() => navigate("/theses", !isAdmin)}>
            {isAdmin ? t("publicMode") : t("admin")}
          </button>
          <div className="language-toggle" aria-label="Language">
            <button className={language === "sv" ? "active" : ""} onClick={() => setLanguage("sv")}>
              SV
            </button>
            <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>
              EN
            </button>
          </div>
        </div>
      </header>

      <main>
        {isAdmin && <p className="admin-banner">{t("adminMode")}</p>}
        {contentPath === "/" && <HomePage t={t} />}
        {contentPath === "/theses" && <ThesesPage isAdmin={isAdmin} t={t} />}
        {contentPath === "/research-areas" && <ResearchAreasPage isAdmin={isAdmin} t={t} />}
        {researchAreaMatch && <ResearchAreasPage categoryId={researchAreaMatch[1]} isAdmin={isAdmin} t={t} />}
        {contentPath === "/references" && <ReferencesPage t={t} />}
        {isAdmin && contentPath === "/discovery" && <DiscoveryPage t={t} />}
        {isAdmin && contentPath === "/classification" && <ClassificationPage t={t} />}
        {detailMatch && <ThesisDetail isAdmin={isAdmin} runningNumber={detailMatch[1]} t={t} />}
        {filteredMatch && (
          <FilteredThesesPage
            filterType={filteredMatch[1]}
            filterValue={decodeURIComponent(filteredMatch[2])}
            isAdmin={isAdmin}
            t={t}
          />
        )}
      </main>
    </div>
  );
}

function HomePage({ t }) {
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
      title: t("byUniversity"),
      getPath: (row) => `/university/${encodePathValue(row.label)}`,
      ...byUniversity,
    },
    byProfession: {
      title: t("byProfession"),
      getPath: (row) => `/profession/${encodePathValue(row.label)}`,
      ...byProfession,
    },
    byCategory: {
      title: t("byCategory"),
      getPath: (row) => `/category/${encodePathValue(categoryIdsByName[row.label] ?? row.label)}`,
      ...byCategory,
    },
    byYear: {
      title: t("byYear"),
      getPath: (row) => `/year/${encodePathValue(row.label)}`,
      sortRows: (rows) => [...rows].sort((a, b) => Number(b.label) - Number(a.label)),
      scrollable: true,
      ...byYear,
    },
  };

  return (
    <>
      <section className="intro">
        <p className="eyebrow">{t("catalogueEyebrow")}</p>
        <h1>{t("homeTitle")}</h1>
        <p>{t("homeIntro")}</p>
      </section>

      <section className="overview-grid" aria-label="Overview statistics">
        {overview.loading && <Status message={t("loadingOverview")} />}
        {overview.error && <Status message={t("couldNotLoadOverview")} />}
        {overview.data &&
          overviewFields.map(([key, labelKey]) => (
            <article className="stat-card" key={key}>
              <span>{t(labelKey)}</span>
              <strong>{overview.data[key] ?? "-"}</strong>
            </article>
          ))}
      </section>

      <section className="stats-grid" aria-label="Descriptive statistics">
        {statsConfig.map(([key]) => (
          <StatsPanel key={key} state={stats[key]} t={t} />
        ))}
      </section>
    </>
  );
}

function StatsPanel({ state, t }) {
  const rows = state.sortRows ? state.sortRows(state.data ?? []) : state.data ?? [];
  const max = Math.max(...rows.map((row) => row.count), 1);
  const visibleRows = state.scrollable ? rows : rows.slice(0, 10);

  return (
    <article className={`panel ${state.scrollable ? "panel-scroll" : ""}`}>
      <h2>{state.title}</h2>
      {state.loading && <Status message={t("loading")} />}
      {state.error && <Status message={t("couldNotLoadData")} />}
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

function ThesesPage({ isAdmin, t }) {
  const { data: theses, loading, error } = useApi("/theses");
  const { data: categories } = useApi("/categories");
  const [filters, setFilters] = useState({
    category: "",
    university: "",
    profession: "",
    year: "",
    metadata_status: "",
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
        matchesFilter(thesis.year, filters.year) &&
        (!isAdmin || matchesFilter(metadataStatus(thesis), filters.metadata_status))
      );
    });
  }, [isAdmin, theses, filters]);

  return (
    <section className="page-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("catalogueEyebrow")}</p>
          <h1>{t("allTheses")}</h1>
        </div>
        <span className="result-count">{filtered.length} {t("results")}</span>
      </div>

      {loading && <Status message={t("loadingTheses")} />}
      {error && <Status message={t("couldNotLoadTheses")} />}
      {theses && (
        <>
          <div className="filters" aria-label="Thesis filters">
            <SelectFilter
              label={t("category")}
              value={filters.category}
              options={options.category}
              onChange={(value) => setFilters((current) => ({ ...current, category: value }))}
              t={t}
            />
            <SelectFilter
              label={t("university")}
              value={filters.university}
              options={options.university}
              onChange={(value) => setFilters((current) => ({ ...current, university: value }))}
              t={t}
            />
            <SelectFilter
              label={t("profession")}
              value={filters.profession}
              options={options.profession}
              onChange={(value) => setFilters((current) => ({ ...current, profession: value }))}
              t={t}
            />
            <SelectFilter
              label={t("year")}
              value={filters.year}
              options={options.year}
              onChange={(value) => setFilters((current) => ({ ...current, year: value }))}
              t={t}
            />
            {isAdmin && (
              <SelectFilter
                label={t("metadataStatus")}
                value={filters.metadata_status}
                options={metadataStatusOptions.map((status) => ({
                  value: status,
                  label: t(status),
                }))}
                onChange={(value) =>
                  setFilters((current) => ({ ...current, metadata_status: value }))
                }
                t={t}
              />
            )}
          </div>

          <ThesisList isAdmin={isAdmin} t={t} theses={filtered} />
        </>
      )}
    </section>
  );
}

function FilteredThesesPage({ filterType, filterValue, isAdmin, t }) {
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
    year: t("year"),
    university: t("university"),
    profession: t("profession"),
    category: t("category"),
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
      <button className="back-button" onClick={() => navigate("/theses", isAdmin)}>
        {t("backToAllTheses")}
      </button>

      <div className="section-heading filtered-heading">
        <div>
          <p className="eyebrow">{label}</p>
          <h1>{heading}</h1>
        </div>
        <span className="result-count">{filtered.length} {t("results")}</span>
      </div>

      {loading && <Status message={t("loadingTheses")} />}
      {error && <Status message={t("couldNotLoadTheses")} />}
      {theses && <ThesisList isAdmin={isAdmin} t={t} theses={filtered} />}
    </section>
  );
}

function ThesisList({ isAdmin = false, t, theses }) {
  const sortedTheses = useMemo(() => sortTheses(theses), [theses]);
  return (
    <div className="thesis-list">
      {sortedTheses.map((thesis) => (
        <button
          className={`thesis-row ${isAdmin ? "thesis-row-admin" : ""}`}
          key={thesis.running_number}
          onClick={() => navigate(`/theses/${thesis.running_number}`, isAdmin)}
        >
          <span className="thesis-number">#{thesis.running_number}</span>
          <span className="thesis-main">
            <strong>{thesis.title}</strong>
            <span>
              {thesis.author} · {thesis.university} · {thesis.year}
            </span>
          </span>
          <span className="thesis-meta">{thesis.profession}</span>
          {isAdmin && (
            <span className={`metadata-status-badge status-${metadataStatus(thesis)}`}>
              {t(metadataStatus(thesis))}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

function ResearchAreasPage({ categoryId, isAdmin, t }) {
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
        <button className="back-button" onClick={() => navigate("/research-areas", isAdmin)}>
          {t("allResearchAreas")}
        </button>
      )}

      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("reportThemes")}</p>
          <h1>{t("researchAreas")}</h1>
        </div>
        {areas.length > 0 && <span className="result-count">{areas.length} {t("researchAreasCount")}</span>}
      </div>

      {loading && <Status message={t("loadingResearchAreas")} />}
      {error && <Status message={t("couldNotLoadResearchAreas")} />}
      {!loading && !error && (
        <div className="research-area-list">
          {areas.map((area) => (
            <ResearchAreaSection
              key={area.id}
              area={area}
              authorLinks={authorLinks}
              isAdmin={isAdmin}
              singleCategory={Boolean(categoryId)}
              t={t}
            />
          ))}
        </div>
      )}
    </section>
  );
}

function ResearchAreaSection({ area, authorLinks, isAdmin, singleCategory, t }) {
  return (
    <article className="research-area" id={`category-${area.id}`}>
      <div className="research-area-heading">
        <div>
          <p className="eyebrow">{t("mainCategory")} {area.id}</p>
          <h2>{area.name}</h2>
        </div>
        {!singleCategory && (
          <button className="text-link-button" onClick={() => navigate(`/research-areas/${area.id}`, isAdmin)}>
            {t("showArea")}
          </button>
        )}
      </div>

      {area.narrative_text && (
        <NarrativeText authorLinks={authorLinks} collapsible linkCitations t={t} text={area.narrative_text} />
      )}

      {area.subcategories.length > 0 && (
        <div className="subcategory-list">
          {area.subcategories.map((subcategory) => (
            <SubcategoryCard
              key={subcategory.id}
              authorLinks={authorLinks}
              isAdmin={isAdmin}
              subcategory={subcategory}
              t={t}
            />
          ))}
        </div>
      )}
    </article>
  );
}

function SubcategoryCard({ authorLinks, isAdmin, subcategory, t }) {
  const [tab, setTab] = useState("overview");

  return (
    <article className="subcategory-card" id={`subcategory-${subcategory.id}`}>
      <div className="subcategory-heading">
        <div>
          <p className="eyebrow">{t("subcategoryLabel")} {subcategory.id}</p>
          <h3>{subcategory.name}</h3>
        </div>
      </div>

      <div className="tab-list" role="tablist" aria-label={`${subcategory.id} sections`}>
        <button
          className={tab === "overview" ? "active" : ""}
          onClick={() => setTab("overview")}
          type="button"
        >
          {t("overviewTab")}
        </button>
        <button
          className={tab === "theses" ? "active" : ""}
          onClick={() => setTab("theses")}
          type="button"
        >
          {t("theses")}
        </button>
        <button
          className={tab === "publications" ? "active" : ""}
          onClick={() => setTab("publications")}
          type="button"
        >
          {t("publications")}
        </button>
      </div>

      {tab === "overview" && (
        <div className="tab-panel">
          {subcategory.narrative_text ? (
            <NarrativeText
              authorLinks={authorLinks}
              collapsible
              linkCitations
              t={t}
              text={subcategory.narrative_text}
            />
          ) : (
            <Status message={t("noNarrative")} />
          )}
        </div>
      )}
      {tab === "theses" && (
        <div className="tab-panel">
          {subcategory.theses.length > 0 ? (
            <ThesisList isAdmin={isAdmin} t={t} theses={subcategory.theses} />
          ) : (
            <Status message={t("noLinkedTheses")} />
          )}
        </div>
      )}
      {tab === "publications" && (
        <div className="tab-panel">
          <p className="placeholder-text">{t("publicationsLater")}</p>
        </div>
      )}
    </article>
  );
}

function ReferencesPage({ t }) {
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
          <p className="eyebrow">{t("reportSources")}</p>
          <h1>{t("references")}</h1>
        </div>
        {references && <span className="result-count">{references.length} {t("referencesCount")}</span>}
      </div>

      {loading && <Status message={t("loadingReferences")} />}
      {error && <Status message={t("couldNotLoadReferences")} />}
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

function DiscoveryPage({ t }) {
  const currentYear = new Date().getFullYear();
  const [searchForm, setSearchForm] = useState({
    year_from: "2024",
    year_to: String(currentYear),
    source: "all",
    keyword_group: "all",
    known_person: "",
    university: "",
  });
  const [filters, setFilters] = useState({
    status_filter: "active",
  });
  const [summary, setSummary] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [status, setStatus] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [includeKnownResults, setIncludeKnownResults] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams();
    params.set("status_filter", filters.status_filter);
    params.set("include_known", includeKnownResults ? "true" : "false");

    fetchJson(`/discovery/candidates?${params.toString()}`)
      .then((data) => {
        setCandidates(data);
        setSelectedCandidate((current) =>
          current && data.some((candidate) => candidate.id === current.id) ? current : null
        );
      })
      .catch(() => setStatus(t("couldNotLoadData")));
    fetchJson("/discovery/summary")
      .then((data) => setSummary(data))
      .catch(() => setStatus(t("couldNotLoadData")));
  }, [filters, includeKnownResults, reloadKey]);

  async function handleSearch(event) {
    event.preventDefault();
    setStatus(t("searching"));
    const isKnownPersonSearch = Boolean(searchForm.known_person.trim());
    try {
      const result = await sendJson("/discovery/search", "POST", {
        ...searchForm,
        show_known_matches: isKnownPersonSearch,
      });
      setIncludeKnownResults(isKnownPersonSearch);
      setStatus(
        result.errors?.length && !result.discovered
          ? t("someRepositorySearchesFailed")
          : `${t("discoveryStored")}: ${result.stored}. ${t("skippedKnown")}: ${result.skipped_known}.${
              result.errors?.length ? ` ${t("someRepositorySearchesFailed")}` : ""
            }`
      );
      setReloadKey((current) => current + 1);
    } catch {
      setStatus(t("lookupFailed"));
    }
  }

  async function updateCandidate(candidate, reviewStatus) {
    const confirmDuplicate =
      reviewStatus === "approved" &&
      candidate.match_status === "possible_duplicate" &&
      window.confirm(t("approveDuplicateConfirm"));
    if (
      reviewStatus === "approved" &&
      candidate.match_status === "possible_duplicate" &&
      !confirmDuplicate
    ) {
      return;
    }

    try {
      const saved = await sendJson(`/discovery/candidates/${candidate.id}`, "PATCH", {
        review_status: reviewStatus,
        confirm_duplicate: Boolean(confirmDuplicate),
      });
      const shouldHide =
        filters.status_filter === "active" &&
        (saved.relevance_status === "approved" || saved.relevance_status === "rejected");
      setCandidates((current) =>
        shouldHide
          ? current.filter((item) => item.id !== candidate.id)
          : current.map((item) => (item.id === candidate.id ? saved : item))
      );
      setSelectedCandidate((current) => {
        if (!current || current.id !== candidate.id) return current;
        return shouldHide ? null : saved;
      });
      setReloadKey((current) => current + 1);
    } catch {
      setStatus(t("statusUpdateFailed"));
    }
  }

  return (
    <section className="page-section discovery-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("adminMode")}</p>
          <h1>{t("missingDissertationDiscovery")}</h1>
        </div>
        <span className="result-count">{candidates.length} {t("results")}</span>
      </div>

      {summary && (
        <div className="discovery-dashboard" aria-label={t("discoveryDashboard")}>
          <SummaryTile label={t("existingTheses")} value={summary.existing_theses} />
          <SummaryTile label={t("awaitingReview")} value={summary.awaiting_review} />
          <SummaryTile label={t("approvedNewTheses")} value={summary.approved_new_theses} />
          <SummaryTile label={t("rejectedCandidates")} value={summary.rejected_candidates} />
          <SummaryTile label={t("possibleDuplicate")} value={summary.possible_duplicates} />
        </div>
      )}

      <form className="discovery-controls" onSubmit={handleSearch}>
        <label>
          <span>{t("yearFrom")}</span>
          <input
            inputMode="numeric"
            value={searchForm.year_from}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, year_from: event.target.value }))
            }
          />
        </label>
        <label>
          <span>{t("yearTo")}</span>
          <input
            inputMode="numeric"
            value={searchForm.year_to}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, year_to: event.target.value }))
            }
          />
        </label>
        <label>
          <span>{t("source")}</span>
          <select
            value={searchForm.source}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, source: event.target.value }))
            }
          >
            <option value="all">{t("allSources")}</option>
            <option value="diva">DiVA</option>
            <option value="swepub">SwePub</option>
            <option value="libris">LIBRIS</option>
            <option value="avhandlingar">avhandlingar.se</option>
          </select>
        </label>
        <label>
          <span>{t("keywordGroup")}</span>
          <select
            value={searchForm.keyword_group}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, keyword_group: event.target.value }))
            }
          >
            <option value="all">{t("allKeywords")}</option>
            <option value="swedish">{t("swedishKeywords")}</option>
            <option value="english">{t("englishKeywords")}</option>
          </select>
        </label>
        <label className="wide-control">
          <span>{t("knownPerson")}</span>
          <input
            placeholder={t("knownPersonPlaceholder")}
            value={searchForm.known_person}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, known_person: event.target.value }))
            }
          />
        </label>
        <label>
          <span>{t("university")}</span>
          <input
            value={searchForm.university}
            onChange={(event) =>
              setSearchForm((current) => ({ ...current, university: event.target.value }))
            }
          />
        </label>
        <div className="form-actions">
          <button className="primary-button" type="submit">{t("runDiscovery")}</button>
        </div>
      </form>

      <div className="discovery-filters discovery-tabs" aria-label={t("metadataStatus")}>
        {[
          ["active", t("active")],
          ["approved", t("approved")],
          ["rejected", t("rejected")],
          ["all", t("all")],
        ].map(([value, label]) => (
          <button
            className={filters.status_filter === value ? "active" : ""}
            key={value}
            onClick={() => setFilters({ status_filter: value })}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      {status && <p className="status">{status}</p>}

      {selectedCandidate && (
        <CandidateReviewPanel
          candidate={selectedCandidate}
          onApprove={() => updateCandidate(selectedCandidate, "approved")}
          onNeedsReview={() => updateCandidate(selectedCandidate, "needs_review")}
          onReject={() => updateCandidate(selectedCandidate, "rejected")}
          t={t}
        />
      )}

      <div className="candidate-list">
        {candidates.map((candidate) => (
          <article className="candidate-card" key={candidate.id}>
            <div className="candidate-heading">
              <div>
                <h4>{candidate.title}</h4>
                <p className="paper-meta">
                  {[candidate.author, candidate.university, candidate.year, candidate.source]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              </div>
              <span className={`metadata-status-badge status-${candidate.match_status}`}>
                {discoveryMatchLabel(candidate.match_status, t)}
              </span>
            </div>
            <p className="paper-meta">
              {t("matchedKeywords")}: {(candidate.matched_keywords ?? []).join(", ") || "-"}
            </p>
            <dl className="candidate-detail-list">
              <div>
                <dt>{t("title")}</dt>
                <dd>{candidate.title || "-"}</dd>
              </div>
              <div>
                <dt>{t("author")}</dt>
                <dd>{candidate.author || "-"}</dd>
              </div>
              <div>
                <dt>{t("year")}</dt>
                <dd>{candidate.year || "-"}</dd>
              </div>
              <div>
                <dt>{t("university")}</dt>
                <dd>{candidate.university || "-"}</dd>
              </div>
              <div>
                <dt>{t("source")}</dt>
                <dd>{[candidate.source, candidate.source_host].filter(Boolean).join(" · ") || "-"}</dd>
              </div>
              {candidate.publication_type && (
                <div>
                  <dt>{t("documentType")}</dt>
                  <dd>{candidate.publication_type}</dd>
                </div>
              )}
              <div>
                <dt>{t("sourceUrl")}</dt>
                <dd>
                  {candidate.source_url ? (
                    <a href={candidate.source_url} target="_blank" rel="noreferrer">
                      {candidate.source_url}
                    </a>
                  ) : (
                    "-"
                  )}
                </dd>
              </div>
              <div>
                <dt>{t("emsMatchReason")}</dt>
                <dd>{candidate.ems_match_reason || "-"}</dd>
              </div>
            </dl>
            {candidate.match_status === "possible_duplicate" && (
              <p className="duplicate-warning">
                {t("possibleDuplicateWarning")}: {t("similarity")} {candidate.similarity_to_existing}
                {candidate.matched_existing_running_number &&
                  ` · ${t("matchedExistingThesis")} #${candidate.matched_existing_running_number}`}
              </p>
            )}
            {candidate.match_status === "already_in_database" && (
              <p className="duplicate-warning">
                {t("alreadyInDatabase")}
                {candidate.matched_existing_running_number &&
                  ` · #${candidate.matched_existing_running_number}`}
              </p>
            )}
            <div className="form-actions">
              <button
                className="primary-button"
                disabled={candidate.match_status === "already_in_database"}
                onClick={() => updateCandidate(candidate, "approved")}
                type="button"
              >
                {t("approve")}
              </button>
              <button
                className="secondary-button"
                onClick={() => setSelectedCandidate(candidate)}
                type="button"
              >
                {t("reviewCandidate")}
              </button>
              <button
                className="secondary-button"
                onClick={() => updateCandidate(candidate, "needs_review")}
                type="button"
              >
                {t("needsReviewAction")}
              </button>
              <button
                className="secondary-button"
                onClick={() => updateCandidate(candidate, "rejected")}
                type="button"
              >
                {t("reject")}
              </button>
              <span className="form-status">{reviewStatusLabel(candidate.review_status, t)}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function SummaryTile({ label, value }) {
  return (
    <div className="summary-tile">
      <strong>{value ?? 0}</strong>
      <span>{label}</span>
    </div>
  );
}

function CandidateReviewPanel({ candidate, onApprove, onNeedsReview, onReject, t }) {
  return (
    <article className="candidate-review-panel">
      <div className="candidate-heading">
        <div>
          <p className="eyebrow">{t("candidateReview")}</p>
          <h3>{candidate.title}</h3>
          <p className="paper-meta">
            {[candidate.author, candidate.university, candidate.year, candidate.source]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <span className={`metadata-status-badge status-${candidate.match_status}`}>
          {discoveryMatchLabel(candidate.match_status, t)}
        </span>
      </div>

      <dl className="candidate-detail-list">
        <div>
          <dt>{t("title")}</dt>
          <dd>{candidate.title || "-"}</dd>
        </div>
        <div>
          <dt>{t("author")}</dt>
          <dd>{candidate.author || "-"}</dd>
        </div>
        <div>
          <dt>{t("year")}</dt>
          <dd>{candidate.year || "-"}</dd>
        </div>
        <div>
          <dt>{t("university")}</dt>
          <dd>{candidate.university || "-"}</dd>
        </div>
        <div>
          <dt>{t("source")}</dt>
          <dd>{[candidate.source, candidate.source_host].filter(Boolean).join(" · ") || "-"}</dd>
        </div>
        <div>
          <dt>{t("sourceUrl")}</dt>
          <dd>
            {candidate.source_url ? (
              <a href={candidate.source_url} target="_blank" rel="noreferrer">
                {candidate.source_url}
              </a>
            ) : (
              "-"
            )}
          </dd>
        </div>
        <div>
          <dt>{t("pdfUrl")}</dt>
          <dd>
            {candidate.pdf_url ? (
              <a href={candidate.pdf_url} target="_blank" rel="noreferrer">
                {candidate.pdf_url}
              </a>
            ) : (
              "-"
            )}
          </dd>
        </div>
        <div>
          <dt>{t("abstract")}</dt>
          <dd>{candidate.abstract || "-"}</dd>
        </div>
        <div>
          <dt>{t("matchedKeywords")}</dt>
          <dd>{(candidate.matched_keywords ?? []).join(", ") || "-"}</dd>
        </div>
        <div>
          <dt>{t("emsMatchReason")}</dt>
          <dd>{candidate.ems_match_reason || "-"}</dd>
        </div>
        <div>
          <dt>{t("matchStatus")}</dt>
          <dd>{discoveryMatchLabel(candidate.match_status, t)}</dd>
        </div>
        <div>
          <dt>{t("similarity")}</dt>
          <dd>{candidate.similarity_to_existing ?? "-"}</dd>
        </div>
        <div>
          <dt>{t("matchedExistingThesis")}</dt>
          <dd>{candidate.matched_existing_running_number ? `#${candidate.matched_existing_running_number}` : "-"}</dd>
        </div>
        <div>
          <dt>{t("relevanceStatus")}</dt>
          <dd>{reviewStatusLabel(candidate.relevance_status || candidate.review_status, t)}</dd>
        </div>
        <div>
          <dt>{t("createdThesis")}</dt>
          <dd>{candidate.created_thesis_running_number ? `#${candidate.created_thesis_running_number}` : "-"}</dd>
        </div>
      </dl>

      <div className="form-actions">
        <button
          className="primary-button"
          disabled={candidate.match_status === "already_in_database"}
          onClick={onApprove}
          type="button"
        >
          {t("approve")}
        </button>
        <button className="secondary-button" onClick={onNeedsReview} type="button">
          {t("needsReviewAction")}
        </button>
        <button className="secondary-button" onClick={onReject} type="button">
          {t("reject")}
        </button>
      </div>
    </article>
  );
}

function ProfessionSelect({ allowNew, onChange, professions = [], t, value }) {
  const knownValue = professions.find(
    (profession) => professionKey(profession) === professionKey(value)
  );
  const selectValue = allowNew || (value && !knownValue) ? "__new__" : knownValue || value || "";

  return (
    <div className="profession-select">
      <label>
        <span>{t("profession")}</span>
        <select
          value={selectValue}
          onChange={(event) => {
            const next = event.target.value;
            if (next === "__new__") {
              onChange("", true);
            } else {
              onChange(next, false);
            }
          }}
        >
          <option value="">{t("selectProfession")}</option>
          {professions.map((profession) => (
            <option key={profession} value={profession}>
              {profession}
            </option>
          ))}
          <option value="__new__">{t("addNewProfession")}</option>
        </select>
      </label>
      {(allowNew || (value && !knownValue)) && (
        <label>
          <span>{t("newProfession")}</span>
          <input
            value={value}
            onChange={(event) => onChange(event.target.value, true)}
          />
        </label>
      )}
    </div>
  );
}

function ClassificationPage({ t }) {
  const [reloadKey, setReloadKey] = useState(0);
  const queueRequest = useApi(`/theses/needs-classification?reload=${reloadKey}`);
  const optionsRequest = useApi("/classification/options");
  const professionsRequest = useApi("/professions");
  const [queue, setQueue] = useState([]);
  const [form, setForm] = useState({
    category_id: "",
    subcategory_id: "",
    profession: "",
    allow_new_profession: false,
  });
  const [validation, setValidation] = useState("");
  const [status, setStatus] = useState("");

  useEffect(() => {
    setQueue(queueRequest.data ?? []);
    setForm({
      category_id: "",
      subcategory_id: "",
      profession: "",
      allow_new_profession: false,
    });
    setValidation("");
  }, [queueRequest.data]);

  const thesis = queue[0];
  const categories = optionsRequest.data ?? [];
  const selectedCategory = categories.find((category) => category.id === form.category_id);
  const subcategories = selectedCategory?.subcategories ?? [];

  function updateCategory(categoryId) {
    setForm({ category_id: categoryId, subcategory_id: "" });
    setValidation("");
  }

  function updateSubcategory(subcategoryId) {
    setForm((current) => ({ ...current, subcategory_id: subcategoryId }));
    setValidation("");
  }

  function updateProfession(profession, allowNewProfession) {
    setForm((current) => ({
      ...current,
      profession,
      allow_new_profession: allowNewProfession,
    }));
    setValidation("");
  }

  async function saveClassification(event) {
    event.preventDefault();
    const profession = cleanProfession(form.profession);
    const isNewProfession =
      profession &&
      form.allow_new_profession &&
      !(professionsRequest.data ?? []).some(
        (existing) => professionKey(existing) === professionKey(profession)
      );
    if (!profession) {
      setValidation(t("professionRequired"));
      return;
    }
    if (!form.category_id) {
      setValidation(t("categoryRequired"));
      return;
    }
    if (!form.subcategory_id) {
      setValidation(t("subcategoryRequired"));
      return;
    }
    if (isNewProfession && !window.confirm(`${t("confirmCreateProfession")} ${form.profession.trim()}`)) {
      return;
    }

    setStatus(t("saving"));
    try {
      await sendJson(`/theses/${thesis.running_number}/classification`, "PATCH", {
        ...form,
        profession,
      });
      setStatus(t("classificationSaved"));
      setQueue((current) => current.slice(1));
      setForm({
        category_id: "",
        subcategory_id: "",
        profession: "",
        allow_new_profession: false,
      });
      setValidation("");
      setReloadKey((current) => current + 1);
    } catch {
      setStatus(t("classificationSaveFailed"));
    }
  }

  return (
    <section className="page-section classification-page">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("adminMode")}</p>
          <h1>{t("needsClassification")}</h1>
        </div>
        <span className="result-count">{queue.length} {t("results")}</span>
      </div>

      {(queueRequest.loading || optionsRequest.loading || professionsRequest.loading) && (
        <Status message={t("loading")} />
      )}
      {(queueRequest.error || optionsRequest.error || professionsRequest.error) && (
        <Status message={t("couldNotLoadData")} />
      )}

      {!queueRequest.loading && !optionsRequest.loading && !professionsRequest.loading && !thesis && (
        <p className="placeholder-text">{t("noClassificationQueue")}</p>
      )}

      {thesis && (
        <article className="classification-work-item">
          <div className="candidate-heading">
            <div>
              <p className="eyebrow">
                {t("theses")} #{thesis.running_number}
              </p>
              <h2>{thesis.title}</h2>
              <p className="paper-meta">
                {[thesis.author, thesis.university, thesis.year, thesis.source]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <span className="metadata-status-badge status-needs_review">
              {t("needsClassification")}
            </span>
          </div>

          <dl className="candidate-detail-list">
            <div>
              <dt>{t("title")}</dt>
              <dd>{thesis.title || "-"}</dd>
            </div>
            <div>
              <dt>{t("author")}</dt>
              <dd>{thesis.author || "-"}</dd>
            </div>
            <div>
              <dt>{t("university")}</dt>
              <dd>{thesis.university || "-"}</dd>
            </div>
            <div>
              <dt>{t("year")}</dt>
              <dd>{thesis.year || "-"}</dd>
            </div>
            <div>
              <dt>{t("source")}</dt>
              <dd>{thesis.source || "-"}</dd>
            </div>
            <div>
              <dt>{t("dissertationUrl")}</dt>
              <dd>
                {thesis.dissertation_url ? (
                  <a href={thesis.dissertation_url} target="_blank" rel="noreferrer">
                    {thesis.dissertation_url}
                  </a>
                ) : (
                  "-"
                )}
              </dd>
            </div>
            <div>
              <dt>{t("abstract")}</dt>
              <dd>{thesis.abstract || "-"}</dd>
            </div>
          </dl>

          <form className="classification-form" onSubmit={saveClassification}>
            <ProfessionSelect
              allowNew={form.allow_new_profession}
              onChange={updateProfession}
              professions={professionsRequest.data ?? []}
              t={t}
              value={form.profession}
            />
            <label>
              <span>{t("category")}</span>
              <select
                value={form.category_id}
                onChange={(event) => updateCategory(event.target.value)}
              >
                <option value="">{t("selectCategory")}</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>{t("subcategory")}</span>
              <select
                disabled={!form.category_id}
                value={form.subcategory_id}
                onChange={(event) => updateSubcategory(event.target.value)}
              >
                <option value="">{t("selectSubcategory")}</option>
                {subcategories.map((subcategory) => (
                  <option key={subcategory.id} value={subcategory.id}>
                    {subcategory.name}
                  </option>
                ))}
              </select>
            </label>
            {validation && <p className="validation-message">{validation}</p>}
            <div className="form-actions">
              <button className="primary-button" type="submit">
                {t("saveClassification")}
              </button>
              {status && <span className="form-status">{status}</span>}
            </div>
          </form>
        </article>
      )}
    </section>
  );
}

function NarrativeText({
  authorLinks = [],
  collapsible = false,
  linkCitations = false,
  t = (key) => translations.sv[key] ?? key,
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
          {expanded ? t("showLess") : t("showMore")}
        </button>
      )}
    </div>
  );
}

function ThesisDetail({ isAdmin, runningNumber, t }) {
  const thesisRequest = useApi(`/theses/${runningNumber}`);
  const [savedThesis, setSavedThesis] = useState(null);
  const [paperReload, setPaperReload] = useState(0);
  const papers = useApi(`/theses/${runningNumber}/papers?reload=${paperReload}`);
  const { data: categories } = useApi("/categories");
  const { data: subcategories } = useApi("/subcategories");
  const [workflowStatus, setWorkflowStatus] = useState("");
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

  async function updateMetadataStatus(nextStatus) {
    setWorkflowStatus(t("saving"));
    try {
      const saved = await sendJson(`/theses/${runningNumber}/metadata-status`, "PATCH", {
        metadata_status: nextStatus,
      });
      setSavedThesis(saved);
      setWorkflowStatus(t("statusUpdated"));
    } catch {
      setWorkflowStatus(t("statusUpdateFailed"));
    }
  }

  return (
    <section className="page-section detail-section">
      <button className="back-button" onClick={() => navigate("/theses", isAdmin)}>
        {t("backToTheses")}
      </button>

      {thesisRequest.loading && <Status message={t("loadingTheses")} />}
      {thesisRequest.error && <Status message={t("couldNotLoadTheses")} />}
      {thesis && (
        <article className="detail">
          <p className="eyebrow">{t("theses")} #{thesis.running_number}</p>
          <h1>{thesis.title}</h1>
          <div className="metadata-status-row">
            <span className={`metadata-status-badge status-${metadataStatus(thesis)}`}>
              {t(metadataStatus(thesis))}
            </span>
            {thesis.metadata_last_checked_at && (
              <span className="metadata-last-checked">
                {t("lastChecked")}: {formatDateTime(thesis.metadata_last_checked_at)}
              </span>
            )}
          </div>
          {isAdmin && (
            <div className="metadata-status-actions">
              <button
                className="secondary-button"
                onClick={() => updateMetadataStatus("not_found")}
                type="button"
              >
                {t("markNotFound")}
              </button>
              <button
                className="secondary-button"
                onClick={() => updateMetadataStatus("needs_review")}
                type="button"
              >
                {t("markNeedsReview")}
              </button>
              {workflowStatus && <span className="form-status">{workflowStatus}</span>}
            </div>
          )}
          <dl>
            <div>
              <dt>{t("author")}</dt>
              <dd>{thesis.author}</dd>
            </div>
            <div>
              <dt>{t("profession")}</dt>
              <dd>{thesis.profession || "-"}</dd>
            </div>
            <div>
              <dt>{t("university")}</dt>
              <dd>{thesis.university || "-"}</dd>
            </div>
            <div>
              <dt>{t("year")}</dt>
              <dd>{thesis.year || "-"}</dd>
            </div>
            <div>
              <dt>{t("category")}</dt>
              <dd>
                {thesis.category_id ? (
                  <button
                    className="detail-link"
                    onClick={() => navigate(`/research-areas/${thesis.category_id}`, isAdmin)}
                  >
                    {categoryNames[thesis.category_id] || thesis.category_id}
                  </button>
                ) : (
                  "-"
                )}
              </dd>
            </div>
            <div>
              <dt>{t("subcategory")}</dt>
              <dd>
                {thesis.subcategory_id ? (
                  <button
                    className="detail-link"
                    onClick={() =>
                      navigate(
                        `/research-areas/${thesis.subcategory_id[0]}#subcategory-${thesis.subcategory_id}`,
                        isAdmin
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
            <h2>{t("digitalThesis")}</h2>
            {!hasDigitalMetadata && (
              <p className="placeholder-text">{t("noDigitalMetadata")}</p>
            )}

            <div className="metadata-block">
              <h3>{t("abstract")}</h3>
              {thesis.abstract ? (
                <NarrativeText t={t} text={thesis.abstract} />
              ) : (
                <p className="placeholder-text">{t("noDigitalMetadata")}</p>
              )}
            </div>

            {(thesis.dissertation_url || thesis.pdf_url || thesis.doi || thesis.urn) && (
              <dl className="metadata-list">
                {thesis.dissertation_url && (
                  <div>
                    <dt>{t("dissertationUrl")}</dt>
                    <dd>
                      <a href={thesis.dissertation_url} target="_blank" rel="noreferrer">
                        {t("openDissertationRecord")}
                      </a>
                    </dd>
                  </div>
                )}
                {thesis.pdf_url && (
                  <div>
                    <dt>PDF</dt>
                    <dd>
                      <a href={thesis.pdf_url} target="_blank" rel="noreferrer">
                        {t("openPdf")}
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
              <h3>{t("includedPapers")}</h3>
              {papers.loading && <Status message={t("loadingPapers")} />}
              {papers.error && <Status message={t("couldNotLoadPapers")} />}
              {papers.data && papers.data.length === 0 && (
                <p className="placeholder-text">{t("noDigitalMetadata")}</p>
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
                      {paper.abstract && <NarrativeText t={t} text={paper.abstract} />}
                    </article>
                  ))}
                </div>
              )}
            </div>

            {isAdmin && (
              <>
                <MetadataEditForm
                  onSaved={setSavedThesis}
                  t={t}
                  thesis={thesis}
                />
                <IncludedPaperForm
                  onSaved={() => setPaperReload((current) => current + 1)}
                  runningNumber={runningNumber}
                  t={t}
                />
              </>
            )}
          </section>
        </article>
      )}
    </section>
  );
}

function MetadataEditForm({ onSaved, t, thesis }) {
  const [form, setForm] = useState(metadataFormFromThesis(thesis));
  const [lookupUrl, setLookupUrl] = useState("");
  const [extraction, setExtraction] = useState(null);
  const [status, setStatus] = useState("");
  const professionsRequest = useApi("/professions");

  useEffect(() => {
    setForm(metadataFormFromThesis(thesis));
  }, [thesis]);

  async function handleSubmit(event) {
    event.preventDefault();
    const profession = cleanProfession(form.profession);
    const isNewProfession =
      profession &&
      form.allow_new_profession &&
      !(professionsRequest.data ?? []).some(
        (existing) => professionKey(existing) === professionKey(profession)
      );
    if (!profession) {
      setStatus(t("professionRequired"));
      return;
    }
    if (isNewProfession && !window.confirm(`${t("confirmCreateProfession")} ${form.profession.trim()}`)) {
      return;
    }

    setStatus(t("saving"));
    try {
      const saved = await sendJson(`/theses/${thesis.running_number}`, "PATCH", {
        ...form,
        profession,
      });
      onSaved(saved);
      setStatus(t("saved"));
    } catch {
      setStatus(t("saveFailed"));
    }
  }

  async function handleUrlExtraction(event) {
    event.preventDefault();
    setStatus(t("fetchingUrl"));
    try {
      const result = await sendJson("/metadata/lookup-url", "POST", { url: lookupUrl });
      setExtraction(result);
      setStatus("");
    } catch {
      setStatus(t("urlLookupFailed"));
    }
  }

  function copyExtractedField(field) {
    const value = extraction?.parsed_fields?.[field];
    if (value === null || value === undefined) return;
    setForm((current) => ({ ...current, [field]: String(value) }));
  }

  function acceptAllExtractedFields() {
    setForm((current) => ({
      ...current,
      ...candidateToMetadata(extraction?.parsed_fields ?? extraction?.candidate ?? {}),
    }));
  }

  return (
    <section className="metadata-form">
      <h3>{t("editMetadata")}</h3>
      <form className="lookup-url-form" onSubmit={handleUrlExtraction}>
        <label>
          <span>{t("lookupFromUrl")}</span>
          <input
            placeholder={t("pasteDissertationUrl")}
            value={lookupUrl}
            onChange={(event) => setLookupUrl(event.target.value)}
          />
        </label>
        <button className="secondary-button" type="submit">
          {t("extractMetadata")}
        </button>
      </form>
      {extraction && (
        <MetadataExtractionReview
          extraction={extraction}
          form={form}
          onAcceptAll={acceptAllExtractedFields}
          onCopyField={copyExtractedField}
          t={t}
          thesis={thesis}
        />
      )}
      <form className="metadata-edit-fields" onSubmit={handleSubmit}>
      <ProfessionSelect
        allowNew={form.allow_new_profession}
        onChange={(profession, allowNewProfession) =>
          setForm((current) => ({
            ...current,
            profession,
            allow_new_profession: allowNewProfession,
          }))
        }
        professions={professionsRequest.data ?? []}
        t={t}
        value={form.profession}
      />
      <label>
        <span>{t("abstract")}</span>
        <textarea
          rows="6"
          value={form.abstract}
          onChange={(event) => setForm((current) => ({ ...current, abstract: event.target.value }))}
        />
      </label>
      <div className="metadata-form-grid">
        <label>
          <span>{t("dissertationUrl")}</span>
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
        <button className="primary-button" type="submit">{t("saveMetadata")}</button>
        {status && <span className="form-status">{status}</span>}
      </div>
      </form>
    </section>
  );
}

function MetadataExtractionReview({ extraction, form, onAcceptAll, onCopyField, t, thesis }) {
  const parsedFields = extraction.parsed_fields ?? extraction.candidate ?? {};
  const missingFields = extraction.missing_fields ?? [];

  return (
    <div className="metadata-extraction-review">
      <div className="extraction-summary">
        <div>
          <h4>{t("extractedMetadata")}</h4>
          <p className="paper-meta">
            {t("parserUsed")}: {extraction.parser_used || extraction.candidate?.parser_used || "generic"} ·{" "}
            {t("confidence")}: {extraction.extraction_confidence ?? extraction.candidate?.extraction_confidence ?? 0}
          </p>
        </div>
        <button className="secondary-button" onClick={onAcceptAll} type="button">
          {t("acceptAllFields")}
        </button>
      </div>
      <p className="paper-meta">
        {t("missingFields")}: {missingFields.length ? missingFields.join(", ") : t("noMissingFields")}
      </p>
      <div className="metadata-comparison">
        <span>{t("title")}</span>
        <span>{t("currentValue")}</span>
        <span>{t("extractedValue")}</span>
        <span />
        {metadataReviewFields.map(({ field, label }) => (
          <MetadataComparisonRow
            currentValue={currentMetadataValue(field, form, thesis)}
            extractedValue={parsedFields[field]}
            field={field}
            key={field}
            label={label(t)}
            onCopyField={onCopyField}
            t={t}
          />
        ))}
      </div>
    </div>
  );
}

function MetadataComparisonRow({ currentValue, extractedValue, field, label, onCopyField, t }) {
  const canCopy = editableMetadataFields.includes(field) && extractedValue !== null && extractedValue !== undefined && extractedValue !== "";
  return (
    <>
      <strong>{label}</strong>
      <span>{displayMetadataValue(currentValue)}</span>
      <span>{displayMetadataValue(extractedValue)}</span>
      <span>
        {canCopy && (
          <button className="text-link-button" onClick={() => onCopyField(field)} type="button">
            {t("copyField")}
          </button>
        )}
      </span>
    </>
  );
}

function MetadataLookup({ onChecked, onSaved, runningNumber, t }) {
  const [lookup, setLookup] = useState({ candidates: [], search: null });
  const [showErrorDetails, setShowErrorDetails] = useState(false);
  const [status, setStatus] = useState("");

  async function handleLookup() {
    setStatus(t("searching"));
    try {
      const result = await sendJson(`/theses/${runningNumber}/lookup-metadata`, "POST", {});
      setLookup(result);
      onChecked(result.candidates.length ? "candidate_found" : "not_found");
      setStatus(
        result.candidates.length
          ? ""
          : result.errors?.length
            ? t("someRepositorySearchesFailed")
            : t("noCandidates")
      );
    } catch {
      setStatus(t("lookupFailed"));
    }
  }

  async function useCandidate(candidate) {
    setStatus(t("savingCandidate"));
    try {
      const saved = await sendJson(`/theses/${runningNumber}`, "PATCH", candidateToMetadata(candidate));
      onSaved(saved);
      setStatus(t("candidateSaved"));
    } catch {
      setStatus(t("candidateSaveFailed"));
    }
  }

  return (
    <section className="metadata-lookup">
      <div className="lookup-heading">
        <div>
          <h3>{t("findDigitalMetadata")}</h3>
          <p className="placeholder-text">{t("candidatesManual")}</p>
        </div>
        <button className="primary-button" onClick={handleLookup} type="button">
          {t("findDigitalMetadata")}
        </button>
      </div>

      {status && <p className="status">{status}</p>}
      {lookup.errors?.length > 0 && (
        <div className="lookup-errors">
          {lookup.errors.map((error) => (
            <p className="status" key={error.source}>
              {error.source}: {error.error}
            </p>
          ))}
        </div>
      )}
      {lookup.error_summary && (
        <div className="lookup-error-summary">
          <p className="status">
            {t("someRepositorySearchesFailed")} ({lookup.error_summary.count})
          </p>
          <button
            className="text-link-button"
            onClick={() => setShowErrorDetails((current) => !current)}
            type="button"
          >
            {showErrorDetails ? t("hideDetails") : t("showDetails")}
          </button>
          {showErrorDetails && (
            <ul>
              {lookup.error_summary.details.map((error, index) => (
                <li key={`${error.url}-${index}`}>
                  {error.url}: {error.error}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {lookup.candidates.length > 0 && (
        <div className="candidate-list">
          {lookup.candidates.map((candidate, index) => (
            <article className="candidate-card" key={`${candidate.source}-${index}`}>
              <h4>{candidate.title || t("untitledCandidate")}</h4>
              <p className="paper-meta">
                {[
                  candidate.author,
                  candidate.university,
                  candidate.year,
                  candidate.source,
                  candidate.source_host,
                  `${t("confidence")}: ${candidate.confidence}`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {candidate.note && (
                <p className="library-note">
                  {candidate.note.startsWith("Library record only")
                    ? t("libraryRecordOnly")
                    : candidate.note}
                </p>
              )}
              <dl className="metadata-list">
                {candidate.parsed_title && (
                  <div>
                    <dt>{t("parsedTitle")}</dt>
                    <dd>{candidate.parsed_title}</dd>
                  </div>
                )}
                {candidate.document_type && (
                  <div>
                    <dt>{t("documentType")}</dt>
                    <dd>{candidate.document_type}</dd>
                  </div>
                )}
                {candidate.classification && (
                  <div>
                    <dt>{t("classification")}</dt>
                    <dd>{candidate.classification}</dd>
                  </div>
                )}
                <div>
                  <dt>{t("abstractAvailable")}</dt>
                  <dd>{candidate.has_abstract ? t("yes") : t("no")}</dd>
                </div>
                <div>
                  <dt>{t("pdfAvailable")}</dt>
                  <dd>{candidate.has_pdf || candidate.pdf_url ? t("yes") : t("no")}</dd>
                </div>
                {candidate.dissertation_url && (
                  <div>
                    <dt>{t("dissertationUrl")}</dt>
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
              {candidate.abstract && <NarrativeText t={t} text={candidate.abstract} />}
              {candidate.included_papers?.length > 0 && (
                <div className="paper-list">
                  <h4>{t("includedPapersFound")}</h4>
                  {candidate.included_papers.map((paper, paperIndex) => (
                    <article className="paper-item" key={`${paper.title}-${paperIndex}`}>
                      <p>{paper.title}</p>
                      {paper.doi && <p className="paper-meta">DOI: {paper.doi}</p>}
                    </article>
                  ))}
                </div>
              )}
              <button className="primary-button" onClick={() => useCandidate(candidate)} type="button">
                {t("useMetadata")}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function IncludedPaperForm({ onSaved, runningNumber, t }) {
  const [form, setForm] = useState(emptyPaperForm());
  const [status, setStatus] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!form.title.trim()) {
      setStatus(t("titleRequired"));
      return;
    }

    setStatus(t("saving"));
    try {
      await sendJson(`/theses/${runningNumber}/papers`, "POST", {
        ...form,
        year: form.year ? Number(form.year) : null,
      });
      setForm(emptyPaperForm());
      setStatus(t("paperSaved"));
      onSaved();
    } catch {
      setStatus(t("paperSaveFailed"));
    }
  }

  return (
    <form className="metadata-form" onSubmit={handleSubmit}>
      <h3>{t("addIncludedPaper")}</h3>
      <label>
        <span>{t("title")}</span>
        <input
          value={form.title}
          onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
        />
      </label>
      <div className="metadata-form-grid">
        <label>
          <span>{t("journal")}</span>
          <input
            value={form.journal}
            onChange={(event) => setForm((current) => ({ ...current, journal: event.target.value }))}
          />
        </label>
        <label>
          <span>{t("year")}</span>
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
        <span>{t("abstract")}</span>
        <textarea
          rows="4"
          value={form.abstract}
          onChange={(event) => setForm((current) => ({ ...current, abstract: event.target.value }))}
        />
      </label>
      <div className="form-actions">
        <button className="primary-button" type="submit">{t("savePaper")}</button>
        {status && <span className="form-status">{status}</span>}
      </div>
    </form>
  );
}

function SelectFilter({ label, value, options, onChange, t }) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">{t("all")}</option>
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

function sortTheses(theses) {
  return [...(theses ?? [])].sort((a, b) => {
    const yearA = Number(a.year) || 0;
    const yearB = Number(b.year) || 0;
    if (yearA !== yearB) return yearB - yearA;
    return Number(b.running_number) - Number(a.running_number);
  });
}

function metadataStatus(thesis) {
  return thesis?.metadata_status || "not_started";
}

function formatDateTime(value) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function discoveryMatchLabel(status, t) {
  const labels = {
    new_candidate: t("newCandidate"),
    possible_duplicate: t("possibleDuplicate"),
    already_in_database: t("alreadyInDatabase"),
  };
  return labels[status] ?? status;
}

function reviewStatusLabel(status, t) {
  const labels = {
    approved: t("approved"),
    rejected: t("rejected"),
    needs_review: t("needsReviewAction"),
    pending: t("active"),
  };
  return labels[status] ?? status;
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

const editableMetadataFields = ["abstract", "dissertation_url", "pdf_url", "doi", "urn"];

const metadataReviewFields = [
  { field: "title", label: (t) => t("title") },
  { field: "author", label: (t) => t("author") },
  { field: "university", label: (t) => t("university") },
  { field: "year", label: (t) => t("year") },
  { field: "abstract", label: (t) => t("abstract") },
  { field: "dissertation_url", label: (t) => t("dissertationUrl") },
  { field: "pdf_url", label: () => "PDF URL" },
  { field: "doi", label: () => "DOI" },
  { field: "urn", label: () => "URN" },
];

function currentMetadataValue(field, form, thesis) {
  if (field in form) return form[field];
  return thesis?.[field];
}

function displayMetadataValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function metadataFormFromThesis(thesis) {
  return {
    profession: thesis?.profession ?? "",
    allow_new_profession: false,
    abstract: thesis?.abstract ?? "",
    dissertation_url: thesis?.dissertation_url ?? "",
    pdf_url: thesis?.pdf_url ?? "",
    doi: thesis?.doi ?? "",
    urn: thesis?.urn ?? "",
  };
}

function cleanProfession(value) {
  return String(value ?? "").trim().replace(/\s+/g, " ");
}

function professionKey(value) {
  return cleanProfession(value).toLocaleLowerCase("sv-SE");
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

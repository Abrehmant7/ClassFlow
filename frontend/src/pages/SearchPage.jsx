import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import { listClassCourses, listMyCourses } from "../api/courses.js";
import { searchContent } from "../api/search.js";
import Alert from "../components/Alert.jsx";
import Button from "../components/Button.jsx";
import EmptyState from "../components/EmptyState.jsx";
import Pagination from "../components/Pagination.jsx";
import SearchResultItem from "../components/SearchResultItem.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { isRepresentative } from "../utils/classrooms.js";
import { parseModule7Error } from "../utils/module7.js";
import { TASK_PRIORITIES, TASK_TYPES } from "../utils/tasks.js";

const PAGE_SIZE = 20;
const ENTITY_TABS = [
  ["all", "All"], ["task", "Tasks"], ["announcement", "Announcements"], ["resource", "Resources"],
];
const FILTER_KEYS = ["entity_type", "classroom_id", "class_course_id", "date_from", "date_to", "task_type", "priority", "status"];

function Select({ id, label, value, onChange, children }) {
  return (
    <div>
      <label className="cf-label" htmlFor={id}>{label}</label>
      <select className="cf-input" id={id} value={value} onChange={onChange}>{children}</select>
    </div>
  );
}

function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q")?.trim() || "";
  const [draft, setDraft] = useState(searchParams.get("q") || "");
  const entityType = searchParams.get("entity_type") || "all";
  const page = Math.max(1, Number(searchParams.get("page")) || 1);
  const [options, setOptions] = useState({ classrooms: [], courses: [] });
  const [optionsError, setOptionsError] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const requestVersion = useRef(0);

  const filters = useMemo(() => Object.fromEntries(
    FILTER_KEYS.map((key) => [key, searchParams.get(key) || ""]),
  ), [searchParams]);
  const courseOptions = useMemo(() => options.courses.filter((course) =>
    !filters.classroom_id || course.classroom_id === Number(filters.classroom_id),
  ), [filters.classroom_id, options.courses]);

  useEffect(() => { setDraft(searchParams.get("q") || ""); }, [searchParams]);

  const loadOptions = useCallback(async () => {
    setOptionsError(null);
    try {
      const mine = await listMyClassrooms();
      const classrooms = mine.filter((item) => item.is_active !== false && item.membership?.status === "approved");
      const courseLists = await Promise.all(classrooms.map(async (classroom) => {
        const entries = isRepresentative(classroom.membership)
          ? await listClassCourses(classroom.id)
          : (await listMyCourses(classroom.id)).map((registration) => registration.class_course);
        return entries.filter((entry) => entry?.is_active).map((entry) => ({
          class_course_id: entry.id, classroom_id: classroom.id,
          code: entry.course.code, name: entry.course.name,
        }));
      }));
      setOptions({ classrooms, courses: courseLists.flat() });
    } catch (apiError) {
      setOptionsError(parseModule7Error(apiError));
    }
  }, []);

  useEffect(() => { loadOptions(); }, [loadOptions]);

  const loadResults = useCallback(async () => {
    const version = ++requestVersion.current;
    if (!query) {
      setResults(null);
      setLoading(false);
      setError(null);
      return;
    }
    setResults(null);
    setLoading(true);
    setError(null);
    const params = { q: query, entity_type: entityType, page, page_size: PAGE_SIZE };
    for (const key of FILTER_KEYS) {
      if (key !== "entity_type" && filters[key]) params[key] = filters[key];
    }
    try {
      const result = await searchContent(params);
      if (version === requestVersion.current) setResults(result);
    } catch (apiError) {
      if (version === requestVersion.current) setError(parseModule7Error(apiError));
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }, [query, entityType, page, filters]);

  useEffect(() => {
    loadResults();
    return () => { requestVersion.current += 1; };
  }, [loadResults]);

  function updateParams(updates) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value && value !== "all") next.set(key, String(value));
      else next.delete(key);
    }
    if (!("page" in updates)) next.delete("page");
    setSearchParams(next);
  }

  function updateFilter(key, value) {
    updateParams({ [key]: value, ...(key === "classroom_id" ? { class_course_id: "" } : {}) });
  }

  function changeEntity(value) {
    const clearTaskFilters = value !== "task" && value !== "all"
      ? { task_type: "", priority: "", status: "" } : {};
    updateParams({ entity_type: value, ...clearTaskFilters });
  }

  function submit(event) {
    event.preventDefault();
    updateParams({ q: draft.trim().slice(0, 100) });
  }

  function clearFilters() {
    const next = new URLSearchParams();
    if (query) next.set("q", query);
    setSearchParams(next);
  }

  return (
    <section className="space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan-700">Find class material</p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">Search</h1>
      </div>
      <form className="cf-card flex flex-col gap-3 p-4 sm:flex-row sm:items-end" onSubmit={submit} role="search">
        <div className="min-w-0 flex-1">
          <label className="cf-label" htmlFor="search-query">Search terms</label>
          <input className="cf-input" id="search-query" maxLength={100} onChange={(event) => setDraft(event.target.value)} placeholder="Search tasks, announcements, and resources" value={draft} />
        </div>
        <Button type="submit" variant="primary">Search</Button>
      </form>
      <div aria-label="Entity type" className="flex flex-wrap gap-2" role="tablist">
        {ENTITY_TABS.map(([value, label]) => <button
          aria-selected={entityType === value} className={`rounded-lg px-3 py-2 text-sm font-semibold cf-focus ${entityType === value ? "bg-blue-600 text-white" : "border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"}`}
          key={value} onClick={() => changeEntity(value)} role="tab" type="button">{label}</button>)}
      </div>

      <div className="cf-card grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <Select id="search-classroom" label="Classroom" value={filters.classroom_id} onChange={(event) => updateFilter("classroom_id", event.target.value)}>
          <option value="">All classrooms</option>
          {options.classrooms.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </Select>
        <Select id="search-course" label="Course" value={filters.class_course_id} onChange={(event) => updateFilter("class_course_id", event.target.value)}>
          <option value="">All courses</option>
          {courseOptions.map((item) => <option key={item.class_course_id} value={item.class_course_id}>{item.code} - {item.name}</option>)}
        </Select>
        <div>
          <label className="cf-label" htmlFor="search-date-from">From date</label>
          <input className="cf-input" id="search-date-from" onChange={(event) => updateFilter("date_from", event.target.value)} type="date" value={filters.date_from} />
        </div>
        <div>
          <label className="cf-label" htmlFor="search-date-to">To date</label>
          <input className="cf-input" id="search-date-to" onChange={(event) => updateFilter("date_to", event.target.value)} type="date" value={filters.date_to} />
        </div>
        {(entityType === "task" || entityType === "all") ? (
          <>
            <Select id="search-task-type" label="Task type" value={filters.task_type} onChange={(event) => updateFilter("task_type", event.target.value)}>
              <option value="">All task types</option>
              {TASK_TYPES.map((value) => <option key={value} value={value}>{value}</option>)}
            </Select>
            <Select id="search-priority" label="Priority" value={filters.priority} onChange={(event) => updateFilter("priority", event.target.value)}>
              <option value="">All priorities</option>
              {TASK_PRIORITIES.map((value) => <option key={value} value={value}>{value}</option>)}
            </Select>
            <Select id="search-status" label="Status" value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
              <option value="">All statuses</option>
              {["active", "completed", "cancelled", "archived"].map((value) => <option key={value} value={value}>{value}</option>)}
            </Select>
          </>
        ) : null}
        <div className="flex items-end"><Button onClick={clearFilters}>Clear filters</Button></div>
      </div>
      {optionsError ? <div className="space-y-2"><Alert title="Could not load filter options" {...optionsError} /><Button onClick={loadOptions}>Retry filters</Button></div> : null}
      {error ? <div className="space-y-2"><Alert title="Search failed" {...error} /><Button onClick={loadResults}>Try again</Button></div> : null}
      {loading ? <p className="text-sm text-slate-500" role="status">Searching...</p> : null}
      {!query && !loading ? <EmptyState title="Start a search" message="Enter a keyword to find accessible class material." /> : null}
      {query && !loading && !error && results?.items.length === 0 ? <EmptyState title="No results" message="Try another keyword or clear a filter." /> : null}
      {results && !loading && !error ? (
        <>
          <div className="flex items-center justify-between text-sm text-slate-500"><span>{results.total} results</span><StatusBadge value={entityType} label={ENTITY_TABS.find(([value]) => value === entityType)?.[1] || "All"} /></div>
          <div className="space-y-3">{results.items.map((item) => <SearchResultItem key={`${item.entity_type}-${item.id}`} result={item} />)}</div>
          <Pagination page={results.page} totalPages={results.total_pages} onChange={(next) => updateParams({ page: next })} />
        </>
      ) : null}
    </section>
  );
}

export default SearchPage;

import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import ClassEntryPage from "./ClassEntryPage.jsx";

vi.mock("./ClassOverviewPage.jsx", () => ({ default: () => <p>Class overview</p> }));

function Destination() {
  const location = useLocation();
  return <p>Destination: {location.pathname}{location.search}</p>;
}

function renderEntry(path) {
  return render(<MemoryRouter initialEntries={[path]}><Routes>
    <Route element={<ClassEntryPage />} path="/classes/:classId" />
    <Route element={<Destination />} path="/classes/:classId/announcements" />
    <Route element={<Destination />} path="/classes/:classId/resources" />
  </Routes></MemoryRouter>);
}

describe("backend classroom action URLs", () => {
  it("retains the usual class overview", () => {
    renderEntry("/classes/4");
    expect(screen.getByText("Class overview")).toBeInTheDocument();
  });

  it("routes announcement tab URLs inside the SPA", async () => {
    renderEntry("/classes/4?tab=announcements");
    expect(await screen.findByText("Destination: /classes/4/announcements")).toBeInTheDocument();
  });

  it("routes a resource URL and keeps its selected ID", async () => {
    renderEntry("/classes/4?tab=resources&resource=9");
    expect(await screen.findByText("Destination: /classes/4/resources?resource=9")).toBeInTheDocument();
  });
});

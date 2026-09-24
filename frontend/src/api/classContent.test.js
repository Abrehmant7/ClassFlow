import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearTokens, getAccessToken, setTokens } from "../auth/tokenStorage.js";
import { announcement, resource } from "../test/classContentFixtures.js";
import { parseContentError } from "../utils/classContent.js";
import { createAnnouncement, deleteAnnouncement, getAnnouncement, listAnnouncements, updateAnnouncement } from "./announcements.js";
import { apiClient, setAuthExpiredHandler } from "./client.js";
import { deleteResource, downloadResource, getResource, listResources, reindexResource, updateResource, uploadResource } from "./resources.js";

const originalAdapter = apiClient.defaults.adapter;
const originalCreate = URL.createObjectURL;
const originalRevoke = URL.revokeObjectURL;
let adapter;
let click;
let responseData;
let responseHeaders;

describe("class content API", () => {
  beforeEach(() => {
    setTokens({ access_token: "test-session-token", refresh_token: "test-refresh-token" });
    responseData = resource;
    responseHeaders = {};
    adapter = vi.fn(async (config) => ({ data: responseData, status: 200, statusText: "OK", headers: responseHeaders, config }));
    apiClient.defaults.adapter = adapter;
    URL.createObjectURL = vi.fn(() => "blob:classflow-test");
    URL.revokeObjectURL = vi.fn();
    click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  });

  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
    URL.createObjectURL = originalCreate;
    URL.revokeObjectURL = originalRevoke;
    setAuthExpiredHandler(null);
    clearTokens();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("uses the announcement endpoints with typed payload shapes", async () => {
    responseData = [announcement];
    expect(await listAnnouncements(1)).toEqual([announcement]);
    responseData = announcement;
    expect(await getAnnouncement(10)).toEqual(announcement);
    const payload = { title: "Notice", body: "Read this", class_course_id: null, is_pinned: false };
    expect(await createAnnouncement(1, payload)).toEqual(announcement);
    await updateAnnouncement(10, { is_pinned: true });
    await deleteAnnouncement(10);
    expect(adapter.mock.calls.map(([config]) => [config.method, config.url])).toEqual([
      ["get", "/classes/1/announcements"], ["get", "/announcements/10"],
      ["post", "/classes/1/announcements"], ["patch", "/announcements/10"], ["delete", "/announcements/10"],
    ]);
    expect(JSON.parse(adapter.mock.calls[2][0].data)).toEqual(payload);
    expect(JSON.parse(adapter.mock.calls[3][0].data)).toEqual({ is_pinned: true });
  });

  it("uses resource list, detail, update, delete and reindex endpoints", async () => {
    await listResources(1);
    await getResource(20);
    await updateResource(20, { title: "Updated", description: null, is_enabled: false });
    await reindexResource(20);
    await deleteResource(20);
    expect(adapter.mock.calls.map(([config]) => [config.method, config.url])).toEqual([
      ["get", "/classes/1/resources"], ["get", "/resources/20"], ["patch", "/resources/20"],
      ["post", "/resources/20/reindex"], ["delete", "/resources/20"],
    ]);
    expect(JSON.parse(adapter.mock.calls[2][0].data)).toEqual({ title: "Updated", description: null, is_enabled: false });
  });

  it("constructs real FormData, forwards progress and leaves multipart headers to Axios/browser", async () => {
    const post = vi.spyOn(apiClient, "post");
    const file = new File(["%PDF-1.7"], "notes.pdf", { type: "application/pdf" });
    const progress = vi.fn();
    await uploadResource(1, { title: "Notes", description: "Chapter one", class_course_id: 11, file }, progress);
    const [url, body, config] = post.mock.calls[0];
    expect(url).toBe("/classes/1/resources");
    expect(body).toBeInstanceOf(FormData);
    expect([...body.keys()]).toEqual(["title", "description", "class_course_id", "file"]);
    expect(body.get("title")).toBe("Notes");
    expect(body.get("description")).toBe("Chapter one");
    expect(body.get("class_course_id")).toBe("11");
    expect(body.get("file")).toBe(file);
    expect(config.headers).toBeUndefined();
    expect(config.onUploadProgress).toBe(progress);
    expect(adapter.mock.calls[0][0].headers.Authorization).toBe("Bearer test-session-token");
  });

  it("omits optional upload fields for an Entire class PDF", async () => {
    const post = vi.spyOn(apiClient, "post");
    const file = new File(["%PDF-1.7"], "notes.pdf", { type: "application/pdf" });
    await uploadResource(1, { title: "Notes", class_course_id: null, file });
    const body = post.mock.calls[0][1];
    expect([...body.keys()]).toEqual(["title", "file"]);
  });

  it.each([
    ['attachment; filename="course notes.pdf"', "course notes.pdf"],
    ["attachment; filename=plain.pdf", "plain.pdf"],
    ["attachment; filename=plain.pdf; filename*=UTF-8''caf%C3%A9%20notes.pdf", "café notes.pdf"],
    ["attachment; filename*=UTF-8''%broken", "notes.pdf"],
    [undefined, "notes.pdf"],
  ])("downloads an authenticated blob using disposition %s", async (disposition, filename) => {
    vi.useFakeTimers();
    responseData = new Blob(["%PDF-1.7"], { type: "application/pdf" });
    responseHeaders = disposition ? { "content-disposition": disposition } : {};
    await downloadResource(resource);
    const request = adapter.mock.calls[0][0];
    expect(request.url).toBe("/resources/20/download");
    expect(request.responseType).toBe("blob");
    expect(request.headers.Authorization).toBe("Bearer test-session-token");
    expect(URL.createObjectURL).toHaveBeenCalledWith(responseData);
    expect(click.mock.instances[0].download).toBe(filename);
    expect(click.mock.instances[0].href).toBe("blob:classflow-test");
    expect(document.querySelector('a[download]')).toBeNull();
    await vi.runAllTimersAsync();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:classflow-test");
  });

  it("decodes blob error bodies for field validation without triggering a download", async () => {
    adapter.mockImplementationOnce(async (config) => {
      throw new AxiosError("Validation", "ERR_BAD_REQUEST", config, null, {
        status: 422, data: new Blob([JSON.stringify({ detail: [{ loc: ["body", "file"], msg: "Invalid PDF" }] })]),
      });
    });
    let failure;
    try { await downloadResource(resource); } catch (error) { failure = error; }
    expect(parseContentError(failure).items).toEqual(["file: Invalid PDF"]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(click).not.toHaveBeenCalled();
  });

  it("keeps the existing 401 session-expiry behavior for downloads", async () => {
    window.localStorage.removeItem("classflow.refreshToken");
    const expired = vi.fn();
    setAuthExpiredHandler(expired);
    adapter.mockImplementationOnce(async (config) => {
      throw new AxiosError("Unauthorized", "ERR_BAD_REQUEST", config, null, { status: 401, data: {} });
    });
    await expect(downloadResource(resource)).rejects.toMatchObject({ response: { status: 401 } });
    expect(expired).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
    expect(click).not.toHaveBeenCalled();
  });
});

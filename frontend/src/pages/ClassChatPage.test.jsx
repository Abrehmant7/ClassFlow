import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listMyClassrooms } from "../api/classrooms.js";
import { sendClassChatFileMessage, sendClassChatMessage } from "../api/chat.js";
import ClassChatPage from "./ClassChatPage.jsx";

vi.mock("../api/classrooms.js", () => ({
  listMyClassrooms: vi.fn(),
}));

vi.mock("../api/chat.js", () => ({
  sendClassChatFileMessage: vi.fn(),
  sendClassChatMessage: vi.fn(),
}));

const approvedClassroom = {
  id: 1,
  name: "Data Structures",
  semester: 5,
  section: "A",
  membership: {
    role: "student",
    status: "approved",
  },
};

function renderChatPage() {
  return render(
    <MemoryRouter initialEntries={["/classes/1/chat"]}>
      <Routes>
        <Route element={<ClassChatPage />} path="/classes/:classId/chat" />
      </Routes>
    </MemoryRouter>,
  );
}

async function loadComposer() {
  renderChatPage();
  return screen.findByPlaceholderText(/ask about class tasks/i);
}

function createPdfFile(name = "question.pdf") {
  return new File(["%PDF-test"], name, { type: "application/pdf" });
}

function selectFile(container, file) {
  const fileInput = container.querySelector('input[type="file"]');
  fireEvent.change(fileInput, { target: { files: [file] } });
}

function textWithContent(content) {
  return (_value, element) => element?.textContent === content;
}

describe("ClassChatPage", () => {
  beforeEach(() => {
    listMyClassrooms.mockReset();
    sendClassChatFileMessage.mockReset();
    sendClassChatMessage.mockReset();
    listMyClassrooms.mockResolvedValue([approvedClassroom]);
  });

  it("sends a normal chat message and hides the sources section when none are returned", async () => {
    sendClassChatMessage.mockResolvedValue({
      answer: "No matching class material was found.",
      sources: [],
    });
    const composer = await loadComposer();

    fireEvent.change(composer, { target: { value: "What is due?" } });
    fireEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() => {
      expect(sendClassChatMessage).toHaveBeenCalledWith(1, "What is due?");
    });
    expect(sendClassChatFileMessage).not.toHaveBeenCalled();
    expect(await screen.findByText("No matching class material was found.")).toBeInTheDocument();
    expect(screen.queryByText("Sources")).not.toBeInTheDocument();
  });

  it("validates unsupported, empty, and oversized chat files before upload", async () => {
    const composer = await loadComposer();
    const container = document.body;

    selectFile(container, new File(["notes"], "notes.txt", { type: "text/plain" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Only PDF and DOCX files");

    selectFile(container, new File([], "empty.pdf", { type: "application/pdf" }));
    expect(screen.getByRole("alert")).toHaveTextContent("empty");

    const largeFile = createPdfFile("large.pdf");
    Object.defineProperty(largeFile, "size", { value: 5 * 1024 * 1024 + 1 });
    selectFile(container, largeFile);
    expect(screen.getByRole("alert")).toHaveTextContent("5 MB");

    fireEvent.change(composer, { target: { value: "Read this" } });
    expect(sendClassChatFileMessage).not.toHaveBeenCalled();
  });

  it("sends selected files to the file chat endpoint and clears the composer file after success", async () => {
    sendClassChatFileMessage.mockResolvedValue({
      answer: "The report must be submitted as a PDF [1].",
      sources: [
        {
          source_type: "uploaded_file",
          source_id: null,
          title: "requirements.pdf",
          page_number: 3,
          preview: "The report must be submitted as a PDF.",
        },
      ],
    });
    const { container } = renderChatPage();
    const composer = await screen.findByPlaceholderText(/ask about class tasks/i);
    const file = createPdfFile("question.pdf");

    selectFile(container, file);
    expect(screen.getByText(/question\.pdf/)).toBeInTheDocument();
    fireEvent.change(composer, { target: { value: "Summarize this" } });
    fireEvent.click(screen.getByLabelText("Send message"));

    await waitFor(() => {
      expect(sendClassChatFileMessage).toHaveBeenCalledWith(1, "Summarize this", file);
    });
    expect(await screen.findByText(textWithContent("The report must be submitted as a PDF [1]."))).toBeInTheDocument();
    expect(screen.getByText("requirements.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 3")).toBeInTheDocument();
    expect(screen.queryByLabelText("Remove selected file")).not.toBeInTheDocument();
  });

  it("preserves the selected file and shows backend validation errors when upload fails", async () => {
    sendClassChatFileMessage.mockRejectedValueOnce({
      response: {
        status: 422,
        data: {
          detail: "Only PDF and DOCX chat attachments are supported",
          error_code: "CHAT_FILE_TYPE_NOT_ALLOWED",
        },
      },
    });
    sendClassChatFileMessage.mockResolvedValueOnce({
      answer: "Recovered answer.",
      sources: [],
    });
    const { container } = renderChatPage();
    const composer = await screen.findByPlaceholderText(/ask about class tasks/i);
    const file = createPdfFile("retry.pdf");

    selectFile(container, file);
    fireEvent.change(composer, { target: { value: "Read this" } });
    fireEvent.click(screen.getByLabelText("Send message"));

    expect(await screen.findByText("Message failed")).toBeInTheDocument();
    expect(screen.getByText("Only PDF and DOCX chat attachments are supported")).toBeInTheDocument();
    expect(screen.getByText("Code: CHAT_FILE_TYPE_NOT_ALLOWED")).toBeInTheDocument();
    expect(screen.getByLabelText("Remove selected file")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(sendClassChatFileMessage).toHaveBeenCalledTimes(2);
    });
    expect(await screen.findByText("Recovered answer.")).toBeInTheDocument();
  });

  it("renders cited sources in backend order and lets citation buttons focus the matching source", async () => {
    sendClassChatMessage.mockResolvedValue({
      answer: "Use the uploaded requirements [1] and class task [2].",
      sources: [
        {
          source_type: "task_attachment",
          source_id: 12,
          title: "requirements.pdf",
          page_number: 3,
          preview: "The report must be submitted as a PDF.",
        },
        {
          source_type: "task",
          source_id: 4,
          title: "Project task",
          page_number: null,
          preview: "Submit the project before Friday.",
        },
      ],
    });
    const composer = await loadComposer();

    fireEvent.change(composer, { target: { value: "What should I submit?" } });
    fireEvent.click(screen.getByLabelText("Send message"));

    const firstCitation = await screen.findByRole("button", { name: "Show source 1" });
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("requirements.pdf")).toBeInTheDocument();
    expect(screen.getByText("task attachment #12")).toBeInTheDocument();
    expect(screen.getByText("Project task")).toBeInTheDocument();

    fireEvent.click(firstCitation);
    expect(screen.getByText("requirements.pdf").closest("[tabindex='-1']")).toHaveFocus();
  });
});

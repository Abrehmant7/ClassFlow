import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { listMyClassrooms } from "../api/classrooms.js";
import { sendClassChatFileMessage, sendClassChatMessage } from "../api/chat.js";
import Alert from "../components/Alert.jsx";
import ClassWorkspaceHeader from "../components/ClassWorkspaceHeader.jsx";
import LoadingScreen from "../components/LoadingScreen.jsx";
import { isApproved } from "../utils/classrooms.js";
import { parseApiError } from "../utils/errors.js";

const exampleQuestions = [
  "What assignments are due this week?",
  "What are the requirements of the latest project?",
  "Which tasks are due before Friday?",
  "Summarize the available course instructions.",
];

const MAX_CHAT_FILE_SIZE_BYTES = 5 * 1024 * 1024;
const ALLOWED_CHAT_FILE_EXTENSIONS = [".pdf", ".docx"];

function createMessage(role, content, extra = {}) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role,
    content,
    ...extra,
  };
}

function getChatError(error) {
  const status = error.response?.status;
  const code = error.response?.data?.error_code;

  if (!error.response) {
    return {
      message: "Unable to reach the ClassFlow API. Check the backend server and API URL.",
      items: [],
    };
  }

  if (status === 401) {
    return { message: "Your session expired. Please log in again.", items: [] };
  }

  if (status === 403) {
    return {
      message: "Approved class membership is required to use the class assistant.",
      items: [],
    };
  }

  if (status === 422) {
    return parseApiError(error);
  }

  if (status === 503 && code === "RAG_NOT_CONFIGURED") {
    return { message: "The class assistant is not configured yet.", items: [] };
  }

  if (status === 503) {
    return { message: "The class assistant is temporarily unavailable.", items: [] };
  }

  return parseApiError(error);
}

function getFileExtension(fileName = "") {
  const lastDotIndex = fileName.lastIndexOf(".");
  return lastDotIndex >= 0 ? fileName.slice(lastDotIndex).toLowerCase() : "";
}

function validateChatFile(file) {
  if (!file) return null;

  const extension = getFileExtension(file.name);
  if (!ALLOWED_CHAT_FILE_EXTENSIONS.includes(extension)) {
    return "Only PDF and DOCX files can be attached to chat questions.";
  }

  if (file.size === 0) {
    return "The selected file is empty.";
  }

  if (file.size > MAX_CHAT_FILE_SIZE_BYTES) {
    return "The selected file is larger than the 5 MB limit.";
  }

  return null;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return "";
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatSourceType(type = "source") {
  return type.replace(/_/g, " ");
}

function SendIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="m22 2-7 20-4-9-9-4 20-7Z" />
      <path d="M22 2 11 13" />
    </svg>
  );
}

function AttachmentIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

function RemoveIcon() {
  return (
    <svg
      aria-hidden="true"
      className="h-4 w-4"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="2"
      viewBox="0 0 24 24"
    >
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
    </svg>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Assistant is thinking">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:120ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:240ms]" />
    </span>
  );
}

function SourceIcon({ type }) {
  const label = {
    task: "T",
    resource: "R",
    course: "C",
    task_attachment: "A",
    uploaded_file: "F",
  }[type] || "S";

  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded bg-blue-50 text-xs font-bold uppercase text-blue-700">
      {label}
    </span>
  );
}

function SourceRow({ source, sourceRef }) {
  const [expanded, setExpanded] = useState(false);
  const sourceType = source.source_type || "source";
  const typeLabel = formatSourceType(sourceType);
  const label = source.title || `${typeLabel} ${source.source_id ? `#${source.source_id}` : ""}`.trim();
  const preview = source.preview || "";
  const isLong = preview.length > 180;
  const visiblePreview = !expanded && isLong
    ? `${preview.slice(0, 180).trim()}...`
    : preview;

  return (
    <div
      className="flex min-w-0 scroll-mt-24 gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 outline-none transition focus-visible:border-blue-600 focus-visible:ring-2 focus-visible:ring-blue-600/20"
      ref={sourceRef}
      tabIndex={-1}
    >
      <SourceIcon type={source.source_type} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <p className="break-words text-xs font-semibold text-slate-900">{label}</p>
          <span className="text-xs font-medium capitalize text-slate-500">
            {typeLabel}
            {source.source_id ? ` #${source.source_id}` : ""}
          </span>
          {source.page_number !== null && source.page_number !== undefined ? (
            <span className="rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-semibold text-blue-700">
              Page {source.page_number}
            </span>
          ) : null}
        </div>
        <p className="mt-1 break-words text-xs leading-5 text-slate-600">
          {visiblePreview || "No preview available."}
        </p>
        {isLong ? (
          <button
            className="mt-1 text-xs font-semibold text-blue-700 hover:text-blue-900 cf-focus"
            onClick={() => setExpanded((current) => !current)}
            type="button"
          >
            {expanded ? "Show less" : "Show more"}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function SourcesList({ sources, sourceRefs }) {
  if (!sources?.length) return null;

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Sources
      </p>
      {sources.map((source, index) => (
        <SourceRow
          key={`${source.source_type}-${source.source_id}-${source.title}-${index}`}
          source={source}
          sourceRef={(element) => {
            sourceRefs.current[index] = element;
          }}
        />
      ))}
    </div>
  );
}

function renderContentWithCitations(content, onCitationClick) {
  const citationPattern = /\[((?:\d+\s*,\s*)*\d+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationPattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index));
    }

    const marker = match[0];
    const sourceNumbers = match[1].split(",").map((value) => value.trim());

    parts.push(
      <span
        className="inline-flex items-baseline rounded bg-blue-50 px-1 font-semibold text-blue-700"
        key={`${marker}-${match.index}`}
      >
        [
        {sourceNumbers.map((sourceNumber, index) => (
          <span key={`${sourceNumber}-${index}`}>
            {index > 0 ? ", " : ""}
            <button
              aria-label={`Show source ${sourceNumber}`}
              className="rounded-sm underline-offset-2 hover:underline cf-focus"
              onClick={() => onCitationClick(Number(sourceNumber) - 1)}
              type="button"
            >
              {sourceNumber}
            </button>
          </span>
        ))}
        ]
      </span>,
    );
    lastIndex = citationPattern.lastIndex;
  }

  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex));
  }

  return parts.length > 0 ? parts : content;
}

function ChatMessage({ message, onRetry }) {
  const isUser = message.role === "user";
  const isAssistant = message.role === "assistant";
  const sourceRefs = useRef([]);
  const error = typeof message.error === "string"
    ? { message: message.error, items: [] }
    : message.error;

  function focusSource(index) {
    const sourceElement = sourceRefs.current[index];
    if (!sourceElement) return;
    sourceElement.scrollIntoView({ behavior: "smooth", block: "center" });
    sourceElement.focus({ preventScroll: true });
  }

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <article
        className={`max-w-[min(760px,100%)] rounded-lg px-4 py-3 shadow-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "border border-slate-200 bg-white text-slate-900"
        }`}
      >
        {message.isLoading ? (
          <LoadingDots />
        ) : (
          <p className="whitespace-pre-wrap break-words text-sm leading-6">
            {isAssistant
              ? renderContentWithCitations(message.content, focusSource)
              : message.content}
          </p>
        )}

        {message.fileName ? (
          <p
            className={`mt-2 inline-flex max-w-full items-center rounded px-2 py-1 text-xs font-medium ${
              isUser
                ? "bg-white/15 text-blue-50"
                : "bg-slate-100 text-slate-600"
            }`}
          >
            <span className="truncate">{message.fileName}</span>
          </p>
        ) : null}

        {error ? (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-red-700">
            <p className="text-xs font-semibold">Message failed</p>
            <p className="mt-1 text-xs leading-5">{error.message}</p>
            {error.items?.length ? (
              <ul className="mt-1 list-disc space-y-1 pl-4 text-xs leading-5">
                {error.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            <button
              className="mt-2 text-xs font-semibold text-red-700 underline-offset-2 hover:underline cf-focus"
              onClick={() => onRetry(message)}
              type="button"
            >
              Retry
            </button>
          </div>
        ) : null}

        {isAssistant ? (
          <SourcesList sources={message.sources} sourceRefs={sourceRefs} />
        ) : null}
      </article>
    </div>
  );
}

function ChatComposer({
  disabled,
  draft,
  fileError,
  onDraftChange,
  onFileSelect,
  onRemoveFile,
  onSend,
  selectedFile,
}) {
  const fileInputRef = useRef(null);

  function handleKeyDown(event) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    onSend();
  }

  function handleFileChange(event) {
    onFileSelect(event.target.files?.[0] || null);
    event.target.value = "";
  }

  return (
    <form
      className="border-t border-slate-200 bg-white p-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSend();
      }}
    >
      {selectedFile || fileError ? (
        <div className="mb-2 flex flex-wrap items-center gap-2">
          {selectedFile ? (
            <span className="inline-flex max-w-full items-center gap-2 rounded-lg border border-blue-100 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-800">
              <span className="truncate">
                {selectedFile.name} ({formatFileSize(selectedFile.size)})
              </span>
              <button
                aria-label="Remove selected file"
                className="rounded text-blue-700 hover:text-blue-900 cf-focus disabled:cursor-not-allowed disabled:opacity-60"
                disabled={disabled}
                onClick={onRemoveFile}
                type="button"
              >
                <RemoveIcon />
              </button>
            </span>
          ) : null}
          {fileError ? (
            <p className="text-xs font-medium text-red-700" role="alert">
              {fileError}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="flex items-end gap-2">
        <label className="sr-only" htmlFor="class-chat-message">
          Message
        </label>
        <input
          accept=".pdf,.docx"
          className="sr-only"
          disabled={disabled}
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />
        <button
          aria-label="Attach PDF or DOCX"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 cf-focus disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-400"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          <AttachmentIcon />
        </button>
        <textarea
          className="min-h-12 max-h-36 flex-1 resize-none rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm leading-6 text-slate-950 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
          disabled={disabled}
          id="class-chat-message"
          maxLength={2000}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about class tasks, resources, or course instructions..."
          rows={2}
          value={draft}
        />
        <button
          aria-label="Send message"
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-sm transition hover:bg-blue-700 cf-focus disabled:cursor-not-allowed disabled:bg-blue-300"
          disabled={disabled || !draft.trim()}
          type="submit"
        >
          <SendIcon />
        </button>
      </div>
    </form>
  );
}

function EmptyChat({ disabled, onSuggestion }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center justify-center px-4 py-12 text-center">
      <h2 className="text-base font-semibold text-slate-900">
        Ask about this class
      </h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
        Answers are generated only from materials available in the selected class.
      </p>
      <div className="mt-5 grid w-full gap-2 sm:grid-cols-2">
        {exampleQuestions.map((question) => (
          <button
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm font-medium leading-6 text-slate-700 shadow-sm transition hover:border-blue-200 hover:bg-blue-50 cf-focus disabled:cursor-not-allowed disabled:opacity-60"
            disabled={disabled}
            key={question}
            onClick={() => onSuggestion(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

function ClassChatPage() {
  const { classId } = useParams();
  const numericClassId = Number(classId);
  const [classroom, setClassroom] = useState(null);
  const [membership, setMembership] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileError, setFileError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState(null);
  const endRef = useRef(null);

  const canChat = useMemo(() => isApproved(membership), [membership]);

  const loadClass = useCallback(async () => {
    setError(null);

    if (!Number.isFinite(numericClassId) || numericClassId <= 0) {
      setClassroom(null);
      setMembership(null);
      setError({ message: "A valid class ID is required for chat.", items: [] });
      setIsLoading(false);
      return;
    }

    try {
      const myClassrooms = await listMyClassrooms();
      const mineRecord = myClassrooms.find((item) => item.id === numericClassId);

      if (!mineRecord) {
        setClassroom(null);
        setMembership(null);
        setError({ message: "This class is not in your memberships.", items: [] });
        return;
      }

      setClassroom(mineRecord);
      setMembership(mineRecord.membership);
    } catch (apiError) {
      setError(parseApiError(apiError));
    } finally {
      setIsLoading(false);
    }
  }, [numericClassId]);

  useEffect(() => {
    setMessages([]);
    setDraft("");
    setSelectedFile(null);
    setFileError(null);
    setIsSending(false);
    setIsLoading(true);
    loadClass();
  }, [loadClass]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  function handleFileSelect(file) {
    if (!file) return;

    const validationError = validateChatFile(file);
    if (validationError) {
      setSelectedFile(null);
      setFileError(validationError);
      return;
    }

    setSelectedFile(file);
    setFileError(null);
  }

  function handleRemoveFile() {
    setSelectedFile(null);
    setFileError(null);
  }

  async function sendMessage(content = draft, file = selectedFile) {
    const message = content.trim();
    if (!message || isSending || !canChat) return;

    const validationError = validateChatFile(file);
    if (validationError) {
      setFileError(validationError);
      return;
    }

    const userMessage = createMessage("user", message, {
      file,
      fileName: file?.name,
    });
    const loadingMessage = createMessage("assistant", "", { isLoading: true });

    setDraft("");
    setFileError(null);
    setIsSending(true);
    setMessages((current) => [...current, userMessage, loadingMessage]);

    try {
      const response = file
        ? await sendClassChatFileMessage(numericClassId, message, file)
        : await sendClassChatMessage(numericClassId, message);
      setSelectedFile(null);
      setMessages((current) =>
        current.map((item) =>
          item.id === loadingMessage.id
            ? createMessage("assistant", response.answer, {
                sources: response.sources || [],
              })
            : item,
        ),
      );
    } catch (apiError) {
      const errorMessage = getChatError(apiError);
      setMessages((current) =>
        current
          .filter((item) => item.id !== loadingMessage.id)
          .map((item) =>
            item.id === userMessage.id
              ? { ...item, error: errorMessage }
              : item,
          ),
      );
    } finally {
      setIsSending(false);
    }
  }

  function retryMessage(messageToRetry) {
    setMessages((current) =>
      current.filter((message) => message.id !== messageToRetry.id),
    );
    if (messageToRetry.file) {
      setSelectedFile(messageToRetry.file);
    }
    sendMessage(messageToRetry.content, messageToRetry.file || null);
  }

  if (isLoading) {
    return <LoadingScreen message="Loading class assistant..." />;
  }

  if (error && !classroom) {
    return (
      <section className="space-y-5">
        <Alert
          title="Could not load class assistant"
          message={error.message}
          items={error.items}
        />
        <Link
          className="inline-flex rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 cf-focus"
          to="/classes"
        >
          Back to classes
        </Link>
      </section>
    );
  }

  return (
    <section className="flex min-h-[calc(100vh-7rem)] flex-col gap-5">
      <ClassWorkspaceHeader classroom={classroom} membership={membership} />

      {error ? (
        <Alert
          title="Assistant access blocked"
          message={error.message}
          items={error.items}
        />
      ) : null}

      {!canChat ? (
        <Alert
          message="The class assistant is available after a representative approves your membership."
          title={`Membership ${membership?.status}`}
          type="warning"
        />
      ) : null}

      <div className="cf-card flex min-h-[560px] flex-1 flex-col overflow-hidden">
        <div className="border-b border-slate-200 px-4 py-3">
          <p className="text-sm font-semibold text-slate-900">
            {classroom?.name || "Class"} assistant
          </p>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            Scoped to Semester {classroom?.semester}, Section {classroom?.section}.
          </p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-slate-50/70 px-3 py-4 sm:px-4">
          {messages.length === 0 ? (
            <EmptyChat disabled={!canChat || isSending} onSuggestion={sendMessage} />
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onRetry={retryMessage}
                />
              ))}
              <div ref={endRef} />
            </div>
          )}
        </div>

        <ChatComposer
          disabled={!canChat || isSending}
          draft={draft}
          fileError={fileError}
          onDraftChange={setDraft}
          onFileSelect={handleFileSelect}
          onRemoveFile={handleRemoveFile}
          onSend={() => sendMessage()}
          selectedFile={selectedFile}
        />
      </div>
    </section>
  );
}

export default ClassChatPage;

import { beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "./client.js";
import { sendClassChatFileMessage, sendClassChatMessage } from "./chat.js";

vi.mock("./client.js", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe("chat api", () => {
  beforeEach(() => {
    apiClient.post.mockReset();
    apiClient.post.mockResolvedValue({ data: { answer: "Ok", sources: [] } });
  });

  it("sends normal class chat messages as JSON", async () => {
    await sendClassChatMessage(7, "What is due?");

    expect(apiClient.post).toHaveBeenCalledWith("/classes/7/chat", {
      message: "What is due?",
    });
  });

  it("sends file chat messages as multipart form data without custom headers", async () => {
    const file = new File(["%PDF-test"], "requirements.pdf", {
      type: "application/pdf",
    });

    await sendClassChatFileMessage(7, "Summarize this", file);

    const [url, body, config] = apiClient.post.mock.calls[0];
    expect(url).toBe("/classes/7/chat/file");
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("message")).toBe("Summarize this");
    expect(body.get("file")).toBe(file);
    expect(config).toBeUndefined();
  });
});

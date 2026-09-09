from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    model_config = ConfigDict(str_strip_whitespace=True)


class ChatSource(BaseModel):
    source_type: str
    source_id: int | None = None
    title: str | None = None
    page_number: int | None = None
    preview: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource]


class RagReindexResponse(BaseModel):
    indexed_tasks: int
    indexed_courses: int
    indexed_attachments: int

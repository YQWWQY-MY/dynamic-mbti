from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class AnswerRequest(BaseModel):
    question_id: int
    # "A"/"B"/"C"/"D" 表示选择选项，其他任意文本视为自由回答
    content: str = Field(min_length=1, max_length=2000)

from datetime import datetime

from pydantic import BaseModel


class KnowledgeBaseOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    vector_namespace: str
    index_status: str
    created_at: datetime

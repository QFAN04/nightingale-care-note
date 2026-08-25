import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    clinic_id: uuid.UUID
    external_ref: str
    display_name: str
    date_of_birth: date
    sex: str
    created_at: datetime
    updated_at: datetime

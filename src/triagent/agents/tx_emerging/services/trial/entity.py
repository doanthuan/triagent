from pydantic import BaseModel
from typing import List

class PatientData(BaseModel):
    biomarkers: List[str]
    histology: str
    staging: str
    ecog_performance_status: str
    first_line_treatment: str
    second_line_treatment: str
    age: str

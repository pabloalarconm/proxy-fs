from pydantic import BaseModel
from typing import List, Optional

# FS Registry

class Contact(BaseModel):
    contact_name: str
    contact_orcid: str
    contact_email: str

class Metadata(BaseModel):
    name: str
    abbreviation: str
    description: str
    homepage: str
    contacts: List[Contact]

class RecordAssociation(BaseModel):
    linked_record_id: str
    record_assoc_label_id: int

class FairsharingRecord(BaseModel):
    metadata: Metadata
    record_type_id: int
    subject_ids: Optional[List[int]] = None
    domain_ids: Optional[List[int]] = None
    record_associations_attributes: Optional[List[RecordAssociation]] = None

class FairsharingRecordRequest(BaseModel):
    fairsharing_record: FairsharingRecord

# Sign in

class UserCredentials(BaseModel):
   login: str
   password: str

class InputBody(BaseModel):
   user: UserCredentials
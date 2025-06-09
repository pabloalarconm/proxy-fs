from pydantic import BaseModel
from typing import List, Optional

class Contact(BaseModel):
    contact_name: str
    contact_orcid: str
    contact_email: str

class AssociatedTool(BaseModel):
    name: str
    url: str

class OrganisationAttributes(BaseModel):
    organisation_type_ids: List[int]
    name: str
    homepage: str
    country_ids: List[int]
    ror_link: str

class OrganisationLink(BaseModel):
    relation: str
    is_lead: bool
    organisation_id: Optional[int] = None
    organisation_attributes: Optional[OrganisationAttributes] = None

class Metadata(BaseModel):
    name: str
    abbreviation: str
    description: str
    homepage: str
    contacts: List[Contact]
    associated_tools: Optional[List[AssociatedTool]] = None

class RecordAssociation(BaseModel):
    linked_record_id: int
    record_assoc_label_id: int

class FairsharingRecord(BaseModel):
    metadata: Metadata
    record_type_id: int
    subject_ids: Optional[List[int]] = None
    domain_ids: Optional[List[int]] = None
    record_associations_attributes: Optional[List[RecordAssociation]] = None
    object_type_ids: Optional[List[int]] = None
    organisation_links_attributes: Optional[List[OrganisationLink]] = None

class FairsharingRecordRequest(BaseModel):
    fairsharing_record: FairsharingRecord

# Sign in

class UserCredentials(BaseModel):
   login: str
   password: str

class InputBody(BaseModel):
   user: UserCredentials
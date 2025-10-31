from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Union


class Contact(BaseModel):
    contact_name: str
    contact_orcid: Optional[str] = None
    contact_email: Optional[str] = None


class AssociatedTool(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None


class AssociatedTest(BaseModel):
    url: str


class ExampleURL(BaseModel):
    url: str


class OrganisationAttributes(BaseModel):
    organisation_type_ids: Optional[List[int]] = None
    name: Optional[str] = None
    homepage: Optional[HttpUrl] = None
    country_ids: Optional[List[int]] = None
    ror_link: Optional[str] = None


class OrganisationLink(BaseModel):
    relation: Optional[str] = None
    is_lead: Optional[bool] = None
    organisation_id: Optional[int] = None
    organisation_attributes: Optional[OrganisationAttributes] = None


class RecordAssociation(BaseModel):
    linked_record_id: int
    record_assoc_label_id: int


class Metadata(BaseModel):
    name: str
    abbreviation: Optional[str] = None
    description: Optional[str] = None
    homepage: Optional[HttpUrl] = None
    contacts: List[Contact]

    associated_tools: Optional[List[AssociatedTool]] = None
    associated_tests: Optional[List[AssociatedTest]] = None
    positive_examples: Optional[List[ExampleURL]] = None
    negative_examples: Optional[List[ExampleURL]] = None


class FairsharingRecord(BaseModel):
    metadata: Metadata
    record_type_id: int

    subject_ids: Optional[List[str]] = None
    domain_ids: Optional[List[str]] = None

    record_associations_attributes: Optional[List[RecordAssociation]] = None
    object_type_ids: Optional[List[int]] = None
    organisation_links_attributes: Optional[List[OrganisationLink]] = None


class FairsharingRecordRequest(BaseModel):
    fairsharing_record: FairsharingRecord
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CompanyResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorCreate(BaseModel):
    company_id: int
    name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    tax_id: str | None = None
    country: str | None = None


class VendorResponse(BaseModel):
    id: int
    company_id: int
    name: str
    email: str | None
    tax_id: str | None
    country: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(BaseModel):
    company_id: int
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryResponse(BaseModel):
    id: int
    company_id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

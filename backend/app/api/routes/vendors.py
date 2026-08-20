from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.company import Company
from app.models.vendor import Vendor
from app.schemas.master_data import VendorCreate, VendorResponse


router = APIRouter(
    prefix="/api/vendors",
    tags=["Vendors"],
)


@router.get("/", response_model=list[VendorResponse])
def list_vendors(
    company_id: int | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Vendor).order_by(Vendor.name.asc())
    if company_id is not None:
        query = query.filter(Vendor.company_id == company_id)
    if q:
        query = query.filter(Vendor.name.ilike(f"%{q.strip()}%"))
    return query.all()


@router.post("/", response_model=VendorResponse, status_code=201)
def create_vendor(
    payload: VendorCreate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    name = payload.name.strip()
    existing = (
        db.query(Vendor)
        .filter(
            Vendor.company_id == payload.company_id,
            Vendor.name.ilike(name),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f'Vendor "{name}" already exists for this company',
        )

    vendor = Vendor(
        company_id=payload.company_id,
        name=name,
        email=payload.email,
        tax_id=payload.tax_id,
        country=payload.country,
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/{vendor_id}", response_model=VendorResponse)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor

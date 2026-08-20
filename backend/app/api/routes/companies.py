from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.company import Company
from app.schemas.master_data import CompanyCreate, CompanyResponse


router = APIRouter(
    prefix="/api/companies",
    tags=["Companies"],
)


@router.get("/", response_model=list[CompanyResponse])
def list_companies(
    q: str | None = Query(None, description="Optional name search"),
    db: Session = Depends(get_db),
):
    query = db.query(Company).order_by(Company.name.asc())
    if q:
        query = query.filter(Company.name.ilike(f"%{q.strip()}%"))
    return query.all()


@router.post("/", response_model=CompanyResponse, status_code=201)
def create_company(
    payload: CompanyCreate,
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    existing = (
        db.query(Company)
        .filter(Company.name.ilike(name))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f'Company "{name}" already exists (id={existing.id})',
        )

    company = Company(name=name)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: int,
    db: Session = Depends(get_db),
):
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

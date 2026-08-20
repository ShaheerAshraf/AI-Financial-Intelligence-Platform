from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.category import Category
from app.models.company import Company
from app.schemas.master_data import CategoryCreate, CategoryResponse


router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"],
)


@router.get("/", response_model=list[CategoryResponse])
def list_categories(
    company_id: int | None = Query(None),
    q: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Category).order_by(Category.name.asc())
    if company_id is not None:
        query = query.filter(Category.company_id == company_id)
    if q:
        query = query.filter(Category.name.ilike(f"%{q.strip()}%"))
    return query.all()


@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
):
    company = db.get(Company, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    name = payload.name.strip()
    existing = (
        db.query(Category)
        .filter(
            Category.company_id == payload.company_id,
            Category.name.ilike(name),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f'Category "{name}" already exists for this company',
        )

    category = Category(
        company_id=payload.company_id,
        name=name,
        description=payload.description,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.company import Company
from app.models.vendor import Vendor
from app.models.category import Category
from app.models.transaction import Transaction


random.seed(42)


COMPANIES = [
    "BMW Financial Services",
    "TechNova GmbH",
    "Global Logistics GmbH",
]


VENDOR_NAMES = [
    "Amazon Web Services",
    "Microsoft",
    "SAP",
    "DHL",
    "Bosch",
    "Siemens",
    "Google Cloud",
    "Oracle",
    "Adobe",
    "Accenture",
    "Deutsche Telekom",
    "Dell Technologies",
    "IBM",
    "Salesforce",
    "Atlassian",
]


CATEGORIES = [
    ("Software", "Software and cloud services"),
    ("Travel", "Business travel and accommodation"),
    ("Equipment", "Hardware and equipment"),
    ("Marketing", "Marketing and advertising"),
    ("Logistics", "Shipping and logistics"),
    ("Office", "Office supplies and expenses"),
    ("Utilities", "Electricity, internet and utilities"),
    ("Professional Services", "External professional services"),
]


DESCRIPTIONS = {
    "Software": [
        "Cloud infrastructure services",
        "Software subscription",
        "Enterprise software license",
        "Cloud hosting",
        "Developer tools subscription",
    ],
    "Travel": [
        "Business flight",
        "Hotel accommodation",
        "Business trip",
        "Train ticket",
        "Travel expenses",
    ],
    "Equipment": [
        "Laptop equipment",
        "Server hardware",
        "Office equipment",
        "Computer accessories",
        "Network equipment",
    ],
    "Marketing": [
        "Online advertising",
        "Marketing campaign",
        "Digital advertising",
        "Marketing services",
        "Advertising campaign",
    ],
    "Logistics": [
        "Shipment",
        "Freight services",
        "Warehouse transportation",
        "Delivery services",
        "International shipping",
    ],
    "Office": [
        "Office supplies",
        "Stationery",
        "Office furniture",
        "Printing services",
        "Office expenses",
    ],
    "Utilities": [
        "Electricity bill",
        "Internet services",
        "Telecommunications",
        "Utility bill",
        "Office utilities",
    ],
    "Professional Services": [
        "Consulting services",
        "Legal services",
        "Accounting services",
        "IT consulting",
        "Professional advisory services",
    ],
}


def random_date(days_back=365):
    today = date.today()
    return today - timedelta(
        days=random.randint(0, days_back)
    )


def generate_normal_amount(category):
    ranges = {
        "Software": (100, 5000),
        "Travel": (50, 2000),
        "Equipment": (500, 15000),
        "Marketing": (500, 10000),
        "Logistics": (100, 5000),
        "Office": (20, 1000),
        "Utilities": (100, 3000),
        "Professional Services": (500, 12000),
    }

    low, high = ranges[category]

    return Decimal(
        str(round(random.uniform(low, high), 2))
    )


def create_company_data(db, company_name):
    company = Company(name=company_name)

    db.add(company)
    db.flush()

    vendors = []

    for vendor_name in VENDOR_NAMES:
        vendor = Vendor(
            company_id=company.id,
            name=vendor_name,
            email=f"finance@{vendor_name.lower().replace(' ', '').replace('.', '')}.com",
            tax_id=f"DE{random.randint(100000000, 999999999)}",
            country="Germany",
        )

        db.add(vendor)
        vendors.append(vendor)

    categories = []

    for category_name, description in CATEGORIES:
        category = Category(
            company_id=company.id,
            name=category_name,
            description=description,
        )

        db.add(category)
        categories.append(category)

    db.flush()

    category_map = {
        category.name: category
        for category in categories
    }

    transactions = []

    for _ in range(1000):
        category_name = random.choice(
            list(category_map.keys())
        )

        category = category_map[category_name]

        vendor = random.choice(vendors)

        transaction = Transaction(
            company_id=company.id,
            vendor_id=vendor.id,
            category_id=category.id,
            amount=generate_normal_amount(
                category_name
            ),
            currency="EUR",
            transaction_date=random_date(),
            description=random.choice(
                DESCRIPTIONS[category_name]
            ),
            reference=f"TXN-{random.randint(100000, 999999)}",
        )

        transactions.append(transaction)

    # Inject deliberately suspicious transactions
    for i in range(10):
        category = random.choice(categories)
        vendor = random.choice(vendors)

        transaction = Transaction(
            company_id=company.id,
            vendor_id=vendor.id,
            category_id=category.id,
            amount=Decimal(
                str(round(random.uniform(50000, 150000), 2))
            ),
            currency="EUR",
            transaction_date=random_date(30),
            description="Unusually large financial transaction",
            reference=f"ANOM-{company.id}-{i}",
        )

        transactions.append(transaction)

    db.add_all(transactions)

    return company


def main():
    db = SessionLocal()

    try:
        existing_company = db.scalar(
            select(Company).limit(1)
        )

        if existing_company:
            print(
                "Database already contains company data."
            )
            print(
                "Skipping seed operation."
            )
            return

        print("Creating financial seed data...")

        for company_name in COMPANIES:
            create_company_data(
                db,
                company_name,
            )

        db.commit()

        print("Seed data created successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
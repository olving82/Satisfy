"""
Database initialization script for Satisfy application
Run this to create tables and seed initial data
"""
from models import (
    Base, Product, CustomerAccount, VendorAccount, 
    ProductInteraction, AdminAccount, init_db_engine, create_tables
)
from sqlalchemy.orm import Session
import os

def seed_initial_data(session: Session):
    """Seed the database with initial product data"""
    
    # Check if products already exist
    if session.query(Product).count() > 0:
        print("Database already has products. Skipping seed...")
        return
    
    print("Seeding database with initial products...")
    
    # Starbucks products
    products = [
        # Hot Coffees
        {"name": "Pike Place Roast", "category": "Hot Coffees", "price": 2.45, "roast": "Medium", "notes": "Smooth, balanced, cocoa & toasted nuts", "allergens": [], "caffeine_mg": 310, "vendor": "Starbucks"},
        {"name": "Caffè Americano", "category": "Hot Coffees", "price": 3.45, "roast": "Dark", "notes": "Espresso with hot water, bold", "allergens": [], "caffeine_mg": 225, "vendor": "Starbucks"},
        {"name": "Cappuccino", "category": "Hot Coffees", "price": 4.25, "roast": "Dark", "notes": "Espresso with steamed milk foam", "allergens": ["milk"], "caffeine_mg": 150, "vendor": "Starbucks"},
        {"name": "Flat White", "category": "Hot Coffees", "price": 4.75, "roast": "Dark", "notes": "Bold ristretto shots, microfoam", "allergens": ["milk"], "caffeine_mg": 195, "vendor": "Starbucks"},
        {"name": "Caffè Latte", "category": "Hot Coffees", "price": 4.45, "roast": "Dark", "notes": "Espresso with steamed milk", "allergens": ["milk"], "caffeine_mg": 150, "vendor": "Starbucks"},
        
        # Cold Coffees
        {"name": "Iced Coffee", "category": "Cold Coffees", "price": 3.25, "roast": "Medium", "notes": "Freshly brewed and chilled", "allergens": [], "caffeine_mg": 165, "vendor": "Starbucks"},
        {"name": "Cold Brew", "category": "Cold Coffees", "price": 4.45, "roast": "Dark", "notes": "Slow-steeped 20 hours, smooth", "allergens": [], "caffeine_mg": 205, "vendor": "Starbucks"},
        {"name": "Vanilla Sweet Cream Cold Brew", "category": "Cold Coffees", "price": 5.25, "roast": "Dark", "notes": "Cold brew with vanilla sweet cream", "allergens": ["milk"], "caffeine_mg": 185, "vendor": "Starbucks"},
        {"name": "Nitro Cold Brew", "category": "Cold Coffees", "price": 5.25, "roast": "Dark", "notes": "Nitrogen-infused, cascading texture", "allergens": [], "caffeine_mg": 280, "vendor": "Starbucks"},
        
        # Frappuccinos
        {"name": "Caramel Frappuccino", "category": "Frappuccinos", "price": 5.45, "roast": None, "notes": "Coffee with caramel blended with ice", "allergens": ["milk"], "caffeine_mg": 100, "vendor": "Starbucks"},
        {"name": "Mocha Frappuccino", "category": "Frappuccinos", "price": 5.45, "roast": None, "notes": "Coffee and chocolate blended", "allergens": ["milk"], "caffeine_mg": 100, "vendor": "Starbucks"},
        {"name": "Java Chip Frappuccino", "category": "Frappuccinos", "price": 5.75, "roast": None, "notes": "Coffee with chocolate chips", "allergens": ["milk"], "caffeine_mg": 105, "vendor": "Starbucks"},
        {"name": "Vanilla Bean Frappuccino", "category": "Frappuccinos", "price": 5.25, "roast": None, "notes": "Vanilla bean crème, no coffee", "allergens": ["milk"], "caffeine_mg": 0, "vendor": "Starbucks"},
        
        # Hot Teas
        {"name": "Chai Tea Latte", "category": "Hot Teas", "price": 4.65, "roast": None, "notes": "Spiced black tea with steamed milk", "allergens": ["milk"], "caffeine_mg": 95, "vendor": "Starbucks"},
        {"name": "Earl Grey Tea", "category": "Hot Teas", "price": 2.95, "roast": None, "notes": "Classic bergamot black tea", "allergens": [], "caffeine_mg": 40, "vendor": "Starbucks"},
        {"name": "Jade Citrus Mint Tea", "category": "Hot Teas", "price": 2.95, "roast": None, "notes": "Green tea with spearmint & lemongrass", "allergens": [], "caffeine_mg": 25, "vendor": "Starbucks"},
        
        # Hot Drinks (non-coffee)
        {"name": "Hot Chocolate", "category": "Hot Drinks", "price": 3.95, "roast": None, "notes": "Steamed milk with mocha sauce", "allergens": ["milk"], "caffeine_mg": 25, "vendor": "Starbucks"},
        {"name": "Caramel Apple Spice", "category": "Hot Drinks", "price": 4.45, "roast": None, "notes": "Steamed apple juice with cinnamon", "allergens": [], "caffeine_mg": 0, "vendor": "Starbucks"},
        
        # Iced Teas
        {"name": "Iced Black Tea", "category": "Iced Teas", "price": 3.25, "roast": None, "notes": "Freshly brewed Teavana tea", "allergens": [], "caffeine_mg": 25, "vendor": "Starbucks"},
        {"name": "Iced Green Tea", "category": "Iced Teas", "price": 3.25, "roast": None, "notes": "Refreshing green tea", "allergens": [], "caffeine_mg": 25, "vendor": "Starbucks"},
        {"name": "Iced Passion Tango Tea", "category": "Iced Teas", "price": 3.25, "roast": None, "notes": "Herbal tea, hibiscus notes", "allergens": [], "caffeine_mg": 0, "vendor": "Starbucks"},
        
        # Refreshers
        {"name": "Strawberry Açaí Refresher", "category": "Refreshers", "price": 4.95, "roast": None, "notes": "Strawberry, açaí, green coffee extract", "allergens": [], "caffeine_mg": 45, "vendor": "Starbucks"},
        {"name": "Mango Dragonfruit Refresher", "category": "Refreshers", "price": 4.95, "roast": None, "notes": "Mango, dragonfruit, tropical", "allergens": [], "caffeine_mg": 45, "vendor": "Starbucks"},
        {"name": "Pink Drink", "category": "Refreshers", "price": 5.25, "roast": None, "notes": "Strawberry Açaí with coconut milk", "allergens": ["coconut"], "caffeine_mg": 45, "vendor": "Starbucks"},
        
        # Espresso Shots
        {"name": "Espresso Shot", "category": "Espresso", "price": 2.45, "roast": "Dark", "notes": "Rich, full-bodied espresso", "allergens": [], "caffeine_mg": 75, "vendor": "Starbucks"},
        {"name": "Espresso Macchiato", "category": "Espresso", "price": 3.25, "roast": "Dark", "notes": "Espresso marked with foam", "allergens": ["milk"], "caffeine_mg": 75, "vendor": "Starbucks"},
        
        # Seasonal/Specialty
        {"name": "Pumpkin Spice Latte", "category": "Hot Coffees", "price": 5.75, "roast": "Dark", "notes": "Espresso with pumpkin, cinnamon", "allergens": ["milk"], "caffeine_mg": 150, "vendor": "Starbucks"},
        {"name": "Peppermint Mocha", "category": "Hot Coffees", "price": 5.75, "roast": "Dark", "notes": "Espresso, mocha, peppermint", "allergens": ["milk"], "caffeine_mg": 175, "vendor": "Starbucks"},
        {"name": "Caramel Brulée Latte", "category": "Hot Coffees", "price": 5.75, "roast": "Dark", "notes": "Espresso with caramel brulée", "allergens": ["milk"], "caffeine_mg": 150, "vendor": "Starbucks"},
        
        # Food/Bakery
        {"name": "Butter Croissant", "category": "Bakery", "price": 3.25, "roast": None, "notes": "Flaky, buttery pastry", "allergens": ["wheat", "milk", "eggs"], "caffeine_mg": 0, "vendor": "Starbucks"},
        {"name": "Blueberry Muffin", "category": "Bakery", "price": 3.45, "roast": None, "notes": "Moist with real blueberries", "allergens": ["wheat", "milk", "eggs"], "caffeine_mg": 0, "vendor": "Starbucks"},
        {"name": "Avocado Spread", "category": "Food", "price": 6.25, "roast": None, "notes": "Multigrain bagel with avocado", "allergens": ["wheat"], "caffeine_mg": 0, "vendor": "Starbucks"},
        {"name": "Bacon Gouda Sandwich", "category": "Food", "price": 5.95, "roast": None, "notes": "Bacon, gouda, egg on artisan roll", "allergens": ["wheat", "milk", "eggs"], "caffeine_mg": 0, "vendor": "Starbucks"},
        
        # Non-Starbucks vendors
        {"name": "Cortado", "category": "Hot Coffees", "price": 3.75, "roast": "Medium", "notes": "Espresso cut with steamed milk", "allergens": ["milk"], "caffeine_mg": 136, "vendor": "Blue Bottle Coffee"},
        {"name": "New Orleans Iced Coffee", "category": "Cold Coffees", "price": 4.50, "roast": "Dark", "notes": "Coffee and chicory, sweet", "allergens": ["milk"], "caffeine_mg": 170, "vendor": "Blue Bottle Coffee"},
    ]
    
    for product_data in products:
        product = Product(**product_data)
        session.add(product)
    
    session.commit()
    print(f"Added {len(products)} products to database")

def seed_admin_account(session: Session):
    """Create the super admin account"""
    
    # Check if admin already exists
    existing_admin = session.query(AdminAccount).filter_by(username='olving82@gmail.com').first()
    if existing_admin:
        print("Super admin already exists. Skipping...")
        return
    
    print("Creating super admin account...")
    
    admin = AdminAccount(
        username='olving82@gmail.com',
        password=os.environ.get('ADMIN_PASSWORD', 'admin123'),
        role='super_admin',
        name='Super Administrator'
    )
    session.add(admin)
    session.commit()
    print("Super admin account created")

def main():
    """Main initialization function"""
    print("=" * 60)
    print("Satisfy Database Initialization")
    print("=" * 60)
    
    # Get database URL
    database_url = os.environ.get('DATABASE_URL', 'postgresql://localhost/satisfy')
    print(f"\nDatabase URL: {database_url}")
    
    try:
        # Initialize database engine
        print("\nInitializing database connection...")
        engine, SessionLocal = init_db_engine(database_url)
        
        # Create all tables
        print("Creating database tables...")
        create_tables(engine)
        print("✓ Tables created successfully")
        
        # Create session and seed data
        session = SessionLocal()
        
        try:
            seed_initial_data(session)
            seed_admin_account(session)
            
            print("\n" + "=" * 60)
            print("✓ Database initialization complete!")
            print("=" * 60)
            print("\nYou can now run your application:")
            print("  python app.py")
            print("\nDefault admin credentials:")
            print("  Username: olving82@gmail.com")
            print("  Password: admin123 (or set ADMIN_PASSWORD env var)")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"\n✗ Error initializing database: {e}")
        print("\nMake sure PostgreSQL is running and the database exists:")
        print("  createdb satisfy")
        raise

if __name__ == '__main__':
    main()

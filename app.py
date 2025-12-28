from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import os
import requests
import json
from datetime import datetime, timedelta
from models import (
    Product, CustomerAccount, VendorAccount, ProductInteraction, AdminAccount,
    init_db_engine, Base
)
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import func
from email_service import (
    send_email, get_vendor_approval_email, get_vendor_rejection_email,
    get_vendor_blocked_email, get_vendor_suspended_email, get_vendor_restored_email
)

app = Flask(__name__, static_folder='static')
CORS(app)

# App configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/satisfy')
engine, SessionLocal = init_db_engine(DATABASE_URL)
db_session = scoped_session(SessionLocal)

# Cleanup database session after each request
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# Facebook OAuth configuration
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')
FACEBOOK_REDIRECT_URI = os.environ.get('FACEBOOK_REDIRECT_URI', 'http://localhost:5000/auth/facebook/callback')

# Ollama configuration
OLLAMA_API = "http://host.docker.internal:11434"

# Vendor settings
SHOW_PRICES = os.environ.get('SHOW_PRICES', 'false').lower() == 'true'

# Helper function to check vendor authentication
def require_vendor_auth():
    """Check if vendor is authenticated via Facebook Business"""
    vendor_id = session.get('vendor_id')
    if not vendor_id:
        return jsonify({"error": "Unauthorized. Please login with Facebook Business account."}), 401
    
    business_name = session.get('business_name')
    if business_name:
        vendor = db_session.query(VendorAccount).filter_by(business_name=business_name).first()
        if vendor:
            if vendor.status == 'blocked':
                return jsonify({
                    "error": "Account Blocked", 
                    "message": f"Your account has been blocked. Reason: {vendor.block_reason or 'Contact administrator'}"
                }), 403
            elif vendor.status == 'suspended':
                return jsonify({
                    "error": "Account Suspended",
                    "message": f"Your account is temporarily suspended. Reason: {vendor.suspend_reason or 'Payment required'}"
                }), 403
    
    return None

def require_admin_auth():
    """Check if admin is authenticated"""
    admin_id = session.get('admin_id')
    if not admin_id:
        return jsonify({"error": "Unauthorized. Admin login required."}), 401
    return None

# Helper function to convert SQLAlchemy model to dict
def model_to_dict(model):
    """Convert SQLAlchemy model to dictionary"""
    if model is None:
        return None
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, datetime):
            result[column.name] = value.isoformat()
        else:
            result[column.name] = value
    return result

# ============= ROUTES =============

@app.route('/')
def home():
    """Serve main customer page"""
    return send_from_directory('static', 'index.html')

@app.route('/vendor')
def vendor_portal():
    """Serve vendor portal page"""
    return send_from_directory('static', 'vendor.html')

@app.route('/dashboard')
def admin_dashboard():
    """Serve admin dashboard page (requires authentication)"""
    if not session.get('admin_id'):
        return redirect('/admin-login')
    return send_from_directory('static', 'dashboard.html')

@app.route('/admin-login')
def admin_login_page():
    """Serve admin login page"""
    return send_from_directory('static', 'admin-login.html')

# ============= ADMIN AUTH ENDPOINTS =============

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    # Find admin in database
    admin = db_session.query(AdminAccount).filter_by(username=username, password=password).first()
    
    if admin:
        session['admin_id'] = admin.username
        session['admin_role'] = admin.role
        session['admin_name'] = admin.name
        session.permanent = True
        return jsonify({
            "success": True,
            "message": "Login successful",
            "admin": {
                "username": admin.username,
                "role": admin.role,
                "name": admin.name
            }
        })
    else:
        return jsonify({"error": "Invalid username or password"}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout endpoint"""
    session.pop('admin_id', None)
    session.pop('admin_role', None)
    session.pop('admin_name', None)
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/api/admin/session', methods=['GET'])
def admin_session():
    """Check admin session status"""
    if session.get('admin_id'):
        return jsonify({
            "authenticated": True,
            "username": session.get('admin_id'),
            "role": session.get('admin_role'),
            "name": session.get('admin_name')
        })
    else:
        return jsonify({"authenticated": False}), 401

@app.route('/api/admin/change-password', methods=['POST'])
def change_admin_password():
    """Change admin password"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "All fields are required"}), 400
    
    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match"}), 400
    
    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    
    admin_username = session.get('admin_id')
    admin = db_session.query(AdminAccount).filter_by(username=admin_username).first()
    
    if not admin:
        return jsonify({"error": "Admin account not found"}), 404
    
    if admin.password != current_password:
        return jsonify({"error": "Current password is incorrect"}), 401
    
    admin.password = new_password
    db_session.commit()
    
    return jsonify({
        "success": True,
        "message": "Password changed successfully"
    })

# ============= PRODUCT ENDPOINTS =============

@app.route('/api/products', methods=['GET'])
def get_products():
    """Get all products from database"""
    products = db_session.query(Product).all()
    return jsonify([model_to_dict(p) for p in products])

@app.route('/api/vendor/products', methods=['GET'])
def get_vendor_products():
    """Get products for authenticated vendor"""
    auth_error = require_vendor_auth()
    if auth_error:
        return auth_error
    
    vendor_business_name = session.get('business_name')
    products = db_session.query(Product).filter_by(vendor=vendor_business_name).all()
    return jsonify([model_to_dict(p) for p in products])

@app.route('/api/vendor/products', methods=['POST'])
def create_product():
    """Create new product"""
    auth_error = require_vendor_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    vendor_business_name = session.get('business_name')
    
    product = Product(
        name=data.get('name'),
        category=data.get('category'),
        price=float(data.get('price', 0)),
        roast=data.get('roast'),
        notes=data.get('notes'),
        allergens=data.get('allergens', []),
        caffeine_mg=data.get('caffeine_mg'),
        vendor=vendor_business_name
    )
    
    db_session.add(product)
    db_session.commit()
    
    return jsonify(model_to_dict(product)), 201

@app.route('/api/vendor/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update existing product"""
    auth_error = require_vendor_auth()
    if auth_error:
        return auth_error
    
    vendor_business_name = session.get('business_name')
    product = db_session.query(Product).filter_by(id=product_id, vendor=vendor_business_name).first()
    
    if not product:
        return jsonify({"error": "Product not found or unauthorized"}), 404
    
    data = request.get_json()
    product.name = data.get('name', product.name)
    product.category = data.get('category', product.category)
    product.price = float(data.get('price', product.price))
    product.roast = data.get('roast', product.roast)
    product.notes = data.get('notes', product.notes)
    product.allergens = data.get('allergens', product.allergens)
    product.caffeine_mg = data.get('caffeine_mg', product.caffeine_mg)
    
    db_session.commit()
    
    return jsonify(model_to_dict(product))

@app.route('/api/vendor/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product"""
    auth_error = require_vendor_auth()
    if auth_error:
        return auth_error
    
    vendor_business_name = session.get('business_name')
    product = db_session.query(Product).filter_by(id=product_id, vendor=vendor_business_name).first()
    
    if not product:
        return jsonify({"error": "Product not found or unauthorized"}), 404
    
    db_session.delete(product)
    db_session.commit()
    
    return jsonify({"message": "Product deleted successfully"})

# ============= PRODUCT INTERACTION ENDPOINTS =============

@app.route('/api/product-interaction', methods=['POST'])
def track_product_interaction():
    """Track customer likes/dislikes for products"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        interaction_type = data.get('type')
        customer_email = data.get('customer_email')
        
        if not product_id or not interaction_type:
            return jsonify({"error": "Missing required fields"}), 400
        
        interaction = ProductInteraction(
            product_id=product_id,
            interaction_type=interaction_type,
            customer_email=customer_email
        )
        
        db_session.add(interaction)
        db_session.commit()
        
        return jsonify({"success": True, "message": "Interaction recorded"})
    
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/vendor/product-stats', methods=['GET'])
def get_product_stats():
    """Get product statistics for vendor"""
    auth_error = require_vendor_auth()
    if auth_error:
        return auth_error
    
    vendor_business_name = session.get('business_name')
    products = db_session.query(Product).filter_by(vendor=vendor_business_name).all()
    
    stats = []
    for product in products:
        likes = db_session.query(ProductInteraction).filter_by(
            product_id=product.id, 
            interaction_type='like'
        ).count()
        
        dislikes = db_session.query(ProductInteraction).filter_by(
            product_id=product.id, 
            interaction_type='dislike'
        ).count()
        
        stats.append({
            'id': product.id,
            'name': product.name,
            'category': product.category,
            'likes': likes,
            'dislikes': dislikes
        })
    
    stats.sort(key=lambda x: x['likes'], reverse=True)
    return jsonify(stats)

# ============= CUSTOMER MANAGEMENT ENDPOINTS =============

@app.route('/api/admin/customers', methods=['GET'])
def get_customers():
    """Get all customer accounts"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    customers = db_session.query(CustomerAccount).all()
    return jsonify([model_to_dict(c) for c in customers])

@app.route('/api/admin/customers', methods=['POST'])
def create_customer():
    """Create new customer account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    customer = CustomerAccount(
        email=data.get('email', ''),
        name=data.get('name', ''),
        allergies=data.get('allergies', []),
        avoid_list=data.get('avoid_list', []),
        liked_drinks=data.get('liked_drinks', []),
        disliked_drinks=data.get('disliked_drinks', []),
        preferred_vendors=data.get('preferred_vendors', [])
    )
    
    db_session.add(customer)
    db_session.commit()
    
    return jsonify(model_to_dict(customer)), 201

@app.route('/api/admin/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """Update customer account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    customer = db_session.query(CustomerAccount).filter_by(id=customer_id).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    data = request.get_json()
    customer.email = data.get('email', customer.email)
    customer.name = data.get('name', customer.name)
    customer.allergies = data.get('allergies', customer.allergies)
    customer.avoid_list = data.get('avoid_list', customer.avoid_list)
    customer.liked_drinks = data.get('liked_drinks', customer.liked_drinks)
    customer.disliked_drinks = data.get('disliked_drinks', customer.disliked_drinks)
    customer.preferred_vendors = data.get('preferred_vendors', customer.preferred_vendors)
    
    db_session.commit()
    
    return jsonify(model_to_dict(customer))

@app.route('/api/admin/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    """Delete customer account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    customer = db_session.query(CustomerAccount).filter_by(id=customer_id).first()
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    db_session.delete(customer)
    db_session.commit()
    
    return jsonify({"message": "Customer deleted successfully"})

# ============= VENDOR MANAGEMENT ENDPOINTS =============

@app.route('/api/admin/vendors', methods=['GET'])
def get_vendors():
    """Get all vendor accounts"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    vendors = db_session.query(VendorAccount).all()
    return jsonify([model_to_dict(v) for v in vendors])

@app.route('/api/admin/vendors', methods=['POST'])
def create_vendor():
    """Create new vendor account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    data = request.get_json()
    vendor = VendorAccount(
        business_name=data.get('business_name'),
        contact_person=data.get('contact_person'),
        email=data.get('email'),
        phone=data.get('phone'),
        facebook_business_id=data.get('facebook_business_id'),
        status=data.get('status', 'pending')
    )
    
    db_session.add(vendor)
    db_session.commit()
    
    return jsonify(model_to_dict(vendor)), 201

@app.route('/api/admin/vendors/<int:vendor_id>', methods=['PUT'])
def update_vendor(vendor_id):
    """Update vendor account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    data = request.get_json()
    vendor.business_name = data.get('business_name', vendor.business_name)
    vendor.contact_person = data.get('contact_person', vendor.contact_person)
    vendor.email = data.get('email', vendor.email)
    vendor.phone = data.get('phone', vendor.phone)
    vendor.facebook_business_id = data.get('facebook_business_id', vendor.facebook_business_id)
    vendor.status = data.get('status', vendor.status)
    
    db_session.commit()
    
    return jsonify(model_to_dict(vendor))

@app.route('/api/admin/vendors/<int:vendor_id>', methods=['DELETE'])
def delete_vendor(vendor_id):
    """Delete vendor account"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    db_session.delete(vendor)
    db_session.commit()
    
    return jsonify({"message": "Vendor deleted successfully"})

@app.route('/api/admin/vendors/<int:vendor_id>/approve', methods=['POST'])
def approve_vendor(vendor_id):
    """Approve vendor and send verification email"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    vendor.status = 'approved'
    db_session.commit()
    
    # Send approval email
    subject, body, html_body = get_vendor_approval_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor'
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor approved and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

@app.route('/api/admin/vendors/<int:vendor_id>/reject', methods=['POST'])
def reject_vendor(vendor_id):
    """Reject vendor application"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    data = request.get_json()
    reason = data.get('reason', 'Application did not meet requirements')
    
    vendor.status = 'rejected'
    vendor.reject_reason = reason
    db_session.commit()
    
    # Send rejection email
    subject, body, html_body = get_vendor_rejection_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor',
        reason
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor rejected and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

@app.route('/api/admin/vendors/<int:vendor_id>/block', methods=['POST'])
def block_vendor(vendor_id):
    """Block vendor (admin override)"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    data = request.get_json()
    reason = data.get('reason', 'Blocked by administrator')
    
    vendor.status = 'blocked'
    vendor.block_reason = reason
    db_session.commit()
    
    # Send block notification email
    subject, body, html_body = get_vendor_blocked_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor',
        reason
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor blocked and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

@app.route('/api/admin/vendors/<int:vendor_id>/unblock', methods=['POST'])
def unblock_vendor(vendor_id):
    """Unblock vendor (admin override)"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    vendor.status = 'approved'
    vendor.block_reason = None
    db_session.commit()
    
    # Send restore notification email
    subject, body, html_body = get_vendor_restored_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor'
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor unblocked and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

@app.route('/api/admin/vendors/<int:vendor_id>/suspend', methods=['POST'])
def suspend_vendor(vendor_id):
    """Suspend vendor temporarily"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    data = request.get_json()
    reason = data.get('reason', 'Payment required')
    
    vendor.status = 'suspended'
    vendor.suspend_reason = reason
    db_session.commit()
    
    # Send suspension notification email
    subject, body, html_body = get_vendor_suspended_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor',
        reason
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor suspended and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

@app.route('/api/admin/vendors/<int:vendor_id>/unsuspend', methods=['POST'])
def unsuspend_vendor(vendor_id):
    """Restore suspended vendor"""
    auth_error = require_admin_auth()
    if auth_error:
        return auth_error
    
    vendor = db_session.query(VendorAccount).filter_by(id=vendor_id).first()
    if not vendor:
        return jsonify({"error": "Vendor not found"}), 404
    
    vendor.status = 'approved'
    vendor.suspend_reason = None
    db_session.commit()
    
    # Send restore notification email
    subject, body, html_body = get_vendor_restored_email(
        vendor.business_name,
        vendor.contact_person or 'Vendor'
    )
    email_result = send_email(vendor.email, subject, body, html_body)
    
    return jsonify({
        "message": "Vendor unsuspended and notification email sent",
        "vendor": model_to_dict(vendor),
        "email_status": email_result
    })

# ============= AI RECOMMENDATION ENDPOINT =============

@app.route('/api/ai-recommend', methods=['POST'])
def ai_recommend():
    """Get AI-powered recommendations using local Ollama"""
    data = request.get_json()
    user_query = data.get('query', '')
    user_id = data.get('user_id', 'guest')
    disliked_ids = data.get('disliked_ids', [])
    allergies = data.get('allergies', [])
    avoid_list = data.get('avoid_list', [])
    preferred_vendors = data.get('preferred_vendors', [])
    category_filter = data.get('category', None)
    
    # Get all products from database
    all_products = db_session.query(Product).all()
    filtered_products = [model_to_dict(p) for p in all_products]
    
    # Filter by category if specified
    if category_filter:
        filtered_products = [p for p in filtered_products if p['category'] == category_filter]
    
    # Filter out disliked drinks
    filtered_products = [p for p in filtered_products if p['id'] not in disliked_ids]
    
    # Filter out drinks containing allergens (check name and notes)
    if allergies:
        allergy_filtered = []
        for p in filtered_products:
            product_text = f"{p['name']} {p.get('notes', '')}".lower()
            has_allergen = False
            for allergen in allergies:
                if allergen.lower() in product_text:
                    has_allergen = True
                    break
            if not has_allergen:
                allergy_filtered.append(p)
        filtered_products = allergy_filtered
    
    # Filter out drinks containing avoid items (check name, notes, category)
    if avoid_list:
        avoid_filtered = []
        for p in filtered_products:
            product_text = f"{p['name']} {p.get('notes', '')} {p['category']}".lower()
            should_avoid = False
            for avoid_item in avoid_list:
                if avoid_item.lower() in product_text:
                    should_avoid = True
                    break
            if not should_avoid:
                avoid_filtered.append(p)
        filtered_products = avoid_filtered
    
    if not filtered_products:
        return jsonify({
            "user_id": user_id,
            "query": user_query,
            "recommendations": [],
            "reasoning": "No drinks match your preferences and restrictions. Please adjust your filters.",
            "ai_model": "deepseek-r1:8b (Local)"
        })
    
    # Build context for AI with filtered products (include notes for better matching)
    products_text = "\n".join([
        f"{p['id']}. {p['name']} ({p['category']}) - {p.get('notes', '')}"
        for p in filtered_products
    ])
    
    # Add preferred vendors context if any
    vendor_note = ""
    if preferred_vendors:
        vendor_note = f"\n\nUSER PREFERS THESE VENDORS: {', '.join(preferred_vendors)}. Prioritize drinks from these brands when possible."
    
    category_note = ""
    if category_filter:
        category_note = f"\n\nONLY RECOMMEND FROM CATEGORY: {category_filter}"
    
    # Add allergen substitution suggestions
    allergen_note = ""
    if allergies:
        allergen_note = f"\n\n⚠️ USER HAS ALLERGIES: {', '.join(allergies)}"
        allergen_note += "\nIMPORTANT: Mention substitution options in your reasoning:"
        if any('milk' in a.lower() or 'dairy' in a.lower() for a in allergies):
            allergen_note += "\n- Milk → Can substitute with: Oat milk, Almond milk, Soy milk, Coconut milk"
        if any('soy' in a.lower() for a in allergies):
            allergen_note += "\n- Soy → Can substitute with: Oat milk, Almond milk, Coconut milk"
        if any('nut' in a.lower() for a in allergies):
            allergen_note += "\n- Nuts → Avoid almond milk, use oat milk or soy milk instead"
        if any('chocolate' in a.lower() or 'cocoa' in a.lower() for a in allergies):
            allergen_note += "\n- Chocolate → Can try vanilla, caramel, or fruit-based drinks"
        if any('caffeine' in a.lower() for a in allergies):
            allergen_note += "\n- Caffeine → Suggest decaf versions, herbal teas, or non-coffee drinks"
    
    prompt = f"""Recommend drinks from this menu for: "{user_query}"{vendor_note}{category_note}{allergen_note}

Menu (format: ID. Name (Category) - Ingredients/Flavors):
{products_text}

CRITICAL INSTRUCTIONS:
- SEARCH CAREFULLY: Match the query against drink names, categories, AND ingredients/flavors in the notes
- If user searches for an ingredient (strawberry, chocolate, milk, vanilla, etc), check ALL notes fields
- FIND ALL MATCHES: Include EVERY drink that matches the query, not just one
- For ingredient searches like "strawberry", look for it in: drink name, notes/description

CAFFEINE KNOWLEDGE (use this for caffeine/energy/strong queries):
- HIGHEST CAFFEINE: Espresso shots (category: Espresso), Americano, Cold Brew, Nitro Cold Brew
- HIGH CAFFEINE: Most Hot Coffees, Cold Coffees with espresso (Latte, Cappuccino, Macchiato, Mocha)
- MEDIUM CAFFEINE: Coffee Frappuccinos, Iced Coffee
- LOW/NO CAFFEINE: Teas (except matcha), Refreshers, Hot Chocolate, Vanilla Bean Frappuccino
- When user asks for "strong", "caffeine", "energy", or "wake up" → recommend Espresso category first!

Rate drinks' match confidence on scale 1-7:
  * 7 = Perfect match (ingredient in name or main flavor)
  * 6 = Very good match (ingredient in notes/closely related)
  * 5 = Good match (same category or complementary)
  * 4 or below = Weak match
- Include drinks with confidence 5, 6, or 7 in your recommendations
- Include ALL qualifying matches (don't limit to just 1-2 drinks)
- Sort by confidence (highest first)

Reply ONLY with JSON: {{"recommendations": [{{"id": id, "confidence": 5-7}}], "reasoning": "brief explanation of all matches found"}}"""

    try:
        # Call Ollama API with increased timeout
        response = requests.post(
            f"{OLLAMA_API}/api/generate",
            json={
                "model": "deepseek-r1:8b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.7,
                    "num_predict": 500
                }
            },
            timeout=90
        )
        
        if response.status_code == 200:
            ai_response = response.json()
            ai_text = ai_response.get('response', '{}')
            
            print(f"DEBUG: AI raw response: {ai_text[:500]}")
            print(f"DEBUG: AI full response length: {len(ai_text)}")
            
            try:
                result = json.loads(ai_text)
                print(f"DEBUG: JSON parsed successfully!")
                recommendations_data = result.get('recommendations', [])
                reasoning = result.get('reasoning', 'AI-powered recommendations based on your preferences.')
                
                print(f"DEBUG: Recommendations data: {recommendations_data}")
                print(f"DEBUG: Reasoning: {reasoning}")
                
                # Filter: confidence 5-7 (good to perfect matches)
                high_confidence = []
                for rec in recommendations_data:
                    if isinstance(rec, dict):
                        rec_id = rec.get('id')
                        # Convert string ID to int if needed
                        if isinstance(rec_id, str):
                            try:
                                rec_id = int(rec_id)
                            except ValueError:
                                continue
                        confidence = rec.get('confidence', 0)
                        if confidence >= 5 and confidence <= 7:
                            high_confidence.append({'id': rec_id, 'confidence': confidence})
                
                # If no matches, return message
                if not high_confidence:
                    return jsonify({
                        "user_id": user_id,
                        "query": user_query,
                        "recommendations": [],
                        "reasoning": "No strong matches found (confidence 5+/7). Try adjusting your search or preferences.",
                        "ai_model": "deepseek-r1:8b (Local)"
                    })
                
                # Get full product details
                recommended_products = []
                for rec in high_confidence:
                    product = next((p for p in filtered_products if p['id'] == rec['id']), None)
                    if product:
                        product_with_confidence = product.copy()
                        product_with_confidence['confidence'] = rec['confidence']
                        recommended_products.append(product_with_confidence)
                
                print(f"DEBUG: high_confidence IDs: {[r['id'] for r in high_confidence]}")
                print(f"DEBUG: recommended_products count: {len(recommended_products)}")
                print(f"DEBUG: recommended_products names: {[p['name'] for p in recommended_products]}")
                
                return jsonify({
                    "user_id": user_id,
                    "query": user_query,
                    "recommendations": recommended_products,
                    "reasoning": reasoning,
                    "ai_model": "deepseek-r1:8b (Local)"
                })
            except json.JSONDecodeError as e:
                print(f"DEBUG: JSON Parse Error: {e}")
                print(f"DEBUG: Full AI text: {ai_text}")
                return jsonify({
                    "user_id": user_id,
                    "query": user_query,
                    "recommendations": filtered_products[:3],
                    "reasoning": "Using fallback recommendations",
                    "note": "AI response parsing failed"
                })
        else:
            return jsonify({"error": "Ollama API error", "status": response.status_code}), 500
            
    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Cannot connect to Ollama. Make sure Ollama is running.",
            "details": str(e)
        }), 500

# ============= MOCK VENDOR LOGIN (for development) =============

@app.route('/api/vendor/mock-login', methods=['POST'])
def mock_vendor_login():
    """Mock login for development/testing"""
    data = request.get_json()
    business_name = data.get('business_name', 'Starbucks')
    
    # Check if vendor exists, if not create it
    vendor = db_session.query(VendorAccount).filter_by(business_name=business_name).first()
    if not vendor:
        vendor = VendorAccount(
            business_name=business_name,
            contact_person='Test User',
            email=f'{business_name.lower().replace(" ", "")}@test.com',
            status='approved'
        )
        db_session.add(vendor)
        db_session.commit()
    
    session['vendor_id'] = vendor.id
    session['business_name'] = vendor.business_name
    session.permanent = True
    
    return jsonify({
        "success": True,
        "message": f"Mock login successful for {business_name}",
        "vendor": model_to_dict(vendor)
    })

if __name__ == '__main__':
    print("Starting Satisfy application with PostgreSQL database...")
    print(f"Database: {DATABASE_URL}")
    app.run(host='0.0.0.0', port=5000, debug=True)

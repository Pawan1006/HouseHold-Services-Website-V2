from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from .models import User, Professional, Admin, Service
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from . import db
from flask_login import login_user, login_required, logout_user, current_user
import os

# Create a Blueprint for authentication routes
auth = Blueprint('auth', __name__)


# login route
@auth.route('/', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")

            user = User.query.filter_by(email=email).first()
            admin = Admin.query.filter_by(email=email).first()
            prof = Professional.query.filter_by(email=email).first()

            if user:
                if user.status != "blocked" and check_password_hash(user.password, password):
                    login_user(user, remember=True)
                    flash('Logged in successfully!', 'success')
                    return jsonify({"success": True, "redirect_url": url_for("views.customer_dashboard")})
                return jsonify({"success": False, "message": "Incorrect password or account blocked."}), 401
            elif admin and check_password_hash(admin.password, password):
                login_user(admin, remember=True)
                flash('Logged in successfully!', 'success')
                return jsonify({"success": True, "redirect_url": url_for("views.admin_dashboard")})
            elif prof:
                if prof.status != "blocked" and check_password_hash(prof.password, password):
                    login_user(prof, remember=True)
                    flash('Logged in successfully!', 'success')
                    return jsonify({"success": True, "redirect_url": url_for("views.professional_dashboard")})
                return jsonify({"success": False, "message": "Incorrect password or account blocked."}), 401
            return jsonify({"success": False, "message": "User does not exist."}), 404
        return jsonify({"success": False, "message": "Request must be in JSON format."}), 400

    return render_template('login.html')


# Define the logout route
@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", category="success")
    return redirect(url_for("auth.login"))



@auth.route('/sign-up', methods=['GET', 'POST'])
def customerSignup():
    if request.method == 'POST':
        # Get JSON data sent from the frontend
        data = request.get_json()
        
        # Extract form data
        email = data.get('email')
        fullName = data.get('fullName')
        address = data.get('address')
        pincode = data.get('pincode')
        password1 = data.get('password1')
        password2 = data.get('password2')

        # Check if email already exists
        user = User.query.filter_by(email=email).first()

        # Validation checks
        if user:
            return jsonify({"success": False, "message": "Email already exists."}), 400
        elif len(email) <= 5:
            return jsonify({"success": False, "message": "Email must be greater than 5 characters."}), 400
        elif len(fullName) < 2:
            return jsonify({"success": False, "message": "Name must be greater than 1 character."}), 400
        elif len(address) <= 2:
            return jsonify({"success": False, "message": "Address must be greater than 2 characters."}), 400
        elif len(pincode) != 6 or not pincode.isdigit():
            return jsonify({"success": False, "message": "Pin Code must be exactly 6 digits."}), 400
        elif len(password1) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        elif password1 != password2:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400
        else:
            # Create a new user if all validation passes
            new_user = User(
                email=email,
                full_name=fullName,
                address=address,
                pincode=pincode,
                password=generate_password_hash(password1, method='pbkdf2:sha256')
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Registration successfull! Please login.', 'success')
            return jsonify({"success": True, "redirect_url": url_for('auth.login')}), 200

    # Handle GET request
    return render_template('customerSignup.html')



# Define the signup route for professionals
@auth.route("/professional-signUp", methods=["GET", "POST"])
def professionalSignup():
    services = Service.query.all()
    services_json = [{"service": service.service} for service in services]
    base_price = None

    if request.method == "POST":
        email = request.form.get("email")
        fullName = request.form.get("fullName")
        address = request.form.get("address")
        service = request.form.get("service")
        experience = request.form.get("experience")
        pincode = request.form.get("pincode")
        password1 = request.form.get("password1")
        password2 = request.form.get("password2")
        pdf_file = request.files.get("pdf_file")
        price = request.form.get("price")

        # Fetch base price for selected service
        service_data = Service.query.filter_by(service=service).first()
        if service_data:
            base_price = service_data.price

        # Form validation
        user = Professional.query.filter_by(email=email).first()
        if user:
            return jsonify({"success": False, "message": "Email already exists."}), 400
        elif len(email) <= 5:
            return jsonify({"success": False, "message": "Email must be greater than 5 characters."}), 400
        elif len(fullName) < 2:
            return jsonify({"success": False, "message": "Name must be greater than 1 character."}), 400
        elif not service:
            return jsonify({"success": False, "message": "Please select a service."}), 400
        elif not experience.isnumeric() or int(experience) < 0:
            return jsonify({"success": False, "message": "Experience must be non-negative."}), 400
        elif int(price) < int(base_price):
            return jsonify({"success": False, "message": "Price must exceed base price."}), 400
        elif len(pincode) != 6:
            return jsonify({"success": False, "message": "Pin Code must be exactly 6 digits."}), 400
        elif password1 != password2:
            return jsonify({"success": False, "message": "Passwords must match."}), 400
        elif pdf_file and not pdf_file.filename.endswith(".pdf"):
            return jsonify({"success": False, "message": "Invalid file type."}), 400
        else:
            # Save PDF securely
            pdf_filename = secure_filename(pdf_file.filename)
            upload_folder = os.path.join(current_app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)
            pdf_path = os.path.join(upload_folder, pdf_filename)
            pdf_file.save(pdf_path)

            # Create professional
            new_user = Professional(
                email=email,
                full_name=fullName,
                address=address,
                service=service,
                experience=experience,
                pincode=pincode,
                price=price,
                pdf_file_path=pdf_filename,
                password=generate_password_hash(password1, method="pbkdf2:sha256")
            )
            db.session.add(new_user)
            db.session.commit()

            flash("Registration successfull! Your account is pending approval.", 'success')
            return jsonify({"success": True, "redirect_url": url_for('auth.login')}), 200

    return render_template("professionalSignup.html", services=services_json, base_price=base_price)
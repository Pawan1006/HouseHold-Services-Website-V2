from flask import Blueprint, render_template, flash, request, redirect, url_for, Response, send_from_directory, jsonify, get_flashed_messages, send_file, current_app
from flask_login import login_required, current_user
from .models import Service, Professional, User, Request
from . import db
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, os
from datetime import datetime
import pytz
from sqlalchemy import or_, extract, func
from sqlalchemy.orm import joinedload
import numpy as np
from .tasks import export_service_requests_csv
views = Blueprint("views", __name__)
from flask_mail import Message
from web import mail, cache


@views.route('/active-users', methods=['GET'])
@cache.cached(timeout=5)  # Apply cache with a timeout of 5 seconds
def active_users():
    # Query to get all active users
    active_users = User.query.filter_by(status='active').all()
    
    # Prepare the user data to be returned in JSON format
    users_data = [{"id": user.id, "email": user.email, "full_name": user.full_name} for user in active_users]
    
    # Return the active users as JSON
    return jsonify({'time' : datetime.now()},users_data)


@views.route('/export', methods=['GET'])
def export():
    return render_template('export.html')


@views.route('/trigger_csv_export', methods=['POST'])
def trigger_csv_export():
    """
    API endpoint to trigger the export_service_requests_csv task.
    """
    try:
        # Replace with the admin email where the CSV should be sent
        admin_email = "admin@gmail.com"
        # Trigger the Celery task
        task = export_service_requests_csv.delay(admin_email)

        # Return the task ID for tracking
        return jsonify({"message": "CSV export task triggered", "task_id": task.id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Customer Dashboard View
# Route to display the customer dashboard with user services and requests.
@views.route("/customer-dashboard")
@login_required
def customer_dashboard():
    user = User.query.get(current_user.id)
    requests = Request.query.filter_by(customer_id=current_user.id).all()
    services = Service.query.all()
    return render_template("user_dash.html", 
                            services=[service.to_dict() for service in services],
                            user=user.to_dict(), u_id=current_user.id,
                            requests=[req.to_dict() for req in requests])



# Route to display and update user profile.
@views.route("/user-profile/<int:Id>", methods=["GET", "POST"])
@login_required
def user_profile(Id):
    if request.method == "POST":
        email = request.json.get("email")
        full_name = request.json.get("name")
        address = request.json.get("address")
        pincode = request.json.get("pincode")

        update_profile = User.query.filter_by(id=Id).first()
        update_profile.email = email
        update_profile.full_name = full_name
        update_profile.address = address
        update_profile.pincode = pincode
        db.session.add(update_profile)
        db.session.commit()
        flash("Profile has been updated successfully!", "success")
        return jsonify({"success": True})    
    user = User.query.filter_by(id=Id).first()
    return render_template("user_profile.html", user=user)


@views.route("/user-search")
@login_required
def user_search():
    user = User.query.get(current_user.id)
    return render_template("user_search.html", user=user)



# Route to handle searching by requests, services, or pincode for users.
@views.route("/api/user/search", methods=["GET"])
@login_required
def api_user_search():
    search_type = request.args.get("search_type")
    query = request.args.get("query")
    results = []

    if search_type:
        if search_type == "requests":
            if query:
                results = search_by_request(query)
            else:
                results = Request.query.filter_by(customer_id=current_user.id).all() 
        elif search_type in ["services", "pincode"]:
            if query:
                results = search_by(query)
            else:
                results = get_all_professionals()
    results_data = [result.to_dict() for result in results]
    return jsonify({"results": results_data, "search_type": search_type})
# Helper function to filter requests by customer, service, or status.
def search_by_request(query):
    return Request.query.join(Professional).filter(
        Request.customer_id == current_user.id,
        or_(
            Professional.full_name.ilike(f'%{query}%'),
            Professional.service.ilike(f'%{query}%'),
            Professional.price.ilike(f'%{query}%'),
            Request.service_status.ilike(f'%{query}%')
        )
    ).options(joinedload(Request.professional)).all()

# Helper function to filter services or pincode search.
def search_by(query):
    return Professional.query.filter(or_(Professional.full_name.ilike(f'%{query}%'),
                                        Professional.service.ilike(f'%{query}%'),
                                        Professional.pincode.ilike(f'%{query}%'),
                                        Professional.price.ilike(f'%{query}%'))).all()


# Route to display summary information for the user.
@views.route("/user-summary")
@login_required
def user_summary():
    user = User.query.get(current_user.id)
    return render_template("user_summary.html",user = user)

# Route to display services and related professionals for users.
@views.route("/show-services/<int:id>", methods=["GET", "POST"])
@login_required
def show_services(id):
    user = User.query.get(current_user.id)
    user_id = current_user.id
    service = Service.query.filter_by(id=id).first()
    professionals = Professional.query.filter_by(service=service.service, status='approved').all()
    requests = Request.query.filter_by(customer_id=user_id, service_id=service.id).all()

    booked_professionals = {}
    for prof in professionals:
        booked = False
        for request in requests:
            if (request.professional_id == prof.id and 
                (request.service_status == 'pending' or request.service_status == 'accepted')):
                booked = True
                break
        booked_professionals[prof.id] = booked

    service_history = []
    for request in requests:
        if request.customer_id == user_id:
            service_history.append({
                'id': request.id,
                'service': request.service.to_dict(),
                'professional': request.professional.to_dict(),
                'date_of_request': request.date_of_request,
                'date_of_completion': request.date_of_completion,
                'service_status': request.service_status
            })

    return render_template("show_services.html", 
                           profs=[prof.to_dict() for prof in professionals], 
                           requests=[req.to_dict() for req in requests], 
                           service=service.to_dict(), 
                           user=user.to_dict(),
                           booked_professionals=booked_professionals,
                           service_history=service_history)



# Route to handle booking of services for users.
@views.route("/book_service/<int:prof_id>", methods=['GET', 'POST'])
@login_required
def book_service(prof_id):
    if request.method == 'POST':
        user_id = current_user.id
        profs = Professional.query.filter_by(id=prof_id).first()
        service = Service.query.filter_by(service=profs.service).first()
        new_request = Request(service_id=service.id, professional_id=profs.id, customer_id=user_id, service_status="pending")
        db.session.add(new_request)
        db.session.commit()
        flash('Service booked successfully!', category='success')
        return redirect(url_for("views.show_services", id=service.id))

    user = current_user
    return render_template("user_dash.html", user=user)



# Route to allow users to cancel a service request.
@views.route("show_services/cancel_request/<int:request_id>", methods=['POST'])
@login_required
def service_cancel_request(request_id):
    request_to_cancel = Request.query.filter_by(id=request_id, customer_id=current_user.id).first()
    if request_to_cancel and request_to_cancel.service_status == "pending":
        request_to_cancel.service_status = "cancelled"
        db.session.commit()
        flash('Request cancelled successfully!', category='success')
    else:
        flash('Request not found or cannot be cancelled.', category='error')

    return redirect(url_for("views.show_services", id=request_to_cancel.service_id))


# Route to allow users to cancel a service request.
@views.route("cancel_request/<int:request_id>", methods=['POST'])
@login_required
def cancel_request(request_id):
    request_to_cancel = Request.query.filter_by(id=request_id, customer_id=current_user.id).first()
    if request_to_cancel and request_to_cancel.service_status == "pending":
        request_to_cancel.service_status = "cancelled"
        db.session.commit()
        flash('Request cancelled successfully!', category='success')
    else:
        flash('Request not found or cannot be cancelled.', category='error')

    return redirect(url_for("views.customer_dashboard"))


# Route to handle service closure, remarks, and ratings.
@views.route("/close_service/<int:request_id>", methods=["GET", "POST"])
@login_required
def close_request(request_id):
    request_to_close = Request.query.filter_by(id=request_id, customer_id=current_user.id).first()
    if request.method == "POST":
        data = request.get_json()
        rating = request.json.get("rating")
        remark = request.json.get("remark")
        if request_to_close and request_to_close.service_status == "accepted":
            request_to_close.service_status = "closed"
            request_to_close.date_of_completion = datetime.now(pytz.timezone('Asia/Kolkata'))
            request_to_close.rating = rating if rating else None
            request_to_close.remarks = remark if remark else None
            db.session.commit()
            flash('Service closed successfully!', 'success')
            return jsonify({"success": True})
    user = current_user
    return render_template("service_remark.html", 
                           requests=request_to_close.to_dict(), 
                           user=user)


# Route to handle update remarks and ratings.
@views.route("/update_remark/<int:request_id>", methods=["GET", "POST"])
@login_required
def update_remark(request_id):
    remark_update = Request.query.filter_by(id=request_id, customer_id=current_user.id).first()
    if request.method == "POST":
        data = request.get_json()
        rating = request.json.get("rating")
        remark = request.json.get("remark")
        if remark_update and remark_update.service_status == "closed":
            remark_update.rating = rating
            remark_update.remarks = remark
            db.session.commit()
            flash('Remark updated successfully!', 'success')
            return jsonify({"success": True})
    user = current_user
    return render_template("update_remark.html", 
                           requests=remark_update.to_dict(), 
                           user=user)


# Route to display dashboard for professionals based on their approval status.
@views.route("/professional-dashboard")
@login_required
def professional_dashboard():
    prof_id = current_user.id
    professional = Professional.query.filter_by(id=prof_id).first()
    requests = Request.query.filter_by(professional_id=professional.id).all()
    
    if professional.status == "pending":
        return render_template("pending.html", prof=professional)
    elif professional.status == "approved":
        return render_template("prof_dash.html", prof=professional, requests=requests, profId=prof_id)
    elif professional.status == "rejected":
        return render_template("rejected.html", prof=professional)

@views.route("/api/prof/data")
def fetch_prof_data():
    prof_id = current_user.id
    requests = Request.query.filter_by(professional_id=prof_id).all()
    if not requests:
        return jsonify([])
    requests_data = [req.to_dict() for req in requests]
    return jsonify(requests_data)



# Route to allow professionals to resend their registration request.
@views.route("/resend", methods=["GET", "POST"])
def resend():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = Professional.query.filter_by(email=email).first()
        if existing_user:
            existing_user.status = 'pending'
            db.session.commit()
            flash('Your registration request has been resent.', category="success")
            return render_template("pending.html")
        

@views.route("/prof-search")
@login_required
def prof_search():
    prof_id = current_user.id
    professional = Professional.query.filter_by(id=prof_id).first()
    return render_template("prof_search.html", prof=professional)


# Route to handle search requests for professionals.
@views.route("/api/prof/search")
@login_required
def api_prof_search():
    search_type = request.args.get("search_type", "")
    query = request.args.get("query","")
    results = []

    if search_type:
        if query:
            results = request_search_by(search_type, query)
        else:
            results = get_all_requests()
    results_data = [result.to_dict() for result in results]
    return jsonify({"results": results_data, "search_type": search_type})
# Helper function to filter search results based on the type of search and query.
def request_search_by(search_type, query):
    if search_type == "date":
        # Check if the query is in the format dd-mm
        if len(query) == 5 and query[2] == '-':
            try:
                day, month = map(int, query.split('-'))
                return Request.query.filter(
                    extract('day', Request.date_of_request) == day,
                    extract('month', Request.date_of_request) == month
                ).options(joinedload(Request.customer)).all()
            except ValueError:
                return []  # Return empty if day/month conversion fails

        # Check if the query is just dd (single day)
        elif len(query) == 2:
            try:
                day = int(query)
                return Request.query.filter(
                    extract('day', Request.date_of_request) == day
                ).options(joinedload(Request.customer)).all()
            except ValueError:
                return []  # Return empty if day conversion fails

        # Check if the query is in the format dd-mm-yyyy
        elif len(query) == 10 and query[2] == '-' and query[5] == '-':
            try:
                # Parse the input date
                search_date = datetime.strptime(query, '%d-%m-%Y')
                # Make it timezone-aware (Asia/Kolkata)
                search_date = pytz.timezone('Asia/Kolkata').localize(search_date)
                
                # Create a date object for comparison
                date_only = search_date.date()
                return Request.query.filter(
                    func.date(Request.date_of_request) == date_only  # Compare just the date part
                ).options(joinedload(Request.customer)).all()
            except ValueError:
                return []  # Return empty if date format is incorrect

        # If the query doesn't match expected formats, return empty
        return []

    # Default behavior for other search types
    return Request.query.join(Request.customer).filter(
        or_(
            User.full_name.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%'),
            User.address.ilike(f'%{query}%'),
            User.pincode.ilike(f'%{query}%'),
            Request.rating.ilike(f'%{query}%'),
            Request.service_status.ilike(f'%{query}%')
        )
    ).options(joinedload(Request.customer)).all()


# Route to display base prices for all services
@views.route("/list/basePrice")
def base_price():
    services = Service.query.all()
    return render_template("base_price.html", services=services)


# Route to render the professional summary page 
@views.route("/prof-summary")
@login_required
def prof_summary():
    prof = Professional.query.get(current_user.id)
    return render_template("prof_summary.html", prof=prof)


# Route to handle file uploads
@views.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)


# Route to display and update professional profile 
@views.route("/prof-profile/<int:Id>", methods=["GET", "POST"])
@login_required
def prof_profile(Id):
    if request.method == "POST":
        email = request.json.get("email")
        full_name = request.json.get("name")
        service = request.json.get("service")
        experience = request.json.get("experience")
        address = request.json.get("address")
        pincode = request.json.get("pincode")
        price = request.json.get("price")
        desc = request.json.get("desc")

        update_profile = Professional.query.filter_by(id=Id).first()
        update_profile.email = email
        update_profile.full_name = full_name
        update_profile.service = service
        update_profile.expirence = experience
        update_profile.address = address
        update_profile.pincode = pincode
        update_profile.price = price
        update_profile.desc = desc
        db.session.add(update_profile)
        db.session.commit()
        flash("Profile has been updated successfully!", "success")
        return jsonify({"success": True})
    profiles = Professional.query.filter_by(id=Id).first()
    service = Service.query.filter_by(service=profiles.service).first()
    return render_template("prof_profile.html", profiles=profiles, service=service)



# Route to accept a service request
@views.route("/request/accept/<int:request_id>", methods=['GET'])
@login_required
def accept_request(request_id):
    request_to_accept = Request.query.get(request_id)
    request_to_accept.professional_id = current_user.id
    request_to_accept.service_status = 'accepted'
    db.session.commit()
    flash('Request has been accepted successfully!', category="success")
    return redirect(url_for("views.professional_dashboard"))


# Route to reject a service request 
@views.route("/request/reject/<int:request_id>", methods=['GET'])
@login_required
def reject_request(request_id):
    request_to_reject = Request.query.get(request_id)
    request_to_reject.service_status = 'rejected'
    db.session.commit()
    flash('Request has been rejected!', "success")
    return redirect(url_for("views.professional_dashboard"))


# Route to close a service request
@views.route("/request/close/<int:request_id>", methods=['GET'])
@login_required
def prof_close_service(request_id):
    close_service = Request.query.get(request_id)
    close_service.service_status = 'closed'
    close_service.date_of_completion = datetime.now(pytz.timezone('Asia/Kolkata'))
    db.session.commit()
    flash('Request has been closed successfully!', "success")
    return redirect(url_for("views.professional_dashboard"))

        
# Admin route to display dashboard with services, professionals, and requests 
@views.route("/admin/dashboard", methods=["GET", "POST"])
@login_required
def admin_dashboard():
    return render_template("admin_dash.html")

@views.route("/api/admin/data", methods=["GET"])
@login_required
def admin_data():
    services = Service.query.all()
    professionals = Professional.query.filter_by(status='pending').all()
    requests = Request.query.all()
    data = {
        "services": [service.to_dict() for service in services],
        "professionals": [prof.to_dict() for prof in professionals],
        "requests": [request.to_dict() for request in requests]
    }
    return jsonify(data), 200

# Admin route to handle search queries for customers, professionals, requests, and services

@views.route("/admin/search")
@login_required
def admin_search():
    return render_template("admin_search.html")

@views.route("/api/admin/search", methods=["GET"])
@login_required
def api_admin_search():
    search_type = request.args.get("search_type", "")
    query = request.args.get("query", "")
    results = [] 

    if search_type:
        if search_type == "customer":
            if query:
                results = search_customers(query)
            else:
                results = get_all_customers()

        elif search_type == "professional":
            if query:
                results = search_professionals(query)
            else:
                results = get_all_professionals()

        elif search_type == "request":
            if query:
                results = search_requests(query)
            else:
                results = get_all_requests()

        elif search_type == "service":
            if query:
                results = search_services(query)
            else:
                results = get_all_services()
    results_data = [result.to_dict() for result in results]
    return jsonify({"results": results_data, "search_type": search_type})


def search_customers(query):
    return User.query.filter(or_(User.full_name.ilike(f'%{query}%'), User.status.ilike(f'%{query}%'))).all()

def get_all_customers():
    return User.query.all()

def search_professionals(query):
    return Professional.query.filter(or_(Professional.full_name.ilike(f'%{query}%'), Professional.status.ilike(f'%{query}%'))).all()

def get_all_professionals():
    return Professional.query.all()

def search_requests(query):
    return Request.query.join(Request.professional).filter(or_(Professional.full_name.ilike(f'%{query}%'),Request.service_status.ilike(f'%{query}%'))).options(joinedload(Request.professional)).all()

def get_all_requests():
    return Request.query.options(db.joinedload(Request.professional)).all()

def search_services(query):
    return Service.query.filter(or_(Service.service.ilike(f'%{query}%'), Service.desc.ilike(f'%{query}%')
)).all()

def get_all_services():
    return Service.query.all()


# Admin route to display summary page
@views.route("/admin/summary")
@login_required
def admin_summary():
    return render_template("admin_summary.html")


# Route to display professional details based on ID 
@views.route("/professional/details/<int:id>")
@login_required
def prof_details(id):
    return render_template("prof_details.html", prof_id=id)

@views.route('/api/prof/<int:prof_id>')
def api_professional_details(prof_id):
    professional = Professional.query.get(prof_id)
    return jsonify(professional.to_dict())


# Route to display service request details for a specific service ID 
@views.route("/service/details/<int:id>")
@login_required
def service_details(id):
    return render_template("service_requested_details.html", req_id=id)

@views.route('/api/service/request/<int:req_id>')
def api_service_req_details(req_id):
    requests = Request.query.filter_by(service_id=req_id).all()
    return jsonify([request.to_dict() for request in requests])


@views.route("/service_add", methods=["GET", "POST"])
@login_required
def service_add():
    if request.method == "POST":
        data = request.json  # Flask is expecting JSON data here
        service = data.get("service")
        desc = data.get("desc")
        price = data.get("price")

        if not service:
            return jsonify({"success": False, "message": "Please add a service name."}), 400
        if not price:
            return jsonify({"success": False, "message": "Please add a price."}), 400
        
        new_service = Service(service=service, desc=desc, price=price)
        db.session.add(new_service)
        db.session.commit()
        flash('Service added successfully!', 'success')
        return jsonify({"success": True, "message": "Service added successfully!"}), 200
    
    return render_template("addService.html")  # Render the page when the request is GET


@views.route("/admin/deleteService/<int:Id>")
@login_required
def delete_service(Id):
    remove_service = Service.query.filter_by(id=Id).first()
    remove_request = Request.query.filter_by(service_id=Id).all()
    remove_prof = Professional.query.filter_by(service=remove_service.service).all()
    for request in remove_request:
        db.session.delete(request)
    for professional in remove_prof:
        db.session.delete(professional)
    db.session.delete(remove_service)
    db.session.commit()
    flash("Service removed successfully.", "success")
    return redirect(url_for("views.admin_dashboard"))




# Route to update a service by ID 
@views.route("/admin/update/<int:Id>", methods=["GET", "POST"])
@login_required
def update(Id):
    if request.method == "POST":
        service = request.json.get("service")
        desc = request.json.get("desc")
        price = request.json.get("price")

        update_service = Service.query.filter_by(id=Id).first()
        update_service.service = service
        update_service.desc = desc
        update_service.price = price
        db.session.commit()
        flash("Service updated successfully!", 'success')
        return jsonify({"success": True })
    service = Service.query.filter_by(id=Id).first()
    return render_template("updateService.html", service=service)



@views.route("/admin/approve/<int:id>", methods=["GET"])
@login_required
def approve_professional(id):
    professional = Professional.query.get(id)
    professional.status = "approved"
    db.session.commit()
    flash(f'Professional {professional.full_name} has been approved.', "success")
    return redirect(url_for("views.admin_dashboard"))



# Route to delete a professional by ID 
@views.route("/admin/delete/professional/<int:Id>")
@login_required
def delete_professional(Id):
    remove_prof = Professional.query.filter_by(id=Id).first()
    if remove_prof.status == "pending":
        db.session.delete(remove_prof)
        db.session.commit()
        flash("Professional request has been rejected successfully!", "success")
        return redirect(url_for('views.admin_dashboard'))
    else:
        db.session.delete(remove_prof)
        db.session.commit()
        flash("Professional has been removed successfully!", "success")
        return redirect(url_for('views.admin_dashboard'))
    
# Route to delete a professional by ID 
@views.route("/admin/delete/prof/<int:Id>")
@login_required
def delete_prof(Id):
    remove_prof = Professional.query.filter_by(id=Id).first()
    remove_request = Request.query.filter_by(professional_id=Id).all()
    for r in remove_request:
        db.session.delete(r)
    db.session.delete(remove_prof)
    db.session.commit()
    flash("Professional has been removed successfully!", "success")
    return redirect(url_for('views.prof_status'))


# Route to reject a professional by ID 
@views.route("/admin/reject/<int:id>")
@login_required
def reject_professional(id):
    prof = Professional.query.get(id)
    if prof:
        prof.status = "rejected"
        db.session.commit()
        flash(f'Professional {prof.full_name} request has been rejected.', "success")
    return redirect(url_for("views.admin_dashboard"))


# Route to block a professional by ID 
@views.route("/admin/block/professional/<int:id>")
@login_required
def block_professional(id):
    prof = Professional.query.get(id)
    if prof:
        prof.status = "blocked"
        db.session.commit()
        flash(f'Professional {prof.full_name} has been blocked.', "success")
    return redirect(url_for("views.prof_status"))


# Route to block a professional in the search result 
@views.route("/admin/search/block/professional/<int:id>", methods=['POST'])
@login_required
def search_block_professional(id):
    prof = Professional.query.get(id)
    if prof:
        prof.status = "blocked"
        db.session.commit()
        flash(f'Professional {prof.full_name} has been blocked.', "success")

    query = request.args.get('query', '')
    search_type = request.args.get('search_type', '')
    return redirect(url_for("views.admin_search", query=query, search_type=search_type))


# Route to unblock a professional in the search result 
@views.route("/admin/search/unblock/professional/<int:id>", methods=['POST'])
@login_required
def search_unblock_professional(id):
    prof = Professional.query.get(id)
    if prof:
        prof.status = "approved"
        db.session.commit()
        flash(f'Professional {prof.full_name} has been unblocked.', "success")

    # Retrieve current search parameters
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', '')

    return redirect(url_for("views.admin_search", query=query, search_type=search_type))


# Route to unblock a professional by ID 
@views.route("/admin/unblock/professional/<int:id>")
@login_required
def unblock_professional(id):
    prof = Professional.query.get(id)
    if prof:
        prof.status = "approved"
        db.session.commit()
        flash(f'Professional {prof.full_name} has been unblocked.', "success")
    return redirect(url_for("views.prof_status"))

# Route to Delete a Prof by ID
@views.route("/admin/search/delete/professional/<int:id>", methods=['POST'])
@login_required
def delete_prof_by_search(id):
    prof = Professional.query.get(id)
    remove_request = Request.query.filter_by(professional_id=id).all()
    for r in remove_request:
        db.session.delete(r)
    db.session.delete(prof)
    db.session.commit()
    flash(f'Professional {prof.full_name} has been deleted.', "success")

    # Retrieve current search parameters
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', '')

    return redirect(url_for("views.admin_search", query=query, search_type=search_type))



# Route to view all professionals' statuses 
@views.route("/professional/status")
@login_required
def prof_status():
    return render_template("prof_status.html")


# Route to view all customers' statuses 
@views.route("/customer/status")
@login_required
def cust_status():
    return render_template("cust_status.html")

@views.route('/api/admin/users', methods=['GET'])
def get_users():
    users = User.query.all()  
    data = {
        "active_users" : [
            {
                "id": u.id,
                "name": u.full_name,
                "pincode": u.pincode,
                "status": u.status
            } for u in users
            ]
        }
    return jsonify(data)

@views.route('/api/admin/prof', methods=['GET'])
def get_prof():
    profs = Professional.query.all()  
    data = {
        "active_prof" : [
            {
                "id": u.id,
                "name": u.full_name,
                "experience": u.experience,
                "service": u.service,
                "pdf_file_path": url_for('static', filename=f'uploads/{u.pdf_file_path}'),
                "status": u.status
            } for u in profs
            ]
        }
    return jsonify(data)

# Route to block a customer by ID 
@views.route("/admin/block/customer/<int:id>")
@login_required
def block_customer(id):
    user = User.query.get(id)
    if user:
        user.status = "blocked"
        db.session.commit()
        flash(f'User {user.full_name} Blocked.', "error")
    return redirect(url_for("views.cust_status"))


# Route to unblock a customer by ID 
@views.route("/admin/unblock/customer/<int:id>")
@login_required
def unblock_customer(id):
    user = User.query.get(id)
    if user:
        user.status = "active"
        db.session.commit()
        flash(f'User {user.full_name} Unblocked.', "success")
    return redirect(url_for("views.cust_status"))


# Route to Block a Customer by ID
@views.route("/admin/search/block/customer/<int:id>", methods=['POST'])
@login_required
def search_block_customer(id):
    search_type = request.args.get('search_type', '')
    query = request.args.get('query', '')
    
    user = User.query.get(id)
    if user:
        user.status = "blocked"
        db.session.commit()
        flash(f'Customer {user.full_name} has been blocked.', "success")
    return redirect(url_for('views.admin_search', search_type=search_type, query=query))


# Route to Unblock a Customer by ID
@views.route("/admin/search/unblock/customer/<int:id>", methods=['POST'])
@login_required
def search_unblock_customer(id):
    user = User.query.get(id)
    if user:
        user.status = "active"
        db.session.commit()
        flash(f'Customer {user.full_name} Unblocked.', "success")

    # Retrieve current search parameters
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', '')

    return redirect(url_for("views.admin_search", query=query, search_type=search_type))


# Route to Delete a Customer by ID
@views.route("/admin/delete/customer/<int:id>")
@login_required
def delete_customer(id):
    user = User.query.get(id)
    remove_request = Request.query.filter_by(customer_id=id).all()
    for r in remove_request:
        db.session.delete(r)
    db.session.delete(user)
    db.session.commit()
    flash(f'Customer {user.full_name} has been deleted.', "error")
    return redirect(url_for('views.cust_status'))


# Route to Delete a Customer by ID
@views.route("/admin/search/delete/customer/<int:id>", methods=['POST'])
@login_required
def delete_customer_by_search(id):
    user = User.query.get(id)   
    remove_request = Request.query.filter_by(customer_id=id).all()
    for r in remove_request:
        db.session.delete(r)
    db.session.delete(user)
    db.session.commit()
    flash(f'Customer {user.full_name} has been deleted.', "success")

    # Retrieve current search parameters
    query = request.args.get('query', '')
    search_type = request.args.get('search_type', '')

    return redirect(url_for("views.admin_search", query=query, search_type=search_type))


@views.route("/request/details/<int:id>")
@login_required
def request_details(id):
    return render_template("request_details.html", req_id=id)

@views.route('/api/request/<int:req_id>')
def api_req_details(req_id):
    request = Request.query.get(req_id)
    return jsonify(request.to_dict())


# Admin Chart: Professional Status Breakdown
@views.route("/chart/prof_status")
def prof_chart():
    # Fetch data from the database
    approved_count = Professional.query.filter_by(status='approved').count()
    rejected_count = Professional.query.filter_by(status='rejected').count()
    pending_count = Professional.query.filter_by(status='pending').count()
    block_count = Professional.query.filter_by(status='blocked').count()

    fig_prof, ax_prof = plt.subplots()
    categories = ["Approved", "Blocked", "Pending", "Rejected"]
    counts = [approved_count, block_count, pending_count, rejected_count]
    ax_prof.bar(categories, counts, color=["lightgreen", "red", "yellow", "blue"])

    ax_prof.set_xlabel('Status')
    ax_prof.set_ylabel('Count')
    ax_prof.set_title('Professional Status')
    ax_prof.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    img_prof = io.BytesIO()
    plt.savefig(img_prof, format='png')
    plt.close(fig_prof)
    img_prof.seek(0)

    response = Response(img_prof.getvalue(), mimetype='image/png')
    print(img_prof.getvalue())
    response.headers['Cache-Control'] = 'no-store'
    img_prof.close()
    return response

# Admin Chart: Customer Status Breakdown
@views.route("chart/cust_status")
def cust_chart():
    # Fetch data from the database
    active_count = User.query.filter_by(status='active').count()
    block_count = User.query.filter_by(status='blocked').count()

    fig_cust, ax_cust = plt.subplots()
    categories = ["Active", "Blocked"]
    counts = [active_count, block_count]
    ax_cust.bar(categories, counts, color=["lightgreen", "red"])

    ax_cust.set_xlabel('Status')
    ax_cust.set_ylabel('Count')
    ax_cust.set_title('Customer Status')
    ax_cust.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    img_cust = io.BytesIO()
    plt.savefig(img_cust, format='png')
    plt.close(fig_cust)
    img_cust.seek(0)

    response = Response(img_cust.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-store'
    img_cust.close()
    return response


# Admin Chart: Service Request Status Breakdown
@views.route("/chart/request_status")
def request_chart():
    # Fetch data from the database
    request_count = Request.query.filter_by(service_status='pending').count()
    accept_count = Request.query.filter_by(service_status='accepted').count()
    rejected_count = Request.query.filter_by(service_status='rejected').count()
    closed_count = Request.query.filter_by(service_status='closed').count()

    fig_req, ax_req = plt.subplots()
    categories = ["Requested", "Accepted", "Rejected", "Closed"]
    counts = [request_count, accept_count, rejected_count, closed_count]
    ax_req.bar(categories, counts, color=["yellow", "lightgreen", "red", "blue"])

    ax_req.set_xlabel('Status')
    ax_req.set_ylabel('Count')
    ax_req.set_title('Request Status')
    ax_req.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

    img_req = io.BytesIO()
    plt.savefig(img_req, format='png')
    plt.close(fig_req)
    img_req.seek(0)

    response = Response(img_req.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-store'
    img_req.close()
    return response


# Admin Chart: Average Rating by Service
@views.route('/chart/average_rating')
def average_rating_chart():
    # Get all ratings grouped by service
    ratings = Request.query.all()
    service_ratings = {}

    # Calculate total ratings and counts for each service
    for r in ratings:
        if r.service not in service_ratings:
            service_ratings[r.service] = {'total_rating': 0, 'count': 0}
        
        if r.rating is not None:  # Check if the rating is not None
            service_ratings[r.service]['total_rating'] += r.rating
            service_ratings[r.service]['count'] += 1

    services = []
    avg_ratings = []

    for service, data in service_ratings.items():
        avg_rating = data['total_rating'] / data['count'] if data['count'] > 0 else 0
        services.append(service.service)
        avg_ratings.append(avg_rating)

    # Check if services and avg_ratings have values
    if not services or not avg_ratings:
        return "No data available", 404

    fig_rating, ax_rating = plt.subplots()
    colors = plt.cm.viridis(np.linspace(0, 1, len(services)))
    ax_rating.barh(services, avg_ratings, color=colors)
    ax_rating.set_xlim(1, 5)
    ax_rating.set_xlabel('Average Rating')
    ax_rating.set_ylabel('Services')
    ax_rating.set_title('Average Rating by Service')

    plt.yticks(rotation=0)  # Ensure y-ticks are horizontal
    plt.subplots_adjust(left=0.2)  # Adjust left margin
    plt.tight_layout()  # Automatically adjust layout

    img_rating = io.BytesIO()
    plt.savefig(img_rating, format='png')
    plt.close(fig_rating)
    img_rating.seek(0)

    response = Response(img_rating.getvalue(), mimetype='image/png')
    response.headers['Cache-Control'] = 'no-store'
    img_rating.close()
    return response



# Professional Chart: Professional's Rating Distribution
@views.route('/rating/chart')
def rating_chart():
    prof_id = current_user.id
    ratings = Request.query.filter_by(professional_id=prof_id).all()

    count_1 = len([r for r in ratings if r.rating == 1])
    count_2 = len([r for r in ratings if r.rating == 2])
    count_3 = len([r for r in ratings if r.rating == 3])
    count_4 = len([r for r in ratings if r.rating == 4])
    count_5 = len([r for r in ratings if r.rating == 5])

    # Generate the bar chart for Rating Distribution
    fig1, ax1 = plt.subplots()
    categories = ["1", "2", "3", "4", "5"]
    counts = [count_1, count_2, count_3, count_4, count_5]
    ax1.bar(categories, counts, color=["red","orange", "yellow", "lightgreen", "green"])

    ax1.set_xlabel('Rating')
    ax1.set_ylabel('Count')
    ax1.set_title('Rating Status')
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))


    # Save the figure to a BytesIO object
    img1 = io.BytesIO()
    plt.savefig(img1, format='png')
    img1.seek(0)
    plt.close(fig1)

    return Response(img1.getvalue(), mimetype='image/png')



# Professional Chart: Service Request Status Breakdown for a Professional
@views.route('/service/chart')
def service_chart():
    prof_id = current_user.id
    service = Request.query.filter_by(professional_id=prof_id).all()

    count_1 = len([r for r in service if r.service_status == "pending"])
    count_2 = len([r for r in service if r.service_status == "accepted"])
    count_3 = len([r for r in service if r.service_status == "rejected"])
    count_4 = len([r for r in service if r.service_status == "closed"])


    # Generate the bar chart for Service Status
    fig1, ax1 = plt.subplots()
    categories = ["Pending", "Accepted", "Rejected", "Closed"]
    counts = [count_1, count_2, count_3, count_4]
    ax1.bar(categories, counts, color=["blue", "lightgreen", "red", "yellow"])

    ax1.set_xlabel('Service Status')
    ax1.set_ylabel('Count')
    ax1.set_title('Service Requests Status')
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))


    # Save the figure to a BytesIO object
    img1 = io.BytesIO()
    plt.savefig(img1, format='png')
    img1.seek(0)
    plt.close(fig1)

    return Response(img1.getvalue(), mimetype='image/png')




# Customer Chart: Service Request Status Breakdown for a Customer
@views.route("/service_requested/chart")
def service_requested_chart():
    user_id = current_user.id
    service = Request.query.filter_by(customer_id=user_id).all()

    count_1 = len([r for r in service if r.service_status == "pending"])
    count_2 = len([r for r in service if r.service_status == "accepted"])
    count_3 = len([r for r in service if r.service_status == "rejected"])
    count_4 = len([r for r in service if r.service_status == "closed"])


    # Generate the bar chart for Service Status
    fig1, ax1 = plt.subplots()
    categories = ["Pending", "Accepted", "Rejected", "Closed"]
    counts = [count_1, count_2, count_3, count_4]
    ax1.bar(categories, counts, color=["blue", "lightgreen", "red", "yellow"])

    ax1.set_xlabel('Service Status')
    ax1.set_ylabel('Count')
    ax1.set_title('Service Requests Status')
    ax1.yaxis.set_major_locator(plt.MaxNLocator(integer=True))


    # Save the figure to a BytesIO object
    img1 = io.BytesIO()
    plt.savefig(img1, format='png')
    img1.seek(0)
    plt.close(fig1)

    return Response(img1.getvalue(), mimetype='image/png')
from web.celery_config import celery
from flask_mail import Message
from web import mail
from web.models import Professional, Request, User
from datetime import date
import logging
from web import create_app
import csv
import os
from email.mime.base import MIMEBase
from email import encoders  
from flask_mail import Message

logging.basicConfig(level=logging.INFO)


@celery.task
def send_daily_reminders():
    app = create_app()
    with app.app_context():
        try:
            logging.info("Starting daily reminders task.")

            pending_requests = Request.query.filter_by(service_status='pending').all()
            print(pending_requests)
            if not pending_requests:
                logging.info("No pending service requests found. Task exiting.")
                return

            for request in pending_requests:
                professional = request.professional
                if not professional or not professional.email:
                    logging.warning(f"Skipping request {request.id}, no professional email found.")
                    continue

                # Email details
                subject = "Reminder: You have pending service requests"
                body = f"""
                Hello {professional.full_name},

                You have pending service requests. Please log in to the platform to accept or reject them.

                Regards,
                The Team
                """

                msg = Message(subject, recipients=[professional.email], body=body)
                mail.send(msg)
                logging.info(f"Reminder sent to {professional.email}.")

            logging.info("Daily reminders task completed.")
        except Exception as e:
            logging.error(f"Error in send_daily_reminders: {e}")



@celery.task
def send_monthly_activity_report():
    app = create_app()
    with app.app_context():
        try:
            logging.info("Starting monthly activity report task.")

            customers = User.query.all()
            if not customers:
                logging.info("No customers found. Task exiting.")
                return

            for customer in customers:
                if not customer.email:
                    logging.warning(f"Skipping customer {customer.id}, no email found.")
                    continue

                # Gather service details
                services_requested = Request.query.filter_by(customer_id=customer.id).count()
                services_closed = Request.query.filter_by(customer_id=customer.id, service_status='closed').count()

                report = f"""
                <html>
                    <body>
                        <h1>Monthly Activity Report</h1>
                        <p>Hello {customer.full_name},</p>
                        <p>Here is a summary of your activity for this month:</p>
                        <ul>
                            <li>Services Requested: {services_requested}</li>
                            <li>Services Closed: {services_closed}</li>
                        </ul>
                        <p>Thank you for using our platform!</p>
                    </body>
                </html>
                """

                subject = "Your Monthly Activity Report"
                msg = Message(subject, recipients=[customer.email])
                msg.html = report
                mail.send(msg)
                logging.info(f"Monthly report sent to {customer.email}.")

            logging.info("Monthly activity report task completed.")
        except Exception as e:
            logging.error(f"Error in send_monthly_activity_report: {e}")



@celery.task
def export_service_requests_csv(admin_email):
    app = create_app()
    with app.app_context():
        try:
            
            requests = Request.query.filter_by(service_status='closed').all()

            file_path = 'service_requests.csv'
            with open(file_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Service ID', 'Customer ID', 'Professional ID', 'Request Date', 'Remarks'])
                for request in requests:
                    writer.writerow([
                        request.id,
                        request.customer_id,
                        request.professional_id,
                        request.date_of_request,
                        request.remarks,
                    ])

            subject = "Service Requests CSV Export"
            body = "Please find attached the service requests CSV export."
            msg = Message(subject, recipients=[admin_email], body=body)
            with open(file_path, 'rb') as file:
                msg.attach('service_requests.csv', 'text/csv', file.read())
            mail.send(msg)

            logging.info(f"CSV export sent to {admin_email}.")
            return f"CSV export sent to {admin_email}."
        except Exception as e:
            logging.error(f"Error in exporting service requests to CSV: {e}")
            raise
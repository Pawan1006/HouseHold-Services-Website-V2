# Household Services Application

---

## 🎯 Objective
The app aims to simplify household service management, offering a secure, user-friendly interface for customers to find verified professionals, manage service requests, and provide feedback. Admins maintain quality control, approving professionals and overseeing platform operations.

---

## 🛠️ Frameworks and Technologies Used
The application uses:
- **Flask**: Backend logic and server management.
- **Vue.js**: Frontend, ensuring a dynamic and interactive user interface.
- **SQLite**: Lightweight, compatible database for storing user and service data.
- **Redis**: For caching, improving performance by storing frequently accessed data.
- **Celery with Redis**: For handling background tasks like sending daily reminders or processing service requests.

All functionality has been thoroughly tested in a local development environment.

---

## 👥 User Roles & Permissions
- **Admin**: Manages user and service data, approves professionals, and enforces platform rules.
- **Service Professional**: Registers, manages profiles, accepts/rejects service requests, and completes service transactions.
- **Customer**: Registers to request services, search by service or location, and leave feedback.

---

## 📂 Database Schema
- **Admin Model**: Manages superuser accounts with fields like id, email, and password.
- **User Model**: Stores customer information and status.
- **Professional Model**: Holds professional profile data, service expertise, and average ratings.
- **Service Model**: Defines service categories with descriptions and base prices.
- **Request Model**: Tracks each service request’s status, customer remarks, and ratings.

---

## 🔑 Core Functionalities
- **Authentication and Authorization**: Enforced with Flask-Login, offering role-based access and session management for Admin, Service Professional, and Customer roles.
- **Admin Dashboard**: Allows the Admin to manage services, approve professionals, and review user activities.
- **Service Management**: Admin can add, edit, or delete service categories with essential details like price and description.
- **Service Request Management**: Customers submit requests; professionals can accept, reject, or close them after completion.
- **Search Feature**: Customers search by service name or location; Admins search professionals by status.
- **Background Jobs**: Using Celery and Redis, tasks like sending reminders to professionals and batch processing are handled efficiently in the background.

---

## 🌀 Application Workflow
1. **Login & Role Redirection**: Users log in and are redirected to dashboards based on their role.
2. **Service Request**: Customers select services, make requests, and post feedback after completion.
3. **Feedback Loop**: Professionals receive feedback to improve visibility.
4. **Background Processing**: Celery handles background jobs such as reminders or data processing tasks, improving the overall performance.

---

## 📈 Conclusion
This Household Services Application fulfills its goal of connecting customers with trusted service providers. With the integration of:
- **Vue.js** for the frontend
- **Flask** for the backend
- **SQLite** for the database
- **Redis with Celery** for background jobs

The platform provides an efficient, scalable solution for household service management.  
Future improvements include stronger authentication, payment integration, and enhanced features to further improve user experience.

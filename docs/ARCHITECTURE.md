# System Architecture

## 1. Overview

The **Scheduling System for Hospital Patient and Appointment Management** is designed using a clean, modular architecture to ensure maintainability, scalability, and separation of concerns. The system is a desktop application built with Python 3.x and Tkinter, utilizing a MySQL database for persistent storage.

The architecture follows a strict layered approach: **Controllers → Services → Repositories → Database**. This ensures that the presentation layer (GUI) is decoupled from the business logic and data access layers, making the application easier to test, maintain, and extend.

## 2. Architectural Pattern

The system employs a variation of the Model-View-Controller (MVC) pattern, adapted for desktop application development with a strong emphasis on clean architecture principles.

* **View (GUI):** The Tkinter-based Graphical User Interface. It is responsible for presenting data to the user and capturing user input. It does not contain business logic.
* **Controller:** Handles user input from the View, translates it into actions, and coordinates with the Services layer. It manages the flow of the application.
* **Service:** Contains the core business logic of the application (e.g., time-slot validation, user authentication, data processing). It acts as a bridge between the Controllers and Repositories.
* **Repository:** Encapsulates the logic required to access data sources (the MySQL database). It provides a collection-like interface for accessing domain objects.
* **Model:** Represents the data structures and entities of the application (e.g., Patient, Doctor, Appointment).

## 3. Technology Stack

* **Programming Language:** Python 3.x
* **GUI Framework:** Tkinter (with `ttk` for modern styling)
* **Database:** MySQL
* **Database Connector:** `mysql-connector-python`
* **Image Handling:** Pillow (PIL)
* **Charts & Analytics:** Matplotlib
* **Calendar Widget:** `tkcalendar`
* **Password Hashing:** `bcrypt`
* **Export Reports:** ReportLab (PDF) and `openpyxl` (Excel)

## 4. Layered Architecture Details

### 4.1 Presentation Layer (GUI)
* **Location:** `src/gui/`
* **Responsibility:** Rendering the user interface, handling user interactions (clicks, inputs), and displaying data returned by the Controller layer.
* **Components:**
  * Splash Screen
  * Login Screen
  * Admin Dashboard
  * Doctor Dashboard
  * Receptionist Dashboard
  * Patient Registration Form
  * Doctor Management Table
  * Appointment Booking Calendar
  * Clinical Records Forms
  * Analytics Dashboard (Matplotlib integration)

### 4.2 Controller Layer
* **Location:** `src/controllers/`
* **Responsibility:** Receiving requests from the GUI, invoking appropriate services, and passing results back to the GUI for display. It also handles input validation before passing data to the Service layer.
* **Components:**
  * `AuthController`: Handles login, logout, and password reset requests.
  * `PatientController`: Handles patient registration, editing, and searching requests.
  * `DoctorController`: Handles doctor and department management requests.
  * `AppointmentController`: Handles booking, rescheduling, and cancellation requests.
  * `ReportController`: Handles report generation and export requests.

### 4.3 Service Layer (Business Logic)
* **Location:** `src/services/`
* **Responsibility:** Implementing the core business rules and logic of the application. This layer is independent of the GUI and database specifics.
* **Components:**
  * `AuthService`: Manages user authentication, session management, and role-based access control.
  * `PatientService`: Manages patient data processing and medical history logic.
  * `DoctorService`: Manages doctor schedules, working hours, and availability logic.
  * `AppointmentService`: Implements the critical time-slot validation logic to prevent double-bookings.
  * `ClinicalService`: Manages diagnoses, prescriptions, and test report logic.
  * `ReportService`: Processes data for reports and analytics.

### 4.4 Repository Layer (Data Access)
* **Location:** `src/repositories/`
* **Responsibility:** Abstracting the data source (MySQL). It provides methods to query and manipulate data in the database, returning Model objects to the Service layer.
* **Components:**
  * `UserRepository`: CRUD operations for the `users` table.
  * `PatientRepository`: CRUD operations for the `patients` table.
  * `DoctorRepository`: CRUD operations for the `doctors` and `departments` tables.
  * `AppointmentRepository`: CRUD operations for the `appointments` table.
  * `ClinicalRepository`: Operations for `medical_history`, `visit_records`, `prescriptions`, and `test_reports` tables.
  * `AuditRepository`: Logging operations for the `audit_logs` table.

### 4.5 Model Layer (Entities)
* **Location:** `src/models/`
* **Responsibility:** Defining the data structures that represent the core entities of the application.
* **Components:**
  * `User`
  * `Patient`
  * `Doctor`
  * `Department`
  * `Appointment`
  * `MedicalHistory`
  * `VisitRecord`
  * `Prescription`
  * `TestReport`

## 5. Database Interaction

The system uses `mysql-connector-python` to establish a connection pool with the MySQL database. All database interactions are strictly confined to the Repository layer. The system employs parameterized SQL queries throughout to prevent SQL injection attacks.

## 6. Security Architecture

* **Authentication:** Handled by the `AuthService`, utilizing `bcrypt` for password hashing.
* **Authorization:** Role-Based Access Control (RBAC) is enforced at the Controller level to ensure users can only access authorized functionalities.
* **Input Validation:** Performed in the Controller layer to sanitize inputs before they reach the Service and Repository layers.
* **Activity Logging:** An `AuditLog` mechanism tracks significant user actions for security and compliance.

## 7. Analytics and Reporting Architecture

* **Data Retrieval:** The `ReportService` fetches aggregated data from the `AppointmentRepository` and `PatientRepository`.
* **Visualization:** The `gui/analytics/` module uses `Matplotlib` to render charts (daily patients, weekly/monthly appointments, doctor utilization, etc.) directly into Tkinter frames.
* **Exporting:** The `ReportService` utilizes `ReportLab` and `openpyxl` to generate PDF and Excel files, respectively, saving them to the `reports/` directory.

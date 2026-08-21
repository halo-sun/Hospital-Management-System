# Installation Guide — Hospital Management System

## System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 (build 17763) | Windows 11 |
| **MySQL** | 8.0 | 8.0+ |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 500 MB free | 1 GB free |
| **Display** | 1280 × 720 | 1920 × 1080 |

> **Note:** Python does NOT need to be installed separately. The
> application is bundled as a standalone executable with the Python
> interpreter included.

---

## What the Installer Does

Running `HospitalScheduler-{version}-Setup.exe` performs these steps:

1. **License Display** — Shows the MIT License for review.
2. **Install Location** — Defaults to `C:\Program Files\HospitalScheduler`
   (or the equivalent on your system). You can change this.
3. **File Copy** — Copies the main application (`HospitalScheduler.exe`),
   the database setup utility (`HMS-Setup.exe`), and all bundled
   dependencies (Python runtime, matplotlib, Pillow, etc.).
4. **Start Menu** — Creates a Start Menu folder with:
   - Hospital Management System (launches the main app)
   - Database Setup (launches the setup wizard)
   - Uninstall shortcut
5. **Desktop Shortcut** — Optionally creates a desktop shortcut
   (unchecked by default).
6. **Database Setup Wizard** — Automatically launches `HMS-Setup.exe`
   to configure the database. This wizard:
   - Detects whether MySQL is installed and running
   - If MySQL is stopped, offers to start the service
   - If MySQL is not installed, shows a download link
   - Prompts for MySQL admin/root credentials (used transiently)
   - Creates the `hospital_db` database
   - Creates the `hms_app` least-privilege database user
   - Initializes all 15 database tables
   - Writes the `.env` configuration file
7. **Optional Launch** — Offers to launch the main application.

After the installer finishes, the application is ready to use.

---

## First Launch

After installation:

1. **Database Setup** (if not already done by the installer):
   - If MySQL is not yet configured, the app shows a connection error
     dialog with a **Run Database Setup** button.
   - Click it to open the setup wizard, which walks you through
     connecting to MySQL and creating the database.

2. **Admin Account Setup**:
   - On the very first launch, the app detects that no admin account
     exists and shows the Initial Setup screen.
   - Create your administrator username and password.
   - This is the only time you need to do this.

3. **Login**:
   - Use the admin account you just created to log in.
   - From there you can create Doctor and Receptionist accounts.

---

## Manual Database Setup (Fallback)

If the automated setup wizard fails for any reason, you can set up
the database manually:

### 1. Ensure MySQL is running

```bash
# Windows (from an elevated command prompt — replace mysql80 with your version):
net start mysql80
# Or for other versions: net start MySQL91, net start MySQL267, etc.
# You can find your service name with: sc query state= all | findstr MySQL

# Linux:
sudo service mysql start
```

### 2. Create the database

```sql
CREATE DATABASE IF NOT EXISTS hospital_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
```

### 3. Create the hms_app user

```sql
-- Replace 'YOUR_PASSWORD' with a strong password
CREATE USER IF NOT EXISTS 'hms_app'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON hospital_db.* TO 'hms_app'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Create the .env file

Create a `.env` file in the application directory with:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=hms_app
DB_PASSWORD=YOUR_PASSWORD
DB_NAME=hospital_db
```

### 5. Initialize the schema

```bash
# From the application directory:
python -m src.database.init_db
```

Or run the main application — it will initialize the schema
automatically on first connection.

---

## Uninstallation

Use **Settings → Apps → Installed apps** (Windows 10/11) or
**Control Panel → Programs and Features** to uninstall.

During uninstall, you will be asked whether to remove the
**user data directory** at `%LOCALAPPDATA%\HospitalScheduler`.
This contains:

- Uploaded patient documents
- Application logs
- Generated reports

**Default: Keep the data.** Only choose to remove it if you are
certain you no longer need these files.

---

## Troubleshooting

### "Cannot connect to MySQL" on launch

- Ensure MySQL 8.0+ is installed and running.
- Check that `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD`
  in `.env` match your MySQL configuration.
- The default configuration expects MySQL on `localhost:3306`.

### Charts not rendering (Analytics dashboard)

This usually means matplotlib's TkAgg backend failed to load.
Ensure you are using the bundled executable (not running from
source with a system-installed Pillow that lacks ImageTk).

### Calendar date picker not working

The tkcalendar widget requires babel locale data. This is bundled
in the installer but may be missing if running from source.
Run `pip install tkcalendar babel` to fix.

### "Access denied for user 'hms_app'"

The hms_app password may be incorrect. Re-run the Database Setup
wizard from the Start Menu, or update the `DB_PASSWORD` value
in `.env`.

---

## For Developers

### Building from source

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# Run the application
python main.py

# Run the setup utility standalone
python src/setup.py

# Build the Windows executable
pyinstaller hms.spec --noconfirm
pyinstaller hms-setup.spec --noconfirm

# Build the installer (requires Inno Setup 6)
ISCC.exe installer/windows/setup.iss
```

### Regenerating the installer script

The Inno Setup script (`installer/windows/setup.iss`) is generated
from `AppConfig` constants. To regenerate after changing metadata:

```bash
python installer/windows/generate_iss.py
```

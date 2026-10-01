-- Create the database
CREATE DATABASE IF NOT EXISTS grievance_db;
USE grievance_db;

-- 1. Users Table (Stores Students, Staff, and Administrators)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('student', 'staff', 'admin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Complaints Table (Stores submitted complaints & ML prediction outputs)
CREATE TABLE IF NOT EXISTS complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    assigned_category VARCHAR(100) DEFAULT 'Unassigned',
    status ENUM('Pending', 'In Progress', 'Resolved', 'Closed') DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Evidence bytes are stored in MySQL. complaint_id matches the portal's JSON complaint IDs.
CREATE TABLE IF NOT EXISTS evidence_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    complaint_id INT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL UNIQUE,
    stored_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(127) NOT NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    file_data LONGBLOB NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- For an existing table, run these once (adjust the FK name if your database uses a custom name):
-- ALTER TABLE evidence_files DROP FOREIGN KEY evidence_files_ibfk_1;
-- ALTER TABLE evidence_files MODIFY complaint_id INT NULL;
-- ALTER TABLE evidence_files ADD COLUMN file_data LONGBLOB NULL;
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

-- 3. Sample Initial Data (Optional test users)
INSERT INTO users (username, email, password, role) VALUES
('240041246', 'khoza@unizulu.ac.za', 'pbkdf2:sha256:password_hash_here', 'student'),
('staff_member', 'staff@unizulu.ac.za', 'pbkdf2:sha256:password_hash_here', 'staff'),
('admin_user', 'admin@unizulu.ac.za', 'pbkdf2:sha256:password_hash_here', 'admin');
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# Expanded Unizulu complaint dataset
data = [
    # 1. ICT Services
    ("I cannot log into my student portal account or reset my password", "ICT Services"),
    ("The campus WiFi is not connecting in the main library", "ICT Services"),
    ("My Moodle page is missing my registered second semester modules", "ICT Services"),
    ("I am having issues accessing my institutional student email", "ICT Services"),
    ("The computers in the computer lab are not powering on", "ICT Services"),
    ("My portal password expired and the self-service reset is down", "ICT Services"),
    ("Unable to access online learning materials due to server error", "ICT Services"),
    ("ITS system is showing an authentication failed message", "ICT Services"),

    # 2. Academics
    ("My continuous assessment test marks for CS301 are missing", "Academics"),
    ("I need an official academic transcript from the registrar office", "Academics"),
    ("I cannot register for my final year computer science modules online", "Academics"),
    ("My lecturer has not uploaded the assignment marks for last month", "Academics"),
    ("I want to apply for a remarking of my final examination paper", "Academics"),
    ("There is a timetable clash between two of my core modules", "Academics"),
    ("My exam seat number is not generated on the portal", "Academics"),
    ("Incorrect grade was recorded on my end of semester results", "Academics"),

    # 3. Financial Aid
    ("My NSFAS allowance status says approved but payment is not reflected", "Financial Aid"),
    ("I need a clearance statement for my external bursary payment", "Financial Aid"),
    ("There is a discrepancy in my university account balance statement", "Financial Aid"),
    ("I have not received my meal and book allowances for this term", "Financial Aid"),
    ("My account has a financial block preventing my registration", "Financial Aid"),
    ("The bursary office has not processed my tuition fee allocation", "Financial Aid"),
    ("Query regarding refund of excess payment on student account", "Financial Aid"),

    # 4. Residences
    ("The water pipe is leaking severely in hostel room 302", "Residences"),
    ("There is no hot water supply in the student residence shower", "Residences"),
    ("The door lock and handle in my assigned residence room are broken", "Residences"),
    ("The electricity sockets in block C residence are not working", "Residences"),
    ("Request for room transfer due to maintenance issues in my floor", "Residences"),
    ("The residence kitchen stoves are faulty and dangerous", "Residences"),

    # 5. Harassment & Student Protection
    ("A staff member is demanding favors in exchange for passing marks", "Harassment & Protection"),
    ("I am being threatened and intimidated by another student on campus", "Harassment & Protection"),
    ("Reporting an incident of verbal harassment and bullying in the corridor", "Harassment & Protection"),
    ("Case of sexual harassment involving a lecturer during consultation", "Harassment & Protection"),
    ("I felt unsafe due to aggressive behavior from a fellow classmate", "Harassment & Protection"),
    ("Victim of gender based violence GBV incident near the student center", "Harassment & Protection"),
    ("A senior student is constantly stalking and harassing me near hostel", "Harassment & Protection"),

    # 6. Campus Security & Lost Items
    ("My laptop was stolen from the library while I was away", "Campus Security"),
    ("I lost my student ID card near the main gate and need to report it", "Campus Security"),
    ("My phone and backpack went missing in the lecture hall", "Campus Security"),
    ("Break in reported at my residence room and personal items missing", "Campus Security"),
    ("Found a set of room keys near the cafeteria turning them in", "Campus Security"),
    ("Bicycle was taken from the parking rack outside the science building", "Campus Security"),
    ("Unidentified intruders seen near the hostel fence late at night", "Campus Security")
]

texts, labels = zip(*data)

# Create machine learning pipeline (Text Processing + Naive Bayes Classifier)
model = make_pipeline(TfidfVectorizer(), MultinomialNB())

# Train the classification model
model.fit(texts, labels)

# Save the trained binary model
os.makedirs('ML_model', exist_ok=True)
model_path = os.path.join('ML_model', 'complaint_classifier.pkl')
joblib.dump(model, model_path)

print(f"Model successfully re-trained with 6 categories and saved to '{model_path}'!")
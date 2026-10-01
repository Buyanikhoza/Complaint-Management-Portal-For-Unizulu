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
    ("Unidentified intruders seen near the hostel fence late at night", "Campus Security"),

    # Natural-language descriptions and requests for help
    ("Please help me, the WiFi in my residence is not working", "ICT Services"),
    ("My campus internet keeps disconnecting when I use the student portal", "ICT Services"),
    ("I cannot sign in to the learning management system", "ICT Services"),
    ("The online portal will not let me log in", "ICT Services"),
    ("My student email is not receiving messages", "ICT Services"),
    ("I have a problem with the campus network in my room", "ICT Services"),
    ("The university website gives me an error when I register", "ICT Services"),
    ("My password reset link does not work", "ICT Services"),
    ("The computers in the lab have no internet connection", "ICT Services"),
    ("I cannot open my online course materials", "ICT Services"),
    ("The app keeps crashing when I try to check my student account", "ICT Services"),
    ("I need help because my account has been locked out of the portal", "ICT Services"),
    ("I have a problem with my NSFAS allowance, I did not receive it", "Financial Aid"),
    ("My bursary money has not come through this month", "Financial Aid"),
    ("I paid my fees but my account still says that I owe money", "Financial Aid"),
    ("Please help with my missing NSFAS payment", "Financial Aid"),
    ("My meal allowance has not been paid", "Financial Aid"),
    ("I have not received my student funding", "Financial Aid"),
    ("My tuition payment is not showing on my university account", "Financial Aid"),
    ("I need help with a refund for fees I paid twice", "Financial Aid"),
    ("My financial aid application has not been processed", "Financial Aid"),
    ("The bursary office has not paid my book allowance", "Financial Aid"),
    ("My student account has an incorrect outstanding balance", "Financial Aid"),
    ("I cannot register because my fees are showing as unpaid", "Financial Aid"),
    ("A lecturer lost my exam paper", "Academics"),
    ("Please help me because my test marks are missing", "Academics"),
    ("My assignment result has not been released", "Academics"),
    ("I was given the wrong mark for my exam", "Academics"),
    ("I cannot add a course to my academic registration", "Academics"),
    ("My exam timetable has two papers at the same time", "Academics"),
    ("I need help getting my transcript from the university", "Academics"),
    ("My lecturer has not responded about my final grade", "Academics"),
    ("I was not included on the class list for my module", "Academics"),
    ("The marks on my student record are incorrect", "Academics"),
    ("I need to appeal the result of my final examination", "Academics"),
    ("My course registration is blocked even though I meet the requirements", "Academics"),
    ("My room has no electricity and the lights do not work", "Residences"),
    ("There is no water in my student residence", "Residences"),
    ("The shower in my hostel has no hot water", "Residences"),
    ("Please help me, my residence room roof is leaking", "Residences"),
    ("The lock on my room door is broken", "Residences"),
    ("My hostel room needs repairs and maintenance", "Residences"),
    ("The stove in the residence kitchen is not working", "Residences"),
    ("I have a problem with pests in my student room", "Residences"),
    ("The bathroom in my residence is blocked", "Residences"),
    ("There is a broken window in my hostel room", "Residences"),
    ("I need to report that my residence has a plumbing leak", "Residences"),
    ("My room allocation has a maintenance problem", "Residences"),
    ("I am being bullied by another student", "Harassment & Protection"),
    ("A staff member is harassing me and I need help", "Harassment & Protection"),
    ("I feel unsafe because someone is threatening me", "Harassment & Protection"),
    ("I want to report verbal abuse from a student", "Harassment & Protection"),
    ("Someone is stalking me on campus", "Harassment & Protection"),
    ("I experienced sexual harassment at the university", "Harassment & Protection"),
    ("I am being intimidated by a lecturer", "Harassment & Protection"),
    ("Please help, another student keeps bullying me", "Harassment & Protection"),
    ("I want to report gender based violence", "Harassment & Protection"),
    ("A student is sending me threatening messages", "Harassment & Protection"),
    ("I was assaulted and need student protection support", "Harassment & Protection"),
    ("I need help reporting discrimination by a staff member", "Harassment & Protection"),
    ("My laptop was stolen from the library", "Campus Security"),
    ("I lost my student ID card near the main gate", "Campus Security"),
    ("Someone took my phone from the lecture hall", "Campus Security"),
    ("I need to report a theft in my residence", "Campus Security"),
    ("My bicycle was stolen from the campus parking area", "Campus Security"),
    ("I found a set of keys and want to hand them in", "Campus Security"),
    ("There was a break in and my belongings are missing", "Campus Security"),
    ("I want to report a suspicious person near campus", "Campus Security"),
    ("My backpack went missing in the student centre", "Campus Security"),
    ("Someone stole my laptop while I was in class", "Campus Security"),
    ("I need help reporting lost property on campus", "Campus Security"),
    ("An intruder was seen near the residence entrance", "Campus Security")
]

texts, labels = zip(*data)

# Create machine learning pipeline (Text Processing + Naive Bayes Classifier)
model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True), MultinomialNB(alpha=0.25))

# Train the classification model
model.fit(texts, labels)

# Save the trained binary model
os.makedirs('ML_model', exist_ok=True)
model_path = os.path.join('ML_model', 'complaint_classifier.pkl')
joblib.dump(model, model_path)

print(f"Model successfully re-trained with 6 categories and saved to '{model_path}'!")
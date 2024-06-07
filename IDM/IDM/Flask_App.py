from flask import Flask, redirect, url_for, render_template, request, session, jsonify, send_from_directory
from flask_mysqldb import MySQL
import secrets
from datetime import datetime, date
import random
import string
import os
from werkzeug.utils import secure_filename
import re
from flask_mail import Mail, Message
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, render_template, request, redirect, url_for, session
import os
from PIL import Image
import mysql.connector

app = Flask(__name__)

app.secret_key = secrets.token_hex(8)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_USE_SIGNER'] = True

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'idmsaglikmerkezi@gmail.com'
app.config['MAIL_PASSWORD'] = 'dpvg kxvt rooe nexf'
app.config['MAIL_DEFAULT_SENDER'] = 'idmsaglikmerkezi@gmail.com'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3307
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'GodzillaV5'
app.config['MYSQL_DB'] = 'pms'

mysql = MySQL(app)
mail = Mail(app)

yolo_model = YOLO('best.pt')
class_dict = {0: "MM", 1: "MM", 2: "MM"}

@app.route('/tespit', methods=['GET', 'POST'])
def tespit_index():
    if 'name_pms' not in session:
        return redirect(url_for('login'))

    patient_name = session['name_pms']
    cur = mysql.connection.cursor()
    query = "SELECT tarih FROM tespit WHERE hasta_ad = %s"
    cur.execute(query, (patient_name,))
    dates = cur.fetchall()
    cur.close()

    dates = [date[0] for date in dates]

    if request.method == 'POST':
        selected_date = request.form['date']
        return redirect(url_for('tespit_predict', date=selected_date))

    return render_template('tespit.html', dates=dates)


def model_predict(img_path, model):
    try:
        if not os.path.exists(img_path):
            return f"Görüntü dosyası bulunamadı: {img_path}", None

        img = Image.open(img_path)
        if img.format not in ['JPEG', 'PNG']:
            img_path = img_path.rsplit('.', 1)[0] + '.jpg'
            img.convert('RGB').save(img_path, 'JPEG')

        results = model(img_path)[0]
        boxes = results.boxes
        predictions = [(class_dict[int(box.cls)], float(box.conf) * 100) for box in boxes]

        img_draw = Image.open(img_path)
        img_draw = draw_results(img_draw, boxes)
        detected_img_path = img_path.replace('.jpg', '_detected.jpg')
        img_draw.save(detected_img_path)

        return predictions, detected_img_path
    except Exception as e:
        return str(e), None


def draw_results(image, boxes):
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 65)
    except IOError:
        font = ImageFont.load_default()

    for box in boxes:
        xmin, ymin, xmax, ymax = box.xyxy[0].tolist()
        class_id = int(box.cls)
        confidence = float(box.conf)
        label = f"{class_dict[class_id]}: {confidence:.2f}%"
        draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=3)

        # Text background
        text_size = draw.textbbox((xmin, ymin), label, font=font)
        draw.rectangle([text_size[0], text_size[1], text_size[2], text_size[3]], fill="red")

        # Text
        draw.text((xmin, ymin), label, fill="white", font=font)

    return image

def calculate_overall_confidence(predictions):
    if not predictions:
        return 0
    total_confidence = sum([confidence for pred in predictions if len(pred) == 2 for _, confidence in [pred]])
    overall_confidence = total_confidence / len(predictions)
    return round(overall_confidence, 2)


@app.route('/predict/<date>', methods=['GET'])
def tespit_predict(date):
    if 'name_pms' not in session:
        return redirect(url_for('login'))

    patient_name = session['name_pms']

    cur = mysql.connection.cursor()
    query = "SELECT goruntu FROM tespit WHERE hasta_ad = %s AND tarih = %s"
    cur.execute(query, (patient_name, date))
    result = cur.fetchone()
    cur.close()

    if result is None:
        return "Image not found in the database."

    image_data = result[0]

    image_path = os.path.join('static/uploads', f'{date}.jpg')
    with open(image_path, 'wb') as f:
        f.write(image_data)

    if not os.path.exists(image_path):
        return f"Görüntü dosyası bulunamadı: {image_path}"

    image_filename = os.path.basename(image_path)

    predictions, detected_img_path = model_predict(image_path, yolo_model)
    if isinstance(predictions, str):
        return predictions
    overall_confidence = calculate_overall_confidence(predictions)
    detected_image_filename = os.path.basename(detected_img_path) if detected_img_path else None

    return render_template('predict.html', file_name=image_filename, detected_file_name=detected_image_filename,
                           overall_confidence=overall_confidence)

#--------------------------------------------------------------------------------------------------------------------
# YOLO modelinin yüklenmesi
yolo_model1 = YOLO('best.pt')
class_dict1 = {0: "MM", 1: "MM", 2: "MM"}

@app.route('/doktor_tespit', methods=['GET', 'POST'])
def tespit_index_doktor():
    if 'name_pms' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT hasta_ad_doktor FROM tespit_doktor")
    patients = cur.fetchall()
    cur.close()

    patients = [patient[0] for patient in patients]

    selected_patient = None
    dates = []

    if request.method == 'POST':
        selected_patient = request.form.get('patient')
        if selected_patient:
            cur = mysql.connection.cursor()
            query = "SELECT tarih_doktor FROM tespit_doktor WHERE hasta_ad_doktor = %s"
            cur.execute(query, (selected_patient,))
            dates = cur.fetchall()
            cur.close()

            dates = [date[0] for date in dates]

        if 'date' in request.form:
            selected_date = request.form['date']
            return redirect(url_for('tespit_predict_doktor', patient=selected_patient, date=selected_date))

    return render_template('doktor_tespit.html', patients=patients, selected_patient=selected_patient, dates=dates)

def model_predict_doktor(img_path, model):
    try:
        if not os.path.exists(img_path):
            return f"Görüntü dosyası bulunamadı: {img_path}", None

        img = Image.open(img_path)
        if img.format not in ['JPEG', 'PNG']:
            img_path = img_path.rsplit('.', 1)[0] + '.jpg'
            img.convert('RGB').save(img_path, 'JPEG')

        results = model(img_path)[0]
        boxes = results.boxes
        predictions = [(class_dict1[int(box.cls)], float(box.conf) * 100) for box in boxes]

        img_draw = Image.open(img_path)
        img_draw = draw_results_doktor(img_draw, boxes)
        detected_img_path = img_path.replace('.jpg', '_detected.jpg')
        img_draw.save(detected_img_path)

        return predictions, detected_img_path
    except Exception as e:
        return str(e), None

def draw_results_doktor(image, boxes):
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("arial.ttf", 65)
    except IOError:
        font = ImageFont.load_default()

    for box in boxes:
        xmin, ymin, xmax, ymax = box.xyxy[0].tolist()
        class_id = int(box.cls)
        confidence = float(box.conf)
        label = f"{class_dict1[class_id]}: {confidence:.2f}%"
        draw.rectangle([xmin, ymin, xmax, ymax], outline="red", width=3)

        # Text background
        text_size = draw.textbbox((xmin, ymin), label, font=font)
        draw.rectangle([text_size[0], text_size[1], text_size[2], text_size[3]], fill="red")

        # Text
        draw.text((xmin, ymin), label, fill="white", font=font)

    return image

def calculate_overall_confidence_doktor(predictions):
    if not predictions:
        return 0
    total_confidence = sum([confidence for pred in predictions if len(pred) == 2 for _, confidence in [pred]])
    overall_confidence = total_confidence / len(predictions)
    return round(overall_confidence, 2)  # İki ondalık basamak ile yuvarla

@app.route('/predict/<patient>/<date>', methods=['GET'])
def tespit_predict_doktor(patient, date):
    if 'name_pms' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    query = "SELECT goruntu_doktor FROM tespit_doktor WHERE hasta_ad_doktor = %s AND tarih_doktor = %s"
    cur.execute(query, (patient, date))
    result = cur.fetchone()
    cur.close()

    if result is None:
        return "Image not found in the database."

    image_data = result[0]

    image_path = os.path.join('static/uploads', f'{patient}_{date}.jpg')
    with open(image_path, 'wb') as f:
        f.write(image_data)

    if not os.path.exists(image_path):
        return f"Görüntü dosyası bulunamadı: {image_path}"

    image_filename = os.path.basename(image_path)

    predictions, detected_img_path = model_predict_doktor(image_path, yolo_model1)
    if isinstance(predictions, str):
        return predictions
    overall_confidence = calculate_overall_confidence_doktor(predictions)
    detected_image_filename = os.path.basename(detected_img_path) if detected_img_path else None

    return render_template('predict.html', file_name=image_filename, detected_file_name=detected_image_filename,
                           overall_confidence=overall_confidence)

# Generate a random verification code and store it in the session
def generate_verification_code():
    verification_code = ''.join(random.choices(string.digits, k=6))
    session['verification_code'] = verification_code
    return verification_code

# ------------------------------------------------------------------------------------------------------------------------------

@app.route("/")
def home():
    if 'loggedin' in session:
        return redirect(url_for('index'))
    session['error']=''
    return render_template("home.html")

@app.route('/about')
def about():
    if 'loggedin' in session:
        return redirect(url_for('index'))
    return render_template("about.html")

@app.route("/contact")
def contact():
    if 'loggedin' in session:
        return redirect(url_for('contact_us'))
    return render_template('contact.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route("/terms-condition")
def terms_condition():
    if 'loggedin' in session:
        return redirect(url_for('terms_condition_user'))
    return render_template("terms-condition.html")

@app.route("/terms-condition-user")
def terms_condition_user():
    if 'loggedin' not in session:
        return redirect(url_for('terms_condition'))
    return render_template("terms-condition-user.html")


@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form['email']

    # Send thank you email
    send_thank_you_email(email)

    return redirect(url_for('home'))

def send_thank_you_email(email):
    message = Message('Abone Olduğunuz İçin Teşekkür Ederiz', recipients=[email])
    message.body = f"Sayın Abone,\n\nHaber bültenimize abone olduğunuz için teşekkür ederiz! Sizi aramızda görmekten heyecan duyuyoruz ve değerli güncellemeleri, haberleri ve teklifleri sizinle paylaşmayı sabırsızlıkla bekliyoruz.\n\nHerhangi bir sorunuz varsa veya yardıma ihtiyacınız varsa ekibimizle iletişime geçmekten çekinmeyin. Heyecan verici içerikler için takipte kalın!\n\nSaygılarımla,\nIDM Ekibi"

    try:
        mail.send(message)
        print("Teşekkür e-postası başarıyla gönderildi")
    except Exception as e:
        print(f"Teşekkür e-postası gönderilemedi: {str(e)}")


@app.route("/unauthorized")
def unauthorized():
    if 'loggedin' not in session:
        return redirect(url_for('home'))
    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')
    error = session.get('error')

    return render_template("404.html", error=error, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

@app.route("/index")
def index():
    if 'loggedin' not in session:
        return redirect(url_for('logout'))

    session['error']=''

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    return render_template("index.html", name=name, profile=profile, user=user, url=url, dashboard=dashboard)

@app.route("/about-us")
def about_us():
    if 'loggedin' not in session:
        return redirect(url_for('about'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    return render_template('about-us.html', name=name, profile=profile, user=user, url=url, dashboard=dashboard)

@app.route("/contact-us")
def contact_us():
    if 'loggedin' not in session:
        return redirect(url_for('contact'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    return render_template('contact-us.html', name=name, profile=profile, user=user, url=url, dashboard=dashboard)

# /login-phone
# /forgot-password
# Search Doctors for unregistered users:

@app.route('/search-doctors-pms', methods=['GET', 'POST'])
def search_doctors_pms():
    if request.method == 'POST':
        clinic_name = request.form["clinic_name"]
        doctor_name = request.form["doctor_name"]
        clinic_address = request.form["clinic_address"]

        # Construct the SQL query and parameters based on the search criteria
        query = "SELECT * FROM registered_doctors WHERE "
        conditions = []
        params = []

        if clinic_name and clinic_name != "":
            conditions.append("Clinic_Name LIKE %s")
            params.append(f"%{clinic_name}%")

        if doctor_name and doctor_name != "":
            conditions.append("Name LIKE %s")
            params.append(f"%{doctor_name}%")

        if clinic_address and clinic_address != "":
            conditions.append("Clinic_Address LIKE %s")
            params.append(f"%{clinic_address}%")

        if conditions:
            query += " AND ".join(conditions)
        else:
            query += "1"  # Dummy condition to retrieve all doctors if no specific criteria are provided

        # Execute the query and fetch the search results
        cur = mysql.connection.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        # Count the number of doctors found
        num_doctors_found = len(rows)
        msg = f"{num_doctors_found} Doktor Bulundu."

        if num_doctors_found == 0:
            return render_template('search-not-found.html')

        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of doctor data dictionaries
        doctor_data_list = []
        for row in rows:
            doctor_data = dict(zip(column_names, row))
            # Filter out None values from the doctor_data dictionary
            doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
            doctor_data_list.append(doctor_data)

        cur.close()

        # Render the search results on the search.html template
        return render_template('search-only.html', search_results=doctor_data_list, msg=msg)

    # Render the search form template for GET requests
    return render_template('home.html')


@app.route('/search-doctors', methods=['GET', 'POST'])
def search_doctors():
    l=['patient','doctor','admin']
    if session.get('user_type') not in l:
        return redirect(url_for('search_doctors_pms'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    if request.method == 'POST':
        clinic_name = request.form["clinic_name"]
        doctor_name = request.form["doctor_name"]
        clinic_address = request.form["clinic_address"]

        # Construct the SQL query and parameters based on the search criteria
        query = "SELECT * FROM registered_doctors WHERE "
        conditions = []
        params = []

        if clinic_name and clinic_name != "":
            conditions.append("Clinic_Name LIKE %s")
            params.append(f"%{clinic_name}%")

        if doctor_name and doctor_name != "":
            conditions.append("Name LIKE %s")
            params.append(f"%{doctor_name}%")

        if clinic_address and clinic_address != "":
            conditions.append("Clinic_Address LIKE %s")
            params.append(f"%{clinic_address}%")

        if conditions:
            query += " AND ".join(conditions)
        else:
            query += "1"  # Dummy condition to retrieve all doctors if no specific criteria are provided

        # Execute the query and fetch the search results
        cur = mysql.connection.cursor()
        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        # Count the number of doctors found
        num_doctors_found = len(rows)
        msg = f"{num_doctors_found} Doktor Bulundu."

        if num_doctors_found == 0:
            return render_template("search_not_found.html", name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of doctor data dictionaries
        doctor_data_list = []
        for row in rows:
            doctor_data = dict(zip(column_names, row))
            # Filter out None values from the doctor_data dictionary
            doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
            doctor_data_list.append(doctor_data)

        cur.close()

        # Render the search results on the search.html template
        return render_template('search.html', search_results=doctor_data_list, msg=msg, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    # Render the search form template for GET requests
    return redirect(url_for('index'))


@app.route('/book-appointment/<string:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if session.get('user_type') != 'patient':
        session['error'] = "Yetkili hasta değilsiniz. Bu sayfaya yalnızca yetkili hastalar erişebilir."
        return redirect(url_for('unauthorized'))

    # Retrieve the doctor's details based on the doctor ID
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM registered_doctors WHERE Doctor_ID = %s", (doctor_id,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    doctor_data = dict(zip(column_names, row))

    # Filter out None values from the doctor_data dictionary
    doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
    cur.close()

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    if request.method == 'POST':
        # Retrieve the form data for the appointment details
        appointment_date = request.form['appointment_date']
        appointment_time = request.form['appointment_time']
        insurance = request.form.get('insurance', 'No')
        reason = request.form['reason']
        symptoms = request.form['symptoms']

        patient_id = session['patient_id']

        if appointment_time == '':
            date_error = "Lütfen saati seçin."
            return render_template('booking.html', doctor_data=doctor_data, date_error=date_error, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Check if the appointment date is in the past
        selected_date = datetime.strptime(appointment_date, '%d/%m/%Y').date()
        current_date = datetime.now().date()
        if selected_date < current_date:
            date_error = "Lütfen şimdiki veya gelecekteki bir tarihi seçin."
            return render_template('booking.html', doctor_data=doctor_data, date_error=date_error, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Change the date format to 'YYYY-MM-DD' for MySQL
        appointment_date_mysql = selected_date.strftime('%Y-%m-%d')

        try:
            # Change the time format to 'HH:MM:SS' for MySQL (try 24-hour format first)
            appointment_time_mysql = datetime.strptime(appointment_time, '%H:%M').strftime('%H:%M:%S')
        except ValueError:
            try:
                # If 24-hour format fails, try 12-hour format
                appointment_time_mysql = datetime.strptime(appointment_time, '%I:%M %p').strftime('%H:%M:%S')
            except ValueError as e:
                date_error = "Lütfen geçerli bir saat formatı girin (24 saat veya 12 saat AM/PM)."
                return render_template('booking.html', doctor_data=doctor_data, date_error=date_error, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Check if the appointment already exists
        cur = mysql.connection.cursor()
        query = """
            SELECT * FROM appointments
            WHERE Patient_ID = %s AND Doctor_ID = %s AND Appointment_Date = %s
        """
        cur.execute(query, (patient_id, doctor_id, appointment_date_mysql))
        existing_appointment = cur.fetchone()

        if existing_appointment:
            # An appointment with the same doctor, date, and time already exists
            error_message = "Lütfen mevcut veya istenen bir tarihi seçin."
            return render_template('booking.html', doctor_data=doctor_data, date_error=error_message, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Store the appointment details in session
        session['doctor_id'] = doctor_id
        session['appointment_date_view'] = appointment_date
        session['appointment_time_view'] = appointment_time
        session['appointment_date'] = appointment_date_mysql
        session['appointment_time'] = appointment_time_mysql
        session['insurance'] = insurance
        session['reason'] = reason
        session['symptoms'] = symptoms

        # Redirect to the payment page
        return redirect(url_for('payment', doctor_id=doctor_id))

    # Render the appointment booking form with the doctor's details and today's date
    return render_template('booking.html', doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)


@app.route('/book-appointment/<string:doctor_id>/payment', methods=['GET', 'POST'])
def payment(doctor_id):
    if session.get('user_type') != 'patient':
        session['error'] = "Yetkili hasta değilsiniz. Bu sayfaya yalnızca yetkili hastalar erişebilir."
        return redirect(url_for('unauthorized'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')
    email = session.get('patient_email')

    # Retrieve the appointment data from session
    patient_id = session['patient_id']
    doctor_id = session['doctor_id']
    appointment_date = session['appointment_date_view']
    appointment_time = session['appointment_time_view']
    appointment_date_mysql = session['appointment_date']
    appointment_time_mysql = session['appointment_time']
    insurance = session['insurance']
    reason = session['reason']
    symptoms = session['symptoms']

    # Retrieve the doctor's details based on the doctor ID
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM registered_doctors WHERE Doctor_ID = %s", (doctor_id,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    doctor_data = dict(zip(column_names, row))

    # Filter out None values from the doctor_data dictionary
    doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
    print(doctor_data.keys())  # Add this line to print the keys
    cur.close()

    # Check if the 'Fee' key is present in the dictionary
    if 'Fee' in doctor_data:
        if doctor_data['Fee'] != None:
            doctor_fee = float(doctor_data['Fee'])
        else:
            doctor_fee = 0.0
    else:
        doctor_fee = 100.0

    booking_fee_amount = 2.0
    tax_amount = (doctor_fee * 3) / 100
    total_fee = doctor_fee + booking_fee_amount + tax_amount

    if request.method == 'POST':
        # Perform payment validation and processing here
        #payment = request.form["payment"]
        #print(payment)

        # Save the appointment details with the doctor ID
        # Insert the appointment data into the appointments table
        cur = mysql.connection.cursor()
        query = """
            INSERT INTO appointments (Patient_ID, Doctor_ID, Appointment_Date, Appointment_Time, Insurance, Reason, Symptoms)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        appointment_values = (
            patient_id,
            doctor_id,
            appointment_date_mysql,
            appointment_time_mysql,
            insurance,
            reason,
            symptoms
        )

        cur.execute(query, appointment_values)
        mysql.connection.commit()
        cur.close()

        #session.pop('patient_id', None)
        session.pop('doctor_id', None)
        session.pop('appointment_date_view', None)
        session.pop('appointment_time_view', None)
        session.pop('appointment_date', None)
        session.pop('appointment_time', None)
        session.pop('insurance', None)
        session.pop('reason', None)
        session.pop('symptoms', None)


        if 'Name' in doctor_data:
            doctor_name = doctor_data['Name']
        else:
            doctor_name = "Unknown"

         # Send email to the patient with appointment details
        msg = Message('Randevu onayı', recipients=[email])

        msg.body = f"Sevgili {name},\n\nIDM ile randevu aldığınız için teşekkür ederiz.\n\nRandevu detaylarınız aşağıdaki gibidir:\n\nDoktor: {doctor_name}\nRandevu Tarihi: {appointment_date}\nBuluşma zamanı: {appointment_time}\n\nSizi görmek için sabırsızlanıyoruz!\n\nSaygılarımla,\nIDM Ekibi"
        mail.send(msg)

        # Redirect to a success page or show a success message
        return render_template('successful.html', doctor=doctor_data, appointment_date=appointment_date, appointment_time=appointment_time, name=name, profile=profile, user=user, url=url, dashboard=dashboard)


        # Redirect to a success page or show a success message
        return render_template('successful.html', doctor=doctor_data, appointment_date = appointment_date, appointment_time = appointment_time, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    return render_template('payment.html', doctor=doctor_data,doctor_id = doctor_id, appointment_date = appointment_date, appointment_time = appointment_time,
                          doctor_fee = doctor_fee, booking_fee=booking_fee_amount, tax=tax_amount, total_fee=total_fee, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

# ------------------------------------------------------------------------------------------------------------------------------

# PATIENTS RECORDS:

@app.route("/patient-register", methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        full_name = request.form["fullname"]
        email = request.form["email"]
        phone_no = request.form["phone"]
        password = request.form["password"]

        # Regular expression patterns
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        phone_pattern = r'^\d{10}$'
        password_pattern = r'^.{8,}$'

        # Validate email
        if not re.match(email_pattern, email):
            error_message = "Geçersiz e-posta adresi. Lütfen geçerli eposta adresini giriniz."
            return render_template("patient-register.html", error=error_message)

        # Validate phone number
        if not re.match(phone_pattern, phone_no):
            error_message = "Geçersiz telefon numarası. Lütfen 10 haneli telefon numarasını giriniz."
            return render_template("patient-register.html", error=error_message)

        # Validate password
        if not re.match(password_pattern, password):
            error_message = "Geçersiz şifre. Şifre en az 8 karakter uzunluğunda olmalıdır."
            return render_template("patient-register.html", error=error_message)

        # Check if the patient already exists in the database
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_patients WHERE Email = %s OR Phone = %s"
        cur.execute(query, (email, phone_no))
        row = cur.fetchone()

        if row is not None:
            column_names = [desc[0] for desc in cur.description]  # Get the column names
            patient_data = dict(zip(column_names, row))
            cur.close()
            # Check if email or phone number is already registered
            if patient_data['Email'] == email:
                error_message = "E-posta zaten kayıtlı."
            else:
                error_message = "Telefon numarası zaten kayıtlı."
            return render_template("patient-register.html", error=error_message)
        cur.close()

        # Generate a unique patient ID
        patient_id = generate_patient_id(full_name)

        # Register the patient if not already registered
        cur = mysql.connection.cursor()
        query = "INSERT INTO registered_patients (Name, Email, Phone, Password, Patient_ID) VALUES (%s, %s, %s, %s, %s)"
        cur.execute(query, (full_name, email, phone_no, password, patient_id))

        mysql.connection.commit()
        cur.close()

        # Send registration email to the user
        msg = Message('Kayıt Onayı', recipients=[email])
        msg.body = f"Sevgili {full_name},\n\nIDM'e kaydolduğunuz için teşekkür ederiz.\n\nIDM'nin sunduğu tüm hizmet ve özelliklere erişmek için artık giriş yapabilirsiniz.\n\nSize hizmet etmek için sabırsızlanıyoruz!\n\nSaygılarımla,\nIDM Ekibi"
        mail.send(msg)

        return render_template('success.html')

    return render_template("patient-register.html")

def generate_patient_id(full_name):
    # Generate random digits
    random_digits = ''.join(random.choices(string.digits, k=4))

    # Get the current date and time
    now = datetime.now()
    day_digit = str(now.day)[0]
    month_digit = str(now.month)[0]
    minute_digit = str(now.minute)[0]
    second_digit = str(now.second)[0]

    # Create the patient ID by combining name characters, digits, and the date
    patient_id = f"{full_name[:3].upper()}{random_digits}{day_digit}{month_digit}{minute_digit}{second_digit}"

    return patient_id


@app.route('/patient-dashboard')
def patient_dashboard():
    if session['user_type'] == 'patient':
        email = session['email']  # Retrieve the logged-in doctor's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_patients WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        column_names = [desc[0] for desc in cur.description]  # Get the column names
        patient_data = dict(zip(column_names, row))
        cur.close()

        # Check if the 'Profile_URL' key exists in the row_dict dictionary
        if 'Profile_URL' in patient_data and patient_data['Profile_URL'] is not None:
            session['profile_pms'] = 'patients/' + patient_data['Profile_URL']
        if 'Name' in patient_data and patient_data['Name'] is not None:
            session['name_pms'] = patient_data['Name']

        # Get user information from the session
        name = session.get('name_pms')
        profile = session.get('profile_pms')
        user = session.get('user_pms')
        url = session.get('url_pms')
        dashboard = session.get('dashboard_pms')

        patient_id = patient_data['Patient_ID']

        cur = mysql.connection.cursor()
        query = """
            SELECT appointments.*, registered_doctors.Name AS Doctor_Name, registered_doctors.Profile_URL AS Profile_URL, registered_doctors.Doctor_ID, registered_doctors.Specialization AS Specialization
            FROM appointments
            JOIN registered_doctors ON appointments.Doctor_ID = registered_doctors.Doctor_ID
            WHERE Patient_ID = %s
            ORDER BY Appointment_Date >= CURDATE() DESC, Appointment_Date ASC
        """
        cur.execute(query, (patient_id,))

        rows = cur.fetchall()
        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of appointment data dictionaries
        appointment_data_list = []
        for row in rows:
            appointment_data = dict(zip(column_names, row))
            # Filter out None values from the appointment_data dictionary
            appointment_data = {k: v for k, v in appointment_data.items() if v is not None}
            appointment_data_list.append(appointment_data)

        cur.close()
        amount_paid = "--"

        # Render the doctor dashboard template
        return render_template('patient-dashboard.html', appointment_data_list=appointment_data_list, amount_paid=amount_paid, patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)
    else:
        session['error'] = "Yetkili hasta değilsiniz. Bu sayfaya yalnızca yetkili hastalar erişebilir."
        return redirect(url_for('unauthorized'))

@app.route("/patient-profile-settings", methods=['GET', 'POST'])
def patient_profile_settings():
    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    if session['user_type'] == 'patient':
        if request.method == 'POST':
            # Get the updated patient data from the form
            name = request.form['name']
            dob = request.form['dob']
            blood_group = request.form['blood_group']
            phone = request.form['phone']
            address = request.form['address']
            city = request.form['city']
            state = request.form['state']
            pincode = request.form['pincode']
            country = request.form['country']

            email = session['email']  # Retrieve the logged-in patient's email from the session

            # Construct the SQL query and parameters based on the updated fields
            query = "UPDATE registered_patients SET"
            params = []

            if name:
                query += " Name = %s,"
                params.append(name)

            if dob:
                query += " Date_of_Birth = %s,"
                params.append(dob)

            if blood_group:
                query += " Blood_Group = %s,"
                params.append(blood_group)

            if phone:
                query += " Phone = %s,"
                params.append(phone)

            if address:
                query += " Address = %s,"
                params.append(address)

            if city:
                query += " City = %s,"
                params.append(city)

            if state:
                query += " State = %s,"
                params.append(state)

            if pincode:
                query += " Pin_Code = %s,"
                params.append(pincode)

            if country:
                query += " Country = %s,"
                params.append(country)

            # Remove the trailing comma from the query
            query = query.rstrip(',')

            # Add the WHERE clause to update the specific patient's record
            query += " WHERE Email = %s"
            params.append(email)

            # Update the patient data in the database
            cur = mysql.connection.cursor()
            cur.execute(query, tuple(params))
            mysql.connection.commit()
            cur.close()

            # Handle image upload
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename != '':
                    email = session['email']
                    cur = mysql.connection.cursor()
                    # Generate a secure filename and specify the upload folder path
                    filename = secure_filename(session['patient_id'] + os.path.splitext(photo.filename)[1])
                    upload_folder = os.path.join(app.root_path, 'static', 'assets', 'img', 'patients')

                    # Save the uploaded image with the patient_id as the filename
                    photo.save(os.path.join(upload_folder, filename))

                    # Update the image filename in the database
                    cur = mysql.connection.cursor()
                    query = "UPDATE registered_patients SET Profile_URL = %s WHERE Email = %s"
                    cur.execute(query, (filename, email))
                    mysql.connection.commit()
                    cur.close()

            # Redirect to the patient dashboard or any other appropriate page
            return redirect(url_for('patient_dashboard'))

        # Retrieve the patient's data from the database for display
        email = session['email']  # Retrieve the logged-in patient's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_patients WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        if row:
            column_names = [desc[0] for desc in cur.description]  # Get the column names
            patient_data = dict(zip(column_names, row))

            # Filter out None values from the patient_data dictionary
            patient_data = {k: v for k, v in patient_data.items() if v is not None}

            session['patient_id'] = patient_data['Patient_ID']
            cur.close()

            # Render the patient profile settings template with the patient's data
            return render_template('patient-profile-settings.html', patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    else:
        session['error'] = "Yetkili hasta değilsiniz. Bu sayfaya yalnızca yetkili hastalar erişebilir."
        return redirect(url_for('unauthorized'))


@app.route('/patient-change-password', methods=['GET', 'POST'])
def patient_change_password():
    if session.get('user_type') != 'patient':
        session['error'] = "Yetkili hasta değilsiniz. Bu sayfaya yalnızca yetkili hastalar erişebilir."
        return redirect(url_for('unauthorized'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    # Retrieve the patient's data from the database for display
    f_email = session['email']  # Retrieve the logged-in patient's email from the session
    cur = mysql.connection.cursor()
    query = "SELECT * FROM registered_patients WHERE Email = %s"
    cur.execute(query, (f_email,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    patient_data = dict(zip(column_names, row))
    session['old_password'] = patient_data['Password']
    cur.close()

    if request.method == 'POST':
        # Access the form data
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Perform validation
        # Example: Check if the old password matches the current password for the patient
        if old_password != session['old_password']:
            error_message = "Eski şifre yanlış."
            return render_template('patient-change-password.html', error=error_message, patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Example: Check if the new password meets the desired criteria
        if new_password != confirm_password:
            error_message = "Yeni şifre ve onay şifresi eşleşmiyor."
            return render_template('patient-change-password.html', error=error_message, patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Update the password in the database for the patient
        patient_id = patient_data['Patient_ID']
        update_password_in_p_database(patient_id, new_password)

        success_message = "Parola başarıyla değiştirildi."
        return render_template('patient-change-password.html', error=success_message, patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    return render_template('patient-change-password.html', patient_data=patient_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

def update_password_in_p_database(patient_id, new_password):
    cur = mysql.connection.cursor()
    query = "UPDATE registered_patients SET Password = %s WHERE Patient_ID = %s"
    cur.execute(query, (new_password, patient_id))
    mysql.connection.commit()
    cur.close()

# -----------------------------------------------------------------------------------------------------------------------------

# DOCTORS RECORDS:

@app.route("/doctor-register", methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        # Handle the POST request for the "/doctor-register" URL
        name = request.form['name']
        gender = request.form["gender"]
        clinic_name = request.form["clinic_name"]
        clinic_address = request.form["clinic_address"]
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Regular expression patterns
        email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        phone_pattern = r'^\d{10}$'
        password_pattern = r'^.{8,}$'

        # Validate email
        if not re.match(email_pattern, email):
            error = "Geçersiz e-posta adresi. Lütfen geçerli eposta adresini giriniz."
            return render_template("doctor-register.html",error=error)

        # Validate phone number
        if not re.match(phone_pattern, phone):
            error = "Geçersiz telefon numarası. Lütfen 10 haneli telefon numarasını giriniz."
            return render_template("doctor-register.html",error=error)

        # Validate password
        if not re.match(password_pattern, password):
            error = "Geçersiz şifre. Şifre en az 8 karakter uzunluğunda olmalıdır."
            return render_template("doctor-register.html",error=error)

        # Check if the patient already exists in the database
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_doctors WHERE Email = %s OR Phone = %s"
        cur.execute(query, (email, phone))
        row = cur.fetchone()

        if row is not None:
            column_names = [desc[0] for desc in cur.description]  # Get the column names
            doctor_data = dict(zip(column_names, row))
            cur.close()
            # Check if email or phone number is already registered
            if doctor_data['Email'] == email:
                error_message = "E-posta zaten kayıtlı."
            else:
                error_message = "Telefon numarası zaten kayıtlı."
            return render_template("patient-register.html", error=error_message)
        cur.close()

        # Generate a verification code
        verification_code = generate_verification_code()

        # Send verification email
        msg = Message('Hesap Doğrulama', recipients=[email])
        msg.body = f"Doğrulama Kodunuz: {verification_code}"
        mail.send(msg)

        print(verification_code)

        # Generate a unique doctor ID
        doctor_id = generate_doctor_id(name)

        # Store user data, verification code, and doctor ID in the session
        session['doctor_id'] = doctor_id
        session['doctor_name'] = name
        session['gender'] = gender
        session['clinic_name'] = clinic_name
        session['clinic_address'] = clinic_address
        session['doctor_email'] = email
        session['doctor_phone'] = phone
        session['doctor_password'] = password
        session['verification_code'] = verification_code

        return redirect(url_for('verify', email=email))

    return render_template("doctor-register.html")


@app.route('/verify/<email>', methods=['GET', 'POST'])
def verify(email):
    if request.method == 'POST':
        verification_code = request.form['verification_code']

        # Retrieve the stored verification code and doctor ID from the session
        stored_verification_code = session.get('verification_code')
        doctor_id = session.get('doctor_id')

        # Compare the codes
        if verification_code == stored_verification_code:
            # Code is correct, store doctor data in the database
            name = session['doctor_name']
            gender = session['gender']
            clinic_name = session['clinic_name']
            clinic_address = session['clinic_address']
            email = session['doctor_email']
            phone = session['doctor_phone']
            password = session['doctor_password']

            # Insert doctor data into the database
            cur = mysql.connection.cursor()
            query = "INSERT INTO registered_doctors (Doctor_ID, Name, Gender, Clinic_Name, Clinic_Address, Email, Phone, Password) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cur.execute(query, (doctor_id, name, gender, clinic_name, clinic_address, email, phone, password))

            mysql.connection.commit()
            cur.close()

            # Clear the session data
            session.pop('doctor_id', None)
            session.pop('doctor_name', None)
            session.pop('gender',None)
            session.pop('clinic_name',None)
            session.pop('clinic_address',None)
            session.pop('doctor_email', None)
            session.pop('doctor_phone', None)
            session.pop('doctor_password', None)
            session.pop('verification_code', None)

            # Send registration email to the user
            msg = Message('Kayıt Onayı', recipients=[email])
            msg.body = f"Sevgili Dr. {name},\n\nIDM'e kaydolduğunuz için teşekkür ederiz.\n\nIDM'nin sunduğu tüm hizmet ve özelliklere erişmek için artık giriş yapabilirsiniz.\n\nSize hizmet etmek için sabırsızlanıyoruz!\n\nSaygılarımla,\nIDM Ekibi"
            mail.send(msg)

            return render_template('success.html')
        else:
            error = 'Incorrect OTP'
            # Code is incorrect, display an error message
            return render_template('verify.html', email=email, error=error)

    return render_template('verify.html', email=email, error=False)

def generate_doctor_id(name):
    # Generate random digits
    random_digits = ''.join(random.choices(string.digits, k=4))

    # Get the current date and time
    now = datetime.now()
    day_digit = str(now.day)[0]
    month_digit = str(now.month)[0]
    minute_digit = str(now.minute)[0]
    second_digit = str(now.second)[0]

    # Create the doctor ID by combining name characters, digits, and the date
    doctor_id = f"{name[:3].upper()}{random_digits}{day_digit}{month_digit}{minute_digit}{second_digit}"

    return doctor_id

@app.route('/doctor-profile/<string:doctor_id>', methods=['GET', 'POST'])
def doctor_profile(doctor_id):
    # Retrieve the doctor's details based on the doctor ID
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM registered_doctors WHERE Doctor_ID = %s", (doctor_id,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    doctor_data = dict(zip(column_names, row))

    # Filter out None values from the doctor_data dictionary
    doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
    cur.close()

    # Check if the 'Fee' key is present in the dictionary
    if 'Fee' in doctor_data:
        if doctor_data['Fee'] is not None:
            doctor_fee = float(doctor_data['Fee'])
        else:
            doctor_fee = 0.0
    else:
        doctor_fee = 100.0

    today_date = date.today()

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    # Check user
    l = ['patient', 'doctor', 'admin']
    if session.get('user_type') not in l:
        return render_template('doctor-profile-non-user.html', today_date=today_date, doctor=doctor_data, doctor_fee=doctor_fee, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    # Render the appointment booking form with the doctor's details and today's date
    return render_template('doctor-profile.html', today_date=today_date, doctor=doctor_data, doctor_fee=doctor_fee, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

@app.route('/doctor-dashboard')
def doctor_dashboard():
    if session['user_type'] == 'doctor':
        email = session['email']  # Retrieve the logged-in doctor's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_doctors WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        column_names = [desc[0] for desc in cur.description]  # Get the column names
        doctor_data = dict(zip(column_names, row))
        cur.close()

        # Check if the 'Profile_URL' key exists in the row_dict dictionary
        if 'Profile_URL' in doctor_data and doctor_data['Profile_URL'] is not None:
            session['profile_pms'] = 'doctors/' + doctor_data['Profile_URL']
        if 'Name' in doctor_data and doctor_data['Name'] is not None:
            session['name_pms'] = doctor_data['Name']

        # Get user information from the session
        name = session.get('name_pms')
        profile = session.get('profile_pms')
        user = session.get('user_pms')
        url = session.get('url_pms')
        dashboard = session.get('dashboard_pms')

        doctor_id = doctor_data['Doctor_ID']

        cur = mysql.connection.cursor()
        query = """
            SELECT appointments.*, registered_patients.Name AS Patient_Name, registered_patients.Profile_URL AS Profile_URL, registered_patients.Patient_ID, tespit.accuracy AS Tespit_Orani, tespit.tarih AS Tarih
            FROM appointments
            JOIN registered_patients ON appointments.Patient_ID = registered_patients.Patient_ID
            LEFT JOIN tespit ON registered_patients.Name = tespit.hasta_ad
            WHERE Doctor_ID = %s
        """
        cur.execute(query, (doctor_id,))
        rows = cur.fetchall()
        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of appointment data dictionaries
        appointment_data_list = []
        for row in rows:
            appointment_data = dict(zip(column_names, row))
            # Filter out None values from the appointment_data dictionary
            appointment_data = {k: v for k, v in appointment_data.items() if v is not None}
            appointment_data_list.append(appointment_data)

        cur.close()
        total_patient = len(rows)

        today_date = date.today()  # Get the current date
        amount_paid = "--"

        # Split appointments into today's patients and upcoming patients
        today_patients = []
        upcoming_patients = []
        for appointment in appointment_data_list:
            appointment_date = appointment['Appointment_Date']
            if appointment_date == today_date:
                today_patients.append(appointment)
            elif appointment_date > today_date:
                upcoming_patients.append(appointment)

        total_today_patients = len(today_patients)
        total_upcoming_patients = len(upcoming_patients)

        # Render the doctor dashboard template
        return render_template('doctor-dashboard.html', amount_paid=amount_paid, today_date=today_date, total_upcoming_patients=total_upcoming_patients, total_today_patients=total_today_patients, doctor_data=doctor_data, today_patients=today_patients, upcoming_patients=upcoming_patients, total_patient=total_patient, name=name, profile=profile, user=user, url=url, dashboard=dashboard)
    else:
        session['error'] = "Yetkili doktor değilsiniz. Bu sayfaya yalnızca yetkili doktorlar erişebilir."
        return redirect(url_for('unauthorized'))

@app.route('/doctor-profile-settings', methods=['GET', 'POST'])
def doctor_profile_settings():
    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    if session['user_type'] == 'doctor':
        if request.method == 'POST':
            # Get the updated doctor data from the form
            name = request.form['name']
            phone = request.form['phone']
            qualification = request.form['qualification']
            specialization = request.form['specialization']
            clinic_name = request.form['clinic_name']
            clinic_address = request.form['clinic_address']
            fees = request.form['fees']
            about_clinic = request.form['about_clinic']
            address_line1 = request.form['address_line1']
            address_line2 = request.form['address_line2']
            city = request.form['city']
            state = request.form['state']
            registration_number = request.form['registration_number']
            year = request.form['year']
            email = session['email']  # Retrieve the logged-in doctor's email from the session

            # Construct the SQL query and parameters based on the updated fields
            query = "UPDATE registered_doctors SET"
            params = []

            if name:
                query += " Name = %s,"
                params.append(name)

            if phone:
                query += " Phone = %s,"
                params.append(phone)

            if qualification:
                query += " Qualification = %s,"
                params.append(qualification)

            if specialization:
                query += " Specialization = %s,"
                params.append(specialization)

            if clinic_name:
                query += " Clinic_Name = %s,"
                params.append(clinic_name)

            if fees:
                query += " Fee = %s,"
                params.append(fees)

            if clinic_address:
                query += " Clinic_Address = %s,"
                params.append(clinic_address)

            if about_clinic:
                query += " About_Clinic = %s,"
                params.append(about_clinic)

            if address_line1:
                query += " Address_Line1 = %s,"
                params.append(address_line1)

            if address_line2:
                query += " Address_Line2 = %s,"
                params.append(address_line2)

            if city:
                query += " City = %s,"
                params.append(city)

            if state:
                query += " State = %s,"
                params.append(state)

            if registration_number:
                query += " Registration_Number = %s,"
                params.append(registration_number)

            if year:
                query += " Year = %s,"
                params.append(year)

            # Remove the trailing comma from the query
            query = query.rstrip(',')

            # Add the WHERE clause to update the specific doctor's record
            query += " WHERE Email = %s"
            params.append(email)

            # Update the doctor data in the database
            cur = mysql.connection.cursor()
            cur.execute(query, tuple(params))
            mysql.connection.commit()
            cur.close()

            # Handle image upload
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename != '':
                    email = session['email']
                    cur = mysql.connection.cursor()
                    # Generate a secure filename and specify the upload folder path
                    filename = secure_filename(session['doctor_id'] + os.path.splitext(photo.filename)[1])
                    upload_folder = os.path.join(app.root_path, 'static', 'assets', 'img', 'doctors')

                    # Save the uploaded image with the doctor_id as the filename
                    photo.save(os.path.join(upload_folder, filename))

                    # Update the image filename in the database
                    cur = mysql.connection.cursor()
                    query = "UPDATE registered_doctors SET Profile_URL = %s WHERE Email = %s"
                    cur.execute(query, (filename, email))
                    mysql.connection.commit()
                    cur.close()

            # Redirect to the doctor dashboard or any other appropriate page
            return redirect(url_for('doctor_dashboard'))

        # Retrieve the doctor's data from the database for display
        email = session['email']  # Retrieve the logged-in doctor's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_doctors WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        if row:
            column_names = [desc[0] for desc in cur.description]  # Get the column names
            doctor_data = dict(zip(column_names, row))

            # Filter out None values from the doctor_data dictionary
            doctor_data = {k: v for k, v in doctor_data.items() if v is not None}

            session['doctor_id'] = doctor_data['Doctor_ID']
            cur.close()

            # Render the doctor profile settings template with the doctor's data
            return render_template('doctor-profile-settings.html', doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)


    else:
        session['error'] = "Yetkili doktor değilsiniz. Bu sayfaya yalnızca yetkili doktorlar erişebilir."
        return redirect(url_for('unauthorized'))


@app.route('/doctor-change-password', methods=['GET', 'POST'])
def doctor_change_password():
    if session.get('user_type') != 'doctor':
        session['error'] = "Yetkili doktor değilsiniz. Bu sayfaya yalnızca yetkili doktorlar erişebilir."
        return redirect(url_for('unauthorized'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    # Retrieve the doctor's data from the database for display
    email = session['email']  # Retrieve the logged-in doctor's email from the session
    cur = mysql.connection.cursor()
    query = "SELECT * FROM registered_doctors WHERE Email = %s"
    cur.execute(query, (email,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    doctor_data = dict(zip(column_names, row))
    session['old_password'] = doctor_data['Password']
    cur.close()

    if request.method == 'POST':
        # Access the form data
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Perform validation
        # Example: Check if the old password matches the current password for the doctor
        if old_password != session['old_password']:
            error_message = "Eski şifre yanlış."
            return render_template('doctor-change-password.html', error=error_message,doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Example: Check if the new password meets the desired criteria
        if new_password != confirm_password:
            error_message = "Yeni şifre ve onay şifresi eşleşmiyor."
            return render_template('doctor-change-password.html', error=error_message,doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Update the password in the database for the doctor
        doctor_id = doctor_data['Doctor_ID']
        update_password_in_d_database(doctor_id, new_password)

        success_message = "Parola başarıyla değiştirildi."
        return render_template('doctor-change-password.html', error=success_message,doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    return render_template('doctor-change-password.html', doctor_data=doctor_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

def update_password_in_d_database(doctor_id, new_password):
    cur = mysql.connection.cursor()
    query = "UPDATE registered_doctors SET Password = %s WHERE Doctor_ID = %s"
    cur.execute(query, (new_password, doctor_id))
    mysql.connection.commit()
    cur.close()

# ------------------------------------------------------------------------------------------------------------------------------
# ADMINS RECORDS:
# ------------------------------------------------------------------------------------------------------------------------------

@app.route("/admin-register", methods=['GET', 'POST'])
def admin_register():
    if session['user_type'] == 'admin':
        email = session['email']  # Retrieve the logged-in admin's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_admins WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        column_names = [desc[0] for desc in cur.description]  # Get the column names
        admin_data = dict(zip(column_names, row))
        cur.close()

        # Check if the 'Profile_URL' key exists in the row_dict dictionary
        if 'Profile_URL' in admin_data and admin_data['Profile_URL'] is not None:
            session['profile_pms'] = 'admins/' + admin_data['Profile_URL']
        if 'Name' in admin_data and admin_data['Name'] is not None:
            session['name_pms'] = admin_data['Name']

        # Get user information from the session
        name = session.get('name_pms')
        profile = session.get('profile_pms')
        user = session.get('user_pms')
        url = session.get('url_pms')
        dashboard = session.get('dashboard_pms')


        if request.method == 'POST':
            full_name = request.form["fullname"]
            email = request.form["email"]
            phone_no = request.form["phone"]
            password = request.form["password"]

            # Regular expression patterns
            email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
            phone_pattern = r'^\d{10}$'
            password_pattern = r'^.{8,}$'

            # Validate email
            if not re.match(email_pattern, email):
                error_message = "Geçersiz e-posta adresi. Lütfen geçerli eposta adresini giriniz."
                return render_template("admin-register.html", error=error_message, admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

            # Validate phone number
            if not re.match(phone_pattern, phone_no):
                error_message = "Geçersiz telefon numarası. Lütfen 10 haneli telefon numarasını giriniz."
                return render_template("admin-register.html", error=error_message,admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

            # Validate password
            if not re.match(password_pattern, password):
                error_message = "Geçersiz şifre. Şifre en az 8 karakter uzunluğunda olmalıdır."
                return render_template("admin-register.html", error=error_message,admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

            # Check if the admin already exists in the database
            cur = mysql.connection.cursor()
            query = "SELECT * FROM registered_admins WHERE Email = %s OR Phone = %s"
            cur.execute(query, (email, phone_no))
            row = cur.fetchone()

            if row is not None:
                column_names = [desc[0] for desc in cur.description]  # Get the column names
                admin_data = dict(zip(column_names, row))
                cur.close()
                # Check if email or phone number is already registered
                if admin_data['Email'] == email:
                    error_message = "E-posta zaten kayıtlı."
                else:
                    error_message = "Telefon numarası zaten kayıtlı."
                return render_template("admin-register.html", error=error_message,admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)
            cur.close()

            # Generate a unique admin ID
            admin_id = generate_admin_id(full_name)

            # Register the admin if not already registered
            cur = mysql.connection.cursor()
            query = "INSERT INTO registered_admins (Name, Email, Phone, Password, Admin_ID) VALUES (%s, %s, %s, %s, %s)"
            cur.execute(query, (full_name, email, phone_no, password, admin_id))

            mysql.connection.commit()
            cur.close()

            success_message = "Yönetici Başarılı Bir Şekilde Kaydedildi."

            return render_template("admin-register.html", error=success_message,admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        return render_template("admin-register.html",admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)


    else:
        session['error'] = "Yetkili bir yönetici değilsiniz. Bu sayfaya yalnızca yetkili yöneticiler erişebilir."
        return redirect(url_for('unauthorized'))


def generate_admin_id(full_name):
    # Generate random digits
    random_digits = ''.join(random.choices(string.digits, k=4))

    # Get the current date and time
    now = datetime.now()
    day_digit = str(now.day)[0]
    month_digit = str(now.month)[0]
    minute_digit = str(now.minute)[0]
    second_digit = str(now.second)[0]

    # Create the admin ID by combining name characters, digits, and the date
    admin_id = f"{full_name[:3].upper()}{random_digits}{day_digit}{month_digit}{minute_digit}{second_digit}"

    return admin_id


@app.route('/admin-dashboard')
def admin_dashboard():
    if session['user_type'] == 'admin':
        email = session['email']  # Retrieve the logged-in admin's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_admins WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        column_names = [desc[0] for desc in cur.description]  # Get the column names
        admin_data = dict(zip(column_names, row))
        cur.close()

        # All Doctors records
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_doctors"
        cur.execute(query)
        rows = cur.fetchall()
        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of doctor data dictionaries
        doctor_data_list = []
        for row in rows:
            doctor_data = dict(zip(column_names, row))
            # Filter out None values from the doctor_data dictionary
            doctor_data = {k: v for k, v in doctor_data.items() if v is not None}
            doctor_data_list.append(doctor_data)

        cur.close()

        # All Patients records
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_patients"
        cur.execute(query)
        rows = cur.fetchall()
        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of patient data dictionaries
        patient_data_list = []
        for row in rows:
            patient_data = dict(zip(column_names, row))
            # Filter out None values from the patient_data dictionary
            patient_data = {k: v for k, v in patient_data.items() if v is not None}
            patient_data_list.append(patient_data)

        cur.close()

        # Check if the 'Profile_URL' key exists in the admin_data dictionary
        if 'Profile_URL' in admin_data and admin_data['Profile_URL'] is not None:
            session['profile_pms'] = 'admins/' + admin_data['Profile_URL']
        if 'Name' in admin_data and admin_data['Name'] is not None:
            session['name_pms'] = admin_data['Name']

        # Get user information from the session
        name = session.get('name_pms')
        profile = session.get('profile_pms')
        user = session.get('user_pms')
        url = session.get('url_pms')
        dashboard = session.get('dashboard_pms')

        admin_id = admin_data['Admin_ID']

        cur = mysql.connection.cursor()
        query = """
            SELECT registered_doctors.Name AS Doctor_Name, registered_doctors.Profile_URL AS Doctor_Profile_URL, registered_doctors.Doctor_ID, registered_doctors.Doctor_ID, registered_doctors.Specialization, registered_patients.Name AS Patient_Name, registered_patients.Profile_URL AS Patient_Profile_URL, registered_patients.Patient_ID, appointments.Appointment_Date, appointments.Appointment_Time
            FROM appointments
            JOIN registered_doctors ON appointments.Doctor_ID = registered_doctors.Doctor_ID
            JOIN registered_patients ON appointments.Patient_ID = registered_patients.Patient_ID
            ORDER BY appointments.Appointment_Date ASC
        """
        cur.execute(query)

        rows = cur.fetchall()
        # Get the column names
        column_names = [desc[0] for desc in cur.description]

        # Prepare the list of appointment data dictionaries
        appointment_data_list = []
        for row in rows:
            appointment_data = dict(zip(column_names, row))
            # Filter out None values from the appointment_data dictionary
            appointment_data = {k: v for k, v in appointment_data.items() if v is not None}
            appointment_data_list.append(appointment_data)

        cur.close()

        total_appointment = len(appointment_data_list)
        total_doctor = len(doctor_data_list)
        total_patient = len(patient_data_list)
        revenue = total_appointment*2

        # Render the admin dashboard template
        return render_template('admin-dashboard.html',total_appointment=total_appointment, total_patient=total_patient, total_doctor=total_doctor, revenue = revenue, doctor_data_list=doctor_data_list, patient_data_list=patient_data_list, appointment_data_list=appointment_data_list, admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)
    else:
        session['error'] = "Yetkili bir yönetici değilsiniz. Bu sayfaya yalnızca yetkili yöneticiler erişebilir."
        return redirect(url_for('unauthorized'))


@app.route("/admin-profile-settings", methods=['GET', 'POST'])
def admin_profile_settings():
    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    if session['user_type'] == 'admin':
        if request.method == 'POST':
            # Get the updated admin data from the form
            name = request.form['name']
            phone = request.form['phone']
            address = request.form['address']
            city = request.form['city']
            state = request.form['state']
            pincode = request.form['pincode']
            country = request.form['country']
            qualification = request.form['qualification']
            job = request.form['job']

            email = session['email']  # Retrieve the logged-in admin's email from the session

            # Construct the SQL query and parameters based on the updated fields
            query = "UPDATE registered_admins SET"
            params = []

            if name:
                query += " Name = %s,"
                params.append(name)

            if qualification:
                query += " Qualification = %s,"
                params.append(qualification)

            if job:
                query += " Job_Profile = %s,"
                params.append(job)

            if phone:
                query += " Phone = %s,"
                params.append(phone)

            if address:
                query += " Address = %s,"
                params.append(address)

            if city:
                query += " City = %s,"
                params.append(city)

            if state:
                query += " State = %s,"
                params.append(state)

            if pincode:
                query += " Pin_Code = %s,"
                params.append(pincode)

            if country:
                query += " Country = %s,"
                params.append(country)

            # Remove the trailing comma from the query
            query = query.rstrip(',')

            # Add the WHERE clause to update the specific admin's record
            query += " WHERE Email = %s"
            params.append(email)

            # Update the admin data in the database
            cur = mysql.connection.cursor()
            cur.execute(query, tuple(params))
            mysql.connection.commit()
            cur.close()

            # Handle image upload
            if 'photo' in request.files:
                photo = request.files['photo']
                if photo.filename != '':
                    email = session['email']
                    cur = mysql.connection.cursor()
                    # Generate a secure filename and specify the upload folder path
                    filename = secure_filename(session['admin_id'] + os.path.splitext(photo.filename)[1])
                    upload_folder = os.path.join(app.root_path, 'static', 'assets', 'img', 'admins')

                    # Save the uploaded image with the admin_id as the filename
                    photo.save(os.path.join(upload_folder, filename))

                    # Update the image filename in the database
                    query = "UPDATE registered_admins SET Profile_URL = %s WHERE Email = %s"
                    cur.execute(query, (filename, email))
                    mysql.connection.commit()
                    cur.close()

            # Redirect to the admin dashboard or any other appropriate page
            return redirect(url_for('admin_dashboard'))

        # Retrieve the admin's data from the database for display
        email = session['email']  # Retrieve the logged-in admin's email from the session
        cur = mysql.connection.cursor()
        query = "SELECT * FROM registered_admins WHERE Email = %s"
        cur.execute(query, (email,))
        row = cur.fetchone()

        if row:
            column_names = [desc[0] for desc in cur.description]  # Get the column names
            admin_data = dict(zip(column_names, row))

            # Filter out None values from the admin_data dictionary
            admin_data = {k: v for k, v in admin_data.items() if v is not None}

            session['admin_id'] = admin_data['Admin_ID']
            cur.close()

            # Render the admin profile settings template with the admin's data
            return render_template('admin-profile-settings.html', admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    else:
        session['error'] = "Yetkili bir yönetici değilsiniz. Bu sayfaya yalnızca yetkili yöneticiler erişebilir."
        return redirect(url_for('unauthorized'))



@app.route('/admin-change-password', methods=['GET', 'POST'])
def admin_change_password():
    if session.get('user_type') != 'admin':
        session['error'] = "Yetkili bir yönetici değilsiniz. Bu sayfaya yalnızca yetkili yöneticiler erişebilir."
        return redirect(url_for('unauthorized'))

    # Get user information from the session
    name = session.get('name_pms')
    profile = session.get('profile_pms')
    user = session.get('user_pms')
    url = session.get('url_pms')
    dashboard = session.get('dashboard_pms')

    # Retrieve the admin's data from the database for display
    email = session['email']  # Retrieve the logged-in admin's email from the session
    cur = mysql.connection.cursor()
    query = "SELECT * FROM registered_admins WHERE Email = %s"
    cur.execute(query, (email,))
    row = cur.fetchone()

    column_names = [desc[0] for desc in cur.description]  # Get the column names
    admin_data = dict(zip(column_names, row))
    session['old_password'] = admin_data['Password']
    cur.close()

    if request.method == 'POST':
        # Access the form data
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Perform validation
        # Example: Check if the old password matches the current password for the admin
        if old_password != session['old_password']:
            error_message = "Eski şifre yanlış."
            return render_template('admin-change-password.html', error=error_message, admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Example: Check if the new password meets the desired criteria
        if new_password != confirm_password:
            error_message = "Yeni şifre ve onay şifresi eşleşmiyor."
            return render_template('admin-change-password.html', error=error_message, admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

        # Update the password in the database for the admin
        admin_id = admin_data['Admin_ID']
        update_password_in_p_database(admin_id, new_password)

        success_message = "Parola başarıyla değiştirildi."
        return render_template('admin-change-password.html', error=success_message, admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

    return render_template('admin-change-password.html', admin_data=admin_data, name=name, profile=profile, user=user, url=url, dashboard=dashboard)

def update_password_in_p_database(admin_id, new_password):
    cur = mysql.connection.cursor()
    query = "UPDATE registered_admins SET Password = %s WHERE Admin_ID = %s"
    cur.execute(query, (new_password, admin_id))
    mysql.connection.commit()
    cur.close()

# -----------------------------------------------------------------------------------------------------------------------------
# LOGIN RECORDS:
# -----------------------------------------------------------------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session:
        # User is already logged in, redirect to a logged-in page
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        user_type = request.form['user_type']
        password = request.form['password']

        if user_type == 'patient':
            session['user_type'] = 'patient'
            # Check if the user exists in the registered_patients table
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM registered_patients WHERE Email = %s", (email,))
            row = cur.fetchone()

            if row is None:
                # User not found, display an error message
                error_message = "Kullanıcı bulunamadı. Lütfen Kayıt Olun."
                cur.close()
                return render_template('login.html', error=error_message)

            # Create a dictionary using column names as keys
            columns = [desc[0] for desc in cur.description]
            row_dict = dict(zip(columns, row))
            row_dict = {k: v for k, v in row_dict.items() if v is not None}

            # Check if the password is correct
            if password != row_dict.get('Password'):
                # Incorrect password, display an error message
                error_message = "Geçersiz kimlik bilgileri. Lütfen tekrar deneyin."
                cur.close()
                return render_template('login.html', error=error_message)

            # Password is correct, continue with the authentication process for the patient

            # Store user information in the session
            session['loggedin'] = True
            session['user_type'] = 'patient'
            session['email'] = email

            # Check if the 'Profile_URL' key exists in the row_dict dictionary
            if 'Profile_URL' in row_dict:
                session['profile_pms'] = 'patients/' + row_dict['Profile_URL']
            else:
                session['profile_pms'] = 'patients/default.png'
            if 'Date_of_Birth' in row_dict:
                session['dob_pms'] = row_dict['Date_of_Birth']
            if 'City' in row_dict:
                session['city_pms'] = row_dict['City']
            if 'State' in row_dict:
                session['state_pms'] = row_dict['State']

            session['patient_id'] = row_dict['Patient_ID']
            session['name_pms'] = row_dict['Name']
            session['patient_email'] = row_dict['Email']
            session['user_pms'] = 'Patient'
            session['url_pms'] = '/patient-profile-settings'
            session['dashboard_pms'] = '/patient-dashboard'

            cur.close()

            # Redirect to the patient dashboard
            return redirect(url_for('patient_dashboard'))

        elif user_type == 'doctor':
            session['user_type'] = 'doctor'
            # Check if the user exists in the registered_doctors table
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM registered_doctors WHERE Email = %s", (email,))
            row = cur.fetchone()

            if row is None:
                # User not found, display an error message
                error_message = "Kullanıcı bulunamadı. Lütfen Kayıt Olun."
                cur.close()
                return render_template('login.html', error=error_message)

            # Create a dictionary using column names as keys
            columns = [desc[0] for desc in cur.description]
            row_dict = dict(zip(columns, row))
            row_dict = {k: v for k, v in row_dict.items() if v is not None}

            # Check if the password is correct
            if password != row_dict.get('Password'):
                # Incorrect password, display an error message
                error_message = "Geçersiz kimlik bilgileri. Lütfen tekrar deneyin."
                cur.close()
                return render_template('login.html', error=error_message)

            # Password is correct, continue with the authentication process for the doctor

            # Store user information in the session
            session['loggedin'] = True
            session['user_type'] = 'doctor'
            session['email'] = email

            # Save some data for all pages
            # Check if the 'Profile_URL' key exists in the row_dict dictionary
            if 'Profile_URL' in row_dict:
                session['profile_pms'] = 'doctors/' + row_dict['Profile_URL']
            else:
                session['profile_pms'] = 'doctors/default.png'  # Provide a default value or handle the case when the key is missing
            if 'Qualification' in row_dict:
                session['qualification_pms'] = row_dict['Qualification']
            if 'Specialization' in row_dict:
                session['specialization_pms'] = row_dict['Specialization']

            session['name_pms'] = row_dict['Name']
            session['user_pms'] = 'Doctor'
            session['url_pms'] = '/doctor-profile-settings'
            session['dashboard_pms'] = '/doctor-dashboard'

            cur.close()

            return redirect(url_for('doctor_dashboard'))

        elif user_type == 'admin':
            session['user_type'] = 'admin'
            # Check if the user exists in the registered_admins table
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM registered_admins WHERE Email = %s", (email,))
            row = cur.fetchone()

            if row is None:
                # User not found, display an error message
                error_message = "Kullanıcı bulunamadı. Lütfen Kayıt Olun."
                cur.close()
                return render_template('login.html', error=error_message)

            # Create a dictionary using column names as keys
            columns = [desc[0] for desc in cur.description]
            row_dict = dict(zip(columns, row))
            row_dict = {k: v for k, v in row_dict.items() if v is not None}

            # Check if the password is correct
            if password != row_dict.get('Password'):
                # Incorrect password, display an error message
                error_message = "Geçersiz kimlik bilgileri. Lütfen tekrar deneyin."
                cur.close()
                return render_template('login.html', error=error_message)

            # Password is correct, continue with the authentication process for the admin

            # Store user information in the session
            session['loggedin'] = True
            session['user_type'] = 'admin'
            session['email'] = email

            # Check if the 'Profile_URL' key exists in the row_dict dictionary
            if 'Profile_URL' in row_dict:
                session['profile_pms'] = 'admins/' + row_dict['Profile_URL']
            else:
                session['profile_pms'] = 'admins/default.png'
            if 'Qualification' in row_dict:
                session['qualification_pms'] = row_dict['Qualification']
            if 'Job_Profile' in row_dict:
                session['job_profile_pms'] = row_dict['Job_Profile']

            session['name_pms'] = row_dict['Name']
            session['user_pms'] = 'Admin'
            session['url_pms'] = '/admin-profile-settings'
            session['dashboard_pms'] = '/admin-dashboard'
            session['Admin_ID'] = row_dict['Admin_ID']

            cur.close()

            # Redirect to the admin dashboard
            return redirect(url_for('admin_dashboard'))

    # Render the login template
    return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear the session data
    session.clear()

    # Redirect to the login page
    return redirect(url_for('home'))

# Generate OTP
def generate_otp():
    # Generate a 4-digit OTP
    otp = ''.join(random.choices(string.digits, k=4))
    return otp

def send_otp_email(email, otp):
    msg = Message("Parola Sıfırlama için OTP", recipients=[email])
    msg.body = f"Şifre sıfırlama için OTP'niz:: {otp}"
    mail.send(msg)

@app.route('/resend-otp', methods=['GET', 'POST'])
def resend_otp():
    # Generate a new OTP
    new_otp = generate_otp()

    # Update the session with the new OTP
    session['otp'] = new_otp

    # Send the OTP to the user's email
    send_otp_email(session['email'], new_otp)

    success_message = "OTP yeniden gönderildi"

    # Return a response indicating success
    return render_template('email-otp.html', error=success_message)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if 'loggedin' in session:
        # User is already logged in, redirect to a logged-in page
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form['email']
        user_type = request.form['user_type']

        cur = mysql.connection.cursor()

        if user_type == 'patient':
            session['user_type'] = 'patient'
            # Check if the user exists in the registered_patients table
            cur.execute("SELECT * FROM registered_patients WHERE Email = %s", (email,))
            row = cur.fetchone()

        elif user_type == 'doctor':
            session['user_type'] = 'doctor'
            # Check if the user exists in the registered_doctors table
            cur.execute("SELECT * FROM registered_doctors WHERE Email = %s", (email,))
            row = cur.fetchone()

        elif user_type == 'admin':
            session['user_type'] = 'admin'
            # Check if the user exists in the registered_admins table
            cur.execute("SELECT * FROM registered_admins WHERE Email = %s", (email,))
            row = cur.fetchone()

        if row is None:
            # User not found, display an error message
            error_message = "Hesap bulunamadı. Lütfen kayıt olun."
            cur.close()
            return render_template('forgot-password.html', error=error_message)

        # Generate OTP
        otp = generate_otp()

        # Store user information in the session
        session['email'] = email
        session['otp'] = otp

        cur.close()

        # Send OTP via email
        send_otp_email(email, otp)


        return redirect(url_for('email_otp_verification'))

    return render_template('forgot-password.html')


@app.route('/email-otp-verification', methods=['GET', 'POST'])
def email_otp_verification():
    if 'email' not in session:
        # Email not found in session, redirect to the forgot password page
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        entered_otp = request.form['digit-1'] + request.form['digit-2'] + request.form['digit-3'] + request.form['digit-4']

        if 'otp' not in session:
            # OTP not found in session, redirect to the forgot password page
            return redirect(url_for('forgot_password'))

        if entered_otp == session['otp']:
            # OTP is correct, allow the user to reset the password
            return redirect(url_for('reset_password'))

        # OTP is incorrect, display an error message
        error_message = "Geçersiz OTP. Lütfen tekrar deneyin."
        return render_template('email-otp.html', error=error_message)

    return render_template('email-otp.html', email=session['email'])


@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if 'email' not in session:
        # Email not found in session, redirect to the forgot password page
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            # Passwords do not match, display an error message
            error_message = "Parolalar uyuşmuyor. Lütfen tekrar deneyin."
            return render_template('reset-password.html', error=error_message)

        # Validate password
        password_pattern = r'^.{8,}$'
        if not re.match(password_pattern, password):
            error_message = "Geçersiz şifre. Şifre en az 8 karakter uzunluğunda olmalıdır."
            return render_template('reset-password.html', error=error_message)

        # Update the user's password in the database
        user_type = session.get('user_type')
        email = session.get('email')

        cur = mysql.connection.cursor()

        if user_type == 'patient':
            # Update the password for patient user type
            cur.execute("UPDATE registered_patients SET Password = %s WHERE Email = %s", (password, email))

        elif user_type == 'doctor':
            # Update the password for doctor user type
            cur.execute("UPDATE registered_doctors SET Password = %s WHERE Email = %s", (password, email))

        elif user_type == 'admin':
            # Update the password for admin user type
            cur.execute("UPDATE registered_admins SET Password = %s WHERE Email = %s", (password, email))

        mysql.connection.commit()
        cur.close()

        # Password reset successful, redirect to login page
        return render_template('password-changed-successful.html')

    # Render the reset-password template
    return render_template('reset-password.html')


@app.route('/contact-form', methods=['POST'])
def contact_form():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        services = request.form.get('services')
        message = request.form.get('message')

        # Create the email message
        subject = 'Yeni İletişim Formu Gönderimi'
        body = f"Name: {name}\nEmail: {email}\nPhone: {phone}\nServices: {services}\nMessage: {message}"
        recipients = ['idmsaglikmerkezi@gmail.com']

        # Send the email
        msg = Message(subject=subject, body=body, recipients=recipients)
        mail.send(msg)

        return 'Mesaj başarıyla gönderildi'
    return redirect(url_for('contact'))

# ------------------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=False)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

# Chromedriver yürütülebilir dosyasının tam yolu
CHROMEDRIVER_PATH = 'C:/path/to/chromedriver.exe'
FLASK_APP_URL = 'http://localhost:5000/login'

# Test için geçerli e-posta ve şifreyi buraya yazın
TEST_EMAIL = 'alper@gmail.com'
TEST_PASSWORD = 'samsun1453'
USER_TYPE = 'patient'

def test_login():
    # Chromedriver'ın yolunu belirterek tarayıcıyı başlatma
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service)

    try:
        # Flask uygulama giriş sayfasını açın
        driver.get(FLASK_APP_URL)

        # E-posta giriş alanını bulun ve test e-postasını girin
        email_field = driver.find_element(By.NAME, 'email')
        email_field.send_keys(TEST_EMAIL)

        # Şifre giriş alanını bulun ve test şifresini girin
        password_field = driver.find_element(By.NAME, 'password')
        password_field.send_keys(TEST_PASSWORD)

        # Kullanıcı türünü seçin
        user_type_field = driver.find_element(By.NAME, 'user_type')
        for option in user_type_field.find_elements(By.TAG_NAME, 'option'):
            if option.text == USER_TYPE.capitalize():
                option.click()
                break

        # Gönder düğmesini bulun ve tıklayın
        submit_button = driver.find_element(By.XPATH, '//button[@type="submit"]')
        submit_button.click()

        # Giriş işleminin tamamlanması için biraz bekleyin
        time.sleep(3)

        # Girişin başarılı olup olmadığını kontrol edin
        dashboard_element = driver.find_element(By.XPATH, '//h1[text()="Dashboard"]')
        assert dashboard_element.is_displayed(), "Giriş başarısız veya gösterge tablosu görüntülenmedi"

        print("Giriş testi başarılı.")

    except Exception as e:
        print(f"Giriş testi başarısız: {e}")

    finally:
        # Tarayıcıyı kapatın
        driver.quit()

if __name__ == '__main__':
    test_login()

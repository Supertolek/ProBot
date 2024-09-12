from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyzbar.pyzbar import decode
from PIL import Image
from uuid import uuid4
import base64
import os
import time
import pronotepy
import json


def get_qrcode(username: str, password: str, verif_code: str = "0000"):

    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')

    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)

    driver.get("https://psn.monlycee.net/")

    username_field = driver.find_element(By.NAME, "username")
    password_field = driver.find_element(By.NAME, "password")

    username_field.send_keys(username)
    password_field.send_keys(password)

    password_field.send_keys(Keys.RETURN)

    time.sleep(1)

    try:
        driver.find_element(By.NAME, "username")
        driver.quit()
        return None
    except Exception as e:
        e = e
    driver.get("https://0781861z.index-education.net/pronote/")

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "ibe_iconebtn"))).click()

    WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located(
            (By.CLASS_NAME, "m-left"))).send_keys(verif_code)

    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "//button[contains(text(), 'Générer le QR Code')]"))).click()

    image_base64 = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//img[@alt=\"QRCode à flasher avec l'application mobile\"]"
             ))).get_attribute("src").split(",")[1]

    image_data = base64.b64decode(image_base64)

    # Save the image as a PNG file
    image_name = f"{username}_qrcode.png"
    with open(image_name, "wb") as f:
        f.write(image_data)
    time.sleep(0.1)

    driver.quit()

    return image_name


def connection_to_pronotepy(username: str,
                            password: str) -> pronotepy.Client | None:
    image = get_qrcode(username, password)
    if image is None:
        return None
    img = Image.open(image)

    decoded_objects = decode(img)

    #print(decoded_objects)
    try:
        qrcode_data = json.loads(decoded_objects[0].data.decode("utf-8"))
    except Exception as e:
        print(f"Can not decode QR code: {str(e)}")
        exit()

    pin = "0000"
    uuid = uuid4()
    print(uuid)

    try:
        client = pronotepy.Client.qrcode_login(qrcode_data, pin, str(uuid))
    except Exception as e:
        print(f"Can not login with QR code: {str(e)}")
        exit()

    os.remove(image)

    return client

def connection_with_qr_code(file_name: str, verif_code: str = "0000") -> pronotepy.Client | None:
    image = Image.open(file_name)
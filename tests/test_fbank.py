import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

BASE_URL = "http://localhost:8000"
CARD = "1111111111111111"


@pytest.fixture
def driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    drv = webdriver.Chrome(options=options)
    yield drv
    drv.quit()


def _wait_for_buttons(driver, count=3, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        n = driver.execute_script("return document.querySelectorAll('button').length")
        if n >= count:
            return
        time.sleep(0.5)
    title = driver.title
    n = driver.execute_script("return document.querySelectorAll('button').length")
    src = driver.page_source[:300]
    raise AssertionError(
        f"Страница не отрисовалась за {timeout}с. "
        f"title='{title}', buttons={n}, source={src!r}"
    )


def _open_transfer_form(driver, balance=30000, reserved=20001):
    driver.get(f"{BASE_URL}/?balance={balance}&reserved={reserved}")
    _wait_for_buttons(driver)
    driver.find_elements(By.TAG_NAME, "button")[0].click()
    end = time.time() + 10
    while time.time() < end:
        if driver.find_elements(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']"):
            break
        time.sleep(0.3)
    driver.find_element(By.CSS_SELECTOR, "input[placeholder='0000 0000 0000 0000']").send_keys(CARD)
    end = time.time() + 10
    while time.time() < end:
        if driver.find_elements(By.CSS_SELECTOR, "input[placeholder='1000']"):
            break
        time.sleep(0.3)


def _set_amount(driver, amount):
    inp = driver.find_element(By.CSS_SELECTOR, "input[placeholder='1000']")
    inp.click()
    inp.send_keys(Keys.CONTROL + "a")
    inp.send_keys(str(amount))
    time.sleep(0.5)


def test_negative_amount_rejected(driver):
    """BUG-001: отрицательная сумма должна отклоняться, кнопка Перевести не показывается"""
    _open_transfer_form(driver)
    _set_amount(driver, -100)
    buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Перевести')]")
    assert len(buttons) == 0, (
        "Дефект #1: кнопка 'Перевести' отображается при отрицательной сумме −100 ₽"
    )


def test_commission_boundary_blocks_transfer(driver):
    """BUG-002: при сумме 9091 комиссия 909, итого 10000 > 9999 — перевод должен быть заблокирован"""
    _open_transfer_form(driver, balance=30000, reserved=20001)
    _set_amount(driver, 9091)
    errors = driver.find_elements(
        By.XPATH, "//*[contains(text(), 'Недостаточно средств')]"
    )
    assert len(errors) > 0, (
        "Дефект #2: при сумме 9091 (комиссия 909, итого 10000 > 9999 доступных) "
        "отображается кнопка 'Перевести' вместо ошибки 'Недостаточно средств на счете'"
    )

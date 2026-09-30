import time
import sys
import os

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:8000"
SCRATCH_DIR = r"C:\Users\naba\.gemini\antigravity-ide\scratch\focusflow"

def test_onboarding():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    try:
        driver.get(BASE_URL)
        time.sleep(1)
        
        # Switch to Signup tab
        signup_tab = driver.find_element(By.ID, "tab-btn-signup")
        signup_tab.click()
        time.sleep(0.5)
        
        # Fill signup
        ts = int(time.time())
        driver.find_element(By.ID, "signup-name").send_keys("Maya Patel")
        driver.find_element(By.ID, "signup-email").send_keys(f"maya_{ts}@university.edu")
        driver.find_element(By.ID, "signup-password").send_keys("password123")
        driver.find_element(By.ID, "signup-submit-btn").click()
        
        # Wait for Onboarding Modal to appear
        wait.until(EC.visibility_of_element_located((By.ID, "modal-onboarding")))
        time.sleep(1)
        
        onboard_step1_path = os.path.join(SCRATCH_DIR, "e2e_onboarding_step1.png")
        driver.save_screenshot(onboard_step1_path)
        print(f"✓ Saved screenshot: e2e_onboarding_step1.png")
        
        # Fill Onboarding fields
        course_input = driver.find_element(By.ID, "onboard-course")
        course_input.clear()
        course_input.send_keys("BSc Information Technology")
        
        sem_input = driver.find_element(By.ID, "onboard-semester")
        sem_input.clear()
        sem_input.send_keys("Semester 5")

        college_input = driver.find_element(By.ID, "onboard-institution")
        college_input.clear()
        college_input.send_keys("Metropolitan Tech University")

        # Add Subjects via chips
        sub_input = driver.find_element(By.ID, "onboard-subject-input")
        add_sub_btn = driver.find_element(By.ID, "btn-onboard-add-sub")

        for subject_name in ["Computer Networks", "Distributed Systems", "Cloud Computing"]:
            sub_input.clear()
            sub_input.send_keys(subject_name)
            add_sub_btn.click()
            time.sleep(0.3)

        # Add Exam
        exam_input = driver.find_element(By.ID, "onboard-exam-title")
        exam_input.send_keys("Semester Finals")
        
        exam_date = driver.find_element(By.ID, "onboard-exam-date")
        exam_date.send_keys("2026-11-15")
        
        time.sleep(1)
        onboard_filled_path = os.path.join(SCRATCH_DIR, "e2e_onboarding_filled.png")
        driver.save_screenshot(onboard_filled_path)
        print(f"✓ Saved screenshot: e2e_onboarding_filled.png")

        # Submit Onboarding via JavaScript click to avoid toast overlay interception
        submit_btn = driver.find_element(By.ID, "btn-onboard-submit")
        driver.execute_script("arguments[0].click();", submit_btn)
        time.sleep(2)
        
        # Confirm user is in dashboard with Maya Patel
        wait.until(EC.visibility_of_element_located((By.ID, "dash-welcome-name")))
        greeting = driver.find_element(By.ID, "dash-welcome-name").text
        print(f"✓ Onboarding complete! Dashboard greeting: '{greeting}'")
        
        new_dash_path = os.path.join(SCRATCH_DIR, "e2e_new_student_dashboard.png")
        driver.save_screenshot(new_dash_path)
        print(f"✓ Saved screenshot: e2e_new_student_dashboard.png")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    test_onboarding()

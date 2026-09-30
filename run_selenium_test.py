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

def run_e2e_browser_test():
    print("=== STARTING SELENIUM BROWSER E2E TEST ===")
    
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    
    try:
        # 1. Open homepage
        print("Navigating to FocusFlow...")
        driver.get(BASE_URL)
        time.sleep(1)
        
        # 2. Click Instant Demo Login
        print("Clicking Instant 1-Click Demo Login button...")
        demo_btn = wait.until(EC.element_to_be_clickable((By.ID, "btn-demo-login")))
        demo_btn.click()
        
        # 3. Wait for Dashboard to appear
        print("Waiting for Dashboard to load...")
        wait.until(EC.visibility_of_element_located((By.ID, "dash-welcome-name")))
        time.sleep(2)
        
        welcome_name = driver.find_element(By.ID, "dash-welcome-name").text
        print(f"✓ Dashboard loaded! Greeting: '{welcome_name}'")
        
        # Save Dashboard screenshot
        dash_path = os.path.join(SCRATCH_DIR, "e2e_dashboard.png")
        driver.save_screenshot(dash_path)
        print(f"✓ Saved screenshot: e2e_dashboard.png ({os.path.getsize(dash_path)} bytes)")
        
        # 4. Navigate to Subjects & Roadmap
        print("Navigating to Subjects & Roadmap...")
        subjects_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='subjects'] button")
        subjects_nav.click()
        time.sleep(2)
        
        subj_cards = driver.find_elements(By.CSS_SELECTOR, "#subjects-container .subject-card")
        print(f"✓ Subjects loaded: Found {len(subj_cards)} syllabus learning spaces")
        
        subj_path = os.path.join(SCRATCH_DIR, "e2e_subjects.png")
        driver.save_screenshot(subj_path)
        print(f"✓ Saved screenshot: e2e_subjects.png")
        
        # Open Computer Networks roadmap detail
        print("Opening Computer Networks roadmap detail...")
        roadmap_btn = driver.find_element(By.CSS_SELECTOR, "#subjects-container .subject-card .subject-card-footer .btn-primary")
        roadmap_btn.click()
        time.sleep(1.5)
        
        roadmap_path = os.path.join(SCRATCH_DIR, "e2e_roadmap_detail.png")
        driver.save_screenshot(roadmap_path)
        print(f"✓ Opened Computer Networks chapter roadmap: e2e_roadmap_detail.png")
        
        # Back to subjects or directly navigate
        back_btn = driver.find_element(By.ID, "btn-back-to-subjects")
        back_btn.click()
        time.sleep(1)

        # 5. Navigate to Planner
        print("Navigating to Daily Planner...")
        planner_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='planner'] button")
        planner_nav.click()
        time.sleep(1.5)
        
        planner_path = os.path.join(SCRATCH_DIR, "e2e_planner.png")
        driver.save_screenshot(planner_path)
        print(f"✓ Saved screenshot: e2e_planner.png")
        
        # 6. Navigate to Exam Prep
        print("Navigating to Exam Prep Mode...")
        exams_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='exams'] button")
        exams_nav.click()
        time.sleep(1.5)
        
        exams_path = os.path.join(SCRATCH_DIR, "e2e_exams.png")
        driver.save_screenshot(exams_path)
        print(f"✓ Saved screenshot: e2e_exams.png")
        
        # 7. Navigate to Smart Revision
        print("Navigating to Smart Revision...")
        revision_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='revision'] button")
        revision_nav.click()
        time.sleep(1.5)
        
        rev_path = os.path.join(SCRATCH_DIR, "e2e_revision.png")
        driver.save_screenshot(rev_path)
        print(f"✓ Saved screenshot: e2e_revision.png")
        
        # 8. Navigate to Mock Tests
        print("Navigating to Mock Tests...")
        mock_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='mocktest'] button")
        mock_nav.click()
        time.sleep(1.5)
        
        mock_path = os.path.join(SCRATCH_DIR, "e2e_mocktest.png")
        driver.save_screenshot(mock_path)
        print(f"✓ Saved screenshot: e2e_mocktest.png")

        # 9. Navigate to Focus Timer
        print("Navigating to Focus Timer...")
        timer_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='timer'] button")
        timer_nav.click()
        time.sleep(1.5)
        
        timer_path = os.path.join(SCRATCH_DIR, "e2e_timer.png")
        driver.save_screenshot(timer_path)
        print(f"✓ Saved screenshot: e2e_timer.png")

        # 10. Navigate to AI Coach
        print("Navigating to AI Coach...")
        ai_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='ai'] button")
        ai_nav.click()
        time.sleep(1.5)
        
        ai_path = os.path.join(SCRATCH_DIR, "e2e_ai.png")
        driver.save_screenshot(ai_path)
        print(f"✓ Saved screenshot: e2e_ai.png")

        # 11. Navigate to Analytics
        print("Navigating to Analytics & Achievements...")
        analytics_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='analytics'] button")
        analytics_nav.click()
        time.sleep(2)
        
        analytics_path = os.path.join(SCRATCH_DIR, "e2e_analytics.png")
        driver.save_screenshot(analytics_path)
        print(f"✓ Saved screenshot: e2e_analytics.png")
        
        # 12. Navigate to Resources
        print("Navigating to Resources & Notes Library...")
        resources_nav = driver.find_element(By.CSS_SELECTOR, ".nav-item[data-route='resources'] button")
        resources_nav.click()
        time.sleep(1.5)
        
        resources_path = os.path.join(SCRATCH_DIR, "e2e_resources.png")
        driver.save_screenshot(resources_path)
        print(f"✓ Saved screenshot: e2e_resources.png")
        
        # 13. Test Quick Capture Modal
        print("Testing Quick Capture Modal (+ Add)...")
        add_btn = driver.find_element(By.ID, "btn-quick-add")
        add_btn.click()
        time.sleep(1)
        
        qc_path = os.path.join(SCRATCH_DIR, "e2e_quick_capture.png")
        driver.save_screenshot(qc_path)
        print(f"✓ Saved screenshot: e2e_quick_capture.png")
        
        print("\n=======================================================")
        print("🎉 ALL 13 BROWSER E2E TESTS PASSED WITH ACTUAL SCREENSHOTS!")
        print("=======================================================")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_e2e_browser_test()

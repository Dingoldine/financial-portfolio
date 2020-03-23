from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, \
ElementClickInterceptedException, MoveTargetOutOfBoundsException
from selenium.webdriver.common.by import By

def clickElement(browser, XPATH, maxWaitTime):
    wait = WebDriverWait(browser, maxWaitTime)
    error = ""
    retries = 0
    while retries < 5:
        print('Clicking Element:', XPATH)
        print('Attempt Number:', retries + 1)
        try:
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, XPATH))
            )
            coordinates = button.location_once_scrolled_into_view
            browser.execute_script(f'window.scrollTo({coordinates["x"]}, {coordinates["y"]});') #scroll to element
            ActionChains(browser).move_to_element(button).perform() #hover ove
            button.click()
            waitforload(browser, maxWaitTime)
            return
        except (TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
            UnexpectedAlertPresentException, MoveTargetOutOfBoundsException) as e:
            browser.refresh()
            waitforload(browser, maxWaitTime)
            retries += 1
            error = e
    
    raise(error)
    


def waitforload(browser, maxWaitTime):
    wait = WebDriverWait(browser, maxWaitTime)
    wait.until(lambda d: d.execute_script(
        'return (document.readyState == "complete" || document.readyState == "interactive")')
    )
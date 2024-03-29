from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, UnexpectedAlertPresentException, \
    ElementClickInterceptedException, MoveTargetOutOfBoundsException
from selenium.webdriver.common.by import By
import time


def clickElement(browser, XPATH, maxWaitTime, extraWaitTime=0):
    wait = WebDriverWait(browser, maxWaitTime)
    error = ""
    moveToTarget = True
    retries = 0
    while retries < 5:
        time.sleep(extraWaitTime)  # wait
        print('Clicking Element:', XPATH)
        print('Attempt Number:', retries + 1)
        try:
            button = wait.until(
                EC.element_to_be_clickable((By.XPATH, XPATH))
            )
            if (moveToTarget):
                coordinates = button.location_once_scrolled_into_view
                browser.execute_script(
                    f'window.scrollTo({coordinates["x"]}, {coordinates["y"]});')  # scroll to element
                ActionChains(browser).move_to_element(
                    button).perform()  # hover over
            button.click()
            waitforload(browser, maxWaitTime)
            return
        except ElementClickInterceptedException:
            browser.execute_script("arguments[0].click();", button)
            waitforload(browser, maxWaitTime)
            return
        except (TimeoutException, NoSuchElementException,
                UnexpectedAlertPresentException, MoveTargetOutOfBoundsException) as e:
            if (isinstance(e, MoveTargetOutOfBoundsException)):
                moveToTarget = False
            browser.refresh()
            # increase max wait time, maybe a slow element
            waitforload(browser, maxWaitTime)
            extraWaitTime += 1
            retries += 1
            error = e

    raise(error)


def waitforload(browser, maxWaitTime):
    wait = WebDriverWait(browser, maxWaitTime)
    wait.until(lambda d: d.execute_script(
        'return (document.readyState == "complete" || document.readyState == "interactive")')
    )

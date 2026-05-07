def assert_url_contains(driver, expected):

    return expected in driver.current_url


def assert_text(element, expected):

    return element.text.strip() == expected


def assert_element_visible(element):

    return element.is_displayed()

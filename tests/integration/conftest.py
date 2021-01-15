import os
import pytest
from selenium import webdriver
import datetime


# Configure options from cmd line
def pytest_addoption(parser):
    parser.addoption("--url", action="store", default="http://localhost:5000")
    parser.addoption("--username", action="store", default="")
    parser.addoption("--password", action="store", default="")

# prepare username and password
@pytest.fixture()
def auth(pytestconfig):
    username = pytestconfig.getoption("username")
    password = pytestconfig.getoption("password")
    if username == "":
        username = os.getenv("USERNAME")
        if not username:
            raise ValueError("Need to define USERNAME environment variable or pass with --username")
    if password == "":
        password = os.getenv("PASSWORD")
        if not password:
            raise ValueError("Need to define PASSWORD environment variable or pass with --password")

    return dict(username=username, password=password)


# return site base url
@pytest.fixture()
def site(pytestconfig):
    return pytestconfig.getoption("url")

# Configure shared setttings that are used across multiple tests
def pytest_configure():
    path_map = dict(
      #################  
      ## Enter map of paths here    
      ##################
    )
    paths = list(path_map.keys())
    pytest.shared = dict(azstorage_path="",
            path_map=path_map, 
            paths=paths, 
            test_path=paths[0]
        )


# Configure selenium webdriver, tests will be repeated across listed browsers
@pytest.fixture(params=["chrome", "firefox"],scope="class")
def setup(request):
    if request.param == "chrome":
        driver = webdriver.Chrome()
    if request.param == "firefox":
        driver = webdriver.Firefox()
    driver.implicitly_wait(10)
    request.cls.driver = driver
    yield
    driver.close()

# Create a small test file for uploading
@pytest.fixture()
def temp_file():
    # Create test file
    basename = "uploadtest"
    suffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    name = basename + "_" + suffix + ".txt"
    f = open(name, "w")
    f.write("Test Content for validating file upload...")
    f.close()
    path = os.path.join(os.getcwd(),name)
    file = dict(name=name, path=path)
    yield file
    os.remove(name)

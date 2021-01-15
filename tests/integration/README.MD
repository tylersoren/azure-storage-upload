# Selenium Integration Tests

The included python files use Selenium webdriver and the Pytest framework for automating tests of the web interface. The conftest.py initializes settings (upload paths, browsers to test, site url) and dependencies and then runs the tests in test_app.py. 

## Setup
To run the test, you must have Python3 installed along with pytest, pytest-dependency, pytest-html, and selenium modules. 
```
python -m pip install -r requirements.txt
```

 You will also need to install the selenium-gecko-driver(Firefox) and selenium-chrome-driver installed to interact with your browsers. These can be installed in Windows with chocolatey.
```
choco install selenium-gecko-driver selenium-chrome-driver
```

## Authentication
Since the application requires authentication, you must configure your user credentials that can login to the app. These can be passed via environment variables set to "USERNAME" and "PASSWORD" or via command line when you execute the test by using --username and --password switches. Using the command line switches takes precedence over the enviornment variables.

## Running tests
Make sure the application is running and accessible and enter the following to run the test files.

```
pytest --url <web_url>
```
"web_url" should be the address of the site to test and defaults to http://localhost:5000 for local debugging purposes. To get a summary report use the -r switch.

```
pytest -rA --url <web_url>
``` 
or
```
pytest -rsx --url <web_url>
```
This will run all tests and provide a summary report on the command line. Different flags will display different types or results, with the first showing all test status, and the second only showing skipped and failed tests ([report flag details](https://docs.pytest.org/en/stable/usage.html#detailed-summary-report)).  To create an HTML report instead run

```
pytest --html=report.html --url <web_url>
```
This will create an HTML report in the local directory.

## References
* [Selenium](https://www.selenium.dev/documentation/en/webdriver/)
* [Selenium Python Docs](https://selenium-python.readthedocs.io/)
* [pytest](https://docs.pytest.org/en/stable/contents.html)

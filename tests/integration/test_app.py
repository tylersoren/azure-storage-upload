# Import the 'modules' that are required for execution
import pytest
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from time import sleep 


@pytest.mark.usefixtures("setup")
class TestClass():

        def test_unauthenticated_redirect(self, site):
            self.driver.get(site)
            assert "Login" in self.driver.title

        @pytest.mark.dependency(name="login")
        def test_login(self, site, auth):
            self.driver.get(site + "/login")

            elem = self.driver.find_element_by_link_text("Sign In")
            elem.click()

            # Enter Username and hit next
            elem = self.driver.find_element_by_id("i0116")
            elem.clear()
            elem.send_keys(auth['username'])
            elem = self.driver.find_element_by_id("idSIButton9")
            elem.click()

            # Enter password
            elem = self.driver.find_element_by_id('passwordInput')
            elem.send_keys(auth['password'])
            elem.submit()

            # Enter Yes button to Stay Signed-in/reduce number of logins
            elem = self.driver.find_element_by_id("idSIButton9")
            elem.click()
            assert "Azure Storage Upload" in self.driver.title

        @pytest.mark.dependency(depends=["login"])
        def test_paths(self, site):
            for path in pytest.shared['paths']:
                self.driver.get(site + "/?folder=" + path)
                # Sometimes session cookie doesn't persist in local dev tests
                # check for redirect back to login screen and click through
                if "Login" in self.driver.title:
                    elem = self.driver.find_element_by_link_text("Sign In")
                    elem.click()
                    self.driver.get(site + "/?folder=" + path)

                elem = self.driver.find_element_by_id('current-folder')
                assert "Path: " + path in elem.text

        @pytest.mark.dependency(name="upload", depends=["login"])
        def test_upload(self, temp_file, site):

            self.driver.get(site + "/?folder=" + pytest.shared['test_path'])
            path = pytest.shared['path_map'][pytest.shared['test_path'] ]
            azstorage_path= path +  temp_file['name']

            self.upload_file(temp_file['path'], azstorage_path) 

        @pytest.mark.dependency(depends=["upload"])
        def test_delete(self, site):
            url = site + "/?folder=" + pytest.shared['test_path']
            self.delete_file(url, pytest.shared['azstorage_path'])

        @pytest.mark.dependency(name="upload_subfolder", depends=["login"])
        def test_upload_subfolder(self, temp_file, site):
            self.driver.get(site + "/?folder=" + pytest.shared['test_path'])

            subfolder = "subfolder_level1/subfolder_level2"
            path = pytest.shared['path_map'][pytest.shared['test_path'] ]
            azstorage_path = path +  subfolder + "/" + temp_file['name']

            elem = self.driver.find_element_by_id("optional-subfolder")
            elem.send_keys(subfolder)   

            self.upload_file(temp_file['path'], azstorage_path) 

        @pytest.mark.dependency(depends=["upload_subfolder"])
        def test_delete_subfolder(self, site):
            url = site + "/?folder=" + pytest.shared['test_path']
            self.delete_file(url, pytest.shared['azstorage_path'])

        @pytest.mark.dependency(depends=["login"])
        def test_logout(self, site):
            self.driver.get(site)

            # Mouse over user dropdown to make logout accessible
            user_dropdown = self.driver.find_element_by_id("current-user")
            actions = ActionChains(self.driver)
            actions.move_to_element(user_dropdown)
            actions.perform()

            elem = self.driver.find_element_by_id("logout")
            elem.click()
            assert "Sign out" in self.driver.title

        # Helper methods
        def upload_file(self, file_path, azstorage_path):
            print("Uploading file to " + azstorage_path)

            elem = self.driver.find_element_by_xpath("//input[@type='file']")
            elem.send_keys(file_path)

            pytest.shared['azstorage_path'] = azstorage_path

            # Add sleep for upload to complete
            sleep(1)

            # Click the page refresh button to reload the uploaded file list
            self.driver.find_element_by_id("refresh").click()

            # validate that filename can be found in the page
            try:
                self.driver.find_element_by_xpath("//img[@alt='delete " + azstorage_path + "']")
                assert True
            except NoSuchElementException:
                print("Failed to find uploaded file: " + azstorage_path)
                assert False

        def delete_file(self, url, azstorage_path):
            self.driver.get(url)

            elem = self.driver.find_element_by_xpath("//img[@alt='delete " + pytest.shared['azstorage_path']  + "']")
            elem.click()

            elem = self.driver.find_element_by_id("response-message")
            assert "File deleted successfully" == elem.text

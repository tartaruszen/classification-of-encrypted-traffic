import sys
sys.path.insert(0, "C:\\Users\\admin\\Documents\\classification-of-encrypted-traffic")
import datetime
from threading import Thread
from selenium import webdriver
from slackclient import SlackClient
import traceback
import os
from selenium.webdriver.support.ui import WebDriverWait


# import trafficgen.Streaming.win_capture as cap
# import trafficgen.Streaming.streaming_types as stream

import win_capture as cap
import streaming_types as stream
# from constants import SLACK_TOKEN

def notifySlack(message):
    sc = SlackClient(SLACK_TOKEN)
    try:
        sc.api_call("chat.postMessage", channel="#server", text=message)
    except:
        print("Could not send stacktrace", message)
        # sc.api_call("chat.postMessage", channel="#server", text="Could not send stacktrace")


def generate_streaming(duration, dir, total_iterations, options=None):
    iterations = 0
    stream_types = {
                    'hbo': (stream.HboNordic, 1),
                    'netflix': (stream.Netflix, 1),
                    # 'twitch': (stream.Twitch, 5),
                    # 'youtube': (stream.Youtube, 5),
                    # 'drtv': (stream.DrTv, 5),
                    }

    while iterations < total_iterations:
        print("Iteration:", iterations)
        if iterations % 25 == 0:
            notifySlack("Windows machine starting iteration: " + str(iterations))
        file =''
        try:
            for stream_type in stream_types.keys():
                browsers, capture_thread, file, streaming_threads, = [], [], [], [] 
                type = stream_types[stream_type][0]
                num_threads = stream_types[stream_type][1]
                
                browsers, capture_thread, file, streaming_threads = generate_threaded_streaming(type, stream_type, dir, duration, options, num_threads=num_threads)
                try:
                    capture_thread.start()
                    for thread in streaming_threads:
                        # Start streaming threads
                        thread.start()
                    print("streaming started", stream_type)
                    capture_thread.join() # Stream until the capture thread joins
                    print("capture done - thread has joined")
                    # for browser in browsers:
                    # #    clear_cache(browser)
                    #     browser.close()

                except Exception as e:
                    notifySlack("Something went wrong %s" % traceback.format_exc())
                    # Wait for capture thread
                    capture_thread.join()
                    # Do a cleanup since somthing went wrong
                    cap.cleanup(file)
                    # for browser in browsers:
                    #     browser.close()
                try:
                    for browser in browsers:
                        browser.quit()
                except Exception as e:
                    notifySlack("Something went wrong %s" % traceback.format_exc())
                        # os.system("killall chrome")
                        # os.system("killall chromedriver")
        except Exception as ex:
            notifySlack("Something went wrong when setting up the threads \n %s" % traceback.format_exc())

       
        
        iterations += 1


def generate_threaded_streaming(obj: stream.Streaming, stream_name, dir, duration, options=None, num_threads=5):
    #### STREAMING ####
    # Create filename
    now = datetime.datetime.now()
    file = dir + "/%s-%.2d%.2d_%.2d%.2d%.2d.pcap" % (stream_name, now.day, now.month, now.hour, now.minute, now.second)
    # Instantiate thread
    capture_thread = Thread(target=cap.captureTraffic, args=(1, duration, dir, file))
    # Create five threads for streaming
    streaming_threads = []
    browsers = []
    for i in range(num_threads):
        firefox_profile_dir = "C:\\Users\\admin\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\sopide1q.default"
        firefox_profile = webdriver.FirefoxProfile(firefox_profile_dir)
        firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'true')
        firefox_profile.set_preference("plugin.state.flash", 1) 
        options = webdriver.FirefoxOptions()
        # options.set_headless()
        browser = webdriver.Firefox(firefox_options=options, firefox_profile=firefox_profile)
        browser.implicitly_wait(10)
        browsers.append(browser)
        t = Thread(target=obj.stream_video, args=(obj, browser))
        streaming_threads.append(t)

    return browsers, capture_thread, file, streaming_threads


def get_clear_browsing_button(driver):
    """Find the "CLEAR BROWSING BUTTON" on the Chrome settings page. /deep/ to go past shadow roots"""
    return driver.find_element_by_css_selector('* /deep/ #clearBrowsingDataConfirm')


def clear_cache(driver, timeout=60):
    """Clear the cookies and cache for the ChromeDriver instance."""
    # navigate to the settings page
    driver.get('chrome://settings/clearBrowserData')

    # wait for the button to appear
    wait = WebDriverWait(driver, timeout)
    wait.until(get_clear_browsing_button)

    # click the button to clear the cache
    get_clear_browsing_button(driver).click()

    # wait for the button to be gone before returning
    wait.until_not(get_clear_browsing_button)


if __name__ == "__main__":
    #netflixuser = os.environ["netflixuser"]
    #netflixpassword = os.environ["netflixpassword"]
    #hbouser = os.environ["hbouser"]
    #hbopassword = os.environ["hbopassword"]
    # slack_token = os.environ['slack_token']
    SLACK_TOKEN = "xoxp-293516421953-294177990549-318123252422-7d590cf48153aeab21db3461ae339610" 
    # Specify duration in seconds
    duration = 60 * 1
    total_iterations = 1000
    save_dir = 'D:\\Data'
    # chrome_profile_dir = "/home/mclrn/.config/google-chrome/"
    firefox_profile_dir = "C:\\Users\\admin\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\sopide1q.default"
    options = webdriver.FirefoxProfile(firefox_profile_dir)
    #options.add_argument('user-data-dir=' + chrome_profile_dir)
    # options.add_argument("--enable-quic")
    # options.add_argument('headless')
    generate_streaming(duration, save_dir, total_iterations)
    print("something")
from tda import auth, client
from tda.client import Client
import json
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

token_path = config.TOKEN_PATH
api_key = config.API_KEY
redirect_uri = config.REDIRECT_URI

try:
    c = auth.client_from_token_file(token_path, api_key)

except FileNotFoundError:
    from selenium import webdriver
    with webdriver.Chrome() as driver:
        c = auth.client_from_login_flow(
            driver, api_key, redirect_uri, token_path)



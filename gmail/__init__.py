##################################################################################
# GMAIL CLASS ####################################################################
# Handles email auth and messages ################################################

# imports
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os.path
import os
from datetime import datetime, timedelta
import config
import pytz

TIMEZONE = config.TIMEZONE
TURN_ON_TIME = config.TURN_ON_TIME

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


class Gmail:

    def __init__(self, logger):

        self.logger = logger

        self.SCOPES = ["https://mail.google.com/"]

        self.creds = None

        self.service = None

        self.token_file = f"{THIS_FOLDER}/creds/token.json"

        self.creds_file = f"{THIS_FOLDER}/creds/credentials.json"

    def connect(self):
        """ METHOD SETS ATTRIBUTES AND CONNECTS TO GMAIL API

        Args:
            mongo ([object]): MONGODB OBJECT
            logger ([object]): LOGGER OBJECT
        """

        try:

            self.logger.info("CONNECTING TO GMAIL...", extra={'log': False})

            if os.path.exists(self.token_file):

                with open(self.token_file, 'r') as token:

                    self.creds = Credentials.from_authorized_user_file(
                        self.token_file, self.SCOPES)

            if not self.creds:

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_file, self.SCOPES)

                self.creds = flow.run_local_server(port=0)

            elif self.creds and self.creds.expired and self.creds.refresh_token:

                self.creds.refresh(Request())

            if self.creds != None:

                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:

                    token.write(self.creds.to_json())

                self.service = build('gmail', 'v1', credentials=self.creds)

                self.logger.info("CONNECTED TO GMAIL!\n", extra={'log': False})

                return True

            else:

                raise Exception("Creds Not Found!")

        except Exception as e:

            self.logger.error(
                f"FAILED TO CONNECT TO GMAIL! - {e}\n", extra={'log': False})

            return False

    def handleOption(self, symbol):

        symbol = symbol.replace(".", "", 1).strip()

        ending_index = 0

        int_found = False

        for index, char in enumerate(symbol):

            try:

                int(char)

                int_found = True

            except:

                if not int_found:

                    ending_index = index

        exp = symbol[ending_index + 1:]

        year = exp[:2]

        month = exp[2:4]

        day = exp[4:6]

        option_type = "CALL" if "C" in exp else "PUT"

        # .AA201211C5.5

        # AA_121120C5.5

        pre_symbol = f"{symbol[:ending_index + 1]}_{month}{day}{year}{exp[6:]}"

        return symbol[:ending_index + 1], pre_symbol, datetime.strptime(f"{year}-{month}-{day}", "%y-%m-%d"), option_type

    def extractSymbolsFromEmails(self, payloads):
        """ METHOD TAKES SUBJECT LINES OF THE EMAILS WITH THE SYMBOLS AND SCANNER NAMES AND EXTRACTS THE NEEDED THE INFO FROM THEM.
            NEEDED INFO: Symbol, Strategy, Side(Buy/Sell), Account ID

        Args:
            payloads ([list]): LIST OF EMAIL CONTENT

        Returns:
            [dict]: LIST OF EXTRACTED EMAIL CONTENT
        """

        trade_data = []

        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY
        # Alert: New Symbol: ABC was added to LinRegEMA_v2, BUY

        for payload in payloads:

            try:

                seperate = payload.split(":")

                if len(seperate) > 1:

                    contains = ["were added to", "was added to"]

                    for i in contains:

                        if i in seperate[2]:

                            sep = seperate[2].split(i)

                            symbols = sep[0].strip().split(",")

                            strategy, side = sep[1].strip().split(",")

                            for symbol in symbols:

                                if strategy != "" and side != "":

                                    obj = {
                                        "Symbol": symbol.strip(),
                                        "Side": side.replace(".", " ").upper().strip(),
                                        "Strategy": strategy.replace(".", " ").upper().strip(),
                                        "Asset_Type": "EQUITY"
                                    }

                                    # IF THIS IS AN OPTION
                                    if "." in symbol:

                                        symbol, pre_symbol, exp_date, option_type = self.handleOption(
                                            symbol)

                                        obj["Symbol"] = symbol

                                        obj["Pre_Symbol"] = pre_symbol

                                        obj["Exp_Date"] = exp_date

                                        obj["Option_Type"] = option_type

                                        obj["Asset_Type"] = "OPTION"

                                    # CHECK TO SEE IF ASSET TYPE AND SIDE ARE A LOGICAL MATCH
                                    if side.replace(".", " ").upper().strip() in ["SELL", "BUY"] and obj["Asset_Type"] == "EQUITY" or side.replace(".", " ").upper().strip() in ["SELL_TO_CLOSE", "SELL_TO_OPEN", "BUY_TO_CLOSE", "BUY_TO_OPEN"] and obj["Asset_Type"] == "OPTION":

                                        trade_data.append(obj)

                                    else:

                                        self.logger.warning(
                                            f"{__class__.__name__} - ILLOGICAL MATCH - SIDE: {side.upper().strip()} / ASSET TYPE: {obj['Asset_Type']}")

                                else:

                                    self.logger.warning(
                                        f"{__class__.__name__} - MISSING FIELDS FOR STRATEGY {strategy}")

                            break

                    self.logger.info(
                        f"New Email: {payload}", extra={'log': False})

            except IndexError:

                pass

            except ValueError:

                self.logger.warning(
                    f"{__class__.__name__} - Email Format Issue: {payload}")

            except Exception as e:

                self.logger.error(f"{__class__.__name__} - {e}")

        return trade_data

    def convertTimestamp(self, tmstmp):

        timestamp = int(tmstmp)

        timestamp = datetime.fromtimestamp(timestamp / 1000)

        timestamp = timestamp.replace(tzinfo=pytz.timezone(TIMEZONE))

        timestamp = timestamp.strftime('%H:%M:%S')

        return timestamp

    def getEmails(self):
        """ METHOD RETRIEVES EMAILS FROM INBOX, ADDS EMAIL TO TRASH FOLDER, AND ADD THEIR CONTENT TO payloads LIST TO BE EXTRACTED.

        Returns:
            [dict]: LIST RETURNED FROM extractSymbolsFromEmails METHOD
        """

        payloads = []

        try:

            # GETS LIST OF ALL EMAILS
            results = self.service.users().messages().list(userId='me').execute()

            if results['resultSizeEstimate'] != 0:

                # {'id': '173da9a232284f0f', 'threadId': '173da9a232284f0f'}
                for message in results["messages"]:

                    result = self.service.users().messages().get(
                        id=message["id"], userId="me", format="metadata").execute()

                    timestamp = self.convertTimestamp(result['internalDate'])

                    """ DELETE ALL EMAILS PRIOR TO BOT STARTING"""
                    if timestamp < TURN_ON_TIME:

                        self.service.users().messages().trash(
                            userId='me', id=message["id"]).execute()

                        continue

                    for payload in result['payload']["headers"]:

                        if payload["name"] == "Subject":

                            payloads.append(payload["value"].strip())

                    # MOVE EMAIL TO TRASH FOLDER
                    self.service.users().messages().trash(
                        userId='me', id=message["id"]).execute()

        except Exception as e:

            self.logger.error(f"{__class__.__name__} - {e}")

        finally:

            return self.extractSymbolsFromEmails(payloads)

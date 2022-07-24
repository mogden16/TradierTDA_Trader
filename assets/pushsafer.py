import requests

import config

PUSH_API_KEY = config.PUSH_API_KEY

class PushNotification:

    def __init__(self, device_id, logger):

        self.url = 'https://www.pushsafer.com/api'

        self.post_fields = {
            "t": "TOS Trading Bot",
            "m": None,
            "s": 0,
            "v": 1,
            "i": 1,
            "c": "#E94B3C",
            "d": device_id,
            "ut": "TOS Trading Bot",
            "k": PUSH_API_KEY,
        }

        self.logger = logger

    def send(self, notification):
        """ METHOD SENDS PUSH NOTIFICATION TO USER

        Args: 
            notification ([str]): MESSAGE TO BE SENT
        """

        try:

            # RESPONSE: {'status': 1, 'success': 'message transmitted', 'available': 983, 'message_ids': '18265430:34011'}

            self.post_fields["m"] = notification

            response = requests.post(self.url, self.post_fields)

            if response.json()["success"] == 'message transmitted':

                self.logger.info(f"Push Sent!\n")

            else:

                self.logger.warning(f"Push Failed!\n")

        except ValueError:

            pass

        except KeyError:

            pass

        except Exception as e:

            self.logger.error(e)

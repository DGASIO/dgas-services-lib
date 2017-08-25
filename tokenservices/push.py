import random
import json
import tornado.httpclient

class PushServerError(Exception):
    pass

class PushServerClient:

    def __init__(self, *, url, username=None, password=None, gcm=False, apn=False):

        if (gcm is False and apn is False) or (gcm is True and apn is True):
            raise TypeError("Requires either gcm=True or apn=True, but not both")

        self.base_url = url
        self.client = tornado.httpclient.AsyncHTTPClient()
        self.username = username
        self.password = password

        if gcm:
            self.path = "/api/v1/push/gcm"
        else:
            self.path = "/api/v1/push/apn"

        while url.endswith("/"):
            url = url[:-1]

        self.url = "{}{}".format(url, self.path)

    async def send(self, token_id, device_token, data):

        # TODO: intricisies of the PushServer format
        # https://raneeli.com:dgasio/dgasio/PushServer/blob/master/src/main/java/org/whispersystems/pushserver/entities/GcmMessage.java

        if len(data) > 1 or 'message' not in data:
            raise NotImplementedError("Only data key allowed is 'message'")

        payload = {
            "gcmId": device_token,
            "number": token_id,
            "message": data['message'],
            "devideId": 1,
            "receipt": False,
            "notification": False,
            "redphone": False,
            "call": False
        }

        resp = await self.client.fetch(self.url, method="PUT",
                                       headers={
                                           'Content-Type': 'application/json'
                                       },
                                       body=json.dumps(payload).encode('utf-8'),
                                       auth_username=self.username,
                                       auth_password=self.password,
                                       raise_error=False)

        if resp.code == 200:
            return True
        raise PushServerError(resp.body)

class GCMHttpPushClient:

    def __init__(self, server_key):

        self.server_key = server_key
        self.client = tornado.httpclient.AsyncHTTPClient()

    def send_impl(self, payload):
        return self.client.fetch("https://gcm-http.googleapis.com/gcm/send", method="POST",
                                 headers={
                                     'Authorization': "key={}".format(self.server_key),
                                     'Content-Type': 'application/json'
                                 },
                                 body=json.dumps(payload).encode('utf-8'),
                                 raise_error=False)

    async def send(self, token_id, device_token, data):

        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        payload = {
            "data": data,
            "to": device_token
        }

        resp = await self.send_impl(payload)

        if resp.code == 200:
            return True
        raise PushServerError(resp.body)

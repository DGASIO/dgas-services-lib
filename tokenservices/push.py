import random
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

    async def send(self, token, payload):

        # TODO: intricisies of the PushServer format
        # https://raneeli.com:dgasio/dgasio/PushServer/blob/master/src/main/java/org/whispersystems/pushserver/entities/GcmMessage.java

        if "data" not in payload:
            raise NotImplementedError("Only data packets are supported")

        data = payload['data']
        if len(data) > 1 or 'message' not in data:
            raise NotImplementedError("Only data key allowed is 'message'")

        payload = {
            "gcmId": token,
            "number": random.randint(0, 1000000000),
            "message": data['message'],
            "devideId": 1,
            "receipt": False,
            "notification": False,
            "redphone": False,
            "call": False
        }

        resp = await self.client.fetch(self.url, method="POST",
                                       auth_username=self.username,
                                       auth_password=self.password,
                                       raise_error=False)

        if resp.code == 200:
            return True
        raise PushServerError(resp.body)

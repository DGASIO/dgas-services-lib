import json
import tornado.httpclient

class PushServerError(Exception):
    pass

class PushServerClient:

    def __init__(self, *, url, username=None, password=None):

        self.client = tornado.httpclient.AsyncHTTPClient()
        self.username = username
        self.password = password

        while url.endswith("/"):
            url = url[:-1]
        self.base_url = url

    async def send(self, dgas_id, service, device_token, data):

        # TODO: intricisies of the PushServer format
        # https://raneeli.com:dgasio/dgasio/PushServer/blob/master/src/main/java/org/whispersystems/pushserver/entities/GcmMessage.java

        if len(data) > 1 or 'message' not in data:
            raise NotImplementedError("Only data key allowed is 'message'")

        payload = {
            "number": dgas_id,
            "deviceId": 1,
            "receipt": False,
            "notification": False,
            "redphone": False,
            "call": False
        }

        if service == 'gcm' or service == 'fcm':
            payload["gcmId"] = device_token
            payload["message"] = data['message']
            url = "{}/api/v1/push/gcm".format(self.base_url)
        elif service == 'apn':
            payload["apnId"] = device_token
            aps_payload = {
                "aps": {
                    "content-available": 1
                },
                "qofp": data['message']
            }
            payload["message"] = json.dumps(aps_payload)
            url = "{}/api/v1/push/apn".format(self.base_url)
        else:
            raise PushServerError("Unsupported network: '{}'".format(service))

        resp = await self.client.fetch(url, method="PUT",
                                       headers={
                                           'Content-Type': 'application/json'
                                       },
                                       body=json.dumps(payload).encode('utf-8'),
                                       auth_username=self.username,
                                       auth_password=self.password,
                                       raise_error=False)

        if resp.code < 400:
            return True
        raise PushServerError(resp.body)

class GCMHttpPushClient:

    def __init__(self, server_key):

        self.server_key = server_key
        self.client = tornado.httpclient.AsyncHTTPClient()

    def send_impl(self, payload, service):
        if service == 'fcm':
            url = 'https://fcm.googleapis.com/fcm/send'
        else:
            url = "https://gcm-http.googleapis.com/gcm/send"
        return self.client.fetch(url, method="POST",
                                 headers={
                                     'Authorization': "key={}".format(self.server_key),
                                     'Content-Type': 'application/json'
                                 },
                                 body=json.dumps(payload).encode('utf-8'),
                                 raise_error=False)

    async def send(self, dgas_id, service, device_token, data):

        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        if not (service == 'gcm' or service == 'fcm'):
            raise PushServerError("Unsupported network: '{}'".format(service))

        payload = {
            "data": data,
            "to": device_token
        }

        resp = await self.send_impl(payload, service)

        if resp.code == 200:
            return True
        raise PushServerError(resp.body)

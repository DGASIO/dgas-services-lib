class JsonRPCError(Exception):
    def __init__(self, request_id, code, message, data, is_notification=False):
        super().__init__(message)
        self.request_id = request_id
        self.code = code
        self.message = message
        self._data = data
        self.is_notification = is_notification

    def format(self, request=None):
        if request:
            if 'id' not in request:
                self.is_notification = True
            else:
                self.request_id = request['id']
        # if the request was a notification, return nothing
        if self.is_notification:
            return None
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": self.code,
                "message": self.message,
                "data": self._data,
            },
            "id": self.request_id
        }

    @property
    def data(self):
        if self._data:
            return self._data
        return {'message': self.message}

    def __repr__(self):
        return "Json RPC Error ({}): {}".format(self.code, self.message)

class JsonRPCInvalidParamsError(JsonRPCError):
    def __init__(self, *, request=None, data=None):
        super().__init__(request.get('id') if request else None,
                         -32602, "Invalid params", data,
                         'id' not in request if request else False)

class JsonRPCInternalError(JsonRPCError):
    def __init__(self, *, request=None, data=None):
        super().__init__(request.get('id') if request else None,
                         -32603, "Internal Error", data,
                         'id' not in request if request else False)

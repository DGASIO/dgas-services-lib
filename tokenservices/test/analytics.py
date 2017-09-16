import asyncio

class MockMixpanel:

    def __init__(self):

        self.events = asyncio.Queue()

    def track(self, distinct_id, event_name, properties=None, meta=None):
        self.events.put_nowait((distinct_id, event_name, properties, meta))

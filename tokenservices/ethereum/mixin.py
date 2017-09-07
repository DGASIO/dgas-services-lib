from .utils import prepare_ethereum_jsonrpc_client

class EthereumMixin:

    @property
    def eth(self):
        if not hasattr(self, '_eth_jsonrpc_client'):
            self._eth_jsonrpc_client = prepare_ethereum_jsonrpc_client(
                self.application.config['ethereum'])
        return self._eth_jsonrpc_client

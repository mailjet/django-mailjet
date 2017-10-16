class MessageFormatStrategy( object ):

    def __init__(self, strategy):
        self._strategy = strategy
		
    def build_send_payload(self, message):
        return self._strategy.build_send_payload(self._strategy,message)

		


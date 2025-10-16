class TestFailedError(Exception):
    """Custom exception for failed Nova Act tests"""

    def __init__(self, message="Test failed"):
        self.message = message
        super().__init__(self.message)

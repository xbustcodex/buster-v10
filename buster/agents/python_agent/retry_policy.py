class RetryPolicy:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempt = 0

    def can_retry(self) -> bool:
        """Returns True if there are remaining retries available."""
        return self.attempt < self.max_retries

    def increment(self):
        """Increments the current attempt counter."""
        self.attempt += 1

    def reset(self):
        """Resets the attempt counter."""
        self.attempt = 0
class Timer:
    def __init__(self, length: float):
        self.length = length
        self.time = 0.0
        self.timeout = False

    def step(self, deltatime: float):
        self.time += deltatime
        if self.time >= self.length:
            self.time -= self.length
            self.timeout = True
            return True
        else:
            self.timeout = False
            return False

    def is_timeout(self) -> bool:
        return self.timeout

    def reset(self):
        self.time = 0.0
        self.timeout = False

from typing import Optional
from TImer import Timer

class Animation:
    def __init__(self, frame_count: int, length: float):
        if frame_count <= 0:
            raise ValueError("Frame count must be positive")
        if length <= 0:
            raise ValueError("Animation length must be positive")
            
        self.frame_count: int = frame_count
        self.length: float = length
        self.time: float = 0.0
        self.timeout: bool = False
        self._current_frame: Optional[int] = None

    def step(self, deltatime: float) -> None:
        if deltatime < 0:
            raise ValueError("Delta time cannot be negative")
            
        self.time += deltatime
        if self.time >= self.length:
            self.time -= self.length
            self.timeout = True
        else:
            self.timeout = False
        self._current_frame = None  # Reset cached frame

    def currentFrame(self) -> int:
        if self._current_frame is not None:
            return self._current_frame
            
        progress = self.time / self.length
        frame_index = int(progress * self.frame_count)
        self._current_frame = frame_index % self.frame_count
        return self._current_frame

    def reset(self) -> None:
        self.time = 0.0
        self.timeout = False
        self._current_frame = None

    @property
    def progress(self) -> float:
        """Returns animation progress as a value between 0 and 1"""
        return self.time / self.length
    
    def isDone():
        return Timer.isTimeout()
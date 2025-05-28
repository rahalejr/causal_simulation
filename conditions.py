import numpy as np
from simulation import width, height

class Condition:

    def __init__(self, angles, preemption):
        self.num_balls = len(angles)
        
        self.y_positions = []
        spacing = (height + 100) / (self.num_balls + 1)
        for i in range(self.num_balls):
            self.y_positions.append(round(spacing*(i+1)))

        self.angles = [ang*np.pi/180 for ang in angles]
        self.preemption = preemption

conditions = [
    Condition([180], False),
    Condition([150, 200], False),
    Condition([150, 180, 200], False),
    Condition([210, 200, 180, 170], True)
]
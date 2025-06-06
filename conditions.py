import numpy as np


width = 1000
height = 800

class Condition:

    def __init__(self, angles, preemption=False, unambiguous=False):
        self.num_balls = len(angles)
        
        self.y_positions = []
        spacing = height / (self.num_balls + 1)
        for i in range(self.num_balls):
            self.y_positions.append(round(spacing*(i+1)))
        self.angles = angles
        self.radians = [ang*np.pi/180 for ang in angles]
        self.preemption = preemption
        self.cause_ball = None
        self.collisions = 0
        self.unambiguous = unambiguous
        self.sim_time = None
        self.diverge = 0
        self.noise_ball = None
        self.jitter = list(np.random.normal(loc=0, scale=10, size=self.num_balls))

    def info(self):
        return {
            'num_balls': self.num_balls,
            'angles': self.angles,
            'preemption': self.preemption,
            'cause_ball': self.cause_ball,
            'collisions': self.collisions,
            'unambiguous': self.unambiguous,
            'jitter': self.jitter
        }

conditions = [
    Condition([227, 137], False), # green cause
    Condition([217, 140, 148, 145], False), # yellow cause
    Condition([239, 133, 152, 145], False), # yellow preempts red
]



test_conditions = [
    Condition([180], False),
    Condition([150, 200], False),
    Condition([150, 180, 200], False),
    Condition([156, 185, 172, 200], False), # not preempted
    Condition([217, 140, 148, 145], False), # not preempted
    Condition([239, 133, 152, 145], False), # yellow preempts red
]
from conditions import *
import numpy as np
import pygame
import os
from moviepy.editor import ImageSequenceClip
from Box2D import (b2World, b2PolygonShape, b2CircleShape, b2_staticBody, b2_dynamicBody)
import shutil

frame_dir = "frames"
if os.path.exists(frame_dir):
    shutil.rmtree(frame_dir)
os.makedirs(frame_dir)

# global parameters
ball_radius = 28
border_width = 7
speed = 50
framerate = 30
time_step = 0.0001
gate_gap_height = 200

# Define width and height explicitly (needed for ypos calculations)
width = 1000
height = 800

# ball parameters
ball_params = [
    {'ball': 'effect', 'rgb': (180, 180, 180), 'ypos': round(height / 2), 'angle': 0},
    {'ball': 'red', 'rgb': (255, 0, 0)},
    {'ball': 'green', 'rgb': (0, 255, 0)},
    {'ball': 'blue', 'rgb': (255, 255, 0)},
    {'ball': 'yellow', 'rgb': (0, 0, 255)}
]

class Ball:
    def __init__(self, world, params):
        self.name = params['ball']
        xpos = round(width / 4) if self.name == 'effect' else width + 50
        self.body = world.CreateDynamicBody(
            position=(xpos, params['ypos']),
            shapes=b2CircleShape(radius=ball_radius)
        )
        self.body.fixtures[0].restitution = 1.0
        self.body.fixtures[0].friction = 0
        self.body.linearDamping = 0
        self.body.linearVelocity = (0, 0) if self.name == 'effect' else (
            speed * np.cos(params['angle']), speed * np.sin(params['angle'])
        )
        self.color = params['rgb']

    @property
    def position(self):
        return tuple(map(int, self.body.position))

# geometry constants for the walls
wall_len = (height - gate_gap_height) / 2
wall_half_len = wall_len / 2
border_half = border_width / 2

screen_center_x = width / 2
screen_half_width = width / 2

top_wall_center_y = wall_half_len
bottom_wall_center_y = height - wall_half_len
top_bottom_wall_center_y = border_half
bottom_wall_center_y_full = height - border_half

def create_world():
    world = b2World(gravity=(0, 0), doSleep=True)

    wall_shapes = [
        ((border_half, top_wall_center_y), b2PolygonShape(box=(border_half, wall_half_len))),
        ((border_half, bottom_wall_center_y), b2PolygonShape(box=(border_half, wall_half_len))),
        ((screen_center_x, top_bottom_wall_center_y), b2PolygonShape(box=(screen_half_width, border_half))),
        ((screen_center_x, bottom_wall_center_y_full), b2PolygonShape(box=(screen_half_width, border_half)))
    ]

    for position, shape in wall_shapes:
        body = world.CreateStaticBody(position=position)
        fixture = body.CreateFixture(shape=shape)
        fixture.restitution = 1.0
        fixture.friction = 0.0

    return world

def run(cond=0, record=False):
    condition = conditions[cond]
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Box2D Ball Collision Demo")

    frame_count = 0
    world = create_world()

    for i in range(condition.num_balls):
        ball_params[i + 1]['ypos'] = condition.y_positions[i]
        ball_params[i + 1]['angle'] = condition.angles[i]


    balls = [Ball(world, params) for params in ball_params[0:condition.num_balls + 1]]

    running = True
    sim_seconds = 0
    SIM_FRAME_TIME = 1.0 / framerate

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((255, 255, 255))

        wall_len = (height - gate_gap_height) / 2
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, border_width, wall_len))
        pygame.draw.rect(screen, (0, 0, 0), (0, height - wall_len, border_width, wall_len))
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, width, border_width))
        pygame.draw.rect(screen, (0, 0, 0), (0, height - border_width, width, border_width))
        pygame.draw.rect(screen, (0, 0, 0), (width - border_width, 0, border_width, height))

        pygame.draw.rect(screen, (255, 130, 150), (0, wall_len, border_width, gate_gap_height))

        for ball in balls:
            pygame.draw.circle(screen, ball.color, (int(ball.body.position[0]), int(ball.body.position[1])), ball_radius)

        if record:
            pygame.image.save(screen, f"frames/frame_{frame_count:05d}.png")
        frame_count += 1
        pygame.display.flip()

        sim_accum = 0.0
        while sim_accum < SIM_FRAME_TIME:
            world.Step(time_step, 20, 10)
            sim_accum += time_step
            sim_seconds += time_step

        if sim_seconds > 20:
            running = False

    pygame.quit()

    frame_files = sorted([os.path.join(frame_dir, fname)
                          for fname in os.listdir(frame_dir) if fname.endswith(".png")])

    if record:
        clip = ImageSequenceClip(frame_files, fps=framerate)
        clip.write_videofile("simulation.mp4", codec="libx264")

if __name__ == '__main__':
    run(3, record=False)

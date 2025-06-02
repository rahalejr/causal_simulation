from conditions import conditions, test_conditions
from random import shuffle
import numpy as np
import pygame
import os
from moviepy.editor import ImageSequenceClip
from Box2D import (b2World, b2PolygonShape, b2CircleShape, b2ContactListener, b2_staticBody, b2_dynamicBody)
import shutil

shutil.rmtree("frames") if os.path.exists("frames") else None
os.makedirs("frames")

# global parameters
width = 1000
height = 800
ball_radius = 28
border_width = 7
speed = 100
framerate = 30
time_step = 0.0001
gate_gap_height = 200

# radomly assign ball colors
red, green, yellow, blue = (255, 0, 0), (0, 255, 0), (255, 255, 0), (0, 0, 255)
colors = [red, green, yellow, blue]
shuffle(colors)

# ball parameters
ball_params = [
    {'ball': 'effect', 'rgb': (180, 180, 180), 'ypos': round(height / 2), 'angle': 0},
    {'ball': 1, 'rgb': colors[0]},
    {'ball': 2, 'rgb': colors[1]},
    {'ball': 3, 'rgb': colors[2]},
    {'ball': 4, 'rgb': colors[3]}
]


class Simulation:

    def __init__(self, balls, counterfactual = False, noise = 0):
        self.balls = balls
        self.num_balls = len(balls)
        self.noise = noise
        self.counterfactual = True if counterfactual else False
        self.hit = False
        self.collisions = []
        self.cause_ball = ''
        self.step = 0
    
    def get_ball(self, name):
        try:
            return self.balls[name-1]
        except:
            return None

    

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
        self.noisy = False
        self.collided_with = set()
        self.ball_collisions = []
        self.all_collisions = []
        self.body.userData = self

    @property
    def position(self):
        return tuple(map(int, self.body.position))
    
    def add_collision(self, obj, step):
        if obj == 'wall':
            self.all_collisions.append({'name': 'wall', 'object': obj, 'step': step})
        elif isinstance(obj, Ball):
            if obj.noisy:
                    self.noisy = True
            if obj.name != 'effect' and 'effect' not in self.collided_with:
                self.ball_collisions.append({'name': obj.name, 'object': obj, 'step': step})
            self.collided_with.add(obj.name)
            self.all_collisions.append({'name': obj.name, 'object': obj, 'step': step})
    
    def last_collision(self):
        return self.ball_collisions[-1]['object'] if len(self.ball_collisions) > 0 else None



class CollisionListener(b2ContactListener):
    def __init__(self, sim):
        super().__init__()
        self.events = []
        self.sim = sim

    def BeginContact(self, contact):
        A = contact.fixtureA.body.userData
        B = contact.fixtureB.body.userData

        names, noisy = [], False
        if isinstance(A, Ball):
            A.add_collision(B, self.sim.step)
            names.append(A.name)
            if A.noisy == True:
                noisy = True
        else:
            names.append('wall')
        
        if isinstance(B, Ball):
            B.add_collision(A, self.sim.step)
            names.append(B.name)
            if B.noisy == True:
                noisy = True
        else:
            names.append('wall')

        self.sim.collisions.append({'objects': names, 'step': self.sim.step, 'noisy': noisy})


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
        body.userData = 'wall'

    return world


def is_hit(sim, effect_ball, sim_seconds):
    effect_x, effect_y = effect_ball.body.position
    if effect_x - ball_radius <= border_width and wall_len <= effect_y <= wall_len + gate_gap_height:
        sim.hit = True
        return sim_seconds
    return False


def run(condition, record=False, counterfactual=None, headless=False):

    if not headless:
        pygame.init()
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Box2D Ball Collision Demo")

    remove = counterfactual['remove'] if counterfactual else None
    frame_count = 0
    world = create_world()

    for i in range(condition.num_balls):
        ball_params[i + 1]['ypos'] = condition.y_positions[i]
        ball_params[i + 1]['angle'] = condition.radians[i]

    filtered_params = [params for params in ball_params[0:condition.num_balls + 1] if not (remove == params['ball'])]

    balls = []
    for params in filtered_params:
        ball = Ball(world, params)
        if ball.name == 'effect':
            effect_ball = ball
        balls.append(ball)

    sim = Simulation(balls, remove)
    collision_listener = CollisionListener(sim)
    world.contactListener = collision_listener 

    running, hit = True, False
    sim_seconds = 0
    SIM_FRAME_TIME = 1.0 / framerate

    if not headless:
        clock = pygame.time.Clock()

    while running:
        if not headless:
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
                pygame.draw.circle(screen, (0, 0, 0), (int(ball.body.position[0]), int(ball.body.position[1])), ball_radius + 1)
                pygame.draw.circle(screen, ball.color, (int(ball.body.position[0]), int(ball.body.position[1])), ball_radius)

            if record:
                pygame.image.save(screen, f"frames/frame_{frame_count:05d}.png")
            frame_count += 1
            pygame.display.flip()


        if not hit:
            hit = is_hit(sim, effect_ball, sim_seconds)
        
        if record:
            sim_accum = 0.0
            while sim_accum < SIM_FRAME_TIME:
                world.Step(time_step, 20, 10)
                sim.step += 1
                sim_accum += time_step
                sim_seconds += time_step
        else:
            steps = int(SIM_FRAME_TIME / time_step)
            for _ in range(steps):
                world.Step(time_step, 20, 10)
                sim.step += 1
                sim_seconds += time_step

        if (hit and sim_seconds > hit+3) or sim_seconds > 18:
            running = False

        if not headless:
            clock.tick(framerate)

    if not headless:
        pygame.quit()

    if record:
        frames = sorted([os.path.join("frames", fname) for fname in os.listdir("frames") if fname.endswith(".png")])
        clip = ImageSequenceClip(frames, fps=framerate)
        clip.write_videofile("simulation.mp4", codec="libx264")

    cause_ball = effect_ball.last_collision()
    if cause_ball and len(cause_ball.ball_collisions) and hit:
       noise_ball = cause_ball.ball_collisions[0]['object']
       diverge_step = cause_ball.ball_collisions[0]['step']
    else:
        noise_ball, diverge_step = None, None

    if hit:
        return {
        'num_balls': sim.num_balls,
        'clear_cut': noise_ball is None and hit,
        'angles': condition.angles,
        'sim_time': sim_seconds,
        'hit': isinstance(hit, float),
        'collisions': len(sim.collisions),
        'cause_ball': cause_ball.name if cause_ball else None,
        'noise_ball': noise_ball.name if noise_ball else None,
        'diverge': diverge_step
        }
    return {
        'num_balls': sim.num_balls,
        'clear_cut': noise_ball is None,
        'angles': condition.angles,
        'sim_time': sim_seconds,
        'hit': isinstance(hit, float),
        'collisions': len(sim.collisions),
        'cause_ball': cause_ball.name if cause_ball else None,
        'noise_ball': noise_ball.name if noise_ball else None,
        'diverge': diverge_step
    }

if __name__ == '__main__':
    run(2, record=False, counterfactual = {'remove': 'green', 'diverge': 150, 'noise_ball': 'blue'}, headless=False)

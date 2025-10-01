from conditions import Condition
from random import shuffle
import numpy as np
import pygame
import os
from moviepy.editor import ImageSequenceClip
from Box2D import (b2World, b2PolygonShape, b2CircleShape, b2ContactListener, b2_staticBody, b2_dynamicBody)
import shutil

digits = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

# global parameters
width = 1000
height = 800
ball_radius = 28
border_width = 11
margin = 15
speed = 300
framerate = 30
time_step = 0.0001
gate_gap_height = 225

# radomly assign ball colors
red, green, yellow, blue, purple = (255, 0, 0), (20, 82, 20), (255, 255, 0), (0, 0, 255), (128, 0, 128)
colors = [red, green, yellow, blue, purple]

# fix this redundancy
col_dict = {
    'red': (255, 0, 0),
    'green': (20, 82, 20),
    'yellow': (255, 255, 0),
    'blue': (0, 0, 255),
    'purple': (128, 0, 128)
}

# Flip keys and values for reverse lookup
rgb_to_name = {v: k for k, v in col_dict.items()}


class Simulation:

    def __init__(self, balls, counterfactual = False, noise = 0):
        self.balls = balls
        self.num_balls = len(balls)-1
        self.noise = noise
        self.counterfactual = True if counterfactual else False
        self.hit = False
        self.collisions = []
        self.cause_ball = ''
        self.step = 0
        self.sim_seconds = 0
    
    def get_ball(self, name):
        try:
            return self.balls[name-1]
        except:
            return None

    

class Ball:

    def __init__(self, world, params):
        self.name = params['ball']
        xpos = round(width / 4) if self.name == 'effect' else width + 30 + params['x_jitter']

        self.body = world.CreateDynamicBody(position=(xpos, params['ypos']),shapes=b2CircleShape(radius=ball_radius))

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
    
    def add_collision(self, obj, step, time):
        if obj == 'wall':
            self.all_collisions.append({'name': 'wall', 'object': obj, 'step': step, 'time': time})
        elif isinstance(obj, Ball):
            if obj.noisy:
                    self.noisy = True
            # if obj.name != 'effect' and 'effect' not in self.collided_with:
            self.ball_collisions.append({'name': obj.name, 'object': obj, 'step': step, 'time': time})
            self.collided_with.add(obj.name)
            self.all_collisions.append({'name': obj.name, 'object': obj, 'step': step, 'time': time})
    
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
            A.add_collision(B, self.sim.step, self.sim.sim_seconds)
            names.append(A.name)
            if A.noisy == True:
                noisy = True
        else:
            names.append('wall')
        
        if isinstance(B, Ball):
            B.add_collision(A, self.sim.step, self.sim.sim_seconds)
            names.append(B.name)
            if B.noisy == True:
                noisy = True
        else:
            names.append('wall')

        self.sim.collisions.append({'objects': names, 'step': self.sim.step, 'noisy': noisy})


def draw_checkerboard_square(surface, center, side, num_checks=16):
    x0, y0 = center
    half = (side // 2) + 5
    check_size = side // num_checks
    colors = [(200, 200, 200), (255,255,255)]  # Black and white

    for row in range(num_checks):
        for col in range(num_checks):
            c = colors[(row+col)%2]
            rect = pygame.Rect(
                x0 - half + col*check_size,
                y0 - half + row*check_size,
                check_size,
                check_size
            )
            pygame.draw.rect(surface, c, rect)

# wall geom constants
left_edge_x = margin + border_width / 2
top_edge_y = margin + border_width / 2
bottom_edge_y = height - margin - border_width / 2
wall_len = (height - gate_gap_height - 2 * margin) / 2
wall_half_len = wall_len / 2


def create_world():
    world = b2World(gravity=(0, 0), doSleep=True)

    wall_shapes = [
        ((left_edge_x, margin + wall_half_len), b2PolygonShape(box=(border_width/2, wall_half_len))),
        ((left_edge_x, height - margin - wall_half_len), b2PolygonShape(box=(border_width/2, wall_half_len))),
        ((width / 2, top_edge_y), b2PolygonShape(box=((width - 2*margin)/2, border_width/2))),
        ((width / 2, bottom_edge_y), b2PolygonShape(box=((width - 2*margin)/2, border_width/2))),
    ]

    for position, shape in wall_shapes:
        body = world.CreateStaticBody(position=position)
        fixture = body.CreateFixture(shape=shape)
        fixture.restitution = 1.0
        fixture.friction = 0.0
        body.userData = 'wall'

    return world


def is_hit(sim, effect_ball, sim_seconds):
    effect_x = effect_ball.body.position[0]
    if effect_x < -5:
        final_pos = effect_ball.body.position[1]
        sim.hit = True
        return sim_seconds, effect_ball.body.position[1]
    return False, 0


def run(condition, cause_color='red', cause_ball = 1, record=False, counterfactual=None, headless=False, clip_num=1):

    ind = colors.index(col_dict[cause_color])
    colors.pop(ind)
    shuffle(colors)
    colors.insert(cause_ball-1, col_dict[cause_color])

    # ball parameters
    ball_params = [
        {'ball': 'effect', 'rgb': (180, 180, 180), 'ypos': round(height / 2), 'angle': 0},
        {'ball': 1, 'rgb': colors[0]},
        {'ball': 2, 'rgb': colors[1]},
        {'ball': 3, 'rgb': colors[2]},
        {'ball': 4, 'rgb': colors[3]},
        {'ball': 5, 'rgb': colors[4]}
]

    shutil.rmtree("frames") if os.path.exists("frames") else None
    os.makedirs("frames")

    if not headless:
        pygame.init()
        screen = pygame.display.set_mode((width, height))
        clock = pygame.time.Clock()

    remove = counterfactual['remove'] if counterfactual else None
    frame_count = 0
    world = create_world()

    for i in range(condition.num_balls):
        ball_params[i + 1]['ypos'] = condition.y_positions[i] + condition.jitter['y'][i]
        ball_params[i + 1]['angle'] = condition.radians[i]
        ball_params[i + 1]['y_jitter'] = condition.jitter['y'][i]
        ball_params[i + 1]['x_jitter'] = condition.jitter['x'][i]

    filtered_params = [params for params in ball_params[0:condition.num_balls + 1] if not (remove == params['ball'])]

    balls = []
    for i, params in enumerate(filtered_params):
        ball = Ball(world, params)
        if ball.name == 'effect':
            effect_ball = ball
        balls.append(ball)

    sim = Simulation(balls, remove)
    collision_listener = CollisionListener(sim)
    world.contactListener = collision_listener 

    running, hit = True, False
    sim_seconds = 0
    final_pos = round(height / 2)
    SIM_FRAME_TIME = 1.0 / framerate

    while running:
        if not headless:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            screen.fill((255, 255, 255))
            
            effect_start_pos = (int(effect_ball.body.position[0])+6, int(effect_ball.body.position[1])+6) if frame_count == 0 else effect_start_pos
            # checkerboard square at the effect ball's initial position
            draw_checkerboard_square(
                screen, 
                effect_start_pos,
                side=ball_radius*2+12
            )

            vert_wall_len = (height - gate_gap_height - 2 * margin) / 2

            pygame.draw.rect(screen, (0, 0, 0), (margin, margin, border_width, vert_wall_len))
            pygame.draw.rect(screen, (0, 0, 0), (margin, height - margin - vert_wall_len, border_width, vert_wall_len))
            pygame.draw.rect(screen, (0, 0, 0), (margin, margin, width - margin, border_width))
            pygame.draw.rect(screen, (0, 0, 0), (margin, height - margin - border_width, width - margin, border_width))
            pygame.draw.rect(screen, (255, 130, 150), (margin, margin + vert_wall_len, border_width, gate_gap_height))

            for ball in balls:
                pygame.draw.circle(screen, (0, 0, 0), (int(ball.body.position[0]), int(ball.body.position[1])), ball_radius + 1)
                pygame.draw.circle(screen, ball.color, (int(ball.body.position[0]), int(ball.body.position[1])), ball_radius)


            if record:
                pygame.image.save(screen, f"frames/frame_{frame_count:05d}.png")
            frame_count += 1
            pygame.display.flip()


        if not hit:
            hit, final_pos = is_hit(sim, effect_ball, sim_seconds)
        
        if record:
            sim_accum = 0.0
            while sim_accum < SIM_FRAME_TIME:
                world.Step(time_step, 20, 10)
                sim.step += 1
                sim_accum += time_step
                sim_seconds += time_step
                sim.sim_seconds += time_step
        else:
            steps = int(SIM_FRAME_TIME / time_step)
            for _ in range(steps):
                world.Step(time_step, 20, 10)
                sim.step += 1
                sim_seconds += time_step
                sim.sim_seconds += time_step

        if (hit and sim_seconds > hit+2) or sim_seconds > 18:
            running = False

        if not headless:
            clock.tick(framerate)

    if not headless:
        pygame.quit()

    if record:
        frames = sorted([os.path.join("frames", fname) for fname in os.listdir("frames") if fname.endswith(".png")])
        clip = ImageSequenceClip(frames, fps=framerate)
        clip.write_videofile(condition.filename, codec="libx264")


    cause_ball = effect_ball.last_collision()
    if cause_ball and len(cause_ball.ball_collisions) and hit:
       noise_ball = cause_ball.ball_collisions[0]['object']
       diverge_step = cause_ball.ball_collisions[0]['step']
    else:
        noise_ball, diverge_step = None, None

    return {
        'num_balls': sim.num_balls,
        'clear_cut': True if hit and noise_ball is None and len(effect_ball.collided_with) == 1 else False,
        'angles': condition.angles,
        'sim_time': sim_seconds,
        'hit': isinstance(hit, float),
        'collisions': len(sim.collisions),
        'cause_ball': cause_ball.name if cause_ball else None,
        'cause_collisions': cause_ball.all_collisions,
        'noise_ball': noise_ball.name if noise_ball else None,
        'diverge': diverge_step,
        'colors': [rgb_to_name[c] for c in colors[0:sim.num_balls]],
        'final_pos': final_pos
    }

if __name__ == '__main__':
    pass


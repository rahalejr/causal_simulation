import math
import os
import shutil

import numpy as np
from Box2D import b2CircleShape, b2ContactListener, b2PolygonShape, b2World


digits = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]

width = 1000
height = 800
ball_radius = 28
border_width = 11
margin = 15
speed = 300
framerate = 30
time_step = 0.0001
gate_gap_height = 225

red, green, yellow, blue, purple = (255, 0, 0), (20, 82, 20), (255, 255, 0), (0, 0, 255), (128, 0, 128)
colors = [green, red, yellow, blue, purple]

col_dict = {
    "red": (255, 0, 0),
    "green": (20, 82, 20),
    "yellow": (255, 255, 0),
    "blue": (0, 0, 255),
    "purple": (128, 0, 128),
}

rgb_to_name = {value: key for key, value in col_dict.items()}

left_edge_x = margin + border_width / 2
top_edge_y = margin + border_width / 2
bottom_edge_y = height - margin - border_width / 2
wall_len = (height - gate_gap_height - 2 * margin) / 2
wall_half_len = wall_len / 2


def gaussian_noise(standard_dev):
    u = 1 - np.random.random()
    v = 1 - np.random.random()
    return standard_dev * np.sqrt(-2 * np.log(u)) * np.cos(2 * np.pi * v)


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def rotate_velocity(vx, vy, theta):
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    return vx * cos_t - vy * sin_t, vx * sin_t + vy * cos_t


def sort_objs(items):
    return sorted(items, key=lambda item: (item == "wall", str(item)))


def get_roles(ball_a, ball_b):
    ax = float(ball_a.body.position[0])
    bx = float(ball_b.body.position[0])

    if ax > bx:
        return ball_a, ball_b
    if bx > ax:
        return ball_b, ball_a

    avx = float(ball_a.body.linearVelocity[0])
    bvx = float(ball_b.body.linearVelocity[0])

    if avx < bvx:
        return ball_a, ball_b
    if bvx < avx:
        return ball_b, ball_a

    if str(ball_a.name) < str(ball_b.name):
        return ball_a, ball_b
    return ball_b, ball_a


def collision_mag(collider, collided):
    cx = float(collider.body.position[0])
    cy = float(collider.body.position[1])
    tx = float(collided.body.position[0])
    ty = float(collided.body.position[1])

    nx = tx - cx
    ny = ty - cy
    dist = math.hypot(nx, ny)
    if dist == 0:
        return 0.0

    nx /= dist
    ny /= dist

    cvx = float(collider.body.linearVelocity[0])
    cvy = float(collider.body.linearVelocity[1])
    tvx = float(collided.body.linearVelocity[0])
    tvy = float(collided.body.linearVelocity[1])

    collider_speed = math.hypot(cvx, cvy)
    if collider_speed == 0:
        return 0.0

    rel_closing_speed = (cvx - tvx) * nx + (cvy - tvy) * ny
    return clamp(rel_closing_speed / collider_speed, 0.0, 1.0)


def load_pygame():
    import pygame

    return pygame


def load_clip():
    from moviepy.editor import ImageSequenceClip

    return ImageSequenceClip


def draw_checkerboard_square(surface, center, side, num_checks=16):
    pygame = load_pygame()
    x0, y0 = center
    half = (side // 2) + 5
    check_size = side // num_checks
    checker_colors = [(200, 200, 200), (255, 255, 255)]

    for row in range(num_checks):
        for col in range(num_checks):
            color = checker_colors[(row + col) % 2]
            rect = pygame.Rect(
                x0 - half + col * check_size,
                y0 - half + row * check_size,
                check_size,
                check_size,
            )
            pygame.draw.rect(surface, color, rect)


def create_world():
    world = b2World(gravity=(0, 0), doSleep=True)

    wall_shapes = [
        ((left_edge_x, margin + wall_half_len), b2PolygonShape(box=(border_width / 2, wall_half_len))),
        ((left_edge_x, height - margin - wall_half_len), b2PolygonShape(box=(border_width / 2, wall_half_len))),
        ((width / 2, top_edge_y), b2PolygonShape(box=((width - 2 * margin) / 2, border_width / 2))),
        ((width / 2, bottom_edge_y), b2PolygonShape(box=((width - 2 * margin) / 2, border_width / 2))),
    ]

    for position, shape in wall_shapes:
        body = world.CreateStaticBody(position=position)
        fixture = body.CreateFixture(shape=shape)
        fixture.restitution = 1.0
        fixture.friction = 0.0
        body.userData = "wall"

    return world


class Ball:
    def __init__(self, world, params=None, state=None):
        if state is not None:
            self.name = state["name"]
            self.slot = state["slot"]
            self.color = tuple(state["color"])
            self.noisy = bool(state.get("noisy", False))
            xpos, ypos = state["position"]
            vx, vy = state["velocity"]
        else:
            self.name = params["ball"]
            self.slot = params["position"]
            self.color = params["rgb"]
            self.noisy = False
            xpos = round(width / 4) if self.name == "effect" else width + 30 + params["x_jitter"]
            ypos = params["ypos"]
            vx = 0.0 if self.name == "effect" else speed * np.cos(params["angle"])
            vy = 0.0 if self.name == "effect" else speed * np.sin(params["angle"])

        self.body = world.CreateDynamicBody(
            position=(float(xpos), float(ypos)),
            shapes=b2CircleShape(radius=ball_radius),
        )
        self.body.fixtures[0].restitution = 1.0
        self.body.fixtures[0].friction = 0.0
        self.body.linearDamping = 0.0
        self.body.linearVelocity = (float(vx), float(vy))
        self.body.userData = self

        self.collided_with = set()
        self.ball_collisions = []
        self.all_collisions = []

    def add_collision(self, obj, step, sim_time):
        if obj == "wall":
            self.all_collisions.append(
                {
                    "name": "wall",
                    "slot": "wall",
                    "object": "wall",
                    "step": step,
                    "time": sim_time,
                }
            )
            return

        if isinstance(obj, Ball):
            if obj.noisy:
                self.noisy = True

            collision = {
                "name": obj.name,
                "slot": obj.slot,
                "object": obj,
                "step": step,
                "time": sim_time,
            }
            self.ball_collisions.append(collision)
            self.collided_with.add(obj.name)
            self.all_collisions.append(collision)

    def last_collision(self):
        if self.ball_collisions:
            return self.ball_collisions[-1]
        return None

    def rotate_velocity(self, theta):
        vx = float(self.body.linearVelocity[0])
        vy = float(self.body.linearVelocity[1])
        new_vx, new_vy = rotate_velocity(vx, vy, theta)
        self.body.linearVelocity = (new_vx, new_vy)

    def add_noise(self, noise=6):
        angle_deg = gaussian_noise(1) * noise
        angle_rad = angle_deg * (math.pi / 180.0)
        self.rotate_velocity(angle_rad)
        self.noisy = True

    def to_state(self):
        return {
            "name": self.name,
            "slot": self.slot,
            "color": list(self.color),
            "position": [float(self.body.position[0]), float(self.body.position[1])],
            "velocity": [float(self.body.linearVelocity[0]), float(self.body.linearVelocity[1])],
            "noisy": bool(self.noisy),
        }


class Simulation:
    def __init__(self, world, balls, noise=6, actual_cols=None, trace_style="simple", save_snaps=False):
        self.world = world
        self.balls = balls
        self.effect_ball = next(ball for ball in balls if ball.name == "effect")
        self.num_balls = len([ball for ball in balls if ball.name != "effect"])
        self.noise = noise
        self.actual_cols = actual_cols or []
        self.trace_style = trace_style
        self.save_snaps = save_snaps

        self.hit = False
        self.step = 0
        self.sim_seconds = 0.0
        self.collisions = []
        self.snapshots = []
        self.pending_noise = []
        self.pending_idxs = []

    def find_ball_by_slot(self, slot):
        for ball in self.balls:
            if ball.slot == slot:
                return ball
        return None

    def find_ball_by_name(self, name):
        for ball in self.balls:
            if ball.name == name:
                return ball
        return None

    def snapshot_world(self):
        return {
            "step": int(self.step),
            "sim_seconds": float(self.sim_seconds),
            "hit": bool(self.hit),
            "balls": [ball.to_state() for ball in self.balls],
        }

    def finalize_step(self):
        if not self.pending_idxs:
            return

        if not self.save_snaps:
            self.pending_idxs.clear()
            return

        snapshot_id = len(self.snapshots)
        snapshot = self.snapshot_world()
        snapshot["snapshot_id"] = snapshot_id
        self.snapshots.append(snapshot)

        for index in self.pending_idxs:
            collision = self.collisions[index]
            collision["snapshot_id"] = snapshot_id
            collision["snapshot_step"] = int(snapshot["step"])
            collision["snapshot_time"] = float(snapshot["sim_seconds"])

            collider_name = collision.get("collider_name")
            collided_name = collision.get("collided_name")
            if collider_name is None or collided_name is None:
                continue

            collider = self.find_ball_by_name(collider_name)
            collided = self.find_ball_by_name(collided_name)

            collision["collider_post_position"] = [
                float(collider.body.position[0]),
                float(collider.body.position[1]),
            ]
            collision["collided_post_position"] = [
                float(collided.body.position[0]),
                float(collided.body.position[1]),
            ]
            collision["collider_post_velocity"] = [
                float(collider.body.linearVelocity[0]),
                float(collider.body.linearVelocity[1]),
            ]
            collision["collided_post_velocity"] = [
                float(collided.body.linearVelocity[0]),
                float(collided.body.linearVelocity[1]),
            ]

        self.pending_idxs.clear()


def same_objs(left, right):
    if isinstance(left, set):
        return left == right
    return set(left) == right


class CollisionListener(b2ContactListener):
    def __init__(self, sim):
        super().__init__()
        self.sim = sim

    def BeginContact(self, contact):
        a = contact.fixtureA.body.userData
        b = contact.fixtureB.body.userData

        object_list = [
            a.slot if isinstance(a, Ball) else "wall",
            b.slot if isinstance(b, Ball) else "wall",
        ]
        object_set = set(object_list)

        if self.sim.actual_cols:
            matched = any(
                collision["step"] == self.sim.step and same_objs(collision["objects"], object_set)
                for collision in self.sim.actual_cols
            )
            if not matched:
                for obj in (a, b):
                    if isinstance(obj, Ball):
                        self.sim.pending_noise.append(obj)

        if isinstance(a, Ball):
            a.add_collision(b, self.sim.step, self.sim.sim_seconds)
        if isinstance(b, Ball):
            b.add_collision(a, self.sim.step, self.sim.sim_seconds)

        if self.sim.trace_style == "simple":
            self.sim.collisions.append({"objects": object_set, "step": self.sim.step})
            return

        collision = {
            "objects": sort_objs(object_list),
            "step": int(self.sim.step),
            "time": float(self.sim.sim_seconds),
            "snapshot_id": None,
            "snapshot_step": None,
            "snapshot_time": None,
            "collider": None,
            "collider_name": None,
            "collided": None,
            "collided_name": None,
            "magnitude": None,
            "collider_pre_position": None,
            "collided_pre_position": None,
            "collider_pre_velocity": None,
            "collided_pre_velocity": None,
            "collider_post_position": None,
            "collided_post_position": None,
            "collider_post_velocity": None,
            "collided_post_velocity": None,
        }

        if isinstance(a, Ball) and isinstance(b, Ball):
            collider, collided = get_roles(a, b)
            collision["collider"] = collider.slot
            collision["collider_name"] = collider.name
            collision["collided"] = collided.slot
            collision["collided_name"] = collided.name
            collision["magnitude"] = float(collision_mag(collider, collided))
            collision["collider_pre_position"] = [
                float(collider.body.position[0]),
                float(collider.body.position[1]),
            ]
            collision["collided_pre_position"] = [
                float(collided.body.position[0]),
                float(collided.body.position[1]),
            ]
            collision["collider_pre_velocity"] = [
                float(collider.body.linearVelocity[0]),
                float(collider.body.linearVelocity[1]),
            ]
            collision["collided_pre_velocity"] = [
                float(collided.body.linearVelocity[0]),
                float(collided.body.linearVelocity[1]),
            ]

        self.sim.collisions.append(collision)
        self.sim.pending_idxs.append(len(self.sim.collisions) - 1)


def build_params(condition):
    ball_cols = [colors[index - 1] for index in condition.ball_positions]
    params = [
        {
            "ball": "effect",
            "rgb": (180, 180, 180),
            "ypos": round(height / 2),
            "angle": 0,
            "position": -1,
            "x_jitter": 0,
            "y_jitter": 0,
        }
    ]

    for index in range(condition.num_balls):
        params.append(
            {
                "ball": index + 1,
                "rgb": ball_cols[index],
                "position": condition.ball_positions[index],
                "ypos": condition.y_positions[index] + condition.jitter["y"][index],
                "angle": condition.radians[index],
                "x_jitter": condition.jitter["x"][index],
                "y_jitter": condition.jitter["y"][index],
            }
        )

    return params, ball_cols


def sim_from_cond(condition, noise=6, remove=None, actual_data=None, trace_style="simple", save_snaps=False):
    world = create_world()
    params, ball_cols = build_params(condition)

    if remove is not None:
        params = [ball for ball in params if ball["ball"] != remove]

    balls = [Ball(world, params=ball) for ball in params]
    actual_cols = actual_data["collisions"] if actual_data else None
    sim = Simulation(
        world,
        balls,
        noise=noise,
        actual_cols=actual_cols,
        trace_style=trace_style,
        save_snaps=save_snaps,
    )
    world.contactListener = CollisionListener(sim)
    return sim, ball_cols


def sim_from_snapshot(snapshot, noise=6):
    world = create_world()
    balls = [Ball(world, state=state) for state in snapshot["balls"]]
    sim = Simulation(world, balls, noise=noise, trace_style="detailed", save_snaps=True)
    sim.step = int(snapshot.get("step", 0))
    sim.sim_seconds = float(snapshot.get("sim_seconds", 0.0))
    sim.hit = bool(snapshot.get("hit", False))
    world.contactListener = CollisionListener(sim)
    return sim


def check_hit(sim):
    effect_x = float(sim.effect_ball.body.position[0])
    if effect_x < -5:
        sim.hit = True
        return True, float(sim.effect_ball.body.position[1])
    return False, 0.0


def apply_noise(sim):
    if not sim.pending_noise:
        return

    for ball in set(sim.pending_noise):
        ball.add_noise(sim.noise)
    sim.pending_noise.clear()


def queue_trace_noise(sim):
    if not sim.actual_cols:
        return

    current = [collision for collision in sim.collisions if collision["step"] == sim.step - 1]
    for actual in sim.actual_cols:
        if sim.step - actual["step"] != 1:
            continue

        matched = any(same_objs(collision["objects"], actual["objects"]) for collision in current)
        if matched:
            continue

        for obj in actual["objects"]:
            ball = sim.find_ball_by_slot(obj)
            if isinstance(ball, Ball):
                sim.pending_noise.append(ball)


def prep_frames(record):
    if not record:
        return

    if os.path.exists("frames"):
        shutil.rmtree("frames")
    os.makedirs("frames")


def open_screen(sim):
    pygame = load_pygame()
    pygame.init()
    screen = pygame.display.set_mode((width, height))
    clock = pygame.time.Clock()
    effect_pos = (
        float(sim.effect_ball.body.position[0]),
        float(sim.effect_ball.body.position[1]),
    )
    return pygame, screen, clock, effect_pos


def render_scene(screen, sim, effect_pos):
    pygame = load_pygame()
    screen.fill((255, 255, 255))

    draw_checkerboard_square(
        screen,
        [effect_pos[0] + 6, effect_pos[1] + 6],
        side=ball_radius * 2 + 12,
    )

    vert_wall_len = (height - gate_gap_height - 2 * margin) / 2
    pygame.draw.rect(screen, (0, 0, 0), (margin, margin, border_width, vert_wall_len))
    pygame.draw.rect(screen, (0, 0, 0), (margin, height - margin - vert_wall_len, border_width, vert_wall_len))
    pygame.draw.rect(screen, (0, 0, 0), (margin, margin, width - margin, border_width))
    pygame.draw.rect(screen, (0, 0, 0), (margin, height - margin - border_width, width - margin, border_width))
    pygame.draw.rect(screen, (255, 130, 150), (margin, margin + vert_wall_len, border_width, gate_gap_height))

    for ball in sim.balls:
        center = (int(ball.body.position[0]), int(ball.body.position[1]))
        pygame.draw.circle(screen, (0, 0, 0), center, ball_radius + 1)
        pygame.draw.circle(screen, ball.color, center, ball_radius)


def write_vid(filename):
    if filename is None:
        return

    frames = sorted(
        os.path.join("frames", frame_name)
        for frame_name in os.listdir("frames")
        if frame_name.endswith(".png")
    )
    clip_class = load_clip()
    clip = clip_class(frames, fps=framerate)
    clip.write_videofile(filename, codec="libx264")


def loop_simple(sim, record=False, headless=False, filename=None, max_time=6.0):
    prep_frames(record)

    pygame = None
    screen = None
    clock = None
    effect_pos = None

    if not headless:
        pygame, screen, clock, effect_pos = open_screen(sim)

    frame_count = 0
    hit_time = None
    final_pos = round(height / 2)
    sim_frame_time = 1.0 / framerate

    running = True
    while running:
        if hit_time is None:
            hit_now, final_pos = check_hit(sim)
            if hit_now:
                hit_time = float(sim.sim_seconds)

        steps = int(sim_frame_time / time_step)
        for _ in range(steps):
            sim.world.Step(time_step, 20, 10)
            sim.step += 1
            sim.sim_seconds += time_step

            apply_noise(sim)
            queue_trace_noise(sim)

        if (hit_time is not None and sim.sim_seconds > hit_time + 2.0) or sim.sim_seconds > max_time:
            break

        if headless:
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        render_scene(screen, sim, effect_pos)

        if record:
            pygame.image.save(screen, f"frames/frame_{frame_count:05d}.png")

        frame_count += 1
        pygame.display.flip()
        clock.tick(framerate)

    if pygame is not None:
        pygame.quit()

    if record:
        write_vid(filename)

    return {
        "sim_time": float(sim.sim_seconds),
        "hit": bool(sim.hit),
        "final_pos": float(final_pos),
    }


def loop_detailed(sim, record=False, headless=False, filename=None, max_time=6.0):
    prep_frames(record)

    pygame = None
    screen = None
    clock = None
    effect_pos = None

    if not headless:
        pygame, screen, clock, effect_pos = open_screen(sim)

    frame_count = 0
    final_pos = round(height / 2)
    hit_time = None
    sim_frame_time = 1.0 / framerate

    running = True
    while running:
        steps = int(sim_frame_time / time_step)

        for _ in range(steps):
            sim.step += 1
            sim.sim_seconds += time_step
            sim.world.Step(time_step, 20, 10)
            sim.finalize_step()

            if hit_time is None:
                hit_now, final_pos = check_hit(sim)
                if hit_now:
                    hit_time = float(sim.sim_seconds)

            if (hit_time is not None and sim.sim_seconds > hit_time + 2.0) or sim.sim_seconds > max_time:
                running = False
                break

        if headless:
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        render_scene(screen, sim, effect_pos)

        if record:
            pygame.image.save(screen, f"frames/frame_{frame_count:05d}.png")

        frame_count += 1
        pygame.display.flip()
        clock.tick(framerate)

    if pygame is not None:
        pygame.quit()

    if record:
        write_vid(filename)

    return {
        "sim_time": float(sim.sim_seconds),
        "hit": bool(sim.hit),
        "final_pos": float(final_pos),
    }


def simple_history(history):
    return [
        {
            "name": item["name"],
            "object": item["object"],
            "step": item["step"],
            "time": item["time"],
        }
        for item in history
    ]


def detailed_history(history):
    return [
        {
            "name": item["name"],
            "slot": item["slot"],
            "step": item["step"],
            "time": item["time"],
        }
        for item in history
    ]


def noise_snapshot(sim, noise=6, target_slots=None, include_effect=False):
    for ball in sim.balls:
        if ball.name == "effect" and not include_effect:
            continue

        if target_slots is not None and ball.slot not in target_slots and ball.name not in target_slots:
            continue

        vx = float(ball.body.linearVelocity[0])
        vy = float(ball.body.linearVelocity[1])
        if math.hypot(vx, vy) == 0:
            continue

        ball.add_noise(noise=noise)


def run_simple(
    condition,
    pause=10,
    actual_data=None,
    noise=6,
    cause_color="red",
    cause_ball=1,
    record=False,
    counterfactual=None,
    headless=False,
    clip_num=1,
    is_cf=False,
    max_time=6.0,
):
    del pause, cause_color, cause_ball, clip_num, is_cf

    remove = counterfactual["remove"] if counterfactual else None
    sim, ball_cols = sim_from_cond(
        condition,
        noise=noise,
        remove=remove,
        actual_data=actual_data,
        trace_style="simple",
        save_snaps=False,
    )
    out = loop_simple(
        sim,
        record=record,
        headless=headless,
        filename=condition.filename if record else None,
        max_time=max_time,
    )

    cause_record = sim.effect_ball.last_collision()
    cause_obj = cause_record["object"] if cause_record else None

    return {
        "num_balls": sim.num_balls,
        "angles": condition.angles,
        "sim_time": out["sim_time"],
        "hit": out["hit"],
        "cause_ball": cause_obj.name if cause_obj else None,
        "cause_collisions": simple_history(cause_obj.all_collisions) if cause_obj else None,
        "colors": [rgb_to_name[color] for color in ball_cols],
        "final_pos": out["final_pos"],
        "collisions": sim.collisions,
    }


def detailed_output(sim, ball_cols=None, angles=None, final_pos=0.0):
    cause_record = sim.effect_ball.last_collision()
    output = {
        "num_balls": sim.num_balls,
        "sim_time": float(sim.sim_seconds),
        "hit": bool(sim.hit),
        "cause_ball": cause_record["name"] if cause_record else None,
        "cause_ball_slot": cause_record["slot"] if cause_record else None,
        "cause_collisions": detailed_history(sim.effect_ball.all_collisions),
        "final_pos": float(final_pos),
        "collisions": sim.collisions,
        "snapshots": sim.snapshots,
        "final_state": sim.snapshot_world(),
    }

    if angles is not None:
        output["angles"] = angles
    if ball_cols is not None:
        output["colors"] = [rgb_to_name[color] for color in ball_cols]

    return output


def run_detailed(
    condition,
    pause=10,
    actual_data=None,
    noise=6,
    cause_color="red",
    cause_ball=1,
    record=False,
    counterfactual=None,
    headless=False,
    clip_num=1,
    is_cf=False,
    max_time=6.0,
):
    del pause, actual_data, cause_color, cause_ball, counterfactual, clip_num, is_cf

    sim, ball_cols = sim_from_cond(
        condition,
        noise=noise,
        trace_style="detailed",
        save_snaps=True,
    )
    out = loop_detailed(
        sim,
        record=record,
        headless=headless,
        filename=condition.filename if record else None,
        max_time=max_time,
    )
    return detailed_output(
        sim,
        ball_cols=ball_cols,
        angles=condition.angles,
        final_pos=out["final_pos"],
    )


def run_from_snapshot_detailed(
    snapshot,
    noise=6,
    target_slots=None,
    include_effect=False,
    record=False,
    headless=True,
    filename=None,
    max_time=6.0,
):
    sim = sim_from_snapshot(snapshot, noise=noise)

    if noise and noise > 0:
        noise_snapshot(
            sim,
            noise=noise,
            target_slots=target_slots,
            include_effect=include_effect,
        )

    out = loop_detailed(
        sim,
        record=record,
        headless=headless,
        filename=filename,
        max_time=max_time,
    )
    return detailed_output(sim, final_pos=out["final_pos"])


def monte_carlo_goal_probability(
    snapshot,
    n_simulations=100,
    noise=6,
    target_slots=None,
    include_effect=False,
    max_time=6.0,
):
    hits = 0
    for _ in range(n_simulations):
        output = run_from_snapshot_detailed(
            snapshot=snapshot,
            noise=noise,
            target_slots=target_slots,
            include_effect=include_effect,
            record=False,
            headless=True,
            max_time=max_time,
        )
        if output["hit"]:
            hits += 1
    return hits / float(n_simulations)

from concurrent.futures import ProcessPoolExecutor, as_completed

import json
import os
import numpy as np
import pandas as pd

from conditions import Condition
from simulation import run, monte_carlo_goal_probability

debug = False

mapping_simulations = 200
mapping_noise = 6
max_workers = 8
effect_slot = -1


def process_conditions(conds_list, output_file='rick_output.csv'):
    table = []

    payloads = []
    for i, c in enumerate(conds_list):
        stim_index = c.get('index', i)
        payloads.append((c, stim_index))

    total = len(payloads)
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(run_condition, p) for p in payloads]
        for done, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            print(f'[{done}/{total}] stim {result[0]}', flush=True)
            results.append(result)

    for stim_index, rows in sorted(results, key=lambda x: x[0]):
        table.extend(rows)

    df = pd.DataFrame(table).sort_values(['stimulus', 'ball_index'], kind='mergesort').reset_index(drop=True)
    df.to_csv(output_file, index=False)
    return df


def run_condition(payload):
    c, stim_index = payload

    np.random.seed((os.getpid() * 1000003 + stim_index) % (2**32))

    cond = Condition(
        index=stim_index,
        angles=c['angles'],
        preemption=c['preemption'],
        jitter=c['jitter'],
        ball_positions=c['ball_positions'],
        filename=c['filename'],
        order=c['order'],
        shape=c.get('shape', 'ball')
    )

    actual_output = run(cond, record=False, headless=(not debug))

    support = build_causal_support(actual_output, effect_slot=effect_slot)
    features_by_slot = support_features(actual_output, support)

    slot_to_ball_index = {
        cond.ball_positions[i]: i + 1
        for i in range(cond.num_balls)
    }

    features_by_ball = {}
    for slot, features in features_by_slot.items():
        ball_index = slot_to_ball_index.get(slot)
        if ball_index is not None:
            features_by_ball[ball_index] = features

    results = []
    for b in range(cond.num_balls):
        ball_index = b + 1
        features = features_by_ball.get(
            ball_index,
            {
                'collision_magnitude': 0.0,
                'mapping_ease': 0.0,
                'support_count': 0,
            }
        )
        row = {
            'stimulus': cond.index,
            'ball_index': ball_index,
            'order': cond.order.index(ball_index) + 1,
            'collision_magnitude': float(features['collision_magnitude']),
            'mapping_ease': float(features['mapping_ease']),
            'support_count': int(features['support_count']),
            'support_gate': int(features['support_count'] > 0),
        }
        results.append(row)

    return stim_index, results


def build_causal_support(actual_output, effect_slot=-1):
    collisions = actual_output.get('collisions', [])

    indexed = []
    for idx, c in enumerate(collisions):
        if c.get('collider') is None:
            continue
        if c.get('collided') is None:
            continue
        if c.get('snapshot_id') is None:
            continue
        indexed.append((idx, c))

    terminal_idx = None
    for pos in range(len(indexed) - 1, -1, -1):
        _, c = indexed[pos]
        if c['collided'] == effect_slot:
            terminal_idx = pos
            break

    if terminal_idx is None:
        return []

    support = [indexed[terminal_idx]]
    relevant_slots = {indexed[terminal_idx][1]['collider']}

    for pos in range(terminal_idx - 1, -1, -1):
        idx, c = indexed[pos]
        if c['collided'] not in relevant_slots:
            continue
        support.append((idx, c))
        relevant_slots.add(c['collider'])

    support.sort(key=lambda item: (item[1]['step'], item[0]))
    return [c for _, c in support]


def clamp(value, low, high):
    return max(low, min(high, value))


def unit_direction(velocity):
    vx = float(velocity[0])
    vy = float(velocity[1])
    speed = np.hypot(vx, vy)
    if speed == 0:
        return None
    return np.array((vx / speed, vy / speed), dtype=float)


def collision_magnitude(collision):
    collided_pre_velocity = collision.get('collided_pre_velocity')
    collided_post_velocity = collision.get('collided_post_velocity')

    if collided_pre_velocity is None or collided_post_velocity is None:
        return 0.0

    pre_direction = unit_direction(collided_pre_velocity)
    post_direction = unit_direction(collided_post_velocity)

    # A collision that writes a direction into a previously stationary object
    # counts as maximal magnitude on this scale.
    if pre_direction is None:
        return 1.0 if post_direction is not None else 0.0

    if post_direction is None:
        return 0.0

    cosine = clamp(float(np.dot(pre_direction, post_direction)), -1.0, 1.0)
    return np.arccos(cosine) / np.pi


def support_features(actual_output, support):
    aggregates = {}
    ease_cache = {}

    for collision in support:
        collider = collision.get('collider')
        magnitude = collision_magnitude(collision)
        snapshot_id = collision.get('snapshot_id')

        if collider is None or snapshot_id is None:
            continue

        if snapshot_id not in ease_cache:
            snapshot = actual_output['snapshots'][snapshot_id]
            ease_cache[snapshot_id] = monte_carlo_goal_probability(
                snapshot=snapshot,
                n_simulations=mapping_simulations,
                noise=mapping_noise,
                target_slots=None,
                include_effect=False
            )

        ease = ease_cache[snapshot_id]
        if collider not in aggregates:
            aggregates[collider] = {
                'collision_magnitude_max': None,
                'mapping_ease_max': None,
                'count': 0,
            }

        current_magnitude = aggregates[collider]['collision_magnitude_max']
        current_ease = aggregates[collider]['mapping_ease_max']

        aggregates[collider]['collision_magnitude_max'] = (
            magnitude if current_magnitude is None else max(current_magnitude, magnitude)
        )
        aggregates[collider]['mapping_ease_max'] = (
            ease if current_ease is None else max(current_ease, ease)
        )
        aggregates[collider]['count'] += 1

    features = {}
    for collider, values in aggregates.items():
        count = values['count']
        if count <= 0:
            continue
        features[collider] = {
            # Aggregate repeated support collisions to one bounded feature row per ball.
            'collision_magnitude': values['collision_magnitude_max'],
            'mapping_ease': values['mapping_ease_max'],
            'support_count': count,
        }

    return features


if __name__ == '__main__':
    filename = 'collisions.json'
    with open(filename, 'r') as f:
        data = json.load(f)

    process_conditions(data)

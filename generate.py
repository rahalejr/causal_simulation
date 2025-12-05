import os
import json
import numpy as np
from random import shuffle, sample, randint
from copy import deepcopy
from simulation import run
from conditions import Condition
from videos.qualpaths import paths

def get_conditions(filename='conditions.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    return data

def simple_info(filename='kept_video_meta.json'):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            for i in data:
                del i['angles']
                del i['jitter']
                sim_number = int(i['file_name'].split('simulation')[-1].split('.')[0])
                i['qual_path'] = paths[sim_number]
            add_conditions(data, filename='cleaned_video_meta.json', append=False)

def add_conditions(new_data, filename='conditions.json', append=True):
    conditions = get_conditions(filename) if append else []
    
    # append new data
    if isinstance(new_data, list):
        conditions.extend(new_data)
    else:
        conditions.append(new_data)
    
    # write back to file
    with open(filename, 'w') as f:
        json.dump(conditions, f, indent=2)

def generate_conditions():
    kept_conditions = []

    for _ in range(2000):
        sd = 20
        num_angles = 3
        raw_angles = np.random.normal(loc=180, scale=sd, size=num_angles)
        clipped_angles = np.clip(raw_angles, 110, 250)
        angles = [round(ang) for ang in clipped_angles.tolist()]
        ball_positions = sample([1,2,3,4,5], 3)
        ball_positions.sort()
        cond = Condition(angles, ball_positions)

        sim = run(cond, record=False, counterfactual=None, headless=True)


        if sim['hit']:

            colls = sim['cause_collisions']
            if colls:
                names = [c['name'] for c in colls if c['name'] != 'wall']
                difference_makers = len(set(names[:names.index('effect')])) + 1
                effect_collisions = [c['name'] for c in sim['effect_collisions'] if c['name'] != 'wall']
                if difference_makers == 3 and len(effect_collisions) == 1:
                    times = []
                    for i in colls:
                        times.append(i['time'])
                        if i['name'] == 'effect':
                            break
                    if len(times) > 1:
                        time_diff = times[-1] - times[-2]
                    else:
                        time_diff = times[-1]
                    time_diff = round(time_diff, 2)


                    # while True:
                    #     if input('replay: ').upper() != 'Y':
                    #         break
                    #     run(cond, record=False, counterfactual=None, headless=False)

                    # if input('keep? :') != 'y':
                    #     continue
                    

                    info = {
                        "index": _,
                        "num_balls": 3,
                        "ball_positions": ball_positions,
                        "angles": angles,
                        "last_collision": time_diff,
                        "cause_ball": sim["cause_ball"] if sim["cause_ball"] else None,
                        "duration": round(sim["duration"], 2),
                        "difference_makers": difference_makers,
                        "jitter": cond.jitter
                    }

                    kept_conditions.append(info)

    add_conditions(kept_conditions, filename="newconds.json")

def run_cf(condition, headless=False):
    colors = ['red', 'green', 'yellow', 'blue', 'purple']
    
    cf_angles = deepcopy(condition['angles'])
    cf_pos = deepcopy(condition['ball_positions'])
    cf_jitter = deepcopy(condition['jitter'])
    remove_index = condition['cause_ball']

    cf_angles.pop(remove_index - 1)
    cf_pos.pop(remove_index - 1)
    [cf_jitter[axis].pop(remove_index - 1) for axis in ['x', 'y']]

    counterfactual = Condition(cf_angles, cf_pos, jitter=cf_jitter)

    cf_output = run(
        counterfactual,
        actual_data=None,
        cause_color=colors[(condition['index'] - 1) % len(colors)],
        cause_index=remove_index,
        record=False,
        counterfactual=None,
        headless=headless
    )

    return cf_output

def time_diff(sim):
    colls = sim.get('cause_collisions') or []
    if not colls:
        return None

    times = []
    for c in colls:
        times.append(c['time'])
        if c['name'] == 'effect':
            break

    if not times:
        return None

    if len(times) > 1:
        diff = times[-1] - times[-2]
    else:
        diff = times[-1]

    return round(diff, 2)

def play_conditions(ind):

    filtered = get_conditions('collisions.json')
    kept = []

    c = filtered[ind-1]
    ind = c['index']
    cause = c['cause_ball']
    filename = f"videos/bin/stim{c['index']}.mp4"
    cond = Condition(c['angles'], c['ball_positions'], jitter=c['jitter'], filename=filename)
    run_cf(c)
    output = run(cond, actual_data = None, noise = .01, cause_color = 'red', cause_index = cause, record=False, counterfactual=None, headless=False)


def record_conditions():

    file = 'newconds.json'

    colors = ['red', 'green', 'blue']
    conditions = get_conditions(file)
    cond_output = []
    for c in conditions:
        ind = c['index']
        cause = c['cause_ball'] if c['cause_ball'] else 1
        filename = filename = f"videos/bin/stim{c['index']}.mp4"
        angles, cf_angles = deepcopy(c['angles']), deepcopy(c['angles'])
        # if group == 'miss':
        #     sd = randint(3, 10)
        #     angles = np.array(angles) + np.random.normal(0, sd, len(angles)).astype(int)
        angles = list(angles)
        pos, cf_pos = deepcopy(c['ball_positions']), deepcopy(c['ball_positions'])
        jitter, cf_jitter = deepcopy(c['jitter']), deepcopy(c['jitter'])
        cause_color = colors[(ind-1) % 3]
        # if group == 'miss':
        #     cause_color = colors[randint(0,2)]
        cond = Condition(angles, pos, jitter=jitter, filename=filename)
        sim = run(cond, actual_data = None, noise = .01, cause_color = cause_color, cause_index = 1, record=True, counterfactual=None, headless=False)
        # c['duration'] = output['duration']
        # c['cause_ball'] = output['cause_ball']
        # c['last_collision'] = time_diff(output)
        # c['filename'] = filename
        # c['colors'] = output['colors']
        # c['cause_color'] = cause_color
        info = {
            "index": c['index'],
            "num_balls": 3,
            "ball_positions": c['ball_positions'],
            "angles": angles,
            "cause_ball": sim["cause_ball"] if sim["cause_ball"] else None,
            "duration": round(sim["duration"], 2),
            "last_collision": time_diff(sim),
            "jitter": cond.jitter,
            "colors": sim['colors'],
            "cause_color": cause_color,
            "preemption": False,
            "filename": f"stimuli/collisions/miss/stim{c['index']}.mp4"
        }

        cond_output.append(info)
    add_conditions(cond_output, filename=f"revised_stim.json", append=True)

if __name__ == '__main__':
    # generate_conditions()
    # play_conditions(16)
    record_conditions()
    # simple_info()



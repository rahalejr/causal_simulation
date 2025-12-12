# noise values range from .1 to 2
# how many e's do we need to generate?

import os
import json
import copy
import numpy as np
from simulation import run, gaussian_noise
from conditions import Condition

n_simulations = 1
perturb_simulations = 1
perturb = 1

def process_conditions(conds_list):
    for c in conds_list:
        cond = Condition(angles=c['angles'], preemption=c['preemption'], jitter=c['jitter'], ball_positions=c['ball_positions'], filename=c['filename'])
        run_condition(cond)

def run_condition(cond):

    actual_output=run(cond, record=False, counterfactual=None, headless=False)
    #counterfactual = run(remove_ball(cond, 2),record=False, counterfactual=None, headless=False)
    #print(collision_compare(actual_output, counterfactual)) 
    #whether(actual_output, cond, 2)
    #how(actual_output, cond, 2)
    #sufficient(cond, 2)
    #robust(actual_output, cond, 2)
    #print(collision_compare(actual_output, counterfactual))
    # difference maker cause
    diff_maker_balls = []
    for c in range(cond.num_balls):
        print('DM ', c)
        diff_maker_balls += [difference_maker(actual_output, cond, c)]
            
    # whether cause
    whether_balls = []
    for c in range(cond.num_balls):
        print('whether ', c)
        whether_balls+= [whether(actual_output, cond, c)]

    # how cause
    how_balls = []
    for c in range(cond.num_balls):
        print('how ', c)
        how_balls += [how(actual_output, cond, c)]
    
    # sufficient cause
    sufficient_balls = []
    for c in range(cond.num_balls):
        print('sufficient ', c)
        sufficient_balls += [sufficient(actual_output,cond, c)]

    #robust cause
    robust_balls = []
    for c in range(cond.num_balls):
        print('robust ', c)
        robust_balls += [robust(actual_output, cond, c)]
    
    #test
    print("DM ", diff_maker_balls, "\n")
    print("HOW ", diff_maker_balls, "\n")
    print("WHETHER ", diff_maker_balls, "\n")
    print("SUFFICIENT ", diff_maker_balls, "\n")
    print("ROBUST ", diff_maker_balls, "\n")
    return

def difference_maker(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, actual_data=actual_output, record=False, counterfactual=None, headless=False)
        outcomes.append((output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time']))
    return sum(outcomes)/float(n_simulations)
         
def whether(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, actual_data=actual_output,record=False, counterfactual=None, headless=False)
        outcomes.append(actual_output['hit']!= output['hit'])
    return sum(outcomes)/float(n_simulations)
    
def how(actual_output, cond, c):
    outcomes = []
    for _ in range(0, perturb_simulations):
        new_cond = change_ball(cond,c)
        output = run(new_cond, actual_data=actual_output, record=False, counterfactual=None, headless=False)
        outcomes.append((output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time']))
    return sum(outcomes)/float(n_simulations)

def sufficient(actual_output, cond, c):
    new_cond = remove_others(cond, c)
    outcomes = []
    for _ in range(0,n_simulations):
        output = run(new_cond, actual_data=actual_output, record=False, counterfactual=None, headless=False)
        # this is effectively the whether cause, comparing to all cause balls removed (always false)
        outcomes.append(output['hit'])
    return sum(outcomes)/float(n_simulations)

def robust(actual_output, cond, c):
    outcomes = []
    for _ in range(0,perturb_simulations):
        new_cond = change_others(cond,c)
        new_actual = run(new_cond, record=False, counterfactual=None, headless=False)
        output = run(new_cond, actual_data=new_actual, record=False, counterfactual=None, headless=False)
        # if goal still occurs when changing others
        outcomes.append(output['hit'] != new_actual['hit'])
    return sum(outcomes)/float(n_simulations)

def remove_ball(cond, c):
    new_cond = copy.deepcopy(cond)

    del new_cond.angles[c]
    del new_cond.y_positions[c]
    del new_cond.radians[c]
    del new_cond.jitter['x'][c]
    del new_cond.jitter['y'][c]
    del new_cond.ball_positions[c]
    new_cond.num_balls -= 1

    return new_cond

def remove_others(cond, c):
    new_cond = copy.deepcopy(cond)
    inds = list(range(cond.num_balls))
    inds.pop(c)
    inds = sorted(inds, reverse=True)
    for i in inds:
        del new_cond.angles[i]
        del new_cond.y_positions[i]
        del new_cond.radians[i]
        del new_cond.jitter['x'][i]
        del new_cond.jitter['y'][i]
        del new_cond.ball_positions[i]
    
    new_cond.num_balls = 1
    
    return new_cond

def change_ball(cond, c):
    new_cond = copy.deepcopy(cond)
    new_cond.jitter['x'][c] += gaussian_noise(1)*perturb
    new_cond.jitter['y'][c] += gaussian_noise(1)*perturb
    return new_cond

def change_others(cond, c):
    new_cond = copy.deepcopy(cond)
    for i in range(cond.num_balls):
        if i != c :
            new_cond.jitter['x'][i] += gaussian_noise(1)*perturb
            new_cond.jitter['y'][i] += gaussian_noise(1)*perturb
    return new_cond

#useless function 
def collision_compare(output, counterfactual):
    i = 0 
    j = 0
    noisy_steps = []
    #is this an off by 1 error?, does it run when i == len(output?)
    while i <= len(output['collisions']) and j <= len(counterfactual['collisions']):
        #need to make fool proof by comparing objects too
        if output['collisions'][i] == counterfactual['collisions'][j]:
            i += 1
            j += 1
        elif output['collisions'][i]['step'] < counterfactual['collisions'][j]['step']:
            noisy_steps.append(output['collisions'][i]['step'])
            i += 1
        else:
            noisy_steps.append(counterfactual['collisions'][j]['step'])
            j += 1
        if i == len(output['collisions']) - 1:
            noisy_steps.extend(item['step'] for item in counterfactual['collisions'][j+1:])
        if j == len(counterfactual['collisions']) - 1:
            noisy_steps.extend(item['step'] for item in output['collisions'][i+1:])
    return noisy_steps

if __name__ == '__main__':
    filename = 'collisions.json'
    with open(filename, 'r') as f:
        data = json.load(f)

    process_conditions(data)
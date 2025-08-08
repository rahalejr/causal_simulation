# noise values range from .1 to 2
# how many e's do we need to generate?
# Jitter problem - we should find each x and why based on jitter before running counterfactual
# How do they define cause(x)?
#   for C in balls
    #   difference_maker(C) = P(de'=/= de | S, remove(C))
    #   if difference_maker(C, cond) > 0
    #       whether_cause(C, cond) = P(e'=/= e | S, remove(C))
    #       how_cause(C, cond) = P(e' = e| S, change(C))
    #       
    #       create 2 new conditions: cond1 = remonve(not C) and cond2 = change(not C)
    #           sufficient_cause(C) = wether_cause(C, cond1)
    #           robust_cause(C) = wether_cause(C, cond2)

import os
import json
import copy
from simulation import run
from conditions import Condition


def process_conditions(conds_list):
    for i in conds_list:
        cond = Condition(i['angles'], i['preemption'], i['unambiguous'], i['jitter'])
        run_condition(cond)
    pass

def run_condition(cond):

    actual_output=run(cond, record=False, counterfactual=None, headless=False)
        
    # difference maker cause
    diff_maker_balls = []
    for c in range(cond.num_balls):
        diff_maker_balls += [difference_maker(actual_output, cond, c)]
            
    # whether cause
    whether_balls = []
    for c in range(cond.num_balls):
        whether_balls+= [whether(actual_output, cond, c)]

    # how cause
    how_balls = []
    for c in range(cond.num_balls):
        how_balls += [how(actual_output, cond, c)]
    
    # sufficient cause
    sufficient_balls = []
    for c in range(cond.num_balls):
        sufficient_balls += [sufficient(cond, c)]

    #robust cause
    robust_balls = []
    for c in range(cond.num_balls):
        robust_balls += [robust(actual_output, cond, c)]

    print("DM ", diff_maker_balls, "\n")
    print("HOW ", diff_maker_balls, "\n")
    print("WHETHER ", diff_maker_balls, "\n")
    print("SUFFICIENT ", diff_maker_balls, "\n")
    print("ROBUST ", diff_maker_balls, "\n")
    return


def difference_maker(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    output = run(new_cond, record=False, counterfactual=None, headless=False)
    if (output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time']):
        return True
    else:  
        return False
         
def whether(actual_output, cond, c):
    new_cond = remove_ball(cond,c)
    output = run(new_cond, record=False, counterfactual=None, headless=False)
    # if c prevents goal
    if actual_output['hit']:
        return False if output['hit'] else True
    # if c causes goal (shouldnt happen)
    else:
        return True if output['hit'] else False
    
def how(actual_output, cond, c):
    new_cond = change_ball(cond,c)
    output = run(new_cond, record=False, counterfactual=None, headless=False)
    if (output['final_pos'], output['sim_time']) != (actual_output['final_pos'] , actual_output['sim_time']):
        return True
    else:
        return False

def sufficient(cond, c):
    new_cond = remove_others(cond, c)
    output = run(new_cond, record=False, counterfactual=None, headless=False)
    # this is effectively the whether cause, comparing to all cause balls removed (always false)
    return True if output['hit'] else False

def robust(actual_output, cond, c):
    new_cond = change_others(cond,c)
    output = run(new_cond, record=False, counterfactual=None, headless=False)
    # if goal still occurs when changing others
    if actual_output['hit']:
        # robust if changing others still leads to hit
        return True if output['hit'] else False
    # if c causes goal (shouldnt happen)
    else:
        return False if output['hit'] else True


def remove_ball(cond, c):
    new_cond = copy.deepcopy(cond)

    del new_cond.angles[c]
    del new_cond.y_positions[c]
    del new_cond.radians[c]
    del new_cond.jitter['x'][c]
    del new_cond.jitter['y'][c]
    new_cond.num_balls -= 1

    return new_cond

def remove_others(cond, c):
    new_cond = copy.deepcopy(cond)

    del new_cond.angles[:c]
    del new_cond.angles[c+1:]
    del new_cond.y_positions[:c]
    del new_cond.y_positions[c+1:]
    del new_cond.radians[:c]
    del new_cond.radians[c+1:]
    del new_cond.jitter['x'][:c]
    del new_cond.jitter['y'][:c]
    del new_cond.jitter['x'][c+1:]
    del new_cond.jitter['y'][c+1:]
    new_cond.num_balls = 1
    
    return new_cond

# PLACEHOLDER
def change_ball(cond, c):
    new_cond = copy.deepcopy(cond)
    # placeholder value
    new_cond.angles[c] += 5
    return new_cond

# PLACEHOLDER
def change_others(cond, c):
    new_cond = copy.deepcopy(cond)
    for i in range(cond.num_balls):
        if i == c : continue
        else:
            new_cond.angles[c] += 5
    return new_cond

if __name__ == '__main__':
    filename = 'video_meta.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    
    process_conditions(data)
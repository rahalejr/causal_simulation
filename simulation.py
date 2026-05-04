from simulation_engine import (
    gaussian_noise,
    monte_carlo_goal_probability,
    run_detailed,
    run_from_snapshot_detailed,
)


def run(
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
    return run_detailed(
        condition=condition,
        pause=pause,
        actual_data=actual_data,
        noise=noise,
        cause_color=cause_color,
        cause_ball=cause_ball,
        record=record,
        counterfactual=counterfactual,
        headless=headless,
        clip_num=clip_num,
        is_cf=is_cf,
        max_time=max_time,
    )


def run_from_snapshot(
    snapshot,
    noise=6,
    target_slots=None,
    include_effect=False,
    record=False,
    headless=True,
    filename=None,
    max_time=6.0,
):
    return run_from_snapshot_detailed(
        snapshot=snapshot,
        noise=noise,
        target_slots=target_slots,
        include_effect=include_effect,
        record=record,
        headless=headless,
        filename=filename,
        max_time=max_time,
    )


if __name__ == "__main__":
    pass

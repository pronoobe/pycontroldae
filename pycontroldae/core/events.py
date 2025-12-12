"""
Event Classes for pycontroldae

Provides event handling capabilities for simulations:
- TimeEvent: Trigger callbacks at specific time points (PresetTimeCallback)
- ContinuousEvent: Trigger callbacks when a condition is met (ContinuousCallback)

Events allow dynamic modification of simulation parameters during execution.
"""

from typing import Callable, Optional, Any, Dict
import inspect


class TimeEvent:
    """
    Time-based event that triggers at a specific time point.

    Maps to Julia's PresetTimeCallback, which executes a callback function
    at predetermined time points during the simulation.

    The callback function can modify integrator parameters, allowing dynamic
    system behavior changes during simulation.

    Parameters:
        time: The time point at which to trigger the event
        callback: Python function that modifies parameters
                  Signature: callback(integrator) -> Dict[str, float]
                  Should return a dictionary of parameter changes

    Example:
        >>> def change_gain(integrator):
        ...     return {"controller.Kp": 5.0}  # Change proportional gain
        >>>
        >>> event = TimeEvent(time=2.0, callback=change_gain)
        >>> system.add_event(event)
    """

    def __init__(self, time: float, callback: Callable[[Any], Dict[str, float]]):
        """
        Initialize a TimeEvent.

        Args:
            time: Time point at which to trigger the event
            callback: Function that returns parameter changes
                     Takes integrator as argument, returns dict {param_name: new_value}
        """
        if time < 0:
            raise ValueError(f"Event time must be non-negative, got {time}")

        self.time = time
        self.callback = callback

    def __repr__(self) -> str:
        return f"TimeEvent(time={self.time}, callback={self.callback.__name__})"


class ContinuousEvent:
    """
    Condition-based event that triggers when a condition crosses zero.

    Maps to Julia's ContinuousCallback, which uses root-finding to detect
    when a condition function crosses zero (changes sign).

    The condition function is evaluated continuously during integration.
    When it crosses zero, the affect function is called to modify parameters.

    Parameters:
        condition: Function that computes a scalar value
                   Signature: condition(u, t, integrator) -> float
                   Event triggers when this crosses zero
        affect: Function that modifies parameters when event triggers
                Signature: affect(integrator) -> Dict[str, float]
                Should return a dictionary of parameter changes
        direction: Which zero-crossing to detect:
                   0 = both directions (default)
                   +1 = only positive-going (- to +)
                   -1 = only negative-going (+ to -)

    Example:
        >>> # Trigger when state x1 crosses 1.0
        >>> def check_threshold(u, t, integrator):
        ...     return u[0] - 1.0  # u[0] is first state
        >>>
        >>> def saturate_input(integrator):
        ...     return {"plant.input_limit": 0.5}
        >>>
        >>> event = ContinuousEvent(
        ...     condition=check_threshold,
        ...     affect=saturate_input,
        ...     direction=1  # Only trigger on upward crossing
        ... )
        >>> system.add_event(event)
    """

    def __init__(
        self,
        condition: Callable[[Any, float, Any], float],
        affect: Callable[[Any], Dict[str, float]],
        direction: int = 0
    ):
        """
        Initialize a ContinuousEvent.

        Args:
            condition: Function (u, t, integrator) -> float
                      Event triggers when return value crosses zero
            affect: Function (integrator) -> dict
                   Returns parameter changes when event triggers
            direction: Zero-crossing direction to detect:
                      0 = both, +1 = positive-going, -1 = negative-going
        """
        if direction not in [-1, 0, 1]:
            raise ValueError(f"direction must be -1, 0, or 1, got {direction}")

        self.condition = condition
        self.affect = affect
        self.direction = direction

        # Validate function signatures
        condition_sig = inspect.signature(condition)
        if len(condition_sig.parameters) != 3:
            raise ValueError(
                f"condition function must take 3 arguments (u, t, integrator), "
                f"got {len(condition_sig.parameters)}"
            )

        affect_sig = inspect.signature(affect)
        if len(affect_sig.parameters) != 1:
            raise ValueError(
                f"affect function must take 1 argument (integrator), "
                f"got {len(affect_sig.parameters)}"
            )

    def __repr__(self) -> str:
        dir_str = {-1: "negative", 0: "both", 1: "positive"}[self.direction]
        return (
            f"ContinuousEvent(condition={self.condition.__name__}, "
            f"affect={self.affect.__name__}, direction={dir_str})"
        )


# Convenience functions for creating events

def at_time(time: float, callback: Callable[[Any], Dict[str, float]]) -> TimeEvent:
    """
    Create a time-based event.

    Convenience function for creating TimeEvent objects.

    Args:
        time: Time point at which to trigger
        callback: Function returning parameter changes

    Returns:
        TimeEvent instance

    Example:
        >>> def increase_gain(integrator):
        ...     return {"pid.Kp": 3.0, "pid.Ki": 1.0}
        >>>
        >>> event = at_time(5.0, increase_gain)
        >>> system.add_event(event)
    """
    return TimeEvent(time, callback)


def when_condition(
    condition: Callable[[Any, float, Any], float],
    affect: Callable[[Any], Dict[str, float]],
    direction: int = 0
) -> ContinuousEvent:
    """
    Create a condition-based event.

    Convenience function for creating ContinuousEvent objects.

    Args:
        condition: Function (u, t, integrator) -> float
        affect: Function (integrator) -> dict
        direction: Zero-crossing direction (-1, 0, or 1)

    Returns:
        ContinuousEvent instance

    Example:
        >>> def check_position(u, t, integrator):
        ...     return u[0] - 10.0  # Trigger when position > 10
        >>>
        >>> def apply_brake(integrator):
        ...     return {"vehicle.brake_force": 100.0}
        >>>
        >>> event = when_condition(check_position, apply_brake, direction=1)
        >>> system.add_event(event)
    """
    return ContinuousEvent(condition, affect, direction)

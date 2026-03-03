import math

def expTime(rng, rate):
    if rate <= 0:
        raise ValueError("Rate must be positive")
    rand = rng.random()
    return -math.log(1.0 - rand) / rate

def travelTime(rng):
    return max(1.0, 10.0 + rng.uniform(-1.0, 1.0))
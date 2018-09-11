import time
import simpy
import sys

def example(env):
    n=1
    while(n<5):

        start = time.perf_counter()
        yield env.timeout(3)
        end = time.perf_counter()
        print('Duration of one simulation time unit: %.2fs' % (end - start))
        sys.stdout.flush()
        n+=1

env = simpy.Environment()
proc = env.process(example(env))
env.run(until=proc)

import simpy.rt
env = simpy.rt.RealtimeEnvironment(factor=1, strict=False)
proc = env.process(example(env))
env.run(until=proc)

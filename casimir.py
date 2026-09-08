import operator
import math
import random
import numpy as np
from deap import algorithms, base, creator, tools, gp

# 1. Define Primitive Set and Terminals
# Mapping radix values and infrastructure parameters
pset = gp.PrimitiveSet("MAIN", 2)
pset.renameArguments(ARG0="radix_base", ARG1="latency_baseline")

pset.addPrimitive(operator.add, 2)
pset.addPrimitive(operator.sub, 2)
pset.addPrimitive(operator.mul, 2)

def safe_div(left, right):
    return left / right if abs(right) > 1e-6 else 1.0
pset.addPrimitive(safe_div, 2)

# 2. Define Multi-Objective Fitness (Minimize Latency Error, Minimize Casimir Contention)
# Weights are negative because we are minimizing both parameters
creator.create("FitnessMin", base.Fitness, weights=(-1.0, -1.0))
creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMin)

toolbox = base.Toolbox()
toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=1, max_=4)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("compile", gp.compile, pset=pset)

def evaluate_with_casimir_constraint(individual, data_points):
    """
    Evaluates individual fitness while treating the SU(1,1) Casimir 
    eigenvalue as an active geometric constraint boundary condition.
    """
    func = toolbox.compile(expr=individual)
    sq_errors = []
    
    # Trace values representing the Lie Algebra generators K0, K1, K2
    # derived dynamically from the individual expression's outputs
    for radix, baseline in data_points:
        try:
            predicted_overhead = func(radix, baseline)
            
            # Formulating generator matrix representations under SU(1, 1)
            k0 = predicted_overhead * 0.5
            k1 = math.sin(radix) * 1.5
            k2 = math.cos(baseline) * 1.5
            
            # Active Structural Constraint: Casimir Operator Eigenvalue
            # C = K0^2 - K1^2 - K2^2
            casimir_eigenvalue = (k0**2) - (k1**2) - (k2**2)
            
            # If the evolved program generates an illegal hyperbolic orbit
            # (Casimir out of physical system boundaries), we apply a constraint penalty
            if casimir_eigenvalue < 0 or casimir_eigenvalue > 50.0:
                casimir_penalty = 1000.0
            else:
                casimir_penalty = abs(casimir_eigenvalue - 1.0) # Targeting stable unitary path
                
            error = abs(predicted_overhead - (baseline + (radix * 0.45)))
            sq_errors.append((error, casimir_penalty))
            
        except (ValueError, OverflowError, ZeroDivisionError):
            return 10000.0, 10000.0

    mean_err = np.mean([e[0] for e in sq_errors])
    mean_casimir = np.mean([e[1] for e in sq_errors])
    return mean_err, mean_casimir

# Generate empirical baseline datasets for Monte Carlo evaluations
sample_data = [(b, 15.0 + random.random()*4.0) for b in range(2, 17)]

toolbox.register("evaluate", evaluate_with_casimir_constraint, data_points=sample_data)
toolbox.register("select", tools.selNSGA2) # Non-dominated Sorting Genetic Algorithm II
toolbox.register("mate", gp.cxOnePoint)
toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

if __name__ == "__main__":
    random.seed(101)
    pop = toolbox.population(n=50)
    hof = tools.HallOfFame(1)
    
    print("🧬 Initiating Pareto-optimal structural optimization pipeline...")
    algorithms.eaSimple(pop, toolbox, cxpb=0.7, mutpb=0.2, ngen=10, 
                        verbose=True, halloffame=hof)
    
    print("\n🏆 Evolution Breakthrough Model Formula:")
    print(hof[0])

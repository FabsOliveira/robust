from gurobipy import *
import numpy as np

from common_data import scenarios, nodes, units, lines, existing_units, existing_lines, \
	candidate_units, candidate_lines, G_max, F_max, F_min, incidence, weights, C_g


# problem-specific data: generation and investment costs
C_x = {unit: 1. for unit in candidate_units}
C_y = {line: 1. for line in candidate_lines}


def get_investment_cost(x, y):
	return sum(C_x[u]*x[u] for u in candidate_units) + sum(C_y[l]*y[l] for l in candidate_lines)


def add_primal_variables(iteration):
	# add generation variables for existing and candidate units
	g = m.addVars(units, scenarios, [iteration], name='generation', lb=0., ub=G_max)

	# flow variables for existing and candidate lines
	f = m.addVars(lines, scenarios, [iteration], name='flow', lb=F_min, ub=F_max)

	return g, f


# create the initial model - no constraints are added
m = Model("master_problem")

g, f = add_primal_variables(0) 	# primal variables for the initial model

# investment to a generation unit and transmission line
x = m.addVars(candidate_units, vtype=GRB.BINARY, name='unit_investment')
y = m.addVars(candidate_lines, vtype=GRB.BINARY, name='line_investment')

# subproblem objective value
theta = m.addVar(name='theta')

# set objective. The optimal solution is no investment
m.setObjective(get_investment_cost(x, y) + theta, GRB.MINIMIZE)


def augment_master_problem(current_iteration, d):
	# augment the master problem for the current iteration
	v = current_iteration

	# create additional primal variables indexed with the current iteration
	g, f = add_primal_variables(v)

	# minimum value for the subproblem objective function
	m.addConstr(theta - sum(sum(C_g[u]*g[u, o, v] for u in units) * weights[o]
	 			for o in scenarios) >= 0., name='minimum_subproblem_objective')

	# balance equation. Note that d[n, v] is input data from the subproblem
	m.addConstrs((g[n, o, v] + sum(incidence[l, n]*f[l, o, v] for l in lines) == d[n, v]
				 for n in nodes for o in scenarios), name='balance')

	# generation constraint for the candidate units
	m.addConstrs((g[u, o, v] <= G_max[u, o]*x[u] for u in candidate_units for o in scenarios),
	 			 name='maximum_candidate_generation')

	# flow constraint for the candidate lines
	m.addConstrs((f[l, o, v] <= F_max[l, o]*y[l] for l in candidate_lines for o in scenarios),
	 			 name='maximum_candidate_flow')

	m.addConstrs((f[l, o, v] >= F_min[l, o]*y[l] for l in candidate_lines for o in scenarios),
	 			 name='minimum_candidate_flow')


master_problem = m

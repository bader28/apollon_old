#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""apollon defaut definitions"""

# Time stamp format
time_stamp_fmt = '%Y-%m-%d %H:%M:%S'

# possible guessing methods for the inital Poisson means
lambda_guess_methods = ['quantile', 'linear']

# standard plot styles
class plot_params:
		signal = {'linewidth':1,
				  'linestyle':'solid',
				  'color':'k',
				  'alpha':.5,
				  'zorder':0}

		sig_ons = {'linewidth':2,
				  'linestyle':'solid',
				  'color':'C1',
				  'alpha':.9,
				  'zorder':0}

		onset = {'linewidth':3,
				 'linestyle':'dashed',
				 'color':'C1',
				 'alpha':.9,
				 'zorder':10}
